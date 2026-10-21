"""UI regression: references remain outside inference and model result exports."""
from io import BytesIO
from pathlib import Path
import sys
from unittest.mock import patch
from zipfile import ZipFile

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
    # AppTest currently has no native expander setter. Exercise its tracked
    # session-state contract; actual click/fragment transport is tested in Edge.
    app.session_state[f'translation_reference_{file_id}'] = opened
    app.run()
    assert not app.exception


def test_panel_is_lazy_and_repeated_open_does_not_infer_or_change_exports():
    app = app_ready()
    file_id = upload(app, 'demo.csv', DEMO)
    with patch.object(backend, 'process_uploaded_file', wraps=backend.process_uploaded_file) as infer, \
         patch.object(reference, 'display_units', return_value=[]) as lookup:
        assert not any(e.label == 'Lihat Terjemahan Referensi' for e in app.expander)
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
        assert not any(e.label == 'Lihat Terjemahan Referensi' for e in app.expander)


def test_panel_reference_plain_text_not_prediction_and_never_exported():
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
        assert len([e for e in app.text if e.value == sentinel]) == 1
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
        assert not any(e.label == 'Lihat Terjemahan Referensi' for e in app.expander)
        app.selectbox(key='_active_file').select(first).run()
        open_panel(app, first)
        app.selectbox(key='_active_file').select(second).run()
        assert app.session_state.filtered_state.get(f'translation_reference_{second}', False) is False
        open_panel(app, second)
        app.selectbox(key='_active_file').select(txt).run()
        assert not any(e.label == 'Lihat Terjemahan Referensi' for e in app.expander)
        app.text_area(key='_manual_input').input('الحمد لله').run()
        app.button(key='process_manual').click().run()
        assert app.session_state.manual_result['success']
        app.button(key='process_all_files').click().run()
        assert infer.call_count == 3
        assert all(v['file_result']['download_bytes'] == before[k] for k, v in app.session_state.upload_files.items())
        app.selectbox(key='_active_file').select(first).run()
        app.button(key='reset_file').click().run()
        assert first not in app.session_state.upload_files
        assert not app.session_state.filtered_state.get(f'translation_reference_{first}', False)
        app.button(key='reset_all_files').click().run()
        assert not app.session_state.upload_files
        assert not any(e.label == 'Lihat Terjemahan Referensi' for e in app.expander)
