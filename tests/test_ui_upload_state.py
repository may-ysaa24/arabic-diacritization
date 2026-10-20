"""Session-only upload identity, parse reuse and invalidation regression tests."""

from hashlib import sha256
from pathlib import Path
import sys
from unittest.mock import patch

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest

APP_DIR = Path(__file__).resolve().parents[1] / "streamlit_app"
sys.path.insert(0, str(APP_DIR))
import inference_engine as backend
from arabic_diacritization import file_processing

CSV = ('arabic,arabic_alt,info\nالحمد لله,رب العالمين,=1+1\n'
       'abc,hello,-12\n,,\nالحمد abc,العالمين abc,plain\n').encode("utf-8")


def new_app():
    app = AppTest.from_file(str(APP_DIR / "app.py"), default_timeout=60).run()
    app.radio(key="page").set_value("Diakritisasi").run()
    assert not app.exception
    return app


def set_upload(app, name, data):
    # AppTest has no native uploader interaction. Real callbacks are covered in browser.
    app.session_state.upload_snapshot = {"name": name, "data": data, "size": len(data),
                                         "digest": sha256(data).hexdigest()}
    app.session_state.file_result = None
    app.session_state.file_result_signature = None
    app.session_state.file_processing = None
    app.session_state.csv_column = None
    app.run()
    assert not app.exception


def assert_active(app, name):
    assert any(f"Berkas aktif: {name}" in item.value and "tersimpan dalam sesi ini" in item.value
               for item in app.caption)


def test_csv_parse_counts_for_unrelated_reruns_column_changes_and_navigation():
    app = new_app()
    with patch.object(backend, "read_csv_file", wraps=backend.read_csv_file) as preview_read, \
         patch.object(file_processing, "read_csv_bytes", wraps=file_processing.read_csv_bytes) as all_reads, \
         patch.object(backend, "detect_arabic_columns", wraps=backend.detect_arabic_columns) as candidates, \
         patch.object(backend, "process_uploaded_file", wraps=backend.process_uploaded_file) as infer:
        set_upload(app, "kitab.csv", CSV)
        assert preview_read.call_count == all_reads.call_count == candidates.call_count == 1
        app.run()
        app.text_area(key="_manual_input").input("الحمد لله").run()
        app.selectbox(key="_csv_column").select("arabic_alt").run()
        app.radio(key="page").set_value("Tentang Model").run()
        app.radio(key="page").set_value("Diakritisasi").run()
        assert app.selectbox(key="_csv_column").value == "arabic_alt"
        assert_active(app, "kitab.csv")
        assert preview_read.call_count == all_reads.call_count == candidates.call_count == 1
        assert infer.call_count == 0
        app.button(key="process_file").click().run()
        assert app.session_state.file_result["success"]
        assert infer.call_count == 1
        # An explicit processing action keeps the backend's own reader unchanged.
        assert all_reads.call_count == 2 and preview_read.call_count == 1
        result = app.session_state.file_result
        elapsed = dict(app.session_state.file_processing)
        for page in ("Beranda", "Contoh Teks", "Tentang Model", "Diakritisasi"):
            app.radio(key="page").set_value(page).run()
        app.run()
        assert app.session_state.file_result["download_bytes"] == result["download_bytes"]
        assert app.session_state.file_processing == elapsed
        assert all_reads.call_count == 2 and infer.call_count == 1
        assert preview_read.call_count == candidates.call_count == 1
        app.selectbox(key="_csv_column").select("arabic").run()
        assert app.session_state.file_result is None
        assert app.session_state.file_result_signature is None
        assert app.session_state.file_processing is None
        assert all_reads.call_count == 2 and infer.call_count == 1
        assert not app.exception


def test_identity_uses_content_and_format_but_not_filename_and_clear_evicts():
    app = new_app()
    other = CSV.replace(b"=1+1", b"+1+1")
    with patch.object(backend, "read_csv_file", wraps=backend.read_csv_file) as read:
        set_upload(app, "same.csv", CSV)
        app.button(key="process_file").click().run()
        first_key = app.session_state.upload_validation_cache["key"]
        set_upload(app, "same.csv", other)
        assert read.call_count == 2
        assert app.session_state.upload_validation_cache["key"] != first_key
        assert app.session_state.file_result is None and app.session_state.file_processing is None
        assert app.dataframe[0].value.loc[0, "info"] == "+1+1"
        other_key = app.session_state.upload_validation_cache["key"]
        set_upload(app, "renamed.csv", other)
        assert read.call_count == 2 and app.session_state.upload_validation_cache["key"] == other_key
        assert_active(app, "renamed.csv")
        app.button(key="process_file").click().run()
        assert app.session_state.file_result["output_filename"].startswith("renamed_")
        # Identical bytes with a different input format require separate validation.
        set_upload(app, "renamed.txt", other)
        assert app.session_state.upload_validation_cache["key"] != other_key
        assert "dataframe" not in app.session_state.upload_validation_cache["validation"]
        set_upload(app, "renamed.csv", other)
        assert read.call_count == 3
        app.button(key="process_file").click().run()
        app.radio(key="page").set_value("Tentang Model").run()
        app.radio(key="page").set_value("Diakritisasi").run()
        app.button(key="reset_file").click().run()
        for key in ("upload_snapshot", "upload_validation_cache", "csv_column", "file_result",
                    "file_result_signature", "file_processing"):
            assert app.session_state[key] is None, key
        assert not app.selectbox
        with pytest.raises(KeyError):
            app.session_state["_csv_column"]  # Streamlit removed the absent widget.
        assert app.button(key="process_file").disabled
        assert len(app.get("download_button")) == 1  # Disabled manual download only.
        assert not any("Berkas aktif:" in item.value for item in app.caption)
        set_upload(app, "renamed.csv", other)
        assert read.call_count == 4


def test_failed_csv_validation_is_cached_and_new_bytes_are_revalidated():
    app = new_app()
    with patch.object(backend, "read_csv_file", wraps=backend.read_csv_file) as read, \
         patch.object(backend, "process_uploaded_file", wraps=backend.process_uploaded_file) as infer:
        set_upload(app, "broken.csv", b'text,id\n"unterminated')
        assert not app.session_state.upload_validation_cache["validation"]["success"]
        assert app.button(key="process_file").disabled
        app.run()
        app.radio(key="page").set_value("Tentang Model").run()
        app.radio(key="page").set_value("Diakritisasi").run()
        assert read.call_count == 1 and infer.call_count == 0
        set_upload(app, "broken.csv", CSV)
        assert read.call_count == 2 and infer.call_count == 0
        assert not app.button(key="process_file").disabled
        assert app.session_state.file_result is None


@pytest.mark.parametrize("replacement", ["changed", "renamed", "removed"])
def test_old_column_callback_cannot_repopulate_a_replaced_or_removed_upload(replacement):
    app = new_app()
    set_upload(app, "old.csv", CSV)
    old_widget = app.selectbox(key="_csv_column")
    # Simulate an upload/remove callback immediately before a queued selectbox
    # callback from the old render. Its args must still identify the old file.
    if replacement == "removed":
        app.session_state.upload_snapshot = None
    else:
        data = CSV.replace(b"=1+1", b"=2+2") if replacement == "changed" else CSV
        app.session_state.upload_snapshot = {
            "name": "old.csv" if replacement == "changed" else "renamed.csv",
            "data": data, "size": len(data), "digest": sha256(data).hexdigest(),
        }
    app.session_state.csv_column = None
    old_widget.select("arabic_alt").run()
    assert not app.exception
    assert app.session_state.csv_column == (None if replacement == "removed" else "arabic")
    assert app.session_state.file_result is None


def test_cached_dataframe_is_isolated_from_render_mutation_and_backend_results():
    app = new_app()
    import streamlit as st
    render = st.dataframe

    def mutate_render_copy(frame, *args, **kwargs):
        if "info" in frame.columns:
            frame.loc[frame.index[0], "info"] = "render-only mutation"
        return render(frame, *args, **kwargs)

    with patch.object(st, "dataframe", side_effect=mutate_render_copy):
        set_upload(app, "private.csv", CSV)
    cached = app.session_state.upload_validation_cache["validation"]["dataframe"]
    assert cached.loc[0, "info"] == "=1+1"
    app.run()
    assert app.dataframe[0].value.loc[0, "info"] == "=1+1"
    app.button(key="process_file").click().run()
    assert app.session_state.file_result["dataframe"].loc[0, "info"] == "=1+1"
    assert app.session_state.upload_validation_cache["validation"]["dataframe"].equals(cached)
    assert "hasil_diacritization" not in cached.columns


def test_upload_cache_is_private_to_each_session():
    first, second = new_app(), new_app()
    with patch.object(backend, "read_csv_file", wraps=backend.read_csv_file) as read:
        set_upload(first, "private.csv", CSV)
        assert second.session_state.upload_snapshot is None
        assert second.session_state.upload_validation_cache is None
        set_upload(second, "private.csv", CSV)
        assert read.call_count == 2
    first_frame = first.session_state.upload_validation_cache["validation"]["dataframe"]
    second_frame = second.session_state.upload_validation_cache["validation"]["dataframe"]
    assert first_frame is not second_frame
    first_frame.loc[0, "info"] = "first session only"
    assert second_frame.loc[0, "info"] == "=1+1"


@pytest.mark.parametrize("encoding", ["utf-8", "utf-16"])
def test_txt_validation_and_success_survive_page_navigation_without_redecode(encoding):
    app = new_app()
    with patch.object(backend, "decode_text_bytes", wraps=backend.decode_text_bytes) as decode:
        set_upload(app, "kitab.txt", "الحمد لله\r\n\r\nabc".encode(encoding))
        assert decode.call_count == 1
        app.button(key="process_file").click().run()
        result = app.session_state.file_result
        stats = dict(app.session_state.file_processing)
        assert result["success"]
        app.radio(key="page").set_value("Tentang Model").run()
        app.radio(key="page").set_value("Diakritisasi").run()
        assert_active(app, "kitab.txt")
        assert decode.call_count == 1
        assert app.session_state.file_processing == stats
        assert app.session_state.file_result["download_bytes"] == result["download_bytes"]
        set_upload(app, "kitab.txt", "الحمد\x00لله".encode(encoding))
        assert decode.call_count == 2
        assert app.button(key="process_file").disabled
        assert app.session_state.file_result is None
        app.run()
        assert decode.call_count == 2
