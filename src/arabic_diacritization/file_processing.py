"""TXT/CSV upload processing API, using the existing reference routines."""

from ._reference_engine import (
    get_uploaded_file_bytes,
    decode_text_bytes,
    classify_text_unit,
    process_text_unit,
    read_csv_bytes,
    read_csv_file,
    detect_arabic_columns,
    process_txt_bytes,
    process_csv_bytes,
    process_uploaded_file,
)

__all__ = ["get_uploaded_file_bytes", "decode_text_bytes", "classify_text_unit",
           "process_text_unit", "read_csv_bytes", "read_csv_file",
           "detect_arabic_columns", "process_txt_bytes", "process_csv_bytes",
           "process_uploaded_file"]
