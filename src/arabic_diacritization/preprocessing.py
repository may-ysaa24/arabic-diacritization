"""Unchanged Arabic character and validation algorithms."""
import re
import unicodedata

def is_arabic_diacritic(char):

    if not char:
        return False


    if (
        unicodedata.category(
            char
        )
        !=
        "Mn"
    ):

        return False


    return (
        "ARABIC"
        in unicodedata.name(
            char,
            ""
        )
    )


def remove_arabic_diacritics(text):

    if text is None:
        return ""


    return "".join(
        char

        for char
        in str(text)

        if not is_arabic_diacritic(
            char
        )
    )


def is_arabic_letter(char):

    if not char:
        return False


    return (
        unicodedata.category(
            char
        ).startswith("L")

        and

        "ARABIC"
        in unicodedata.name(
            char,
            ""
        )
    )


def is_latin_letter(char):

    if not char:
        return False


    return (
        unicodedata.category(
            char
        ).startswith("L")

        and

        "LATIN"
        in unicodedata.name(
            char,
            ""
        )
    )


def normalize_text(text):

    if text is None:
        return ""

    text = unicodedata.normalize(
        "NFC",
        str(text),
    )

    # Samakan normalisasi inferensi dengan prapemrosesan data pelatihan.
    text = text.replace("ـ", "")
    text = text.replace("\u0670", "")
    text = re.sub(r"\s+", " ", text).strip()

    return text


def count_arabic_letters(text):

    return sum(
        1
        for char in text
        if is_arabic_letter(
            char
        )
    )


def find_latin_letters(text):

    return sorted(
        set(
            char

            for char
            in text

            if is_latin_letter(
                char
            )
        )
    )


def contains_arabic_diacritics(text):

    return any(
        is_arabic_diacritic(
            char
        )
        for char in text
    )


def validate_input(text):

    normalized = normalize_text(
        text
    )


    if not normalized.strip():

        return {
            "valid": False,
            "message":
                "Input masih kosong.",
            "normalized_text":
                normalized,
            "clean_text":
                "",
            "had_diacritics":
                False,
            "arabic_letters":
                0,
            "latin_letters":
                [],
        }


    latin_letters = find_latin_letters(
        normalized
    )


    if latin_letters:

        return {
            "valid": False,

            "message": (
                "Input manual mengandung "
                "huruf Latin. Masukkan teks "
                "Arab tanpa huruf Latin."
            ),

            "normalized_text":
                normalized,

            "clean_text":
                "",

            "had_diacritics":
                contains_arabic_diacritics(
                    normalized
                ),

            "arabic_letters":
                count_arabic_letters(
                    normalized
                ),

            "latin_letters":
                latin_letters,
        }


    arabic_letters = count_arabic_letters(
        normalized
    )


    if arabic_letters == 0:

        return {
            "valid": False,

            "message":
                "Tidak ditemukan huruf Arab "
                "pada input.",

            "normalized_text":
                normalized,

            "clean_text":
                "",

            "had_diacritics":
                False,

            "arabic_letters":
                0,

            "latin_letters":
                [],
        }


    had_diacritics = (
        contains_arabic_diacritics(
            normalized
        )
    )


    clean_text = (
        remove_arabic_diacritics(
            normalized
        )
    )


    clean_text = unicodedata.normalize(
        "NFC",
        clean_text,
    )


    return {
        "valid":
            True,

        "message":
            "Input valid.",

        "normalized_text":
            normalized,

        "clean_text":
            clean_text,

        "had_diacritics":
            had_diacritics,

        "arabic_letters":
            arabic_letters,

        "latin_letters":
            [],
    }



def split_long_text(text, max_len=None):
    """Compatibility facade for model-aware chunking."""
    from .inference import split_long_text as impl
    return impl(text, max_len=max_len)
