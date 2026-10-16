"""Public inference API, delegating to the unmodified reference algorithms."""

from ._reference_engine import (
    health_check,
    get_model_info,
    predict_single_chunk,
    predict_long_text,
    reconstruct_diacritized_text,
    label_to_diacritics,
)

__all__ = ["health_check", "get_model_info", "predict_single_chunk",
           "predict_long_text", "reconstruct_diacritized_text", "label_to_diacritics"]
