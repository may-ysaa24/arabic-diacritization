"""Tests for the read-only baseline resume auditor."""
import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / "scripts" / "check_resume_readiness.py"
spec = importlib.util.spec_from_file_location("resume_readiness", path)
resume = importlib.util.module_from_spec(spec)
spec.loader.exec_module(resume)

def fixture(losses):
    history = [{"epoch": i, "validation_loss": loss} for i, loss in enumerate(losses, 1)]
    best, best_epoch = float("inf"), 0
    for row in history:
        if row["validation_loss"] < best - 1e-4:
            best, best_epoch = row["validation_loss"], row["epoch"]
    cp = {"last_epoch": len(history), "best_epoch": best_epoch,
          "best_validation_loss": best, "history": history,
          "model_state_dict": {}, "optimizer_state_dict": {}}
    csv = [{"epoch": str(r["epoch"]), "validation_loss": str(r["validation_loss"])} for r in history]
    return cp, csv

class ResumeTests(unittest.TestCase):
    def test_early_stopped(self):
        cp, csv = fixture([.5, .4, .41, .42, .43, .44, .45])
        self.assertFalse(resume.audit_resume(cp, csv)["can_continue_as_same_experiment"])

    def test_interrupted_not_exact(self):
        cp, csv = fixture([.5, .4, .41])
        r = resume.audit_resume(cp, csv)
        self.assertTrue(r["can_continue_as_same_experiment"])
        self.assertFalse(r["exact_rng_replay_supported"])

    def test_duplicate_epoch(self):
        cp, csv = fixture([.5, .4, .41])
        csv[-1]["epoch"] = "2"
        with self.assertRaises(ValueError):
            resume.audit_resume(cp, csv)

    def test_mismatched_loss(self):
        cp, csv = fixture([.5, .4, .41])
        csv[-1]["validation_loss"] = ".3"
        with self.assertRaises(ValueError):
            resume.audit_resume(cp, csv)

    def test_wrong_best_epoch(self):
        cp, csv = fixture([.5, .4, .41])
        cp["best_epoch"] = 3
        with self.assertRaises(ValueError):
            resume.audit_resume(cp, csv)

    def test_history_checked(self):
        cp, csv = fixture([.4])
        self.assertEqual(resume.audit_resume(cp, csv)["checked_rows"], 1)
