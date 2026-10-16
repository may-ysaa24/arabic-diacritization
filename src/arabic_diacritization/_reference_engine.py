# ============================================================
# inference_engine.py
# Backend Sistem Diakritisasi Otomatis Teks Arab Gundul
# Model BiLSTM-CRF
# ============================================================

from pathlib import Path
from io import StringIO
from collections import Counter
import json
import os
import re
import unicodedata

import pandas as pd
import torch
import torch.nn as nn

from torch.nn.utils.rnn import (
    pack_padded_sequence,
    pad_packed_sequence,
)

from torchcrf import CRF


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


# ============================================================
# 2. GLOBAL BACKEND STATE
# ============================================================

_DEVICE = None
_MODEL = None
_CONFIG = None
_CHAR2ID = None
_LABEL2ID = None
_ID2LABEL = None
_METRICS = None
_MODEL_INFO = None


# ============================================================
# 3. JSON HELPER
# ============================================================

def _load_json(path):

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as file:

        return json.load(file)


# ============================================================
# 4. MODEL
# ============================================================

class BiLSTMCRF(nn.Module):

    def __init__(
        self,
        vocab_size,
        num_labels,
        embedding_dim,
        hidden_dim,
        num_layers,
        dropout,
        pad_idx,
    ):

        super().__init__()


        if hidden_dim % 2 != 0:

            raise ValueError(
                "hidden_dim BiLSTM harus genap."
            )


        hidden_per_direction = (
            hidden_dim // 2
        )


        self.embedding = nn.Embedding(
            num_embeddings=vocab_size,
            embedding_dim=embedding_dim,
            padding_idx=pad_idx,
        )


        self.embedding_dropout = nn.Dropout(
            dropout
        )


        self.bilstm = nn.LSTM(
            input_size=embedding_dim,
            hidden_size=hidden_per_direction,
            num_layers=num_layers,
            batch_first=True,
            bidirectional=True,
            dropout=(
                dropout
                if num_layers > 1
                else 0.0
            ),
        )


        self.output_dropout = nn.Dropout(
            dropout
        )


        self.classifier = nn.Linear(
            hidden_dim,
            num_labels,
        )


        self.crf = CRF(
            num_tags=num_labels,
            batch_first=True,
        )


    def forward(
        self,
        input_ids,
        lengths,
    ):

        embeddings = self.embedding(
            input_ids
        )


        embeddings = self.embedding_dropout(
            embeddings
        )


        packed = pack_padded_sequence(
            embeddings,
            lengths.cpu(),
            batch_first=True,
            enforce_sorted=False,
        )


        packed_output, _ = self.bilstm(
            packed
        )


        bilstm_output, _ = (
            pad_packed_sequence(
                packed_output,
                batch_first=True,
                total_length=
                    input_ids.size(1),
            )
        )


        bilstm_output = self.output_dropout(
            bilstm_output
        )


        return self.classifier(
            bilstm_output
        )


    def loss(
        self,
        input_ids,
        tags,
        mask,
        lengths,
    ):

        emissions = self.forward(
            input_ids,
            lengths,
        )


        log_likelihood = self.crf(
            emissions,
            tags,
            mask=mask,
            reduction="token_mean",
        )


        return -log_likelihood


    def decode(
        self,
        input_ids,
        mask,
        lengths,
    ):

        emissions = self.forward(
            input_ids,
            lengths,
        )


        return self.crf.decode(
            emissions,
            mask=mask,
        )


# ============================================================
# 5. LOAD BACKEND
# ============================================================

def _ensure_loaded():

    global _DEVICE
    global _MODEL
    global _CONFIG
    global _CHAR2ID
    global _LABEL2ID
    global _ID2LABEL
    global _METRICS
    global _MODEL_INFO


    if _MODEL is not None:

        return


    required_files = [
        MODEL_PATH,
        CONFIG_PATH,
        CHAR2ID_PATH,
        LABEL2ID_PATH,
        ID2LABEL_PATH,
        METRICS_PATH,
    ]


    missing = [
        str(path)
        for path in required_files
        if not path.exists()
    ]


    if missing:

        raise FileNotFoundError(
            "File backend tidak ditemukan:\n"
            +
            "\n".join(
                missing
            )
        )


    _DEVICE = torch.device(
        "cuda"
        if torch.cuda.is_available()
        else "cpu"
    )


    _CONFIG = _load_json(
        CONFIG_PATH
    )

    _CHAR2ID = _load_json(
        CHAR2ID_PATH
    )

    _LABEL2ID = _load_json(
        LABEL2ID_PATH
    )


    id2label_raw = _load_json(
        ID2LABEL_PATH
    )


    _ID2LABEL = {
        int(key): value
        for key, value
        in id2label_raw.items()
    }


    _METRICS = _load_json(
        METRICS_PATH
    )


    vocab_size = len(
        _CHAR2ID
    )

    num_labels = len(
        _LABEL2ID
    )


    pad_id = int(
        _CHAR2ID[
            "<PAD>"
        ]
    )


    checkpoint = torch.load(
        MODEL_PATH,
        map_location=_DEVICE,
        weights_only=True,
    )


    if (
        not isinstance(
            checkpoint,
            dict
        )
        or
        "model_state_dict"
        not in checkpoint
    ):

        raise RuntimeError(
            "Format checkpoint tidak valid."
        )


    state_dict = checkpoint[
        "model_state_dict"
    ]


    # Bersihkan prefix DataParallel bila ada.
    state_dict = {
        (
            key[len("module."):]
            if key.startswith("module.")
            else key
        ): value

        for key, value
        in state_dict.items()
    }


    model = BiLSTMCRF(
        vocab_size=vocab_size,

        num_labels=num_labels,

        embedding_dim=int(
            _CONFIG[
                "embedding_dimension"
            ]
        ),

        hidden_dim=int(
            _CONFIG[
                "hidden_dimension"
            ]
        ),

        num_layers=int(
            _CONFIG[
                "number_of_lstm_layers"
            ]
        ),

        dropout=float(
            _CONFIG[
                "dropout"
            ]
        ),

        pad_idx=pad_id,
    )


    model.load_state_dict(
        state_dict,
        strict=True,
    )


    model = model.to(
        _DEVICE
    )

    model.eval()


    _MODEL = model


    total_parameters = sum(
        parameter.numel()
        for parameter
        in model.parameters()
    )


    hidden_dimension = int(
        _CONFIG[
            "hidden_dimension"
        ]
    )


    _MODEL_INFO = {

        "device":
            str(_DEVICE),

        "vocab_size":
            vocab_size,

        "num_labels":
            num_labels,

        "embedding_dim":
            int(
                _CONFIG[
                    "embedding_dimension"
                ]
            ),

        "hidden_dim":
            hidden_dimension,

        "hidden_per_direction":
            hidden_dimension // 2,

        "num_layers":
            int(
                _CONFIG[
                    "number_of_lstm_layers"
                ]
            ),

        "dropout":
            float(
                _CONFIG[
                    "dropout"
                ]
            ),

        "max_len":
            int(
                _CONFIG[
                    "max_sequence_length"
                ]
            ),

        "total_parameters":
            total_parameters,

        "checkpoint_epoch":
            checkpoint.get(
                "epoch"
            ),

        "model_name":
            _CONFIG.get(
                "model_name",
                "BiLSTM-CRF",
            ),
    }


# ============================================================
# 6. PREPROCESSING
# ============================================================

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


# ============================================================
# 7. CHUNKING
# ============================================================

def split_long_text(
    text,
    max_len=None,
):

    _ensure_loaded()


    if max_len is None:

        max_len = int(
            _MODEL_INFO[
                "max_len"
            ]
        )


    text = normalize_text(
        text
    )


    if not text:

        return []


    if max_len <= 0:

        raise ValueError(
            "max_len harus lebih besar dari 0."
        )


    if len(text) <= max_len:

        return [
            text
        ]


    chunks = []

    start = 0
    text_length = len(
        text
    )


    while start < text_length:

        end = min(
            start + max_len,
            text_length,
        )


        if end == text_length:

            chunk = text[
                start:end
            ]


            if chunk:

                chunks.append(
                    chunk
                )


            break


        split_position = None


        for index in range(
            end - 1,
            start,
            -1,
        ):

            if text[
                index
            ].isspace():

                split_position = (
                    index + 1
                )

                break


        if split_position is None:

            split_position = end


        chunk = text[
            start:split_position
        ]


        if chunk:

            chunks.append(
                chunk
            )


        start = split_position


    return chunks


# ============================================================
# 8. RECONSTRUCTION
# ============================================================

def label_to_diacritics(label):

    if label == "O":
        return ""


    return "".join(
        part

        for part
        in label.split("|")

        if part
    )


def reconstruct_diacritized_text(
    clean_text,
    predicted_label_ids,
):

    _ensure_loaded()


    if len(
        clean_text
    ) != len(
        predicted_label_ids
    ):

        raise ValueError(
            "Panjang teks dan label prediksi berbeda."
        )


    output = []


    for char, label_id in zip(
        clean_text,
        predicted_label_ids,
    ):

        label_id = int(
            label_id
        )


        if label_id not in _ID2LABEL:

            raise KeyError(
                f"ID label tidak dikenal: "
                f"{label_id}"
            )


        output.append(
            char
        )


        if is_arabic_letter(
            char
        ):

            diacritics = (
                label_to_diacritics(
                    _ID2LABEL[
                        label_id
                    ]
                )
            )


            if diacritics:

                output.append(
                    diacritics
                )


    return unicodedata.normalize(
        "NFC",
        "".join(
            output
        ),
    )


# ============================================================
# 9. INFERENCE SINGLE CHUNK
# ============================================================

def predict_single_chunk(text):

    _ensure_loaded()


    normalized = normalize_text(
        text
    )


    if not normalized:

        return {
            "success": False,
            "message": "Chunk kosong.",
            "input_text": "",
            "clean_text": "",
            "prediction": "",
            "predicted_label_ids": [],
            "predicted_labels": [],
            "unknown_characters": [],
            "length": 0,
        }


    clean_text = (
        remove_arabic_diacritics(
            normalized
        )
    )


    clean_text = unicodedata.normalize(
        "NFC",
        clean_text,
    )


    if not clean_text:

        return {
            "success": False,
            "message":
                "Tidak ada karakter yang "
                "dapat diproses.",
            "input_text":
                normalized,
            "clean_text":
                "",
            "prediction":
                "",
            "predicted_label_ids":
                [],
            "predicted_labels":
                [],
            "unknown_characters":
                [],
            "length":
                0,
        }


    max_len = int(
        _MODEL_INFO[
            "max_len"
        ]
    )


    if len(
        clean_text
    ) > max_len:

        raise ValueError(
            f"Chunk terlalu panjang: "
            f"{len(clean_text)} karakter. "
            f"Maksimum {max_len}."
        )


    unk_id = int(
        _CHAR2ID[
            "<UNK>"
        ]
    )


    input_ids = []
    unknown_characters = []


    for char in clean_text:

        if char in _CHAR2ID:

            char_id = _CHAR2ID[
                char
            ]

        else:

            char_id = unk_id


            if (
                char
                not in
                unknown_characters
            ):

                unknown_characters.append(
                    char
                )


        input_ids.append(
            char_id
        )


    input_tensor = torch.tensor(
        [
            input_ids
        ],
        dtype=torch.long,
        device=_DEVICE,
    )


    lengths = torch.tensor(
        [
            len(
                input_ids
            )
        ],
        dtype=torch.long,
    )


    mask = torch.ones(
        (
            1,
            len(
                input_ids
            ),
        ),
        dtype=torch.bool,
        device=_DEVICE,
    )


    _MODEL.eval()


    with torch.inference_mode():

        decoded = _MODEL.decode(
            input_tensor,
            mask,
            lengths,
        )


    if len(
        decoded
    ) != 1:

        raise RuntimeError(
            "CRF menghasilkan jumlah "
            "sequence tidak sesuai."
        )


    predicted_label_ids = (
        decoded[
            0
        ]
    )


    if len(
        predicted_label_ids
    ) != len(
        clean_text
    ):

        raise RuntimeError(
            "Jumlah label tidak sama "
            "dengan panjang input."
        )


    predicted_labels = [
        _ID2LABEL[
            int(label_id)
        ]

        for label_id
        in predicted_label_ids
    ]


    prediction = (
        reconstruct_diacritized_text(
            clean_text,
            predicted_label_ids,
        )
    )


    return {
        "success":
            True,

        "message":
            "Inference berhasil.",

        "input_text":
            normalized,

        "clean_text":
            clean_text,

        "prediction":
            prediction,

        "predicted_label_ids":
            predicted_label_ids,

        "predicted_labels":
            predicted_labels,

        "unknown_characters":
            unknown_characters,

        "length":
            len(
                clean_text
            ),
    }


# ============================================================
# 10. INFERENCE LONG TEXT
# ============================================================

def predict_long_text(
    text,
    progress_callback=None,
):

    _ensure_loaded()


    validation = validate_input(
        text
    )


    if not validation[
        "valid"
    ]:

        return {
            "success":
                False,

            "message":
                validation[
                    "message"
                ],

            "input_text":
                validation[
                    "normalized_text"
                ],

            "clean_text":
                validation[
                    "clean_text"
                ],

            "prediction":
                "",

            "had_diacritics":
                validation[
                    "had_diacritics"
                ],

            "arabic_letters":
                validation[
                    "arabic_letters"
                ],

            "total_characters":
                0,

            "total_chunks":
                0,

            "chunk_lengths":
                [],

            "unknown_characters":
                [],
        }


    clean_text = validation[
        "clean_text"
    ]


    chunks = split_long_text(
        clean_text,
        max_len=int(
            _MODEL_INFO[
                "max_len"
            ]
        ),
    )


    if not chunks:

        return {
            "success":
                False,

            "message":
                "Tidak ada teks yang "
                "dapat diproses.",

            "input_text":
                validation[
                    "normalized_text"
                ],

            "clean_text":
                clean_text,

            "prediction":
                "",

            "had_diacritics":
                validation[
                    "had_diacritics"
                ],

            "arabic_letters":
                validation[
                    "arabic_letters"
                ],

            "total_characters":
                len(
                    clean_text
                ),

            "total_chunks":
                0,

            "chunk_lengths":
                [],

            "unknown_characters":
                [],
        }


    predictions = []
    unknown_characters = []

    total_chunks = len(
        chunks
    )


    for index, chunk in enumerate(
        chunks,
        start=1,
    ):

        result = predict_single_chunk(
            chunk
        )


        if not result[
            "success"
        ]:

            return {
                "success":
                    False,

                "message": (
                    f"Gagal memproses chunk "
                    f"{index}/{total_chunks}: "
                    f"{result['message']}"
                ),

                "input_text":
                    validation[
                        "normalized_text"
                    ],

                "clean_text":
                    clean_text,

                "prediction":
                    "",

                "had_diacritics":
                    validation[
                        "had_diacritics"
                    ],

                "arabic_letters":
                    validation[
                        "arabic_letters"
                    ],

                "total_characters":
                    len(
                        clean_text
                    ),

                "total_chunks":
                    total_chunks,

                "chunk_lengths": [
                    len(
                        item
                    )
                    for item in chunks
                ],

                "unknown_characters":
                    unknown_characters,
            }


        # Normalisasi di predict_single_chunk() menghapus spasi di akhir
        # setiap segmen. Kembalikan pemisah tersebut setelah prediksi
        # agar penggabungan identik dengan input yang sudah dibersihkan.
        trailing_separator = chunk[len(chunk.rstrip()):]

        predictions.append(
            result[
                "prediction"
            ] + trailing_separator
        )


        for char in result[
            "unknown_characters"
        ]:

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
                index,
                total_chunks,
            )


    prediction = unicodedata.normalize(
        "NFC",
        "".join(
            predictions
        ),
    )


    reconstructed_clean = (
        remove_arabic_diacritics(
            prediction
        )
    )


    if (
        reconstructed_clean
        !=
        clean_text
    ):

        raise RuntimeError(
            "Rekonstruksi hasil inference "
            "tidak sama dengan input bersih."
        )


    return {
        "success":
            True,

        "message":
            "Diakritisasi berhasil.",

        "input_text":
            validation[
                "normalized_text"
            ],

        "clean_text":
            clean_text,

        "prediction":
            prediction,

        "had_diacritics":
            validation[
                "had_diacritics"
            ],

        "arabic_letters":
            validation[
                "arabic_letters"
            ],

        "total_characters":
            len(
                clean_text
            ),

        "total_chunks":
            total_chunks,

        "chunk_lengths": [
            len(
                chunk
            )
            for chunk in chunks
        ],

        "unknown_characters":
            unknown_characters,
    }


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


# ============================================================
# 15. PUBLIC BACKEND INFO
# ============================================================

def health_check():

    try:

        _ensure_loaded()


        test_text = (
            "قال الشيخ الإمام العالم"
        )


        result = predict_single_chunk(
            test_text
        )


        if not result[
            "success"
        ]:

            raise RuntimeError(
                result[
                    "message"
                ]
            )


        return {
            "success":
                True,

            "message":
                "Backend siap digunakan.",

            "project_root":
                str(
                    PROJECT_ROOT
                ),

            "model_path":
                str(
                    MODEL_PATH
                ),

            "model":
                dict(
                    _MODEL_INFO
                ),

            "metrics":
                _METRICS,
        }


    except Exception as error:

        return {
            "success":
                False,

            "message":
                str(
                    error
                ),

            "project_root":
                str(
                    PROJECT_ROOT
                ),

            "model_path":
                str(
                    MODEL_PATH
                ),

            "model":
                None,

            "metrics":
                None,
        }


def get_model_info():

    _ensure_loaded()

    return dict(
        _MODEL_INFO
    )


def get_metrics():

    _ensure_loaded()

    return _METRICS
