"""File validation and spreadsheet export policy for the UI, not research inference."""

import csv
from io import StringIO
import re
import unicodedata


_TEXT_CONTROLS = frozenset("\t\r\n\u0085")  # HT, CR, LF, Unicode next-line.
_NEGATIVE_DECIMAL = re.compile(r"-(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?\Z")


def txt_control_error(text):
    """Validate decoded text without stripping controls or normalizing Arabic."""
    forbidden = sorted({ord(char) for char in text
                        if unicodedata.category(char) == "Cc" and char not in _TEXT_CONTROLS})
    if not forbidden:
        return None
    codes = ", ".join(f"U+{code:04X}" for code in forbidden[:8])
    if len(forbidden) > 8:
        codes += ", …"
    return (f"Berkas TXT mengandung karakter kontrol terlarang ({codes}). "
            "Tab, CR/LF, dan pemisah baris Unicode NEL diizinkan. "
            "Gunakan berkas teks yang valid; karakter tidak dihapus otomatis.")


def _spreadsheet_value(value):
    """Prefix risky strings with a literal tab; retain strict negative decimals."""
    if not isinstance(value, str) or not value or _NEGATIVE_DECIMAL.fullmatch(value):
        return value
    for char in value:
        category = unicodedata.category(char)
        # Ignore leading whitespace, controls, bidi/format chars and combining marks
        # for detection only. Preserve every original character in the exported value.
        if char.isspace() or category in {"Cc", "Cf"} or category.startswith("M"):
            continue
        if unicodedata.normalize("NFKC", char) in {"=", "+", "-", "@"}:
            return "\t" + value
        break
    return value


def spreadsheet_safe_csv(dataframe):
    """Export a copy of the representation, including headers, without mutating data.

    A quoted leading tab follows OWASP's Excel-oriented mitigation. It is part of
    the downloaded value; CSV importers and save/reopen behavior may differ.
    No formula wrappers are added. The backend's own CSV bytes remain untouched.
    """
    output = StringIO(newline="")
    writer = csv.writer(output, quoting=csv.QUOTE_ALL, lineterminator="\r\n")
    writer.writerow([_spreadsheet_value(value) for value in dataframe.columns])
    for row in dataframe.itertuples(index=False, name=None):
        writer.writerow([_spreadsheet_value(value) for value in row])
    return output.getvalue().encode("utf-8-sig")
