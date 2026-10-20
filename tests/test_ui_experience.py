"""Stage 4 UI semantics and active-result/export consistency regressions."""

from hashlib import sha256
from html import escape
from pathlib import Path
import sys
from unittest.mock import patch

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest

APP_DIR = Path(__file__).resolve().parents[1] / "streamlit_app"
sys.path.insert(0, str(APP_DIR))
import inference_engine as backend


def new_app():
    app = AppTest.from_file(str(APP_DIR / "app.py"), default_timeout=60).run()
    app.radio(key="page").set_value("Diakritisasi").run()
    return app


def html_bodies(app):
    return [item.proto.body for item in app.get("html")]


def apply_correction(app, text):
    editor = next(item for item in app.text_area if item.label == "Koreksi Manual Harakat")
    editor.input(text)
    next(item for item in app.button if item.label == "Terapkan Koreksi").click().run()
    assert not app.exception


@pytest.mark.parametrize("correction", ["الْحَمْدُ لِلَّهِ\nرَبِّ الْعَالَمِينَ", "", 'بِسْمِ الله\n" & </script>'])
def test_correction_updates_main_result_and_source_in_same_rerun_without_inference(correction):
    app = new_app()
    with patch.object(backend, "predict_long_text", wraps=backend.predict_long_text) as predict:
        app.text_area(key="_manual_input").input("الحمد لله").run()
        app.button(key="process_manual").click().run()
        model_result = dict(app.session_state.manual_result)
        timing = dict(app.session_state.manual_processing)
        assert predict.call_count == 1
        apply_correction(app, correction)
        assert app.session_state.manual_result == model_result
        assert app.session_state.manual_correction == correction
        assert app.session_state.manual_processing == timing
        assert predict.call_count == 1
        assert any('arabic-text arabic-result' in body and escape(correction) in body for body in html_bodies(app))
        assert any("Koreksi Pengguna" in body for body in html_bodies(app))
        assert any("Koreksi Pengguna" in item.value and "teks yang ditampilkan" in item.value for item in app.caption)
        assert any(item.label == "Akses Hasil Asli Model" for item in app.expander)
        app.button(key="restore_manual_model").click().run()
        assert app.session_state.manual_correction is None
        assert app.session_state.manual_result == model_result
        assert app.session_state.manual_processing == timing and predict.call_count == 1
        assert any('arabic-text arabic-result' in body and escape(model_result["prediction"]) in body
                   for body in html_bodies(app))
        assert not any(item.label == "Akses Hasil Asli Model" for item in app.expander)


def test_changed_input_discards_applied_correction_and_saved_result():
    app = new_app()
    app.text_area(key="_manual_input").input("الحمد لله").run()
    app.button(key="process_manual").click().run()
    apply_correction(app, "الْحَمْدُ لِلَّهِ")
    app.text_area(key="_manual_input").input("رب العالمين").run()
    assert not app.exception
    assert app.session_state.manual_correction is None
    assert app.session_state.manual_result is None and app.session_state.manual_processing is None
    assert not any(item.label == "Koreksi Hasil" for item in app.expander)


def test_queued_correction_cannot_reappear_after_input_invalidation():
    app = new_app()
    app.text_area(key="_manual_input").input("الحمد لله").run()
    app.button(key="process_manual").click().run()
    old_submit = next(item for item in app.button if item.label == "Terapkan Koreksi")
    next(item for item in app.text_area if item.label == "Koreksi Manual Harakat").input("الْحَمْدُ لِلَّهِ")
    app.text_area(key="_manual_input").input("رب العالمين")
    old_submit.click().run()
    assert not app.exception
    assert app.session_state.manual_correction is None
    assert app.session_state.manual_result is None and app.session_state.manual_processing is None


def test_file_status_labels_explain_normalization_without_changing_backend_counts():
    app = new_app()
    data = ('teks,info\nالحمد لله,=1+1\nabc   def,-12\n,\nالحمد abc,plain\n').encode("utf-8")
    app.session_state.upload_snapshot = {"name": "status.csv", "data": data, "size": len(data),
                                         "digest": sha256(data).hexdigest()}
    app.run()
    app.button(key="process_file").click().run()
    assert not app.exception and app.session_state.file_result["success"]
    result = app.session_state.file_result
    assert result["status_summary"] == {"berhasil": 1, "non_arab": 1, "kosong": 1, "campuran": 1}
    summary = next(body for body in html_bodies(app) if 'processing-summary-file' in body)
    assert "Tidak diprediksi</dt><dd>3</dd>" in summary
    assert "teks dapat dinormalisasi" in summary and "Dipertahankan" not in summary
    assert app.dataframe[0].value.loc[1, "teks"] == "abc   def"  # Original preview stays literal.
    statuses = app.dataframe[-1].value
    assert not statuses["Status"].str.contains("dipertahankan", case=False).any()
    assert statuses.loc[statuses["Status"].str.contains("tidak diprediksi"), "Jumlah"].sum() == 3


def test_sidebar_navigation_emits_only_one_mobile_close_request():
    app = new_app()
    script = next(body for body in html_bodies(app) if "_unimalSidebarNavigation" in body)
    assert "max-width:780px" in script and "stSidebarCollapseButton" in script
    assert app.session_state.filtered_state.get("mobile_navigation_request") is None
    app.run()
    assert not any("_unimalSidebarNavigation" in body for body in html_bodies(app))
