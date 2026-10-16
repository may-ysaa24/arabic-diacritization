"""Isolated, synthetic PyTorch training resume replay with a tiny BiLSTM-CRF.

This script does NOT import real research data or checkpoints. It tests that
replaying from the last epoch, optimizer, early stopping and RNG states matches
uninterrupted training. Uses CPU + in-memory serialization only.

    python scripts/synthetic_resume_replay.py
"""
from __future__ import annotations

import io
import json
import random
from copy import deepcopy

import numpy as np
import torch
from torch import nn
from torch.nn.utils.rnn import pack_padded_sequence, pad_packed_sequence
from torch.utils.data import DataLoader, Dataset

SEED = 20261017


class SyntheticSequences(Dataset):
    """Fully generated tokens and labels; no Fathul Qorib or Tashkeela input."""

    def __init__(self, count: int, *, offset: int = 0):
        rng = np.random.default_rng(SEED + offset)
        self.examples = []
        for _ in range(count):
            length = int(rng.integers(3, 7))
            tokens = rng.integers(1, 18, size=length).tolist()
            tags = [(x * 3 + i) % 4 for i, x in enumerate(tokens)]
            self.examples.append((tokens, tags))

    def __len__(self):
        return len(self.examples)

    def __getitem__(self, i):
        return self.examples[i]


def collate(batch):
    lengths = torch.tensor([len(x) for x, _ in batch], dtype=torch.long)
    width = int(lengths.max())
    x = torch.zeros((len(batch), width), dtype=torch.long)
    y = torch.zeros_like(x)
    mask = torch.zeros((len(batch), width), dtype=torch.bool)
    for i, (tokens, labels) in enumerate(batch):
        n = len(tokens)
        x[i, :n] = torch.tensor(tokens)
        y[i, :n] = torch.tensor(labels)
        mask[i, :n] = True
    return x, y, mask, lengths


class TinyCRF(nn.Module):
    """Differentiable CRF negative log likelihood, for this synthetic test only.

    This is NOT the pytorch-crf package used by the published notebook.
    """

    def __init__(self, tags: int):
        super().__init__()
        self.start = nn.Parameter(torch.empty(tags).uniform_(-0.1, 0.1))
        self.end = nn.Parameter(torch.empty(tags).uniform_(-0.1, 0.1))
        self.transitions = nn.Parameter(torch.empty(tags, tags).uniform_(-0.1, 0.1))

    def forward(self, emissions, truth, mask):
        b, t, _ = emissions.shape
        rows = torch.arange(b)
        score = self.start[truth[:, 0]] + emissions[rows, 0, truth[:, 0]]
        alpha = self.start + emissions[:, 0]
        for i in range(1, t):
            next_tags = truth[:, i]
            score = score + (
                self.transitions[truth[:, i - 1], next_tags]
                + emissions[rows, i, next_tags]
            ) * mask[:, i]
            next_alpha = torch.logsumexp(
                alpha.unsqueeze(2) + self.transitions.unsqueeze(0)
                + emissions[:, i].unsqueeze(1), dim=1
            )
            alpha = torch.where(mask[:, i].unsqueeze(1), next_alpha, alpha)
        last = mask.long().sum(1) - 1
        score = score + self.end[truth[rows, last]]
        normalizer = torch.logsumexp(alpha + self.end, dim=1)
        return (normalizer - score).mean()


class TinyBiLSTMCRF(nn.Module):
    def __init__(self):
        super().__init__()
        self.embedding = nn.Embedding(18, 8, padding_idx=0)
        self.dropout = nn.Dropout(0.25)
        self.encoder = nn.LSTM(8, 8, batch_first=True, bidirectional=True)
        self.classifier = nn.Linear(16, 4)
        self.crf = TinyCRF(4)

    def forward(self, tokens, tags, mask, lengths):
        embeds = self.dropout(self.embedding(tokens))
        packed = pack_padded_sequence(
            embeds, lengths.cpu(), batch_first=True, enforce_sorted=False,
        )
        output, _ = self.encoder(packed)
        padded, _ = pad_packed_sequence(
            output, batch_first=True, total_length=tokens.shape[1],
        )
        logits = self.classifier(self.dropout(padded))
        return self.crf(logits, tags, mask)


def set_seed():
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)


def snapshot(model, optimizer, generator, epoch, history, best, best_epoch, patience_count):
    """Must be called after an epoch ends, before the next DataLoader iterator."""
    return {
        'epoch': epoch,
        'model_state_dict': deepcopy(model.state_dict()),
        'optimizer_state_dict': deepcopy(optimizer.state_dict()),
        'train_generator_state': generator.get_state().clone(),
        'python_rng_state': random.getstate(),
        'numpy_rng_state': (lambda state: (state[0], state[1].tolist(), state[2], state[3], state[4]))(np.random.get_state()),
        'torch_rng_state': torch.get_rng_state().clone(),
        'history': deepcopy(history),
        'best_loss': best,
        'best_epoch': best_epoch,
        'patience_counter': patience_count,
    }


def restore_rng(checkpoint, generator):
    random.setstate(checkpoint['python_rng_state'])
    name, state, position, gaussian, cached = checkpoint['numpy_rng_state']
    np.random.set_state((name, np.array(state, dtype=np.uint32), position, gaussian, cached))
    torch.set_rng_state(checkpoint['torch_rng_state'])
    generator.set_state(checkpoint['train_generator_state'])


def new_run():
    set_seed()
    model = TinyBiLSTMCRF()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.002)
    generator = torch.Generator().manual_seed(SEED + 7)
    training = DataLoader(SyntheticSequences(16), batch_size=4, shuffle=True,
                          collate_fn=collate, generator=generator, num_workers=0)
    validation = DataLoader(SyntheticSequences(8, offset=1), batch_size=4, shuffle=False,
                            collate_fn=collate, num_workers=0)
    return model, optimizer, generator, training, validation


def train(total_epochs=6, *, interrupt_after=None, saved=None, restore_random=True):
    model, optimizer, generator, training, validation = new_run()
    history, best, best_epoch, count, start = [], float('inf'), 0, 0, 1
    if saved is not None:
        model.load_state_dict(saved['model_state_dict'])
        optimizer.load_state_dict(saved['optimizer_state_dict'])
        history = deepcopy(saved['history'])
        best, best_epoch = saved['best_loss'], saved['best_epoch']
        count = saved['patience_counter']
        start = saved['epoch'] + 1
        if restore_random:
            restore_rng(saved, generator)

    for epoch in range(start, total_epochs + 1):
        if count >= 99:
            break
        model.train()
        losses = []
        for x, y, mask, lengths in training:
            optimizer.zero_grad(set_to_none=True)
            loss = model(x, y, mask, lengths)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            losses.append(loss.item())
        model.eval()
        with torch.no_grad():
            val = sum(model(x, y, mask, lens).item() for x, y, mask, lens in validation) / len(validation)
        history.append((epoch, float(sum(losses) / len(losses)), float(val)))
        if val < best - 1e-4:
            best, best_epoch, count = val, epoch, 0
        else:
            count += 1
        if interrupt_after == epoch:
            return snapshot(model, optimizer, generator, epoch, history, best, best_epoch, count)
    return snapshot(model, optimizer, generator, history[-1][0], history, best, best_epoch, count)


def diff_count(reference, comparison):
    return sum(int(not torch.equal(value, comparison['model_state_dict'][key]))
               for key, value in reference['model_state_dict'].items())


def audit():
    continuous = train()
    interrupted = train(interrupt_after=3)
    # In-memory torch serialization exercises real torch.save/torch.load mechanics.
    buffer = io.BytesIO()
    torch.save(interrupted, buffer)
    buffer.seek(0)
    restored = torch.load(buffer, map_location='cpu', weights_only=True)
    resumed = train(saved=restored)
    control_without_rng = train(saved=restored, restore_random=False)
    passed = (
        continuous['history'] == resumed['history']
        and continuous['epoch'] == resumed['epoch'] == 6
        and continuous['best_epoch'] == resumed['best_epoch']
        and continuous['patience_counter'] == resumed['patience_counter']
        and diff_count(continuous, resumed) == 0
        and diff_count(continuous, control_without_rng) > 0
    )
    return {
        'passed': passed,
        'platform': 'PyTorch CPU',
        'synthetic_dataset': True,
        'model': 'tiny BiLSTM + self-contained demonstration CRF',
        'uninterrupted_epochs': continuous['epoch'],
        'restart_from_epoch': 4,
        'matching_epoch_history': continuous['history'] == resumed['history'],
        'different_model_tensors_after_correct_resume': diff_count(continuous, resumed),
        'different_model_tensors_if_rng_not_restored': diff_count(continuous, control_without_rng),
        'checkpoint_written_to_disk': False,
        'research_checkpoint_used': False,
        'research_dataset_used': False,
        'limitations': 'Does not establish exact replay of historical training or pytorch-crf=0.7.2 behavior.',
    }


if __name__ == '__main__':
    result = audit()
    print(json.dumps(result, indent=2))
    if not result['passed']:
        raise SystemExit(1)
