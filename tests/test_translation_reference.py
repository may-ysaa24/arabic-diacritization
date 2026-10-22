"""V3 original review/identity checks; no internet rights or pilot dependencies."""
from copy import deepcopy
from io import BytesIO
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'streamlit_app'))
import translation_reference as r
from test_translation_prediction import direct_fixture
from translation_test_fixture import write_units, SENTINEL


def load(f):
    return r.display_units(f['data'], f['frame'], 'teks_gundul')


def test_verified_original_requires_no_internet_permission_registry(direct_fixture):
    f = direct_fixture
    assert len(load(f)) == 1
    assert load(f)[0]['translation']['text_indonesian'] == SENTINEL
    assert not list(f['path'].parent.glob('*permission*'))


@pytest.mark.parametrize('case', ['version', 'paragraph', 'unit_id', 'chunk', 'hash', 'vowel_hash',
    'span', 'record', 'page', 'reversed', 'missing', 'digest', 'empty_text', 'no_author', 'internet_origin',
    'draft', 'needs_review', 'reviewer', 'date', 'text_review_hash', 'target_review_hash', 'extra_legacy_field'])
def test_invalid_or_unreviewed_original_hidden(direct_fixture, case):
    f = direct_fixture
    unit = f['unit']
    target = unit['targets'][0]
    if case == 'version': unit['dataset_version'] = 'WRONG'
    elif case == 'paragraph': unit['paragraph_id'] = 'WRONG'
    elif case == 'unit_id': unit['unit_id'] = 'WRONG'
    elif case == 'chunk': target['chunk_id'] = 'WRONG'
    elif case == 'hash': target['arabic_gundul_sha256'] = '0' * 64
    elif case == 'vowel_hash': target['arabic_text_sha256'] = '0' * 64
    elif case == 'span': target['source_span']['end_exclusive'] += 1
    elif case == 'record': target['source_record_1based'] += 1
    elif case == 'page': target['pdf_page'] += 1
    elif case == 'reversed': unit['targets'].reverse()
    elif case == 'missing': unit['targets'].pop()
    elif case == 'digest': unit['target_digest'] = '0' * 64
    elif case == 'empty_text': unit['translation']['text_indonesian'] = ''
    elif case == 'no_author': unit['translation']['translator'] = None
    elif case == 'internet_origin': unit['translation']['origin'] = 'internet'
    elif case in ('draft', 'needs_review'): unit['verification']['status'] = case
    elif case == 'reviewer': unit['verification']['reviewer'] = None
    elif case == 'date': unit['verification']['reviewed_at'] = '2026-10-22'
    elif case == 'text_review_hash': unit['verification']['reviewed_text_sha256'] = '0' * 64
    elif case == 'target_review_hash': unit['verification']['reviewed_target_digest'] = '0' * 64
    elif case == 'extra_legacy_field': unit['permission_registry_digest'] = '0' * 64
    write_units(f['path'], [unit])
    assert load(f) == []


@pytest.mark.parametrize('case', ['csv_bytes', 'csv_id', 'csv_text', 'column', 'duplicate_id', 'missing_column',
    'catalog_changed', 'catalog_missing', 'context_changed', 'duplicate_unit', 'malformed_unit', 'oversize', 'outside_storage'])
def test_input_and_storage_fail_closed(direct_fixture, monkeypatch, case):
    f = direct_fixture
    if case == 'csv_bytes': f['data'] += b'\n'
    elif case == 'csv_id': f['frame'].loc[0, 'id'] = 'FQDEMO_16_00001'
    elif case == 'csv_text': f['frame'].loc[0, 'teks_gundul'] += ' '
    elif case == 'column': assert r.display_units(f['data'], f['frame'], 'judul_arab') == []; return
    elif case == 'duplicate_id': f['frame'].loc[1, 'id'] = f['frame'].loc[0, 'id']
    elif case == 'missing_column': f['frame'].drop(columns='chunk_id', inplace=True)
    elif case == 'catalog_changed':
        catalog = r.load_catalog(); catalog['books'][0]['dataset']['row_count'] += 1
        path = f['path'].parent / 'changed_catalog.json'; path.write_text(json.dumps(catalog), encoding='utf-8')
        monkeypatch.setattr(r, 'CATALOG_PATH', path)
    elif case == 'catalog_missing': monkeypatch.setattr(r, 'CATALOG_PATH', f['path'].parent / 'MISSING.json')
    elif case == 'context_changed': monkeypatch.setattr(r, 'load_context', lambda book: (_ for _ in ()).throw(ValueError('Changed source hash')))
    elif case == 'duplicate_unit': write_units(f['path'], [f['unit'], f['unit']])
    elif case == 'malformed_unit': f['path'].write_text('{', encoding='utf-8')
    elif case == 'oversize': f['path'].write_bytes(b'X' * (r.MAX_REFERENCE_BYTES + 1))
    elif case == 'outside_storage': monkeypatch.setattr(r, 'ORIGINAL', f['path'].parent / 'OTHER')
    assert load(f) == []


def test_malformed_record_does_not_block_valid_paragraph(direct_fixture):
    f = direct_fixture
    with f['path'].open('a', encoding='utf-8') as stream:
        stream.write('{malformed\n')
    assert len(load(f)) == 1


def test_draft_change_seen_without_cached_translation(direct_fixture):
    f = direct_fixture
    assert load(f)
    f['unit']['verification']['status'] = 'draft'
    write_units(f['path'], [f['unit']])
    assert load(f) == []


def test_json_duplicate_keys_rejected(tmp_path):
    path = tmp_path / 'duplicate.json'
    path.write_text('{"id":1,"id":2}', encoding='utf-8')
    with pytest.raises(ValueError): r._read_json(path)


@pytest.mark.parametrize('number', range(17))
def test_all_demo_books_keep_identity_and_paragraph_context(number):
    book = r.load_catalog()['books'][number]
    path = r.DEMO / 'CSV' / book['dataset']['file']
    if not path.exists(): pytest.skip('Private demo dataset unavailable')
    data = path.read_bytes()
    frame = pd.read_csv(BytesIO(data), dtype=str, keep_default_na=False)
    assert r.match_demo_book(data, frame, 'teks_gundul')['kitab_id'] == f'{number:02d}'
    assert r.match_demo_book(data + b'\n', frame, 'teks_gundul') is None
    context = r.load_context(book)
    assert len(context['refs']) == len(frame)
    assert all(row['id'] in context['refs'] for row in frame.to_dict('records'))


def test_runtime_has_no_internet_or_pilot_dependencies():
    for filename in ('translation_reference.py', 'translation_panel.py', 'translation_prediction.py'):
        source = (ROOT / 'streamlit_app' / filename).read_text(encoding='utf-8')
        assert all(value not in source for value in ('external_sources', 'pilot_thaharah', 'permission_registry',
                                                      'requests.', 'urlopen(', 'terjemahankitab.com'))


def draftify(unit):
    unit['translation']['origin'] = 'ai_assisted_original'
    unit['verification'] = {key: (r.DRAFT_STATUS if key == 'status' else None)
                            for key in unit['verification']}


def test_preview_requires_explicit_opt_in_at_reader_and_prediction_binding(direct_fixture):
    from translation_prediction import prediction_pairs
    f = direct_fixture
    draftify(f['unit'])
    write_units(f['path'], [f['unit']])
    assert load(f) == []
    units = r.display_units(f['data'], f['frame'], 'teks_gundul', preview_drafts=True)
    assert len(units) == 1
    assert prediction_pairs(units, f['frame'], f['result']) == []
    assert len(prediction_pairs(units, f['frame'], f['result'], preview_drafts=True)) == 1


@pytest.mark.parametrize('case', ['wrong_hash', 'missing_target', 'wrong_paragraph', 'human_origin',
                                 'legacy_draft', 'fake_reviewer', 'fake_review_hash', 'promoted_without_review'])
def test_preview_preserves_identity_and_does_not_fake_verification(direct_fixture, case):
    f = direct_fixture
    unit = f['unit']
    draftify(unit)
    if case == 'wrong_hash': unit['targets'][0]['arabic_gundul_sha256'] = '0' * 64
    elif case == 'missing_target': unit['targets'].pop()
    elif case == 'wrong_paragraph': unit['paragraph_id'] = 'WRONG'
    elif case == 'human_origin': unit['translation']['origin'] = 'original'
    elif case == 'legacy_draft': unit['verification']['status'] = 'draft'
    elif case == 'fake_reviewer': unit['verification']['reviewer'] = 'UNTRUE_REVIEW'
    elif case == 'fake_review_hash': unit['verification']['reviewed_text_sha256'] = '0' * 64
    elif case == 'promoted_without_review': unit['verification']['status'] = 'verified'
    write_units(f['path'], [unit])
    assert r.display_units(f['data'], f['frame'], 'teks_gundul', preview_drafts=True) == []
    assert load(f) == []


def test_real_complete_thaharah_and_repeated_titles():
    path = r.DEMO / 'CSV/01_Thaharah.csv'
    if not path.exists() or not r.TRANSLATIONS_PATH.exists(): pytest.skip('Local draft data unavailable')
    data = path.read_bytes()
    frame = pd.read_csv(BytesIO(data), dtype=str, keep_default_na=False)
    units = r.display_units(data, frame, 'teks_gundul', preview_drafts=True)
    assert len(units) == 317
    covered_ids = [t['segment_id'] for u in units for t in u['targets']]
    assert covered_ids == frame['id'].tolist() == [f'FQDEMO_01_{i:05d}' for i in range(1, 329)]
    assert len(set(covered_ids)) == 328
    assert len({u['paragraph_id'] for u in units}) == 317
    assert [[t['segment_id'] for t in u['targets']] for u in units if len(u['targets']) > 1] == [
        ['FQDEMO_01_00027', 'FQDEMO_01_00028'], ['FQDEMO_01_00043', 'FQDEMO_01_00044'],
        ['FQDEMO_01_00061', 'FQDEMO_01_00062'], ['FQDEMO_01_00065', 'FQDEMO_01_00066'],
        ['FQDEMO_01_00110', 'FQDEMO_01_00111'], ['FQDEMO_01_00122', 'FQDEMO_01_00123'],
        ['FQDEMO_01_00229', 'FQDEMO_01_00230'], ['FQDEMO_01_00247', 'FQDEMO_01_00248'],
        ['FQDEMO_01_00250', 'FQDEMO_01_00251', 'FQDEMO_01_00252'],
        ['FQDEMO_01_00327', 'FQDEMO_01_00328']]
    assert '00051' in units[47]['source_note']
    by_id = {t['segment_id']: u for u in units for t in u['targets']}
    assert by_id['FQDEMO_01_00050']['paragraph_id'] != by_id['FQDEMO_01_00051']['paragraph_id']
    assert '00050' in by_id['FQDEMO_01_00051']['source_note']
    assert 'lam yarudda' in by_id['FQDEMO_01_00080']['source_note']
    assert 'tatslits' in by_id['FQDEMO_01_00098']['source_note']
    assert by_id['FQDEMO_01_00100']['paragraph_id'] != by_id['FQDEMO_01_00101']['paragraph_id']
    assert '00100/00101' in by_id['FQDEMO_01_00101']['source_note']
    assert '00150/00151' in by_id['FQDEMO_01_00150']['source_note']
    assert by_id['FQDEMO_01_00150']['paragraph_id'] != by_id['FQDEMO_01_00151']['paragraph_id']
    assert '00150/00151' in by_id['FQDEMO_01_00151']['source_note']
    assert '00200/00201' in by_id['FQDEMO_01_00200']['source_note']
    assert by_id['FQDEMO_01_00200']['paragraph_id'] != by_id['FQDEMO_01_00201']['paragraph_id']
    assert '00200/00201' in by_id['FQDEMO_01_00201']['source_note']
    assert '00250/00251' in by_id['FQDEMO_01_00250']['source_note']
    assert by_id['FQDEMO_01_00250'] is by_id['FQDEMO_01_00251'] is by_id['FQDEMO_01_00252']
    assert by_id['FQDEMO_01_00252']['paragraph_id'] != by_id['FQDEMO_01_00253']['paragraph_id']
    assert '00252/00253' in by_id['FQDEMO_01_00253']['source_note']
    assert by_id['FQDEMO_01_00300']['paragraph_id'] != by_id['FQDEMO_01_00301']['paragraph_id']
    assert '00300/00301' in by_id['FQDEMO_01_00300']['source_note']
    assert by_id['FQDEMO_01_00327'] is by_id['FQDEMO_01_00328']
    assert 'empat tahun' in by_id['FQDEMO_01_00303']['translation']['text_indonesian']
    assert 'bukan klaim medis' in by_id['FQDEMO_01_00303']['source_note']
    assert 'PRIORITAS' in by_id['FQDEMO_01_00270']['source_note']
    assert 'PRIORITAS' in by_id['FQDEMO_01_00318']['source_note']
    assert 'la yahrumu minha' in by_id['FQDEMO_01_00250']['source_note']
    assert '00185' in by_id['FQDEMO_01_00183']['source_note']
    assert 'PRIORITAS' in by_id['FQDEMO_01_00188']['source_note']
    assert 'lima' in by_id['FQDEMO_01_00200']['translation']['text_indonesian']
    assert by_id['FQDEMO_01_00200']['translation']['text_indonesian'].endswith(',')
    assert 'enam' in by_id['FQDEMO_01_00112']['translation']['text_indonesian']
    assert 'lima' in by_id['FQDEMO_01_00114']['translation']['text_indonesian']
    assert 'PRIORITAS' in by_id['FQDEMO_01_00110']['source_note']
    assert 'PRIORITAS' in by_id['FQDEMO_01_00145']['source_note']
    assert all(u['verification']['status'] == r.DRAFT_STATUS for u in units)
    assert all(u['translation']['origin'] == 'ai_assisted_original' for u in units)
    assert all(u['verification']['reviewer'] is None for u in units)
    assert units[1]['translation']['text_indonesian'] == units[8]['translation']['text_indonesian']
    assert units[1]['paragraph_id'] != units[8]['paragraph_id']
    assert 'daftar belum lengkap' in units[2]['source_note'].lower()
    assert 'damah' in units[7]['translation']['text_indonesian']
    assert 'fathah' in units[7]['source_note']
    assert '00011' in units[9]['source_note']
    assert r.display_units(data, frame, 'teks_gundul') == []


def test_real_multisegment_drafts_are_not_displayed_with_partial_predictions():
    from translation_prediction import prediction_pairs
    path = r.DEMO / 'CSV/01_Thaharah.csv'
    if not path.exists() or not r.TRANSLATIONS_PATH.exists(): pytest.skip('Local draft data unavailable')
    data = path.read_bytes()
    frame = pd.read_csv(BytesIO(data), dtype=str, keep_default_na=False)
    units = r.display_units(data, frame, 'teks_gundul', preview_drafts=True)
    output = frame.copy()
    output['TEST_prediction'] = ['TEST_ONLY_' + key for key in output['id']]
    output['TEST_status'] = 'berhasil'
    result = {'success': True, 'input_type': 'csv', 'text_column': 'teks_gundul',
              'dataframe': output, 'output_columns': {'prediction': 'TEST_prediction', 'status': 'TEST_status'}}
    assert len(prediction_pairs(units, frame, result, preview_drafts=True)) == 317
    output.loc[output['id'] == 'FQDEMO_01_00028', 'TEST_status'] = 'gagal'
    output.loc[output['id'] == 'FQDEMO_01_00044', 'TEST_prediction'] = ''
    output.loc[output['id'] == 'FQDEMO_01_00062', 'TEST_status'] = 'gagal'
    output.loc[output['id'] == 'FQDEMO_01_00066', 'TEST_prediction'] = ''
    output.loc[output['id'] == 'FQDEMO_01_00111', 'TEST_status'] = 'gagal'
    output.loc[output['id'] == 'FQDEMO_01_00123', 'TEST_prediction'] = ''
    output.loc[output['id'] == 'FQDEMO_01_00230', 'TEST_status'] = 'gagal'
    output.loc[output['id'] == 'FQDEMO_01_00248', 'TEST_prediction'] = ''
    output.loc[output['id'] == 'FQDEMO_01_00251', 'TEST_status'] = 'gagal'
    output.loc[output['id'] == 'FQDEMO_01_00328', 'TEST_status'] = 'gagal'
    pairs = prediction_pairs(units, frame, result, preview_drafts=True)
    assert len(pairs) == 307
    covered = {segment['segment_id'] for pair in pairs for segment in pair['segments']}
    assert covered == {f'FQDEMO_01_{i:05d}' for i in range(1, 329)} - {
        'FQDEMO_01_00027', 'FQDEMO_01_00028', 'FQDEMO_01_00043', 'FQDEMO_01_00044',
        'FQDEMO_01_00061', 'FQDEMO_01_00062', 'FQDEMO_01_00065', 'FQDEMO_01_00066',
        'FQDEMO_01_00110', 'FQDEMO_01_00111', 'FQDEMO_01_00122', 'FQDEMO_01_00123',
        'FQDEMO_01_00229', 'FQDEMO_01_00230', 'FQDEMO_01_00247', 'FQDEMO_01_00248',
        'FQDEMO_01_00250', 'FQDEMO_01_00251', 'FQDEMO_01_00252',
        'FQDEMO_01_00327', 'FQDEMO_01_00328'}
    output.loc[output['id'] == 'FQDEMO_01_00251', 'TEST_status'] = 'berhasil'
    output.loc[output['id'] == 'FQDEMO_01_00252', 'TEST_status'] = 'gagal'
    last_failed = prediction_pairs(units, frame, result, preview_drafts=True)
    assert {s['segment_id'] for p in last_failed for s in p['segments']} == covered
    assert prediction_pairs(units, frame, result) == []
