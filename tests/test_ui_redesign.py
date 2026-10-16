"""Regression coverage for the redesigned academic Streamlit UI.

All inference still goes through the original modular backend; this test
checks UI-only changes without modifying checkpoints or source datasets.
"""
from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "streamlit_app" / "app.py"


def test_redesigned_pages_load_and_preserve_navigation():
    app = AppTest.from_file(str(APP), default_timeout=45).run()
    assert not app.exception
    for page in ("Diakritisasi", "Contoh Teks", "Tentang Model", "Beranda"):
        app.radio(key="page").set_value(page).run()
        assert not app.exception
    assert "Beranda" in app.radio(key="page").options


def test_empty_manual_request_has_readable_error():
    app = AppTest.from_file(str(APP), default_timeout=45).run()
    app.radio(key="page").set_value("Diakritisasi").run()
    app.button(key="process_manual").click().run()
    assert not app.exception
    assert app.session_state["manual_result"]["success"] is False
    assert "Masukkan teks Arab" in app.session_state["manual_result"]["message"]


def test_manual_result_can_be_reset_without_stale_output():
    app = AppTest.from_file(str(APP), default_timeout=45).run()
    app.radio(key="page").set_value("Diakritisasi").run()
    app.text_area(key="_manual_input").input("الحمد لله رب العالمين").run()
    app.button(key="process_manual").click().run()
    result = app.session_state["manual_result"]
    assert result and result["success"]
    app.button(key="reset_manual").click().run()
    assert not app.exception
    assert app.session_state["manual_result"] is None
    assert app.session_state["manual_input"] == ""
