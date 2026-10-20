"""UI file-safety policy; research readers, inference and results stay unchanged."""

import csv
from hashlib import sha256
from io import StringIO
from pathlib import Path
import sys
import subprocess
from unittest.mock import patch

import pytest

pd = pytest.importorskip("pandas")
pytest.importorskip("streamlit")
toml = pytest.importorskip("toml")
from streamlit.testing.v1 import AppTest

APP_DIR = Path(__file__).resolve().parents[1] / "streamlit_app"
sys.path.insert(0, str(APP_DIR))
from file_safety import spreadsheet_safe_csv, txt_control_error


def test_builtin_table_export_cannot_bypass_the_csv_serializer():
    config = toml.loads((APP_DIR / ".streamlit" / "config.toml").read_text(encoding="utf-8"))
    assert config["client"]["disableDataExport"] is True
    official = toml.loads((APP_DIR.parent / ".streamlit" / "config.toml").read_text(encoding="utf-8"))
    assert official == config


@pytest.mark.parametrize("directory", [APP_DIR.parent, APP_DIR], ids=["official-root", "compat-subfolder"])
def test_startup_reads_export_policy_and_theme_from_working_directory(directory):
    code = ('import streamlit as st; '
            'assert st.get_option("client.disableDataExport") is True; '
            'assert st.get_option("theme.primaryColor") == "#009344"; '
            'assert st.get_option("browser.gatherUsageStats") is False')
    subprocess.run([sys.executable, "-B", "-c", code], cwd=directory, check=True,
                   capture_output=True, text=True, timeout=30)


def test_application_enforces_export_policy_without_local_configuration(tmp_path):
    # An isolated process avoids changing the other AppTest sessions' config.
    code = f'''
import streamlit as st
from streamlit.testing.v1 import AppTest
st.set_option("client.disableDataExport", False)
app = AppTest.from_file({str(APP_DIR / "app.py")!r}, default_timeout=60).run()
assert not app.exception
assert st.get_option("client.disableDataExport") is True
assert app.session_state["_ui_export_policy_ready"] is True
app.radio(key="page").set_value("Diakritisasi").run()
assert not app.exception
assert not app.session_state.manual_result
'''
    subprocess.run([sys.executable, "-B", "-c", code], cwd=tmp_path, check=True,
                   capture_output=True, text=True, timeout=90)


def test_git_ignores_local_secrets_and_test_artifacts_but_not_theme():
    ignored = {".streamlit/secrets.toml", "streamlit_app/.streamlit/secrets.toml",
               "local/secrets.toml", "local/secrets.local.json", "streamlit_app/.env",
               "src/example.egg-info/PKG-INFO", "test-results/audit.png",
               "playwright-report/index.html", ".coverage"}
    themes = {".streamlit/config.toml", "streamlit_app/.streamlit/config.toml"}
    result = subprocess.run(["git", "check-ignore", "--no-index", "-z", "--stdin"],
                            input=("\0".join(sorted(ignored | themes)) + "\0").encode(),
                            cwd=APP_DIR.parent, capture_output=True, check=True)
    assert set(result.stdout.decode().rstrip("\0").split("\0")) == ignored


@pytest.mark.parametrize("code", [*range(0, 9), 11, 12, *range(14, 32), 127,
                                   *range(128, 133), *range(134, 160)])
def test_txt_rejects_forbidden_controls_after_decoding(code):
    error = txt_control_error("الحمد لله" + chr(code))
    assert error and f"U+{code:04X}" in error


@pytest.mark.parametrize("text", [
    "الْحَمْدُ لِلَّهِ\tرب العالمين\r\n", "abc\tdef\r\n", "  \t\n",
    "\u061c\u200fبِسْمِ\u200d الله\u200c\u200e\ufeff",
    "الحمد\u0085لله\u2028رب\u2029العالمين",
])
def test_txt_allows_text_whitespace_harakat_and_rtl_formatting(text):
    assert txt_control_error(text) is None


@pytest.mark.parametrize("value", [
    "=1+1", "+SUM(1,1)", "@SUM(1,1)", "-SUM(1,1)", "-1+2",
    " =1+1", "\t=1+1", "\r\n+SUM(1,1)", "\x00=1+1", "\x1b@SUM(1,1)",
    "\ufeff=1+1", "\u200b=1+1", "\u200f=1+1", "\u061c-1+2",
    "\u034f=1+1", "\u00a0=1+1", "\uff1d1+1", "\uff0bSUM(1,1)",
    "\uff0d1+2", "\uff20SUM(1,1)", "-1,234", " -12", "+12",
    '=1+1\",\n=2+2',
])
def test_csv_neutralizes_risky_and_obfuscated_values(value):
    original = pd.DataFrame({"text": [value]})
    exported = spreadsheet_safe_csv(original)
    rows = list(csv.reader(StringIO(exported.decode("utf-8-sig"), newline="")))
    assert rows == [["text"], ["\t" + value]]
    assert original.iloc[0, 0] == value
    assert exported.startswith(b"\xef\xbb\xbf")


@pytest.mark.parametrize("value", [
    "-12", "-3.5", "-.5", "-1.", "-1e3", "-1.2E-3", "-0", "0", "123",
    "الْحَمْدُ لِلَّهِ", "سطر أول\nسطر ثانٍ", "سطر\r\nثانٍ", "", "  ",
    "'literal", 'قال "الشيخ", ثم كتب', "العربية\n=1+1",
])
def test_csv_preserves_safe_text_and_strict_negative_numbers(value):
    frame = pd.DataFrame({"text": [value]})
    rows = list(csv.reader(StringIO(spreadsheet_safe_csv(frame).decode("utf-8-sig"), newline="")))
    assert rows == [["text"], [value]]


def test_csv_preserves_structure_headers_row_order_and_dataframe():
    frame = pd.DataFrame({"=header": ["=1+1", "بِسْمِ الله", "", "line\nnext"],
                          "id": ["1", "2", "3", "4"],
                          "status": ["non_arab", "berhasil", "kosong", "non_arab"]})
    before = frame.copy(deep=True)
    rows = list(csv.reader(StringIO(spreadsheet_safe_csv(frame).decode("utf-8-sig"), newline="")))
    assert rows == [["\t=header", "id", "status"], ["\t=1+1", "1", "non_arab"],
                    ["بِسْمِ الله", "2", "berhasil"], ["", "3", "kosong"],
                    ["line\nnext", "4", "non_arab"]]
    pd.testing.assert_frame_equal(frame, before)


def upload_snapshot(app, name, data):
    app.session_state.upload_snapshot = {"name": name, "size": len(data), "data": data,
                                         "digest": sha256(data).hexdigest()}
    app.session_state.file_result = None
    app.session_state.file_result_signature = None
    app.session_state.file_processing = None
    app.run()


@pytest.mark.parametrize("data", [b"\x00\x01\x02", "الحمد\x00لله".encode("utf-16"), b"",
                                   pytest.param(b"x" * (5 * 1024 * 1024 + 1), id="over-5MB")])
def test_invalid_txt_is_rejected_by_ui_and_server_process_guard(data):
    app = AppTest.from_file(str(APP_DIR / "app.py"), default_timeout=60).run()
    app.radio(key="page").set_value("Diakritisasi").run()
    upload_snapshot(app, "invalid.txt", data)
    assert app.button(key="process_file").disabled
    import inference_engine as backend
    with patch.object(backend, "process_uploaded_file", wraps=backend.process_uploaded_file) as process:
        # A forged/stale button event must also be checked on the server.
        button = app.button(key="process_file")
        button.proto.disabled = False  # Test transport only; app recomputes validation on rerun.
        button.click().run()
        assert process.call_count == 0
    assert not app.exception
    assert app.session_state.file_result is None and app.session_state.file_processing is None
    assert len(app.get("download_button")) == 1  # Only the disabled manual result download.


@pytest.mark.parametrize("encoding", ["utf-8", "utf-16", "utf-16-be"])
def test_valid_txt_encoding_uses_the_unchanged_backend(encoding):
    app = AppTest.from_file(str(APP_DIR / "app.py"), default_timeout=60).run()
    app.radio(key="page").set_value("Diakritisasi").run()
    text = "الْحَمْدُ لِلَّهِ\tرب العالمين\r\n\r\nabc\n"
    data = text.encode(encoding)
    if encoding == "utf-16-be":
        data = b"\xfe\xff" + data
    upload_snapshot(app, "valid.txt", data)
    assert not app.button(key="process_file").disabled
    app.button(key="process_file").click().run()
    assert not app.exception and app.session_state.file_result["success"]
    result = app.session_state.file_result
    assert result["status_summary"] == {"berhasil": 1, "kosong": 1, "non_arab": 1}
    assert result["prediction"].encode("utf-8") == result["download_bytes"]
    assert app.session_state.upload_snapshot["data"] == data


def test_csv_backend_output_preview_and_status_are_not_mutated():
    app = AppTest.from_file(str(APP_DIR / "app.py"), default_timeout=60).run()
    app.radio(key="page").set_value("Diakritisasi").run()
    data = ('teks,info,id\nالْحَمْدُ لِلَّهِ,=1+1,1\nabc,"+SUM(1,1)",2\n,,3\n'
            'الحمد abc,-12,4\n"سطر\nعربي",ملاحظة,5\n').encode("utf-8")
    upload_snapshot(app, "export.csv", data)
    app.button(key="process_file").click().run()
    assert not app.exception and app.session_state.file_result["success"]
    result = app.session_state.file_result
    frame = result["dataframe"]
    before = frame.copy(deep=True)
    raw_download = result["download_bytes"]
    statuses = dict(result["status_summary"])
    exported = spreadsheet_safe_csv(frame)
    rows = list(csv.reader(StringIO(exported.decode("utf-8-sig"), newline="")))
    assert rows[0] == list(frame.columns)
    assert [row[2] for row in rows[1:]] == ["1", "2", "3", "4", "5"]
    assert rows[1][1] == "\t=1+1" and rows[2][1] == "\t+SUM(1,1)" and rows[4][1] == "-12"
    assert frame.loc[0, "info"] == "=1+1" and frame.loc[1, "info"] == "+SUM(1,1)"
    assert result["download_bytes"] == raw_download and b"\t=1+1" not in raw_download
    pd.testing.assert_frame_equal(frame, before)
    assert result["status_summary"] == statuses == {"berhasil": 2, "non_arab": 1, "kosong": 1, "campuran": 1}
    preview = app.dataframe[0].value
    assert preview.loc[0, "info"] == "=1+1"
    assert any("CSV unduhan diamankan" in caption.value for caption in app.caption)
