"""Stored-result pairing and positive UI tests; no real book translation."""
from copy import deepcopy
from pathlib import Path
import sys
from unittest.mock import patch
from io import BytesIO
from zipfile import ZipFile

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'streamlit_app'))
sys.path.insert(0, str(ROOT / 'scripts'))
import translation_reference as r
from translation_prediction import prediction_pairs
from translation_test_fixture import build_fixture, write_units, SENTINEL


@pytest.fixture
def direct_fixture(tmp_path, monkeypatch):
    if not (r.DEMO / 'CSV/01_Thaharah.csv').exists():
        pytest.skip('Private demo dataset unavailable')
    f = build_fixture(tmp_path, r)
    monkeypatch.setattr(r, 'ORIGINAL', tmp_path)
    monkeypatch.setattr(r, 'TRANSLATIONS_PATH', f['path'])
    frame = f['frame'].copy()
    frame['TEST_prediction'] = [f'TEST_MODEL_{i}' for i in range(len(frame))]
    frame['TEST_status'] = 'berhasil'
    f['result'] = {'success': True, 'input_type': 'csv', 'text_column': 'teks_gundul',
                   'dataframe': frame, 'output_columns': {'prediction': 'TEST_prediction', 'status': 'TEST_status'}}
    f['target_indices'] = [frame.index[frame['id'] == t['segment_id']][0] for t in f['unit']['targets']]
    return f


def pairs(f):
    return prediction_pairs(r.display_units(f['data'], f['frame'], 'teks_gundul'), f['frame'], f['result'])


def test_original_review_and_two_predictions_one_paragraph(direct_fixture):
    f = direct_fixture
    result = pairs(f)
    assert len(result) == 1
    assert result[0]['unit']['translation']['text_indonesian'] == SENTINEL
    assert [s['prediction'] for s in result[0]['segments']] == list(f['result']['dataframe'].loc[f['target_indices'], 'TEST_prediction'])


@pytest.mark.parametrize('case', ['id', 'duplicate', 'chunk', 'page', 'hash', 'missing', 'reordered',
    'failed', 'empty', 'nan', 'missing_column', 'collision', 'same_output_column', 'wrong_column', 'unsuccessful',
    'not_csv', 'stale_other_input_column', 'duplicate_column'])
def test_stale_or_partial_result_never_shows_whole_translation(direct_fixture, case):
    f = direct_fixture
    result, frame = f['result'], f['result']['dataframe']
    if case == 'id': frame.loc[0, 'id'] = 'FQDEMO_01_99999'
    elif case == 'duplicate': frame.loc[1, 'id'] = frame.loc[0, 'id']
    elif case == 'chunk': frame.loc[0, 'chunk_id'] = 'WRONG'
    elif case == 'page': frame.loc[0, 'page'] = '9'
    elif case == 'hash': frame.loc[0, 'teks_gundul'] += ' '
    elif case == 'missing': result['dataframe'] = frame.iloc[:1]
    elif case == 'reordered': result['dataframe'] = frame.iloc[::-1]
    elif case == 'failed': frame.loc[f['target_indices'][1], 'TEST_status'] = 'gagal'
    elif case == 'empty': frame.loc[f['target_indices'][1], 'TEST_prediction'] = ''
    elif case == 'nan': frame.loc[f['target_indices'][1], 'TEST_prediction'] = float('nan')
    elif case == 'missing_column': result['output_columns']['prediction'] = 'ABSENT'
    elif case == 'collision': result['output_columns']['prediction'] = 'teks_gundul'
    elif case == 'same_output_column': result['output_columns']['status'] = 'TEST_prediction'
    elif case == 'wrong_column': result['text_column'] = 'judul_arab'
    elif case == 'unsuccessful': result['success'] = False
    elif case == 'not_csv': result['input_type'] = 'txt'
    elif case == 'stale_other_input_column': frame.loc[0, 'kitab'] = 'WRONG'
    elif case == 'duplicate_column': result['dataframe'] = frame.rename(columns={'TEST_status': 'TEST_prediction'})
    assert pairs(f) == []


@pytest.mark.parametrize('case', ['version', 'paragraph', 'target_hash', 'target_chunk', 'target_page', 'duplicate_targets'])
def test_target_mismatch_rejected_even_if_helper_called_directly(direct_fixture, case):
    f = direct_fixture
    unit = deepcopy(f['unit'])
    if case == 'version': unit['dataset_version'] = 'WRONG'
    elif case == 'paragraph': unit['paragraph_id'] = 'WRONG'
    elif case == 'target_hash': unit['targets'][0]['arabic_gundul_sha256'] = '0' * 64
    elif case == 'target_chunk': unit['targets'][0]['chunk_id'] = 'WRONG'
    elif case == 'target_page': unit['targets'][0]['pdf_page'] = 99
    elif case == 'duplicate_targets': unit['targets'][1] = unit['targets'][0]
    assert prediction_pairs([unit], f['frame'], f['result']) == []


@pytest.mark.parametrize('status', ['draft', 'needs_review'])
def test_drafts_never_display_as_verified(direct_fixture, status):
    f = direct_fixture
    assert pairs(f)
    f['unit']['verification']['status'] = status
    write_units(f['path'], [f['unit']])
    assert pairs(f) == []


def test_changed_translation_requires_new_review(direct_fixture):
    f = direct_fixture
    assert pairs(f)
    f['unit']['translation']['text_indonesian'] += ' CHANGED'
    write_units(f['path'], [f['unit']])
    assert pairs(f) == []


def test_identical_titles_keep_independent_ids_and_partial_failure(direct_fixture):
    """Pure binding test with two already-authorized synthetic title units."""
    f = direct_fixture
    frame = f['frame'].iloc[f['target_indices']].reset_index(drop=True).copy()
    result = deepcopy(f['result'])
    result['dataframe'] = result['dataframe'].iloc[f['target_indices']].reset_index(drop=True).copy()
    frame.loc[1, 'teks_gundul'] = frame.loc[0, 'teks_gundul']
    result['dataframe']['teks_gundul'] = frame['teks_gundul']
    units = []
    for i in (0, 1):
        unit = deepcopy(f['unit'])
        unit['paragraph_id'] = f'TEST_TITLE_{i}'
        target = deepcopy(unit['targets'][i])
        target['paragraph_id'] = unit['paragraph_id']
        target['arabic_gundul_sha256'] = f['w'].sha_text(frame.loc[i, 'teks_gundul'])
        unit['targets'] = [target]
        unit['translation']['text_indonesian'] = f'TEST_ONLY_TITLE_{i}'
        units.append(unit)
    bound = prediction_pairs(units, frame, result)
    assert [p['unit']['paragraph_id'] for p in bound] == ['TEST_TITLE_0', 'TEST_TITLE_1']
    assert [p['segments'][0]['prediction'] for p in bound] == list(result['dataframe']['TEST_prediction'])
    result['dataframe'].loc[0, 'TEST_status'] = 'gagal'
    bound = prediction_pairs(units, frame, result)
    assert len(bound) == 1 and bound[0]['unit']['paragraph_id'] == 'TEST_TITLE_1'


def test_ui_actual_gates_model_predictions_columns_and_exports(direct_fixture):
    from test_ui_translation_panel import app_ready, upload, open_panel
    import inference_engine as backend
    f = direct_fixture
    app = app_ready()
    file_id = upload(app, 'TEST_ONLY.csv', f['data'])
    with patch.object(backend, 'process_uploaded_file', wraps=backend.process_uploaded_file) as infer:
        app.button(key='process_file').click().run()
        assert infer.call_count == 1 and not app.exception
        before = app.session_state.file_result['download_bytes']
        predictions = list(app.session_state.file_result['dataframe'].loc[f['target_indices'],
            app.session_state.file_result['output_columns']['prediction']])
        assert all(predictions)
        for _ in range(2):
            open_panel(app, file_id)
            assert len([e for e in app.text if e.value == SENTINEL]) == 1
            assert all(any(e.value == value for e in app.text) for value in predictions)
            assert len(app.columns) >= 2 and not app.exception
            assert any(f['unit']['paragraph_id'] in e.value for e in app.text)
            open_panel(app, file_id, False)
        app.button(key='prepare_queue_zip').click().run()
        assert infer.call_count == 1
        assert before == app.session_state.file_result['download_bytes']
        with ZipFile(BytesIO(app.session_state.queue_zip)) as archive:
            assert all(SENTINEL.encode() not in archive.read(name) for name in archive.namelist())
        # Another active CSV with one changed ID must never inherit the text.
        other = upload(app, 'OTHER.csv', f['data'].replace(b'00002', b'00003'))
        app.button(key='process_all_files').click().run()
        assert infer.call_count == 2
        app.selectbox(key='_active_file').select(other).run()
        open_panel(app, other)
        assert not any(e.value == SENTINEL for e in app.text)
        assert any(e.value == 'Terjemahan belum tersedia' for e in app.info)
        app.selectbox(key='_active_file').select(file_id).run()
        open_panel(app, file_id)
        assert any(e.value == SENTINEL for e in app.text)
        f['unit']['verification']['status'] = 'draft'
        write_units(f['path'], [f['unit']])
        open_panel(app, file_id, False)
        open_panel(app, file_id)
        assert not any(e.value == SENTINEL for e in app.text)
        assert any(e.value == 'Terjemahan belum tersedia' for e in app.info)
        assert infer.call_count == 2
