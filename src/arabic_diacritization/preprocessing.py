"""Public preprocessing API, delegating to the original tested behavior."""

from ._reference_engine import (
    is_arabic_diacritic,
    is_arabic_letter,
    is_latin_letter,
    remove_arabic_diacritics,
    normalize_text,
    count_arabic_letters,
    find_latin_letters,
    contains_arabic_diacritics,
    validate_input,
    split_long_text,
)

__all__ = [
    "is_arabic_diacritic", "is_arabic_letter", "is_latin_letter",
    "remove_arabic_diacritics", "normalize_text", "count_arabic_letters",
    "find_latin_letters", "contains_arabic_diacritics", "validate_input",
    "split_long_text",
]
