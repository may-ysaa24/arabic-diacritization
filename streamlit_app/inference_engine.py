"""Compatibility entry point. Production uses independent modules, not reference."""
from arabic_diacritization.preprocessing import is_arabic_diacritic, remove_arabic_diacritics, is_arabic_letter, is_latin_letter, normalize_text, count_arabic_letters, find_latin_letters, contains_arabic_diacritics, validate_input
from arabic_diacritization.inference import predict_long_text, predict_single_chunk, split_long_text, label_to_diacritics, reconstruct_diacritized_text, health_check, get_model_info, get_metrics
from arabic_diacritization.file_processing import get_uploaded_file_bytes, decode_text_bytes, classify_text_unit, process_text_unit, split_line_ending, process_txt_bytes, read_csv_bytes, read_csv_file, detect_arabic_columns, safe_column_name, process_csv_bytes, process_uploaded_file
