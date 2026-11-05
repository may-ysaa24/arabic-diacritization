"""Synthetic train/resume equivalence checks; no research artifacts accessed."""
import importlib.util
from pathlib import Path

import pytest

torch = pytest.importorskip("torch")
path = Path(__file__).resolve().parents[1] / "scripts" / "synthetic_resume_replay.py"
spec = importlib.util.spec_from_file_location("synthetic_resume_replay", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_exact_synthetic_resume():
    result = module.audit()
    assert result["passed"]
    assert result["different_model_tensors_after_correct_resume"] == 0
    assert result["different_model_tensors_if_rng_not_restored"] > 0
    assert result["matching_epoch_history"]


def test_checkpoint_contains_required_replay_state():
    snapshot = module.train(interrupt_after=2)
    assert snapshot["epoch"] == 2
    assert len(snapshot["history"]) == 2
    for key in ("model_state_dict", "optimizer_state_dict", "train_generator_state",
                "python_rng_state", "numpy_rng_state", "torch_rng_state",
                "best_epoch", "patience_counter"):
        assert key in snapshot


def test_resume_starts_from_last_epoch_plus_one():
    snapshot = module.train(interrupt_after=3)
    result = module.train(saved=snapshot)
    assert [r[0] for r in result["history"]] == [1, 2, 3, 4, 5, 6]
