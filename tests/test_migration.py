"""Verify the migrated interfaces without asserting checkpoint availability."""

import json
import sys
from pathlib import Path

import pytest

pytest.importorskip("torch")
pytest.importorskip("torchcrf")

from arabic_diacritization import preprocessing, inference, model
from arabic_diacritization import _reference_engine as reference

ROOT = Path(__file__).resolve().parents[1]


def test_migrated_root():
    assert reference.PROJECT_ROOT == ROOT
    assert reference.CONFIG_PATH.is_file()
    assert reference.CHAR2ID_PATH.is_file()
    assert reference.LABEL2ID_PATH.is_file()


def test_preprocessing_contract():
    assert preprocessing.remove_arabic_diacritics("الْحَمْدُ") == "الحمد"
    assert preprocessing.validate_input("الحمد لله")["valid"]
    assert not preprocessing.validate_input("abc")["valid"]
    assert model.BiLSTMCRF is reference.BiLSTMCRF
    assert inference.predict_long_text is reference.predict_long_text


def test_mapping_and_metrics_provenance():
    chars = json.loads(reference.CHAR2ID_PATH.read_text(encoding="utf-8"))
    labels = json.loads(reference.LABEL2ID_PATH.read_text(encoding="utf-8"))
    audit = json.loads((ROOT / "evaluation/comparison/evaluation_audit.json").read_text(encoding="utf-8"))
    assert len(chars) == 55 and len(labels) == 15
    assert audit["evaluation_protocol"]["test_set_used_for_training"] is False


def test_legacy_streamlit_import_api():
    sys.path.insert(0, str(ROOT / "streamlit_app"))
    import inference_engine
    assert inference_engine.predict_long_text is inference.predict_long_text
    assert (ROOT / "streamlit_app/app.py").is_file()
    assert (ROOT / "streamlit_app/assets/logo_unimal.png").is_file()


@pytest.mark.skipif(
    not (ROOT / "models/finetuned/best_finetuned_model.pt").exists(),
    reason="Fine-tuned checkpoint not yet transferred; cannot validate inference output",
)
def test_checkpoint_inference_when_available():
    status = inference.health_check()
    assert status["success"], status.get("message")
    result = inference.predict_long_text("الحمد لله رب العالمين")
    assert result["success"], result.get("message")
    assert preprocessing.remove_arabic_diacritics(result["prediction"]) == result["clean_text"]
