"""UI regression: references remain outside inference and model result exports."""
from io import BytesIO
from pathlib import Path
import sys
from unittest.mock import patch
from zipfile import ZipFile
from html.parser import HTMLParser

import pytest
pytest.importorskip('streamlit')
import streamlit as st
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / 'streamlit_app'
sys.path.insert(0, str(APP))
import inference_engine as backend
import translation_reference as reference

DEMO = ('id,chunk_id,page,judul_arab,teks_gundul\n'
        'FQDEMO_01_00001,TEST_CHUNK,24,الطهارة,الحمد لله\n').encode()


def upload(app, name, data):
    item = BytesIO(data)
    item.name, item.size = name, len(data)
    def submit(*args, **kwargs):
        key = kwargs['key']
        st.session_state[key] = [item]
        kwargs['on_change'](key)
        return []
    with patch.object(st, 'file_uploader', side_effect=submit): app.run()
    app.run()
    assert not app.exception
    return list(app.session_state.upload_files)[-1]


def app_ready():
    app = AppTest.from_file(str(APP / 'app.py'), default_timeout=60).run()
    app.radio(key='page').set_value('Diakritisasi').run()
    return app


def open_panel(app, file_id, opened=True):
    app.button_group(key=f'translation_reference_view_{file_id}').set_value(
        'Arab + Terjemahan' if opened else 'Arab Berharakat').run()
    assert not app.exception


def readable_values(app, kind=None):
    """Read escaped presentation text, excluding scripts, CSS, and other HTML."""
    class Parser(HTMLParser):
        def __init__(self):
            super().__init__(); self.active = False; self.buffer = ''; self.values = []
        def handle_starttag(self, tag, attrs):
            classes = dict(attrs).get('class', '').split()
            if tag == 'div' and ('arabic-text' in classes or 'translation-indonesian' in classes) and (kind is None or kind in classes):
                self.active, self.buffer = True, ''
        def handle_data(self, data):
            if self.active: self.buffer += data
        def handle_endtag(self, tag):
            if tag == 'div' and self.active:
                self.values.append(self.buffer); self.active = False
    parser = Parser()
    for item in app.get('html'): parser.feed(item.proto.body)
    return parser.values


def has_text(app, value):
    return value in readable_values(app) or any(e.value == value for e in app.text)


def translation_values(app):
    return readable_values(app, 'translation-indonesian')


def test_panel_is_lazy_and_repeated_open_does_not_infer_or_change_exports():
    app = app_ready()
    file_id = upload(app, 'demo.csv', DEMO)
    with patch.object(backend, 'process_uploaded_file', wraps=backend.process_uploaded_file) as infer, \
         patch.object(reference, 'display_units', return_value=[]) as lookup:
        assert app.button_group(key=f'translation_reference_view_{file_id}').value == 'Arab Berharakat'
        app.button(key='process_file').click().run()
        assert infer.call_count == 1 and lookup.call_count == 0
        before = app.session_state.file_result['download_bytes']
        timing = dict(app.session_state.file_processing)
        app.button(key='prepare_queue_zip').click().run()
        zip_before = app.session_state.queue_zip
        for _ in range(2):
            open_panel(app, file_id)
            assert any(e.value == 'Terjemahan belum tersedia' for e in app.info)
            open_panel(app, file_id, False)
        assert lookup.call_count == 2 and infer.call_count == 1
        assert app.session_state.file_result['download_bytes'] == before
        assert app.session_state.file_processing == timing
        assert app.session_state.queue_zip == zip_before
        with ZipFile(BytesIO(zip_before)) as archive:
            assert len(archive.namelist()) == 2
        app.selectbox(key='_csv_column').select('judul_arab').run()
        assert app.session_state.file_result is None
        app.button(key='process_file').click().run()
        assert infer.call_count == 2
        assert any(e.label == 'Tampilan hasil' for e in app.button_group)
        open_panel(app, file_id)
        assert any(e.value == 'Terjemahan belum tersedia' for e in app.info)


def test_panel_rejects_unbound_reference_and_never_exports_it():
    app = app_ready()
    file_id = upload(app, 'demo.csv', DEMO)
    app.button(key='process_file').click().run()
    sentinel = 'TEST_DATA_NOT_A_TRANSLATION <script>TEST_ONLY</script>'
    unit = {'paragraph_id': 'TEST_PARAGRAPH', 'targets': [{'segment_id': 'FQDEMO_01_00001'},
                {'segment_id': 'FQDEMO_01_00002'}], 'arabic_gundul': 'TEST_ONLY_SOURCE',
            'translation': {'text_indonesian': sentinel, 'translator': 'TEST_ONLY'},
            'verification': {'reviewer': 'TEST_ONLY'}, 'source_parts': [{'source_url': 'https://example.invalid/TEST_ONLY'}]}
    with patch.object(reference, 'display_units', return_value=[unit]) as lookup:
        open_panel(app, file_id)
        assert not has_text(app, sentinel)
        assert lookup.call_args.args[0] == DEMO
        assert lookup.call_args.args[1].iloc[0]['teks_gundul'] == 'الحمد لله'
        assert lookup.call_args.args[2] == 'teks_gundul'
        app.button(key='prepare_queue_zip').click().run()
        assert sentinel.encode() not in app.session_state.file_result['download_bytes']
        with ZipFile(BytesIO(app.session_state.queue_zip)) as archive:
            assert all(sentinel.encode() not in archive.read(name) for name in archive.namelist())


def test_multifile_panel_stays_with_active_file_and_manual_txt_are_unchanged():
    app = app_ready()
    first = upload(app, 'one.csv', DEMO)
    second = upload(app, 'two.csv', DEMO.replace(b'00001', b'00002'))
    txt = upload(app, 'three.txt', 'الحمد لله'.encode())
    with patch.object(backend, 'process_uploaded_file', wraps=backend.process_uploaded_file) as infer:
        app.button(key='process_all_files').click().run()
        assert infer.call_count == 3
        before = {k: v['file_result']['download_bytes'] for k, v in app.session_state.upload_files.items()}
        app.selectbox(key='_active_file').select(txt).run()
        assert any(e.label == 'Tampilan hasil' for e in app.button_group)
        open_panel(app, txt)
        assert any(e.value == 'Terjemahan belum tersedia' for e in app.info)
        app.selectbox(key='_active_file').select(first).run()
        open_panel(app, first)
        app.selectbox(key='_active_file').select(second).run()
        assert app.button_group(key=f'translation_reference_view_{second}').value == 'Arab Berharakat'
        open_panel(app, second)
        app.selectbox(key='_active_file').select(txt).run()
        assert any(e.label == 'Tampilan hasil' for e in app.button_group)
        app.text_area(key='_manual_input').input('الحمد لله').run()
        app.button(key='process_manual').click().run()
        assert app.session_state.manual_result['success']
        app.button(key='process_all_files').click().run()
        assert infer.call_count == 3
        assert all(v['file_result']['download_bytes'] == before[k] for k, v in app.session_state.upload_files.items())
        app.selectbox(key='_active_file').select(first).run()
        app.button(key='reset_file').click().run()
        assert first not in app.session_state.upload_files
        assert f'translation_reference_view_{first}' not in app.session_state.filtered_state
        app.button(key='reset_all_files').click().run()
        assert not app.session_state.upload_files
        assert app.session_state.file_result is None
        assert app.session_state.manual_result['success']



def test_real_complete_thaharah_pagination_model_arabic_and_exports_are_independent():
    import pandas as pd
    path = reference.DEMO / 'CSV/01_Thaharah.csv'
    if not path.exists() or not reference.TRANSLATIONS_PATH.exists():
        pytest.skip('Local draft data unavailable')
    data = path.read_bytes()
    frame = pd.read_csv(BytesIO(data), dtype=str, keep_default_na=False)
    units = reference.display_units(data, frame, 'teks_gundul', preview_drafts=True)
    assert len(units) == 317
    assert sum(len(unit['targets']) for unit in units) == len(frame) == 328
    app = app_ready()
    file_id = upload(app, '01_Thaharah.csv', data)
    key = f'translation_reference_draft_{file_id}'
    page_key = f'translation_reference_page_{file_id}'
    def rerun_panel(widget):
        widget.run()
        assert not app.exception
    with patch.object(backend, 'process_uploaded_file', wraps=backend.process_uploaded_file) as infer:
        app.button(key='process_file').click().run()
        assert not app.exception and infer.call_count == 1
        before = app.session_state.file_result['download_bytes']
        timing = dict(app.session_state.file_processing)
        app.button(key='prepare_queue_zip').click().run()
        zip_before = app.session_state.queue_zip
        open_panel(app, file_id)
        assert not any(e.key == key for e in app.checkbox)
        result = app.session_state.file_result
        predicted = result['dataframe'].set_index('id')[result['output_columns']['prediction']]
        visited, segments = [], []
        # Visit every actual page, including the middle and the short last page.
        for number in range(1, 33):
            rerun_panel(app.selectbox(key=page_key).select(number))
            assert not app.exception
            expected = units[(number - 1) * 10:number * 10]
            paragraphs = translation_values(app)
            assert len(paragraphs) == len(expected) <= 10
            assert not any(e.value == reference.DRAFT_LABEL for e in app.warning)
            assert not any(e.value == reference.CONTENT_DRAFT_LABEL for e in app.caption)
            assert not any(e.label == 'Detail Referensi' for e in app.expander)
            assert paragraphs == [unit['translation']['text_indonesian'] for unit in expected]
            assert any(e.value == f'Paragraf {(number - 1) * 10 + 1}–{min(number * 10, 317)} dari 317 · Halaman {number} dari 32'
                       for e in app.caption)
            for unit in expected:
                assert has_text(app, unit['translation']['text_indonesian'])
                visited.append(unit['unit_id'])
                for target in unit['targets']:
                    assert has_text(app, predicted[target['segment_id']])
                    segments.append(target['segment_id'])
            assert not any(e.value.startswith('Verifikasi: verified') for e in app.text)
            assert infer.call_count == 1
            assert app.session_state.file_processing == timing
            assert app.session_state.file_result['download_bytes'] == before
            assert app.session_state.queue_zip == zip_before
        assert visited == [unit['unit_id'] for unit in units]
        assert segments == frame['id'].tolist()
        app.button(key=f'translation_reference_prev_{file_id}').click().run()
        assert app.selectbox(key=page_key).value == 31
        app.button(key=f'translation_reference_next_{file_id}').click().run()
        assert app.selectbox(key=page_key).value == 32
        assert app.button(key=f'translation_reference_next_{file_id}').disabled
        assert infer.call_count == 1
        # Number buttons share the selector's state and never duplicate cards
        # or invoke processing, including a jump from the middle to either end.
        rerun_panel(app.selectbox(key=page_key).select(16))
        for number in (17, 32, 1):
            app.button(key=f'translation_reference_number_{file_id}_{number}').click().run()
            assert not app.exception and app.selectbox(key=page_key).value == number
            assert translation_values(app) == [u['translation']['text_indonesian']
                                               for u in units[(number-1)*10:number*10]]
            buttons = [b for b in app.button if (b.key or '').startswith(f'translation_reference_number_{file_id}_')]
            assert len(buttons) <= 5 and infer.call_count == 1
            assert app.session_state.file_result['download_bytes'] == before
            assert app.session_state.queue_zip == zip_before
        rerun_panel(app.selectbox(key=page_key).select(32))
        # If the eligible result scope shrinks, page 32 must recover to page 1.
        with patch.object(reference, 'display_units', return_value=units[:7]):
            open_panel(app, file_id)
            assert app.selectbox(key=page_key).value == 1
            assert len(translation_values(app)) == 7
        open_panel(app, file_id)
        assert app.selectbox(key=page_key).value == 1
        rerun_panel(app.selectbox(key=page_key).select(32))
        open_panel(app, file_id, False)
        assert not translation_values(app)
        assert not any(e.key == page_key for e in app.selectbox)
        open_panel(app, file_id)
        assert app.selectbox(key=page_key).value == 32
        assert any(e.value == 'Paragraf 311–317 dari 317 · Halaman 32 dari 32' for e in app.caption)
        assert translation_values(app) == [u['translation']['text_indonesian'] for u in units[310:]]
        for unit in units[310:]:
            for target in unit['targets']:
                assert has_text(app, predicted[target['segment_id']])
        assert infer.call_count == 1
        assert app.session_state.file_result['download_bytes'] == before
        assert app.session_state.queue_zip == zip_before
        rerun_panel(app.selectbox(key=page_key).select(32))
        with ZipFile(BytesIO(zip_before)) as archive:
            for unit in units:
                text = unit['translation']['text_indonesian'].encode()
                assert text not in before
                assert all(text not in archive.read(name) for name in archive.namelist())
        txt = upload(app, 'other.txt', 'الحمد لله'.encode())
        app.selectbox(key='_active_file').select(txt).run()
        app.button(key='process_all_files').click().run()
        assert infer.call_count == 2 and app.session_state.file_result['success']
        assert any(e.label == 'Tampilan hasil' for e in app.button_group)
        app.selectbox(key='_active_file').select(file_id).run()
        open_panel(app, file_id)
        assert not any(e.key == key for e in app.checkbox)
        assert app.selectbox(key=page_key).value == 1
        assert len(translation_values(app)) == 10
        assert infer.call_count == 2
        assert app.session_state.file_result['download_bytes'] == before
