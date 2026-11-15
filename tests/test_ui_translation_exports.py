"""Explicit export controls stay independent of legacy downloads and pagination."""
from copy import deepcopy
from io import BytesIO
from unittest.mock import patch
from zipfile import ZipFile

import pandas as pd

from test_ui_translation_panel import app_ready, upload, open_panel
import inference_engine as backend
import translation_reference as r
import translation_exports as x


def expand(app, identity):
    # AppTest does not expose expander events. Set only its native bool state;
    # real browser interaction with this control is tested separately.
    app.session_state[f'v3_exports_{identity}'] = True
    app.run()
    assert not app.exception


def test_actual_csv_explicit_exports_preserve_old_zip_and_page():
    raw=(r.DEMO/'CSV/01_Thaharah.csv').read_bytes()
    app=app_ready();fid=upload(app,'Thaharah.csv',raw)
    with patch.object(backend,'process_uploaded_file',wraps=backend.process_uploaded_file) as infer:
        app.button(key='process_file').click().run();open_panel(app,fid)
        key=f'translation_reference_page_{fid}'
        app.selectbox(key=key).select(32).run()
        result=deepcopy(app.session_state.file_result)
        app.button(key='prepare_queue_zip').click().run();oldzip=app.session_state.queue_zip
        expand(app,fid)
        assert app.selectbox(key=key).value==app.session_state[key]==32
        assert any(b.proto.label=='Unduh CSV + Terjemahan' for b in app.get('download_button'))
        app.session_state[f'v3_exports_{fid}'] = True  # native expander state is not serialized by AppTest
        app.button(key=f'v3_prepare_zip_{fid}').click().run()
        assert not app.exception and infer.call_count==1
        assert app.session_state.queue_zip==oldzip
        with ZipFile(BytesIO(app.session_state.v3_export_zip['data'])) as archive,ZipFile(BytesIO(oldzip)) as old:
            assert all(archive.read(name)==old.read(name) for name in old.namelist())
            assert 'ringkasan_terjemahan_v3.csv' in archive.namelist()
        open_panel(app,fid,False);open_panel(app,fid)
        assert app.selectbox(key=key).value==32 and infer.call_count==1
        assert app.session_state.file_result['download_bytes']==result['download_bytes']
        pd.testing.assert_frame_equal(app.session_state.file_result['dataframe'],result['dataframe'])


def test_actual_manual_correction_substantive_and_mark_only_exports():
    import translation_matching as m
    index=m._index(m._signature())
    e=next(e for e in index[0].values() if e['draft_ok'] and len(e['text'])>100 and len(index[1][e['text']])==1)
    app=app_ready();app.text_area(key='_manual_input').input(e['text']).run()
    with patch.object(backend,'predict_long_text',wraps=backend.predict_long_text) as infer:
        app.button(key='process_manual').click().run()
        before=deepcopy(app.session_state.manual_result)
        expand(app,'manual')
        assert any(b.proto.label=='Unduh Arab + Terjemahan (TXT)' for b in app.get('download_button'))
        # Use the existing correction form, never modify the stored prediction.
        app.button(key='open_manual_correction').click().run()
        area=next(a for a in app.text_area if (a.key or '').startswith('_manual_correction_'))
        area.input(before['prediction']+' لا').run()
        next(b for b in app.button if b.label=='Terapkan Koreksi').click().run()
        expand(app,'manual')
        assert any('koreksi_teks_berubah' in c.value for c in app.caption)
        assert app.session_state.manual_result==before and infer.call_count==1
        app.button(key='restore_manual_model').click().run();expand(app,'manual')
        assert not any('koreksi_teks_berubah' in c.value for c in app.caption)
        assert app.session_state.manual_result==before and infer.call_count==1
