"""Independent TXT and CSV processing powered by modular inference."""
from pathlib import Path
from io import StringIO
from collections import Counter
import pandas as pd
from .config import MAX_FILE_SIZE
from .preprocessing import normalize_text, is_arabic_letter, is_latin_letter
from .inference import predict_long_text

# ============================================================
# 11. FILE UTILITIES
# ============================================================

def get_uploaded_file_bytes(uploaded_file):

    if uploaded_file is None:
        return b""


    if isinstance(
        uploaded_file,
        bytes,
    ):

        return uploaded_file


    if isinstance(
        uploaded_file,
        bytearray,
    ):

        return bytes(
            uploaded_file
        )


    if hasattr(
        uploaded_file,
        "getvalue",
    ):

        return uploaded_file.getvalue()


    if hasattr(
        uploaded_file,
        "read",
    ):

        position = None


        if hasattr(
            uploaded_file,
            "tell",
        ):

            try:
                position = uploaded_file.tell()
            except Exception:
                pass


        data = uploaded_file.read()


        if (
            position is not None
            and
            hasattr(
                uploaded_file,
                "seek",
            )
        ):

            try:
                uploaded_file.seek(
                    position
                )
            except Exception:
                pass


        return data


    raise TypeError(
        "Format file tidak didukung."
    )


def decode_text_bytes(data):

    for encoding in [
        "utf-8-sig",
        "utf-8",
        "utf-16",
        "cp1256",
    ]:

        try:

            return {
                "success":
                    True,

                "text":
                    data.decode(
                        encoding
                    ),

                "encoding":
                    encoding,

                "message": (
                    f"File berhasil dibaca "
                    f"dengan encoding "
                    f"{encoding}."
                ),
            }

        except UnicodeDecodeError:
            continue


    return {
        "success":
            False,

        "text":
            "",

        "encoding":
            None,

        "message": (
            "Encoding file tidak dikenali. "
            "Gunakan UTF-8 jika memungkinkan."
        ),
    }


def classify_text_unit(text):

    text = normalize_text(
        text
    )


    if not text.strip():
        return "kosong"


    has_arabic = any(
        is_arabic_letter(
            char
        )
        for char in text
    )


    has_latin = any(
        is_latin_letter(
            char
        )
        for char in text
    )


    if has_arabic and has_latin:
        return "campuran"


    if has_arabic:
        return "arab"


    return "non_arab"


def process_text_unit(text):

    normalized = normalize_text(
        text
    )


    category = classify_text_unit(
        normalized
    )


    if category == "kosong":

        return {
            "success":
                True,
            "status":
                "kosong",
            "input":
                normalized,
            "prediction":
                normalized,
            "note":
                "Teks kosong dipertahankan.",
            "unknown_characters":
                [],
        }


    if category == "non_arab":

        return {
            "success":
                True,
            "status":
                "non_arab",
            "input":
                normalized,
            "prediction":
                normalized,
            "note": (
                "Tidak mengandung huruf Arab; "
                "teks dipertahankan."
            ),
            "unknown_characters":
                [],
        }


    if category == "campuran":

        return {
            "success":
                True,
            "status":
                "campuran",
            "input":
                normalized,
            "prediction":
                normalized,
            "note": (
                "Teks mengandung campuran "
                "huruf Arab dan Latin; "
                "dipertahankan tanpa prediksi."
            ),
            "unknown_characters":
                [],
        }


    result = predict_long_text(
        normalized
    )


    if not result[
        "success"
    ]:

        return {
            "success":
                False,
            "status":
                "gagal",
            "input":
                normalized,
            "prediction":
                normalized,
            "note":
                result[
                    "message"
                ],
            "unknown_characters":
                [],
        }


    note = (
        "Diakritisasi berhasil."
    )


    if result[
        "had_diacritics"
    ]:

        note = (
            "Harakat lama dihapus "
            "dan teks diprediksi ulang."
        )


    return {
        "success":
            True,

        "status":
            "berhasil",

        "input":
            normalized,

        "prediction":
            result[
                "prediction"
            ],

        "note":
            note,

        "unknown_characters":
            result[
                "unknown_characters"
            ],
    }


def split_line_ending(line):

    if line.endswith(
        "\r\n"
    ):
        return (
            line[:-2],
            "\r\n",
        )


    if line.endswith(
        "\n"
    ):
        return (
            line[:-1],
            "\n",
        )


    if line.endswith(
        "\r"
    ):
        return (
            line[:-1],
            "\r",
        )


    return (
        line,
        "",
    )


# ============================================================
# 12. TXT
# ============================================================

def process_txt_bytes(
    data,
    filename="input.txt",
    progress_callback=None,
):

    decoded = decode_text_bytes(
        data
    )


    if not decoded[
        "success"
    ]:

        return {
            "success":
                False,

            "message":
                decoded[
                    "message"
                ],
        }


    text = decoded[
        "text"
    ]


    lines = text.splitlines(
        keepends=True
    )


    if (
        not lines
        and
        text
    ):

        lines = [
            text
        ]


    output_parts = []
    statuses = []
    warnings = []
    unknown_characters = []

    total_lines = len(
        lines
    )


    for index, raw_line in enumerate(
        lines,
        start=1,
    ):

        content, line_ending = (
            split_line_ending(
                raw_line
            )
        )


        result = process_text_unit(
            content
        )


        output_parts.append(
            result[
                "prediction"
            ]
            +
            line_ending
        )


        statuses.append(
            result[
                "status"
            ]
        )


        for char in result.get(
            "unknown_characters",
            [],
        ):

            if (
                char
                not in
                unknown_characters
            ):

                unknown_characters.append(
                    char
                )


        if (
            result[
                "status"
            ]
            ==
            "campuran"
        ):

            warnings.append({
                "line":
                    index,

                "note":
                    result[
                        "note"
                    ],
            })


        if progress_callback is not None:

            progress_callback(
                index,
                total_lines,
            )


    prediction = "".join(
        output_parts
    )


    output_filename = (
        f"{Path(filename).stem}"
        "_hasil_diakritisasi.txt"
    )


    return {
        "success":
            True,

        "message":
            "File TXT berhasil diproses.",

        "input_type":
            "txt",

        "encoding":
            decoded[
                "encoding"
            ],

        "prediction":
            prediction,

        "status_summary":
            dict(
                Counter(
                    statuses
                )
            ),

        "warnings":
            warnings,

        "unknown_characters":
            unknown_characters,

        "output_filename":
            output_filename,

        "download_bytes":
            prediction.encode(
                "utf-8"
            ),
    }


# ============================================================
# 13. CSV
# ============================================================

def read_csv_bytes(data):

    decoded = decode_text_bytes(
        data
    )


    if not decoded[
        "success"
    ]:

        return {
            "success":
                False,

            "message":
                decoded[
                    "message"
                ],
        }


    try:

        dataframe = pd.read_csv(
            StringIO(
                decoded[
                    "text"
                ]
            ),

            sep=None,
            engine="python",
            dtype=str,
            keep_default_na=False,
        )

    except Exception as error:

        return {
            "success":
                False,

            "message": (
                "CSV tidak dapat dibaca: "
                f"{error}"
            ),
        }


    return {
        "success":
            True,

        "message":
            "CSV berhasil dibaca.",

        "dataframe":
            dataframe,

        "encoding":
            decoded[
                "encoding"
            ],
    }


def read_csv_file(uploaded_file):

    data = get_uploaded_file_bytes(
        uploaded_file
    )


    if not data:

        return {
            "success":
                False,

            "message":
                "File kosong.",
        }


    if len(
        data
    ) > MAX_FILE_SIZE:

        return {
            "success":
                False,

            "message":
                "Ukuran file melebihi 5 MB.",
        }


    return read_csv_bytes(
        data
    )


def detect_arabic_columns(dataframe):

    results = []


    for column in dataframe.columns:

        values = dataframe[
            column
        ].astype(
            str
        )


        non_empty = 0
        arabic_rows = 0


        for value in values:

            if not value.strip():
                continue


            non_empty += 1


            if any(
                is_arabic_letter(
                    char
                )
                for char in value
            ):

                arabic_rows += 1


        ratio = (
            arabic_rows / non_empty
            if non_empty > 0
            else 0.0
        )


        if arabic_rows > 0:

            results.append({
                "column":
                    column,

                "arabic_rows":
                    arabic_rows,

                "non_empty_rows":
                    non_empty,

                "ratio":
                    ratio,
            })


    results.sort(
        key=lambda item:
            item[
                "ratio"
            ],

        reverse=True,
    )


    return results


def safe_column_name(
    dataframe,
    base_name,
):

    if (
        base_name
        not in
        dataframe.columns
    ):

        return base_name


    number = 2


    while (
        f"{base_name}_{number}"
        in dataframe.columns
    ):

        number += 1


    return (
        f"{base_name}_{number}"
    )


def process_csv_bytes(
    data,
    filename="input.csv",
    text_column=None,
    progress_callback=None,
):

    read_result = read_csv_bytes(
        data
    )


    if not read_result[
        "success"
    ]:

        return read_result


    dataframe = (
        read_result[
            "dataframe"
        ]
        .copy()
    )


    candidates = detect_arabic_columns(
        dataframe
    )


    if text_column is None:

        if not candidates:

            return {
                "success":
                    False,

                "message": (
                    "Tidak ditemukan kolom "
                    "yang mengandung teks Arab."
                ),
            }


        text_column = (
            candidates[
                0
            ][
                "column"
            ]
        )


    if (
        text_column
        not in
        dataframe.columns
    ):

        return {
            "success":
                False,

            "message": (
                f"Kolom '{text_column}' "
                "tidak ditemukan."
            ),
        }


    output_col = safe_column_name(
        dataframe,
        "hasil_diacritization",
    )

    status_col = safe_column_name(
        dataframe,
        "status_diacritization",
    )

    note_col = safe_column_name(
        dataframe,
        "catatan_diacritization",
    )


    predictions = []
    statuses = []
    notes = []
    unknown_characters = []


    total_rows = len(
        dataframe
    )


    for row_number, value in enumerate(
        dataframe[
            text_column
        ].astype(
            str
        ),
        start=1,
    ):

        result = process_text_unit(
            value
        )


        predictions.append(
            result[
                "prediction"
            ]
        )

        statuses.append(
            result[
                "status"
            ]
        )

        notes.append(
            result[
                "note"
            ]
        )


        for char in result.get(
            "unknown_characters",
            [],
        ):

            if (
                char
                not in
                unknown_characters
            ):

                unknown_characters.append(
                    char
                )


        if progress_callback is not None:

            progress_callback(
                row_number,
                total_rows,
            )


    dataframe[
        output_col
    ] = predictions

    dataframe[
        status_col
    ] = statuses

    dataframe[
        note_col
    ] = notes


    csv_text = dataframe.to_csv(
        index=False
    )


    return {
        "success":
            True,

        "message":
            "File CSV berhasil diproses.",

        "input_type":
            "csv",

        "text_column":
            text_column,

        "detected_columns":
            candidates,

        "dataframe":
            dataframe,

        "status_summary":
            dict(
                Counter(
                    statuses
                )
            ),

        "unknown_characters":
            unknown_characters,

        "output_columns": {
            "prediction":
                output_col,

            "status":
                status_col,

            "note":
                note_col,
        },

        "output_filename": (
            f"{Path(filename).stem}"
            "_hasil_diakritisasi.csv"
        ),

        "download_bytes":
            csv_text.encode(
                "utf-8-sig"
            ),
    }


# ============================================================
# 14. UNIVERSAL UPLOAD PROCESSOR
# ============================================================

def process_uploaded_file(
    uploaded_file,
    text_column=None,
    progress_callback=None,
):

    if uploaded_file is None:

        return {
            "success":
                False,

            "message":
                "File belum dipilih.",
        }


    filename = getattr(
        uploaded_file,
        "name",
        "uploaded_file",
    )


    data = get_uploaded_file_bytes(
        uploaded_file
    )


    if not data:

        return {
            "success":
                False,

            "message":
                "File kosong.",
        }


    if len(
        data
    ) > MAX_FILE_SIZE:

        return {
            "success":
                False,

            "message":
                "Ukuran file melebihi batas 5 MB.",
        }


    suffix = Path(
        filename
    ).suffix.lower()


    if suffix == ".txt":

        return process_txt_bytes(
            data,

            filename=
                filename,

            progress_callback=
                progress_callback,
        )


    if suffix == ".csv":

        return process_csv_bytes(
            data,

            filename=
                filename,

            text_column=
                text_column,

            progress_callback=
                progress_callback,
        )


    return {
        "success":
            False,

        "message": (
            "Format file tidak didukung. "
            "Gunakan TXT atau CSV."
        ),
    }


