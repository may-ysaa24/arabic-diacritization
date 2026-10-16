"""Configuration paths and maximum accepted file size."""
from pathlib import Path
import os

# ============================================================
# 1. PATH PROJECT
# ============================================================

APP_DIR = (
    Path(__file__)
    .resolve()
    .parent
)

DEFAULT_PROJECT_ROOT = (
    Path(__file__).resolve().parents[2]
)

PROJECT_ROOT = Path(
    os.environ.get(
        "BILSTM_CRF_PROJECT_ROOT",
        str(DEFAULT_PROJECT_ROOT),
    )
).resolve()


MODEL_PATH = (
    PROJECT_ROOT
    / "models"
    / "finetuned"
    / "best_finetuned_model.pt"
)

CONFIG_PATH = (
    PROJECT_ROOT
    / "models"
    / "finetuned"
    / "finetuning_config.json"
)

CHAR2ID_PATH = (
    PROJECT_ROOT
    / "mappings"
    / "char2id.json"
)

LABEL2ID_PATH = (
    PROJECT_ROOT
    / "mappings"
    / "label2id.json"
)

ID2LABEL_PATH = (
    PROJECT_ROOT
    / "mappings"
    / "id2label.json"
)

METRICS_PATH = (
    PROJECT_ROOT
    / "evaluation"
    / "comparison"
    / "metrics_comparison.json"
)


MAX_FILE_SIZE = (
    5 * 1024 * 1024
)


