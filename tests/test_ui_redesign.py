"""Regression coverage for the redesigned academic Streamlit UI.

All inference still goes through the original modular backend; this test
checks UI-only changes without modifying checkpoints or source datasets.
"""
from pathlib import Path
from hashlib import sha256
from html import escape
import sys
from unittest.mock import patch

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "streamlit_app" / "app.py"
sys.path.insert(0, str(APP.parent))
from result_presentation import arabic_markup, indonesian_markup


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


@pytest.mark.parametrize('text', ['الْحَمْدُ لِلَّهِ\nرَبِّ الْعَالَمِينَ', '<script>alert(1)</script>',
                                  '" & <img src=x onerror=alert(1)>', ''])
def test_readable_result_markup_preserves_exact_escaped_text(text):
    arabic = arabic_markup(text)
    indonesia = indonesian_markup(text)
    assert 'lang="ar" dir="rtl"' in arabic and escape(text) in arabic
    assert 'lang="id" dir="ltr"' in indonesia and escape(text) in indonesia
    assert '<script>' not in arabic and '<img ' not in indonesia


@pytest.mark.parametrize('mode,expected', [
    ('manual', '33d2856a05ca3b79c3a8c9c8a40e52caa2dd9110c49d11320a1d239b3424ee84'),
    ('txt', '0a2c118d326e189a7f3271b8849382fdea59838c867ceb817e70b80651bafbd0'),
    ('csv', '094fb75a787b4255ef2cb3bf16a8a811babb2d0a0aa8905398702ec92e6e9d4d')])
def test_model_and_export_bytes_equal_pre_redesign_baseline(mode, expected):
    # Captured through the actual UI at ee1d8c0 before presentation changes.
    from test_ui_translation_panel import app_ready, upload
    app = app_ready()
    text = 'الحمد لله'
    if mode == 'manual':
        app.text_area(key='_manual_input').input(text).run()
        app.button(key='process_manual').click().run()
        output = app.session_state.manual_result['prediction'].encode()
    else:
        data = (text + '\n\nabc\n' if mode == 'txt' else 'arabic,info\n' + text + ',=1+1\nabc,-12\n').encode()
        upload(app, 'baseline.' + mode, data)
        app.button(key='process_file').click().run()
        output = app.session_state.file_result['download_bytes']
    assert not app.exception and sha256(output).hexdigest() == expected


def test_result_view_defaults_to_arabic_and_translations_display_without_checkbox():
    import pandas as pd
    import translation_reference as reference
    import inference_engine as backend
    from test_ui_translation_panel import app_ready, has_text, open_panel
    path = reference.DEMO / 'CSV/01_Thaharah.csv'
    if not path.exists(): pytest.skip('Local canonical dataset unavailable')
    source = pd.read_csv(path, dtype=str, keep_default_na=False).iloc[4]['teks_gundul']
    app = app_ready()
    app.text_area(key='_manual_input').input(source).run()
    with patch.object(backend, 'predict_long_text', wraps=backend.predict_long_text) as infer:
        app.button(key='process_manual').click().run()
        saved = dict(app.session_state.manual_result)
        assert app.button_group(key='translation_reference_view_manual').value == 'Arab Berharakat'
        assert not any(c.key == 'translation_reference_draft_manual' for c in app.checkbox)
        assert has_text(app, saved['prediction'])
        open_panel(app, 'manual')
        assert not any(c.key == 'translation_reference_draft_manual' for c in app.checkbox)
        assert has_text(app, saved['prediction'])
        assert not any(e.value == reference.CONTENT_DRAFT_LABEL for e in app.caption)
        assert not any(e.label == 'Detail Referensi' for e in app.expander)
        assert any('translation-indonesian' in item.proto.body for item in app.get('html'))
        open_panel(app, 'manual', False)
        assert infer.call_count == 1 and app.session_state.manual_result == saved
        from test_ui_experience import apply_correction
        correction = 'نص التصحيح التجريبي'
        apply_correction(app, correction)
        open_panel(app, 'manual')
        assert has_text(app, saved['prediction'])
        assert not has_text(app, correction)
        assert any('memakai hasil asli model' in e.value for e in app.info)
        assert app.session_state.manual_correction == correction and infer.call_count == 1


def test_csv_clipboard_uses_same_spreadsheet_safe_serializer_as_download():
    import json
    import re
    from test_ui_translation_panel import app_ready, upload
    from file_safety import spreadsheet_safe_csv
    app = app_ready()
    upload(app, 'safety.csv', 'arabic,info\nالحمد لله,=1+1\n'.encode())
    app.button(key='process_file').click().run()
    result = app.session_state.file_result
    body = next(item.proto.body for item in app.get('html') if 'id="copy_file_csv"' in item.proto.body)
    clipboard = json.loads(re.search(r'const text = (.*?);\n', body).group(1))
    assert clipboard == spreadsheet_safe_csv(result['dataframe']).decode('utf-8-sig')
    assert '\t=1+1' in clipboard and '<script>' not in clipboard


def test_ui1_manual_heading_counter_and_existing_input_limit_policy():
    from test_ui_translation_panel import app_ready
    app = app_ready()
    assert not app.exception
    assert app.text_area(key='_manual_input').proto.max_chars == 0
    html = '\n'.join(item.proto.body for item in app.get('html'))
    assert '<h1>Diakritisasi Teks Arab</h1>' in html
    assert '<h2>Masukan Teks Arab</h2>' in html and '<h2>Hasil Diakritisasi</h2>' in html
    assert 'id="manual_char_count">0</span>' in html
    assert '10.000 karakter per proses' not in html
    app.text_area(key='_manual_input').input('الحمد لله').run()
    assert app.session_state.manual_result is None


def test_ui1_correction_action_opens_editor_without_reinference():
    from test_ui_translation_panel import app_ready
    import inference_engine as backend
    app = app_ready()
    app.text_area(key='_manual_input').input('الحمد لله').run()
    with patch.object(backend,'predict_long_text',wraps=backend.predict_long_text) as infer:
        app.button(key='process_manual').click().run()
        original = dict(app.session_state.manual_result)
        app.button(key='open_manual_correction').click().run()
        assert not app.exception and app.session_state['manual_correction_editor'] is True
        assert app.session_state.manual_result == original and infer.call_count == 1


def test_ui1_three_real_manual_paragraphs_paginate_without_changing_model_result():
    import pandas as pd
    import translation_reference as reference
    import inference_engine as backend
    from test_ui_translation_panel import app_ready, open_panel, readable_values
    path = reference.DEMO / 'CSV/01_Thaharah.csv'
    if not path.exists(): pytest.skip('Local canonical dataset unavailable')
    frame = pd.read_csv(path,dtype=str,keep_default_na=False)
    source = '\n\n'.join(frame.iloc[i]['teks_gundul'] for i in (91,92,93))
    app = app_ready()
    app.text_area(key='_manual_input').input(source).run()
    with patch.object(backend,'predict_long_text',wraps=backend.predict_long_text) as infer:
        app.button(key='process_manual').click().run()
        original = dict(app.session_state.manual_result)
        open_panel(app,'manual')
        assert app.selectbox(key='translation_reference_page_manual').options == ['1 / 3','2 / 3','3 / 3']
        for number in (1,2,3):
            app.selectbox(key='translation_reference_page_manual').select(number).run()
            assert not app.exception
            from test_ui_translation_panel import translation_values
            assert len(translation_values(app)) == 1
            assert len(readable_values(app)) == 4  # One pair plus two optional comparison texts.
        assert app.session_state.manual_result == original and infer.call_count == 1


def test_result_card_titles_have_requested_icon_order_and_no_decorative_arabic_letter():
    from result_presentation import pane_heading
    indonesia, arabic = pane_heading('id'), pane_heading('ar')
    assert indonesia.index('result-icon-translate') < indonesia.index('Terjemahan Indonesia')
    assert arabic.index('Teks Arab Berharakat') < arabic.index('result-icon-book')
    assert 'ع' not in indonesia + arabic


def test_success_summary_uses_saved_measurements_and_active_correction_without_inference():
    from test_ui_translation_panel import app_ready
    import inference_engine as backend
    app = app_ready()
    source = 'الحمد لله'
    app.text_area(key='_manual_input').input(source).run()
    with patch.object(backend, 'predict_long_text', wraps=backend.predict_long_text) as infer:
        app.button(key='process_manual').click().run()
        app.session_state['manual_processing']['elapsed_seconds'] = .432
        app.run()
        summary = next(e.proto.body for e in app.get('html') if 'class="processing-summary result-success"' in e.proto.body)
        assert f'<dd>{len(source)}</dd>' in summary and '<dd>0,432 dtk</dd>' in summary
        assert '<dd>Prediksi Model</dd>' in summary
        from test_ui_experience import apply_correction
        apply_correction(app, 'نص تصحيح')
        summary = next(e.proto.body for e in app.get('html') if 'class="processing-summary result-success"' in e.proto.body)
        assert '<dd>Koreksi Pengguna</dd>' in summary
        assert infer.call_count == 1 and not app.exception


def test_failure_never_shows_success_summary_and_summary_escapes_values():
    from test_ui_translation_panel import app_ready
    from result_presentation import success_summary_markup
    app = app_ready()
    app.button(key='process_manual').click().run()
    assert not any('class="processing-summary result-success"' in e.proto.body for e in app.get('html'))
    body = success_summary_markup([('Status', '<script>alert(1)</script>')], '<img src=x onerror=alert(1)>')
    assert '<script>' not in body and '<img ' not in body
    assert '&lt;script&gt;' in body and '&lt;img ' in body


@pytest.mark.parametrize('legacy_value', [False, True])
def test_removed_preview_state_does_not_gate_saved_translation_or_modify_data(legacy_value):
    import pandas as pd
    import translation_reference as reference
    import inference_engine as backend
    from test_ui_translation_panel import app_ready, open_panel, translation_values
    path = reference.DEMO / 'CSV/01_Thaharah.csv'
    if not path.exists(): pytest.skip('Local canonical dataset unavailable')
    source = pd.read_csv(path, dtype=str, keep_default_na=False).iloc[4]['teks_gundul']
    digest = sha256(reference.TRANSLATIONS_PATH.read_bytes()).hexdigest()
    app = app_ready()
    app.text_area(key='_manual_input').input(source).run()
    with patch.object(backend, 'predict_long_text', wraps=backend.predict_long_text) as infer:
        app.button(key='process_manual').click().run()
        saved = dict(app.session_state.manual_result)
        key = 'translation_reference_draft_manual'
        app.session_state[key] = legacy_value
        open_panel(app, 'manual')
        assert translation_values(app) and key not in app.session_state.filtered_state
        assert not any(e.label == 'Detail Referensi' for e in app.expander)
        assert not any(e.value == reference.CONTENT_DRAFT_LABEL for e in app.caption)
        assert not any('Catatan sumber tersedia' in e.value or 'FQDEMO_' in e.value for e in app.caption)
        assert not any('input-book-label' in e.proto.body for e in app.get('html'))
        assert app.session_state.manual_result == saved and infer.call_count == 1
    assert sha256(reference.TRANSLATIONS_PATH.read_bytes()).hexdigest() == digest


def test_about_explains_unverified_static_translation_database():
    from test_ui_translation_panel import app_ready
    app = app_ready()
    app.radio(key='page').set_value('Tentang Model').run()
    assert not app.exception
    text = '\n'.join(e.value for e in app.markdown)
    assert 'referensi statis berbantuan AI' in text and 'belum diverifikasi ahli' in text
    assert 'bukan keluaran model BiLSTM–CRF' in text


@pytest.mark.parametrize('kind', ['outside', 'shalat'])
def test_automatic_translation_missing_preserves_saved_arabic(kind):
    from test_ui_translation_panel import app_ready, open_panel, has_text, translation_values
    source = 'السلام عليكم'
    if kind == 'shalat':
        import pandas as pd
        import translation_reference as reference
        path = reference.DEMO / 'CSV/02_Shalat.csv'
        if not path.exists(): pytest.skip('Local Shalat dataset unavailable')
        source = pd.read_csv(path, dtype=str, keep_default_na=False).iloc[10]['teks_gundul']
    app = app_ready()
    app.text_area(key='_manual_input').input(source).run()
    app.button(key='process_manual').click().run()
    saved = dict(app.session_state.manual_result)
    open_panel(app, 'manual')
    assert not app.exception and not translation_values(app)
    assert any(e.value == 'Terjemahan belum tersedia' for e in app.info)
    assert has_text(app, saved['prediction']) and app.session_state.manual_result == saved
