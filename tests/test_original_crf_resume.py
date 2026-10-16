"""Synthetic resume check using the production BiLSTMCRF + pytorch-crf 0.7.2.

This test uses no Fathul Qorib/Tashkeela data, no research checkpoints,
and in-memory serialization. It does not retrain the thesis model.
"""
import io
import random
from copy import deepcopy

import numpy as np
import torch
from torch.utils.data import DataLoader

from arabic_diacritization.model import BiLSTMCRF

SEED = 24519
EPOCHS = 4


def _collate(samples):
    lengths = torch.tensor([len(x) for x, _ in samples], dtype=torch.long)
    width = int(lengths.max().item())
    x = torch.zeros((len(samples), width), dtype=torch.long)
    y = torch.zeros_like(x)
    mask = torch.zeros_like(x, dtype=torch.bool)
    for row, (tokens, labels) in enumerate(samples):
        n = len(tokens)
        x[row, :n] = torch.tensor(tokens, dtype=torch.long)
        y[row, :n] = torch.tensor(labels, dtype=torch.long)
        mask[row, :n] = True
    return x, y, mask, lengths


def _samples(start, count):
    rows = []
    for i in range(start, start + count):
        length = 3 + i % 3
        tokens = [1 + ((i * 7 + j * 3) % 14) for j in range(length)]
        labels = [((i + j * 2) % 5) for j in range(length)]
        rows.append((tokens, labels))
    return rows


def _make_training():
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    model = BiLSTMCRF(
        vocab_size=16,
        num_labels=5,
        embedding_dim=8,
        hidden_dim=16,
        num_layers=1,
        dropout=0.25,
        pad_idx=0,
    )
    optimizer = torch.optim.Adam(model.parameters(), lr=0.005)
    generator = torch.Generator().manual_seed(SEED + 2)
    train = DataLoader(
        _samples(0, 18), batch_size=3, shuffle=True,
        generator=generator, collate_fn=_collate, num_workers=0,
    )
    validation = DataLoader(
        _samples(100, 6), batch_size=3, shuffle=False,
        collate_fn=_collate, num_workers=0,
    )
    return model, optimizer, generator, train, validation


def _store(model, optimizer, generator, epoch, history, best_epoch, best_val, stale):
    np_state = np.random.get_state()
    return {
        "epoch": epoch,
        "model_state_dict": deepcopy(model.state_dict()),
        "optimizer_state_dict": deepcopy(optimizer.state_dict()),
        "generator_state": generator.get_state().clone(),
        "python_rng_state": random.getstate(),
        "numpy_rng_state": (
            np_state[0], np_state[1].tolist(), np_state[2], np_state[3], np_state[4]
        ),
        "torch_rng_state": torch.get_rng_state().clone(),
        "history": deepcopy(history),
        "best_epoch": best_epoch,
        "best_validation_loss": best_val,
        "patience_counter": stale,
    }


def _restore_random_state(checkpoint, generator):
    random.setstate(checkpoint["python_rng_state"])
    name, values, position, gauss, cached = checkpoint["numpy_rng_state"]
    np.random.set_state(
        (name, np.array(values, dtype=np.uint32), position, gauss, cached)
    )
    torch.set_rng_state(checkpoint["torch_rng_state"])
    generator.set_state(checkpoint["generator_state"])


def _train(*, stop_after=EPOCHS, resume=None, restore_rng=True):
    model, optimizer, generator, train_loader, validation_loader = _make_training()
    history, best_epoch, best_val, stale, start = [], 0, float("inf"), 0, 1
    if resume is not None:
        model.load_state_dict(resume["model_state_dict"])
        optimizer.load_state_dict(resume["optimizer_state_dict"])
        history = deepcopy(resume["history"])
        best_epoch = resume["best_epoch"]
        best_val = resume["best_validation_loss"]
        stale = resume["patience_counter"]
        start = resume["epoch"] + 1
        if restore_rng:
            _restore_random_state(resume, generator)

    for epoch in range(start, stop_after + 1):
        model.train()
        train_losses = []
        for x, y, mask, lengths in train_loader:
            optimizer.zero_grad(set_to_none=True)
            loss = model.loss(x, y, mask, lengths)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            train_losses.append(loss.item())
        model.eval()
        with torch.inference_mode():
            val_losses = [
                model.loss(x, y, mask, lengths).item()
                for x, y, mask, lengths in validation_loader
            ]
        val = sum(val_losses) / len(val_losses)
        history.append((epoch, sum(train_losses) / len(train_losses), val))
        if val < best_val - 1e-4:
            best_val, best_epoch, stale = val, epoch, 0
        else:
            stale += 1

    assert history
    return _store(
        model, optimizer, generator, stop_after, history,
        best_epoch, best_val, stale,
    )


def test_original_crf_resume_matches_uninterrupted_training():
    """Interrupted/continued training must match full training bit for bit."""
    uninterrupted = _train()
    paused = _train(stop_after=2)
    buf = io.BytesIO()
    torch.save(paused, buf)
    buf.seek(0)
    restored = torch.load(buf, map_location="cpu", weights_only=True)
    continued = _train(resume=restored)

    assert [r[0] for r in continued["history"]] == [1, 2, 3, 4]
    assert continued["history"] == uninterrupted["history"]
    assert continued["best_epoch"] == uninterrupted["best_epoch"]
    assert continued["patience_counter"] == uninterrupted["patience_counter"]
    assert all(
        torch.equal(weight, continued["model_state_dict"][name])
        for name, weight in uninterrupted["model_state_dict"].items()
    )

    # Negative control: omitting RNG restoration must be detected.
    no_rng_restore = _train(resume=restored, restore_rng=False)
    changed_tensors = sum(
        not torch.equal(weight, no_rng_restore["model_state_dict"][name])
        for name, weight in uninterrupted["model_state_dict"].items()
    )
    assert changed_tensors > 0


def test_original_crf_synthetic_decoding_keeps_valid_lengths():
    model, _, _, train_loader, _ = _make_training()
    model.eval()
    with torch.inference_mode():
        x, _, mask, lengths = next(iter(train_loader))
        decoded = model.decode(x, mask, lengths)
    assert [len(tags) for tags in decoded] == lengths.tolist()
