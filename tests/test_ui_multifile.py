"""Multi-upload state, isolation, bounded resources and safe aggregate exports."""

import csv
from io import BytesIO, StringIO
from pathlib import Path
import sys
from unittest.mock import patch
from zipfile import ZipFile

import pandas as pd
import pytest

pytest.importorskip("streamlit")
import streamlit as st
from streamlit.testing.v1 import AppTest

APP_DIR = Path(__file__).resolve().parents[1] / "streamlit_app"
sys.path.insert(0, str(APP_DIR))
import inference_engine as backend
import upload_queue as queue

TEXT = "الحمد لله\n\nabc\n".encode("utf-8")
CSV = "judul_arab,teks_gundul,info\nرب العالمين,الحمد لله,=1+1\n".encode("utf-8")


def file(name, data):
    stream = BytesIO(data)
    stream.name = name
    stream.size = len(data)
    return stream


def new_app():
    app = AppTest.from_file(str(APP_DIR / "app.py"), default_timeout=60).run()
    app.radio(key="page").set_value("Diakritisasi").run()
    assert not app.exception
    return app


def upload(app, *files, stale_key=None):
    # AppTest cannot drive a native uploader. Invoke the real callback in its
    # ScriptRunContext; the native transport is covered by browser acceptance.
    def submit(*args, **kwargs):
        key = stale_key or kwargs["key"]
        st.session_state[key] = list(files)
        kwargs["on_change"](key)
        return []
    with patch.object(st, "file_uploader", side_effect=submit):
        app.run()
    app.run()
    assert not app.exception
    return list(app.session_state.upload_files)


def choose(app, file_id):
    app.selectbox(key="_active_file").select(file_id).run()
    assert not app.exception


def test_mixed_batch_real_backend_retains_results_addition_navigation_and_downloads():
    app = new_app()
    with patch.object(backend, "process_uploaded_file", wraps=backend.process_uploaded_file) as infer:
        ids = upload(app, file("a.txt", TEXT), file("a.csv", CSV))
        assert len(ids) == 2
        app.button(key="process_all_files").click().run()
        assert not app.exception and infer.call_count == 2
        entries = app.session_state.upload_files
        before = {key: value["file_result"]["download_bytes"] for key, value in entries.items()}
        assert all(e["file_result"]["success"] for e in entries.values())
        assert entries[ids[1]]["csv_column"] == "teks_gundul"
        for page in ("Beranda", "Contoh Teks", "Tentang Model", "Diakritisasi"):
            app.radio(key="page").set_value(page).run()
        choose(app, ids[1])
        assert app.selectbox(key="_csv_column").value == "teks_gundul"
        assert len(app.get("download_button")) == 2
        ids = upload(app, file("b.txt", "رب العالمين".encode()))
        assert len(ids) == 3 and infer.call_count == 2
        for key, result in before.items():
            assert app.session_state.upload_files[key]["file_result"]["download_bytes"] == result
        app.button(key="process_all_files").click().run()
        assert infer.call_count == 3  # Completed entries are not processed again.
        choose(app, ids[0])
        app.button(key="process_file").click().run()
        assert infer.call_count == 4
        assert app.session_state.upload_files[ids[1]]["file_result"]["download_bytes"] == before[ids[1]]
        app.button(key="prepare_queue_zip").click().run()
        assert app.session_state.queue_zip
        assert any(x.proto.label == "Unduh Semua (ZIP)" for x in app.get("download_button"))
        with ZipFile(BytesIO(app.session_state.queue_zip)) as archive:
            assert len(archive.namelist()) == 4
            rows = list(csv.DictReader(StringIO(archive.read("ringkasan_status.csv").decode("utf-8-sig"))))
            assert len(rows) == 3 and {r["status"] for r in rows} == {"Selesai"}
            csv_name = next(r["hasil"] for r in rows if r["berkas"] == "a.csv")
            assert b"\t=1+1" in archive.read(csv_name)
            assert b"\t=1+1" not in app.session_state.upload_files[ids[1]]["file_result"]["download_bytes"]
        app.run()
        assert infer.call_count == 4 and not app.exception


def test_partial_failure_invalid_txt_and_remaining_files_continue():
    app = new_app()
    ids = upload(app, file("bad.csv", CSV), file("invalid.txt", b"\x00"), file("good.txt", TEXT))
    real = backend.process_uploaded_file
    def sometimes_fails(uploaded, **kwargs):
        if uploaded.name == "bad.csv":
            raise RuntimeError("deliberate test failure")
        return real(uploaded, **kwargs)
    with patch.object(backend, "process_uploaded_file", side_effect=sometimes_fails) as infer:
        app.button(key="process_all_files").click().run()
    entries = app.session_state.upload_files
    assert infer.call_count == 2 and not app.exception
    assert queue.entry_status(entries[ids[0]])[0] == "Gagal"
    assert queue.entry_status(entries[ids[1]])[0] == "Tidak valid"
    assert entries[ids[2]]["file_result"]["success"]
    app.button(key="prepare_queue_zip").click().run()
    with ZipFile(BytesIO(app.session_state.queue_zip)) as archive:
        rows = list(csv.DictReader(StringIO(archive.read("ringkasan_status.csv").decode("utf-8-sig"))))
        assert [r["status"] for r in rows] == ["Gagal", "Tidak valid", "Selesai"]
        assert len(archive.namelist()) == 2
    choose(app, ids[0])
    app.button(key="process_file").click().run()
    assert app.session_state.file_result["success"]
    assert app.session_state.queue_zip is None


def test_per_file_column_defaults_manual_choice_and_stale_callbacks():
    app = new_app()
    other_csv = "arabic,arabic_alt\nالحمد لله,رب العالمين\n".encode()
    ids = upload(app, file("first.csv", CSV), file("second.csv", other_csv))
    assert app.selectbox(key="_csv_column").value == "teks_gundul"
    app.selectbox(key="_csv_column").select("judul_arab").run()
    app.button(key="process_all_files").click().run()
    first_bytes = app.session_state.upload_files[ids[0]]["file_result"]["download_bytes"]
    old_widget = app.selectbox(key="_csv_column")
    # Switch active entry just before a queued event from the previous entry.
    queue.persist_active(app.session_state)
    queue.load_active(app.session_state, ids[1])
    old_widget.select("teks_gundul").run()
    assert not app.exception and app.session_state.csv_column == "arabic"
    app.selectbox(key="_csv_column").select("arabic_alt").run()
    assert app.session_state.file_result is None
    assert app.session_state.upload_files[ids[0]]["file_result"]["download_bytes"] == first_bytes
    choose(app, ids[0])
    assert app.selectbox(key="_csv_column").value == "judul_arab"
    choose(app, ids[1])
    assert app.selectbox(key="_csv_column").value == "arabic_alt"


def test_duplicate_names_changed_content_explicit_removal_and_stale_upload():
    app = new_app()
    ids = upload(app, file("same.txt", TEXT), file("same.txt", TEXT), file("same.txt", b"abc"))
    assert len(ids) == 2
    app.button(key="process_all_files").click().run()
    stale_key = f"_upload_{app.session_state.uploader_generation}"
    app.button(key="reset_file").click().run()
    assert list(app.session_state.upload_files) == [ids[1]]
    assert app.session_state.file_result["success"]
    upload(app, file("same.txt", TEXT), stale_key=stale_key)
    assert len(app.session_state.upload_files) == 1
    app.button(key="reset_all_files").click().run()
    assert not app.session_state.upload_files and app.session_state.active_upload_id is None
    assert app.session_state.queue_zip is None
    for key in queue.ACTIVE_FIELDS:
        assert app.session_state[key] is None
    assert not app.selectbox and app.button(key="process_file").disabled
    assert len(app.get("download_button")) == 1
    ids = upload(app, file("same.txt", TEXT))
    assert len(ids) == 1 and app.session_state.file_result is None


def test_validation_cache_and_results_are_session_private():
    first, second = new_app(), new_app()
    with patch.object(backend, "read_csv_file", wraps=backend.read_csv_file) as read:
        ids = upload(first, file("a.csv", CSV), file("b.csv", CSV))
        assert read.call_count == 2
        first.run()
        choose(first, ids[1])
        first.radio(key="page").set_value("Tentang Model").run()
        first.radio(key="page").set_value("Diakritisasi").run()
        assert read.call_count == 2
        assert not second.session_state.upload_files
        other = upload(second, file("a.csv", CSV))
        assert read.call_count == 3
    first.session_state.upload_files[ids[0]]["upload_validation_cache"]["validation"]["dataframe"].iloc[0, 2] = "private"
    assert second.session_state.upload_files[other[0]]["upload_validation_cache"]["validation"]["dataframe"].iloc[0, 2] == "=1+1"


def empty_state():
    return {"upload_files": {}, "active_upload_id": None, "uploader_generation": 0,
            **dict.fromkeys(queue.ACTIVE_FIELDS)}


def test_file_count_input_size_and_oversize_payload_not_retained():
    state = empty_state()
    queue.add_uploads(state, [file(f"a{i}.txt", TEXT) for i in range(21)])
    assert len(state["upload_files"]) == queue.MAX_FILES and state["upload_messages"]
    state = empty_state()
    queue.add_uploads(state, [file(f"a{i}.txt", b"x" * queue.MAX_FILE_BYTES) for i in range(5)])
    assert len(state["upload_files"]) == 4 and "20 MiB" in state["upload_messages"][0]
    state = empty_state()
    queue.add_uploads(state, [file("large.txt", b"x" * (queue.MAX_FILE_BYTES + 1))])
    assert state["upload_snapshot"]["data"] is None


@pytest.mark.parametrize("text,csv_input", [
    ("a" * (queue.MAX_TEXT_CHARS + 1), False),
    ("a\n" * (queue.MAX_ROWS + 1), False),
    ("a\u2028" * (queue.MAX_ROWS + 1), False),
    (",".join(f"c{i}" for i in range(101)) + "\n" + ",".join("a" for _ in range(101)), True),
    ("a,b\n" * (queue.MAX_ROWS + 2), True),
    ("a" * 1_000_001, True),
], ids=["txt-characters", "txt-lines", "txt-unicode-lines", "csv-columns", "csv-rows", "csv-characters"])
def test_resource_preflight_refuses_without_truncation(text, csv_input):
    assert queue.text_capacity_error(text, csv_input)


def test_preflight_accepts_quoted_separators_and_embedded_newlines():
    assert queue.text_capacity_error('text,info\n"الحمد\nلله","' + "," * 150 + '"\n', True) is None


def test_memory_budget_rejects_new_entry_and_result_without_affecting_others():
    state = empty_state()
    with patch.object(queue, "MAX_RETAINED_BYTES", 1):
        queue.add_uploads(state, [file("a.txt", TEXT)])
    assert not state["upload_files"] and state["upload_messages"]
    app = new_app()
    ids = upload(app, file("a.txt", TEXT), file("b.txt", TEXT))
    app.button(key="process_file").click().run()
    before = app.session_state.file_result["download_bytes"]
    choose(app, ids[1])
    with patch.object(queue, "MAX_RETAINED_BYTES", 1):
        app.button(key="process_file").click().run()
    assert not app.exception and not app.session_state.file_result["success"]
    assert app.session_state.upload_files[ids[0]]["file_result"]["download_bytes"] == before


@pytest.mark.parametrize("name", ["../../escape.txt", r"C:\secret\CON.txt", "NUL.csv", "x\x00\u202e.exe.txt", "=1+1.csv", "a:b?.csv"])
def test_safe_names_are_flat_portable_and_not_spreadsheet_formulas(name):
    output = queue.safe_output_name(name, "txt", "001")
    assert output.startswith("hasil_001_") and output.endswith(".txt")
    assert not any(c in output for c in '/\\:\x00\u202e?')
    assert len(output) < 120


def test_zip_no_collisions_pending_summary_and_formula_injection_protection():
    state = empty_state()
    queue.add_uploads(state, [file("=1+1.txt", TEXT), file("=1+1.txt", b"abc"), file("pending.csv", CSV)])
    for entry in list(state["upload_files"].values())[:2]:
        entry["file_result"] = {"success": True, "input_type": "txt", "download_bytes": b"abc"}
    archive_bytes = queue.build_zip(state["upload_files"])
    with ZipFile(BytesIO(archive_bytes)) as archive:
        names = archive.namelist()
        assert len(names) == len(set(n.casefold() for n in names)) == 3
        assert all("/" not in n and "\\" not in n for n in names)
        rows = list(csv.DictReader(StringIO(archive.read("ringkasan_status.csv").decode("utf-8-sig"))))
        assert rows[0]["berkas"] == "\t=1+1.txt" and rows[2]["status"] == "Menunggu"
    with patch.object(queue, "MAX_EXPORT_BYTES", 1), pytest.raises(ValueError, match="32 MiB"):
        queue.build_zip(state["upload_files"])


def test_research_demo_csv_defaults_without_modifying_inputs():
    root = APP_DIR.parent / "data/demo_fathul_qorib_per_bab/CSV"
    if not root.exists():
        pytest.skip("Local demonstration package is not distributed with the repository")
    app = new_app()
    sources = list(root.glob("*.csv"))
    assert len(sources) == 17
    originals = {p: p.read_bytes() for p in sources}
    ids = upload(app, *(file(p.name, payload) for p, payload in originals.items()))
    assert len(ids) == 17
    assert all(e["csv_column"] == "teks_gundul" for e in app.session_state.upload_files.values())
    assert all(e["upload_validation_cache"]["validation"]["success"] for e in app.session_state.upload_files.values())
    assert all(p.read_bytes() == payload for p, payload in originals.items())
