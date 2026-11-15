"""Result-scoped pagination; native widget persistence never invokes inference."""
from copy import deepcopy
from io import BytesIO
from unittest.mock import patch

import pandas as pd
import pytest

from test_ui_translation_panel import app_ready, upload, open_panel, translation_values, has_text
from test_translation_legacy_csv import legacy
import inference_engine as backend
import translation_reference as ref
import translation_matching as matching


def assert_page(app, identity, units, number, size=10):
    assert not app.exception
    key = f'translation_reference_page_{identity}'
    assert app.selectbox(key=key).value == app.session_state[key] == number
    current = units[(number - 1) * size:number * size]
    pages = (len(units) + size - 1) // size
    end = min(number * size, len(units))
    assert any(e.value == f'Paragraf {(number - 1) * size + 1}–{end} dari {len(units)} · Halaman {number} dari {pages}'
               for e in app.caption)
    assert translation_values(app) == [u['translation']['text_indonesian'] for u in current]


@pytest.fixture(scope='module')
def thaharah():
    raw = (ref.DEMO / 'CSV/01_Thaharah.csv').read_bytes()
    frame = pd.read_csv(BytesIO(raw), dtype=str, keep_default_na=False)
    units = ref.display_units(raw, frame, 'teks_gundul', preview_drafts=True)
    assert len(units) == 317
    return raw, frame, units


def test_process_all_preserves_unchanged_active_result_and_views(thaharah):
    raw, _, units = thaharah
    app = app_ready(); fid = upload(app, 'Long.csv', raw)
    key = f'translation_reference_page_{fid}'
    arabic_key = f'translation_reference_arabic_page_{fid}'
    with patch.object(backend, 'process_uploaded_file', wraps=backend.process_uploaded_file) as infer:
        app.button(key='process_file').click().run(); open_panel(app, fid)
        before = deepcopy(app.session_state.file_result)
        app.selectbox(key=key).select(32).run(); assert_page(app, fid, units, 32)
        app.button(key='prepare_queue_zip').click().run(); archive = app.session_state.queue_zip
        app.button(key='process_all_files').click().run()
        assert_page(app, fid, units, 32)
        assert infer.call_count == 1 and app.session_state.queue_zip == archive
        open_panel(app, fid, False)
        app.selectbox(key=arabic_key).select(33).run()
        app.button(key='process_all_files').click().run()
        assert app.selectbox(key=arabic_key).value == app.session_state[arabic_key] == 33
        open_panel(app, fid); assert_page(app, fid, units, 32)
        # Adding and processing another file cannot change the active result.
        tid = upload(app, 'Other.txt', 'الحمد لله'.encode())
        assert app.session_state.active_upload_id == fid
        app.button(key='process_all_files').click().run()
        assert_page(app, fid, units, 32)
        assert infer.call_count == 2 and app.session_state.upload_files[tid]['file_result']['success']
        pd.testing.assert_frame_equal(app.session_state.file_result['dataframe'], before['dataframe'])
        assert app.session_state.file_result['download_bytes'] == before['download_bytes']
        # Same content but a new user-requested processing generation must reset.
        app.button(key='process_file').click().run(); assert_page(app, fid, units, 1)
        assert infer.call_count == 3
        app.selectbox(key=key).select(32).run(); open_panel(app, fid, False)
        app.button(key='process_file').click().run()
        assert app.selectbox(key=arabic_key).value == app.session_state[arabic_key] == 1
        open_panel(app, fid); assert_page(app, fid, units, 1)
        assert infer.call_count == 4
        assert app.session_state.file_result['download_bytes'] == before['download_bytes']


def test_file_switch_and_shrinking_result_reset_without_stale_pages(thaharah):
    raw, _, units = thaharah
    app = app_ready(); fid = upload(app, 'Long.csv', raw)
    with patch.object(backend, 'process_uploaded_file', wraps=backend.process_uploaded_file) as infer:
        app.button(key='process_file').click().run(); open_panel(app, fid)
        key = f'translation_reference_page_{fid}'
        app.selectbox(key=key).select(32).run()
        before = app.session_state.file_result['download_bytes']
        with patch.object(ref, 'display_units', return_value=units[:7]):
            app.run(); assert_page(app, fid, units[:7], 1)
            assert len(app.selectbox(key=key).options) == 1
        app.run(); assert_page(app, fid, units, 1)
        assert infer.call_count == 1 and app.session_state.file_result['download_bytes'] == before
        app.selectbox(key=key).select(32).run()
        text = matching._index(matching._signature())[0][units[2]['paragraph_id']]['text']
        tid = upload(app, 'Short.txt', text.encode())
        app.selectbox(key='_active_file').select(tid).run()
        app.button(key='process_all_files').click().run(); open_panel(app, tid)
        assert app.selectbox(key=f'translation_reference_page_{tid}').value == 1
        app.selectbox(key='_active_file').select(fid).run(); open_panel(app, fid)
        assert_page(app, fid, units, 1)
        assert infer.call_count == 2
        assert app.session_state.file_result['download_bytes'] == before


def test_manual_view_persistence_and_explicit_new_result_reset():
    index = matching._index(matching._signature())
    entries = [e for e in index[0].values() if e['kitab_id'] == '01' and e['draft_ok']
               and len(e['text']) > 80 and len(index[1][e['text']]) == 1][:3]
    text = '\n\n'.join(e['text'] for e in entries); units = [e['unit'] for e in entries]
    app = app_ready(); app.text_area(key='_manual_input').input(text).run()
    with patch.object(backend, 'predict_long_text', wraps=backend.predict_long_text) as infer:
        app.button(key='process_manual').click().run(); open_panel(app, 'manual')
        before = deepcopy(app.session_state.manual_result)
        app.selectbox(key='translation_reference_page_manual').select(3).run()
        assert_page(app, 'manual', units, 3, size=1)
        for _ in range(2):
            open_panel(app, 'manual', False)
            assert app.session_state['translation_reference_page_manual'] == 3
            open_panel(app, 'manual'); assert_page(app, 'manual', units, 3, size=1)
            app.run(); assert_page(app, 'manual', units, 3, size=1)
        assert infer.call_count == 1 and app.session_state.manual_result == before
        app.button(key='process_manual').click().run()
        assert_page(app, 'manual', units, 1, size=1)
        assert infer.call_count == 2
        assert app.session_state.manual_result['prediction'] == before['prediction']
        app.selectbox(key='translation_reference_page_manual').select(3).run()
        app.text_area(key='_manual_input').input(entries[0]['text']).run()
        app.button(key='process_manual').click().run()
        open_panel(app, 'manual')
        assert_page(app, 'manual', units[:1], 1, size=1)
        assert infer.call_count == 3


def test_real_new_short_column_result_resets_317_to_7(thaharah):
    _, frame, _ = thaharah
    frame = frame.copy()
    frame['short_text'] = [text if i < 7 else '' for i, text in enumerate(frame.teks_gundul)]
    app = app_ready(); fid = upload(app, 'Columns.csv', frame.to_csv(index=False).encode())
    with patch.object(backend, 'process_uploaded_file', wraps=backend.process_uploaded_file) as infer:
        app.button(key='process_file').click().run(); open_panel(app, fid)
        key = f'translation_reference_page_{fid}'
        app.selectbox(key=key).select(32).run()
        app.selectbox(key='_csv_column').select('short_text').run()
        assert app.session_state.file_result is None
        app.button(key='process_file').click().run()
        report = matching.lookup(app.session_state.file_result, dataframe=frame, column='short_text', preview_drafts=True)
        assert len(report['pairs']) == 7
        assert_page(app, fid, [p['unit'] for p in report['pairs']], 1)
        assert len(app.selectbox(key=key).options) == 1 and infer.call_count == 2


def test_legacy_csv_paging_preserves_multisegment_units_and_ambiguity():
    index = matching._index(matching._signature())
    selected = [e for e in index[0].values() if e['kitab_id'] == '02' and e['draft_ok']
                and len(e['text']) > 100 and len(index[1][e['text']]) == 1][:21]
    multi = next(e for e in selected if len(e['targets']) > 1)
    frames = []; ordinal = 1
    for source, e in enumerate(selected, 1):
        f = legacy(e['text'], 3)
        f['id'] = [str(ordinal + i) for i in range(3)]; ordinal += 3
        f['baris_sumber'] = str(source); frames.append(f)
    ambiguous = legacy('[ أنواع المياه ]', 1)
    ambiguous['id'] = str(ordinal); ambiguous['baris_sumber'] = '99'
    frames.append(ambiguous); frame = pd.concat(frames, ignore_index=True)
    app = app_ready(); fid = upload(app, 'Legacy.csv', frame.to_csv(index=False).encode())
    with patch.object(backend, 'process_uploaded_file', wraps=backend.process_uploaded_file) as infer:
        app.button(key='process_file').click().run(); open_panel(app, fid)
        before = deepcopy(app.session_state.file_result)
        report = matching.lookup(before, dataframe=frame, column='teks_gundul', preview_drafts=True)
        assert report['counts'] == {'ambigu': 1, 'tersedia': 63}
        units = [p['unit'] for p in report['pairs']]
        assert len(units) == len({u['unit_id'] for u in units}) == 21
        pair = next(p for p in report['pairs'] if p['unit'] == multi['unit'])
        assert pair['input_parts'] == 3 and len(pair['segments']) == 1
        for number in (1, 2, 3, 1):
            app.selectbox(key=f'translation_reference_page_{fid}').select(number).run()
            assert_page(app, fid, units, number)
            for p in report['pairs'][(number - 1) * 10:number * 10]:
                assert has_text(app, p['segments'][0]['prediction'])
        app.button(key='process_all_files').click().run()
        assert_page(app, fid, units, 1)
        assert infer.call_count == 1
        assert app.session_state.file_result['download_bytes'] == before['download_bytes']
        pd.testing.assert_frame_equal(app.session_state.file_result['dataframe'], before['dataframe'])
