"""Independent checkpoint loading, model inference and diacritic reconstruction."""
import json
import torch
import unicodedata
from .config import PROJECT_ROOT, MODEL_PATH, CONFIG_PATH, CHAR2ID_PATH, LABEL2ID_PATH, ID2LABEL_PATH, METRICS_PATH
from .model import BiLSTMCRF
from .preprocessing import is_arabic_letter, remove_arabic_diacritics, normalize_text, validate_input

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

