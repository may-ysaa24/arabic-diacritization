"""Regression tests for migrated models, notebooks, TXT/CSV and downloads."""
import hashlib
import io
import json
from pathlib import Path

import pytest

pytest.importorskip("torch")
pytest.importorskip("torchcrf")
pytest.importorskip("pandas")

from arabic_diacritization import _reference_engine as engine

ROOT = Path(__file__).resolve().parents[1]


def assert_git_hash(path, expected):
    data = path.read_bytes()
    sha = hashlib.sha1(f"blob {len(data)}".encode() + bytes([0]) + data).hexdigest()
    assert sha == expected, path


def test_original_checkpoints_unchanged():
    for name, sha in (
        ("baseline/best_model.pt", "a3c1421cf413e7ce53767b62278c5430a954fabd"),
        ("pretrained/best_pretrained_model.pt", "60f3a9fa32648d3daa54eb99b2580458fcdf3aed"),
        ("finetuned/best_finetuned_model.pt", "bf4b19d2a175852d7ce37a695ba781f7a6e5c176"),
    ):
        assert_git_hash(ROOT / "models" / name, sha)


def test_all_original_notebooks_unchanged():
    originals = {
        "01_prepare_data.ipynb": "20b4e65becfbfe195f89c9ca2f7e4c093df08e39",
        "02_train_baseline.ipynb": "8781f0290b44bcfeaa03a6dc5363307eeb5c74fa",
        "03_pretrain_tashkeela.ipynb": "8abb0a4f715341160688628648d0bfad9260ae93",
        "04_finetune_fathul_qorib.ipynb": "38976b7486ae2ef1168e81ab6ed924bc2f1324c5",
        "05_evaluate_compare.ipynb": "3b609e7a39bd1702192a17e8bb0c216c0217cf7e",
        "06_build_backend.ipynb": "f9b25fd24464efbda72b6c72f426231a86300181",
        "07_build_streamlit_ui.ipynb": "06ae9c5ff606e17f5dd947c454904a49318631b9",
        "FQ_OCR.ipynb": "fe5bb5a034f98bcb751d1ae30617f445e5276b69",
        "data_tashkeela.ipynb": "7a175867e1c5c81ea1ac50e37f1495685141300f",
        "inference_demo.ipynb": "2a4248a69a3e66db5ece600ea0054832d4933701",
    }
    for filename, sha in originals.items():
        path = ROOT / "notebooks" / filename
        assert_git_hash(path, sha)
        notebook = json.loads(path.read_text(encoding="utf-8"))
        assert notebook["nbformat"] == 4
        assert notebook["cells"]


def test_txt_upload_inference_and_download():
    progress = []
    source = "الحمد لله\n\nabc\n".encode("utf-8")
    result = engine.process_txt_bytes(
        source, filename="kitab.txt",
        progress_callback=lambda n, total: progress.append((n, total)),
    )
    assert result["success"], result.get("message")
    assert result["input_type"] == "txt"
    assert result["output_filename"] == "kitab_hasil_diakritisasi.txt"
    assert engine.remove_arabic_diacritics(result["prediction"]).splitlines()[0] == "الحمد لله"
    assert result["download_bytes"].decode("utf-8") == result["prediction"]
    assert progress == [(1, 3), (2, 3), (3, 3)]


def test_csv_upload_inference_and_download():
    source = "teks,id\nالحمد لله,1\nabc,2\n".encode("utf-8")
    result = engine.process_csv_bytes(source, filename="kitab.csv", text_column="teks")
    assert result["success"], result.get("message")
    assert result["input_type"] == "csv"
    assert result["output_filename"] == "kitab_hasil_diakritisasi.csv"
    assert "teks" in result["dataframe"].columns
    output_column = result["output_columns"]["prediction"]
    assert engine.remove_arabic_diacritics(result["dataframe"].iloc[0][output_column]) == "الحمد لله"
    assert result["download_bytes"].decode("utf-8-sig").startswith("teks,id,")
    assert "abc" in result["download_bytes"].decode("utf-8-sig")


def test_upload_validation():
    assert not engine.process_uploaded_file(None)["success"]
    assert not engine.process_uploaded_file(io.BytesIO(b""))["success"]
    class NamedBytesIO(io.BytesIO):
        name = "invalid.exe"
    assert not engine.process_uploaded_file(NamedBytesIO(b"nonempty"))["success"]
    assert not engine.process_csv_bytes(b"hello\nworld", text_column="missing")["success"]


def test_streamlit_app_initial_render():
    st = pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest
    app = AppTest.from_file(str(ROOT / "streamlit_app" / "app.py"), default_timeout=45).run()
    assert not app.exception, [str(e.message) for e in app.exception]


def test_backend_reference_only_differs_by_project_root():
    source = (ROOT / "src/arabic_diacritization/_reference_engine.py").read_text(encoding="utf-8")
    replacement = "\n".join(["DEFAULT_PROJECT_ROOT = (", "    Path(__file__).resolve().parents[2]", ")"])
    original_block = "\n".join(["DEFAULT_PROJECT_ROOT = (", "    APP_DIR.parent", ")"])
    assert source.count(replacement) == 1
    restored = source.replace(replacement, original_block).encode("utf-8")
    old_sha = hashlib.sha1(f"blob {len(restored)}".encode() + bytes([0]) + restored).hexdigest()
    assert old_sha == "9638075c6a1ed6cbe654211a261deef006e8e751"


def test_streamlit_manual_navigation_and_prediction():
    from streamlit.testing.v1 import AppTest

    app = AppTest.from_file(str(ROOT / "streamlit_app" / "app.py"), default_timeout=45).run()
    app.radio(key="page").set_value("Diakritisasi").run()
    assert not app.exception, [str(e.message) for e in app.exception]
    app.text_area(key="_manual_input").input("الحمد لله رب العالمين").run()
    app.button(key="process_manual").click().run()
    assert not app.exception, [str(e.message) for e in app.exception]
    result = app.session_state["manual_result"]
    assert result and result["success"], result
    assert engine.remove_arabic_diacritics(result["prediction"]) == result["clean_text"]


def test_modular_inference_matches_reference_exactly():
    from arabic_diacritization import inference, preprocessing
    samples = (
        "الحمد لله رب العالمين",
        "قال الشيخ الإمام العالم العلامة شمس الدين",
        "وأسأله الهداية إلى سواء السبيل",
        "الْحَمْدُ لِلَّهِ",
        "قال الشيخ الإمام العالم " * 30,
    )
    for sample in samples:
        assert inference.predict_long_text(sample) == engine.predict_long_text(sample), sample
    assert inference.health_check()["model"] == engine.health_check()["model"]
    assert inference.get_metrics() == engine.get_metrics()
    for max_len in (8, 50, 300):
        sample = "قال الشيخ الإمام العالم " * 6
        assert inference.split_long_text(sample, max_len=max_len) == engine.split_long_text(sample, max_len=max_len)
    assert preprocessing.remove_arabic_diacritics("بِسْمِ اللَّهِ") == engine.remove_arabic_diacritics("بِسْمِ اللَّهِ")


def test_modular_txt_csv_matches_reference_exactly():
    from arabic_diacritization import file_processing
    raw = "الحمد لله\n\nabc\n".encode()
    assert file_processing.process_txt_bytes(raw, filename="test.txt") == engine.process_txt_bytes(raw, filename="test.txt")
    raw_csv = "teks,id\nالحمد لله,1\nabc,2\n".encode()
    old = engine.process_csv_bytes(raw_csv, filename="test.csv", text_column="teks")
    new = file_processing.process_csv_bytes(raw_csv, filename="test.csv", text_column="teks")
    assert set(old) == set(new)
    for key in old:
        if key == "dataframe":
            assert old[key].equals(new[key])
        else:
            assert old[key] == new[key], key


@pytest.mark.parametrize("text", [
    "",
    "   ",
    "abc",
    "الحمد لله abc",
    "الحمد لله ١٢٣",
    "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ",
    "؟!،،؛: 123",
    "الْحَمْدُ" * 80,
])
def test_modular_prediction_edge_cases_match_reference(text):
    from arabic_diacritization import inference
    old = engine.predict_long_text(text)
    new = inference.predict_long_text(text)
    assert old == new, (text, old, new)


@pytest.mark.parametrize("data", [
    b"",
    b"abc\n123\n",
    "الحمد لله\r\nabc\r\n".encode("utf-8"),
    "قال الشيخ الإمام العالم\n" * 10,
])
def test_modular_txt_edge_cases_match_reference(data):
    from arabic_diacritization import file_processing
    raw = data.encode("utf-8") if isinstance(data, str) else data
    assert file_processing.process_txt_bytes(raw) == engine.process_txt_bytes(raw)


def test_backend_compatibility_on_all_streamlit_pages():
    from streamlit.testing.v1 import AppTest
    for page in ("Beranda", "Diakritisasi", "Contoh Teks", "Tentang Model"):
        app = AppTest.from_file(str(ROOT / "streamlit_app/app.py"), default_timeout=45).run()
        app.radio(key="page").set_value(page).run()
        assert not app.exception, (page, [str(e.message) for e in app.exception])
