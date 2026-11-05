"""Read-only audit of baseline final-checkpoint resume readiness.

Usage:
    python scripts/check_resume_readiness.py \
        --checkpoint /path/to/final_checkpoint.pt \
        --history /path/to/training_history.csv

Never writes training artifacts. Load checkpoints only from trusted sources.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence


RNG_KEYS = (
    "python_rng_state",
    "numpy_rng_state",
    "torch_rng_state",
    "torch_cuda_rng_state_all",
    "train_generator_state",
)


def read_history(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def audit_resume(
    checkpoint: Mapping[str, Any],
    history_csv: Sequence[Mapping[str, Any]],
    *,
    patience: int = 5,
    min_delta: float = 1e-4,
) -> dict[str, Any]:
    """Audit recorded training metadata, without running or saving a model."""
    if patience < 1 or min_delta < 0:
        raise ValueError("patience must be positive and min_delta nonnegative")

    required = (
        "last_epoch", "best_epoch", "best_validation_loss",
        "model_state_dict", "optimizer_state_dict", "history",
    )
    missing = [key for key in required if key not in checkpoint]
    if missing:
        raise ValueError(f"Checkpoint missing required keys: {missing}")

    internal_history = checkpoint["history"]
    if not isinstance(internal_history, list) or not internal_history:
        raise ValueError("Checkpoint history is empty or not a list")
    if len(internal_history) != len(history_csv):
        raise ValueError("Checkpoint and CSV history have different lengths")

    last_epoch = int(checkpoint["last_epoch"])
    if len(internal_history) != last_epoch:
        raise ValueError("Epoch count differs from checkpoint last_epoch")

    best_loss = math.inf
    best_epoch = 0
    epochs_without_improvement = 0
    for index, (record, csv_record) in enumerate(
        zip(internal_history, history_csv), start=1
    ):
        epoch = int(record["epoch"])
        if epoch != index or int(csv_record["epoch"]) != epoch:
            raise ValueError(f"Missing, reordered, or duplicated epoch at row {index}")
        val_loss = float(record["validation_loss"])
        csv_loss = float(csv_record["validation_loss"])
        if not math.isfinite(val_loss) or not math.isclose(
            val_loss, csv_loss, rel_tol=0.0, abs_tol=1e-10
        ):
            raise ValueError(f"Invalid or mismatched validation loss at epoch {epoch}")
        if val_loss < best_loss - min_delta:
            best_loss = val_loss
            best_epoch = epoch
            epochs_without_improvement = 0
        else:
            epochs_without_improvement += 1

    if best_epoch != int(checkpoint["best_epoch"]):
        raise ValueError("Best epoch is inconsistent with early-stopping rule")
    if not math.isclose(
        best_loss, float(checkpoint["best_validation_loss"]),
        rel_tol=0.0, abs_tol=1e-10,
    ):
        raise ValueError("Best validation loss inconsistent with checkpoint")

    rng_missing = [key for key in RNG_KEYS if key not in checkpoint]
    stopped = epochs_without_improvement >= patience
    reasons = []
    if stopped:
        reasons.append("Early stopping already reached; this run is complete.")
    if rng_missing:
        reasons.append("RNG/DataLoader state missing; exact deterministic continuation not available.")

    return {
        "last_epoch": last_epoch,
        "best_epoch": best_epoch,
        "best_validation_loss": best_loss,
        "epochs_without_improvement": epochs_without_improvement,
        "patience": patience,
        "next_epoch_if_interrupted": last_epoch + 1,
        "early_stopping_reached": stopped,
        "can_continue_as_same_experiment": not stopped,
        "exact_rng_replay_supported": not rng_missing,
        "rng_state_keys_missing": rng_missing,
        "reasons": reasons,
        "checked_rows": len(history_csv),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--history", type=Path, required=True)
    parser.add_argument("--patience", type=int, default=5)
    parser.add_argument("--min-delta", type=float, default=1e-4)
    args = parser.parse_args()

    import torch

    # Do not load checkpoints obtained from untrusted sources.
    checkpoint = torch.load(
        args.checkpoint, map_location="cpu", weights_only=True,
    )
    result = audit_resume(
        checkpoint, read_history(args.history),
        patience=args.patience, min_delta=args.min_delta,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
