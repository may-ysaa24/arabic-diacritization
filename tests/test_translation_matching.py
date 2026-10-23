"""Real canonical sources; model-free lookup plus actual-backend AppTest checks."""
from copy import deepcopy
from io import BytesIO
from pathlib import Path
import sys
from unittest.mock import patch
from zipfile import ZipFile

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'streamlit_app'))
import translation_matching as m
import translation_reference as r


@pytest.fixture(scope='module')
def corpus():
    if not (r.DEMO / 'CSV/01_Thaharah.csv').exists():
        pytest.skip('Local canonical demo dataset unavailable')
    index = m._index(m._signature())
    entry = next(e for e in index[0].values() if e['unit'] and len(e['text']) > 100
                 and len(e['targets']) == 1 and len(index[1][e['text']]) == 1)
    return index, entry


def csv_result(frame, column):
    output = frame.copy(deep=True)
    output['TEST_prediction'] = frame[column]
    output['TEST_status'] = 'berhasil'
    return {'success': True, 'input_type': 'csv', 'text_column': column, 'dataframe': output,
            'output_columns': {'prediction': 'TEST_prediction', 'status': 'TEST_status'}}


def text_result(text, kind='manual'):
    return {'success': True, 'input_type': kind, 'input_text': text, 'prediction': text}


def text_lookup(text, preview=True):
    return m.lookup(text_result(text), text=text, preview_drafts=preview)


@pytest.mark.parametrize('a,b,equal', [
    ('إِنَّ الماء', 'إن الماء', True), ('إن\n  الماء', 'إن الماء', True),
    ('ا\u0654ن الماء', 'أن الماء', True), ('ان الماء', 'إن الماء', False),
    ('علي', 'على', False), ('رحمة', 'رحمه', False), ('ماء،', 'ماء', False),
    ('مـاء', 'ماء', False), ('ماء ٧', 'ماء 7', False), ('لا يجوز', 'يجوز', False)])
def test_limited_normalization(a, b, equal):
    assert (m.normalize(a) == m.normalize(b)) is equal


def test_original_demo_and_reserialized_reordered_csv(corpus):
    frame = pd.read_csv(r.DEMO / 'CSV/01_Thaharah.csv', dtype=str, keep_default_na=False)
    original = m.lookup(csv_result(frame, 'teks_gundul'), dataframe=frame, column='teks_gundul', preview_drafts=True)
    assert len(original['pairs']) == 317 and original['counts'] == {'tersedia': 328}
    changed = frame.iloc[::-1].copy()
    changed['local_note'] = 'Different metadata, not a canonical identity'
    changed = changed[list(reversed(changed.columns))]
    blob = changed.to_csv(index=False, sep=';').encode('utf-8-sig')
    changed = pd.read_csv(BytesIO(blob), sep=';', dtype=str, keep_default_na=False)
    assert r.match_demo_book(blob, changed, 'teks_gundul') is None
    result = csv_result(changed, 'teks_gundul')
    before = result['dataframe'].copy(deep=True)
    report = m.lookup(result, dataframe=changed, column='teks_gundul', preview_drafts=True)
    assert len(report['pairs']) == 317 and report['counts'] == {'tersedia': 328}
    pd.testing.assert_frame_equal(result['dataframe'], before)
    assert {p['unit']['unit_id'] for p in report['pairs']} == {p['unit']['unit_id'] for p in original['pairs']}


def test_plain_csv_without_demo_columns(corpus):
    _, e = corpus
    frame = pd.DataFrame({'arabic': [e['text']], 'notes': ['local']})
    report = m.lookup(csv_result(frame, 'arabic'), dataframe=frame, column='arabic', preview_drafts=True)
    assert len(report['pairs']) == 1 and report['counts'] == {'tersedia': 1}


def test_real_txt_complete_book_rejects_repeated_titles(corpus):
    text = (r.DEMO / 'TXT/01_Thaharah.txt').read_text(encoding='utf-8-sig')
    report = m.lookup(text_result(text, 'txt'), text=text, preview_drafts=True)
    assert not report.get('error')
    assert report['total'] == 317
    assert len(report['pairs']) == 315 and report['counts'] == {'ambigu': 2, 'tersedia': 315}
    assert all(p['unit']['verification']['status'] == r.DRAFT_STATUS for p in report['pairs'])


def test_manual_paragraph_and_soft_wrapped_txt(corpus):
    _, e = corpus
    text = e['text']
    assert text_lookup(text)['pairs'][0]['unit'] == e['unit']
    wrapped = '\n'.join(' '.join(text.split()[i:i+4]) for i in range(0, len(text.split()), 4))
    report = m.lookup(text_result(wrapped, 'txt'), text=wrapped, preview_drafts=True)
    assert len(report['pairs']) == 1 and report['pairs'][0]['unit'] == e['unit']
    assert m.normalize(report['pairs'][0]['segments'][0]['prediction']) == text
    assert text_lookup(text, preview=False)['counts'] == {'belum_terverifikasi': 1}


def test_whole_multisegment_paragraph_and_incomplete_segment(corpus):
    index, _ = corpus
    e = next(e for e in index[0].values() if e['unit'] and len(e['targets']) > 1
             and len(index[1][e['text']]) == 1)
    assert len(text_lookup(e['text'])['pairs']) == 1
    context = r.load_context(r.load_catalog()['books'][1])
    rows = [context['demo'][t['segment_id']] for t in e['targets']]
    first = rows[0]['teks_gundul']
    assert not text_lookup(first)['pairs']
    frame = pd.DataFrame(rows).iloc[::-1]
    report = m.lookup(csv_result(frame, 'teks_gundul'), dataframe=frame, column='teks_gundul', preview_drafts=True)
    assert len(report['pairs']) == 1
    assert [s['segment_id'] for s in report['pairs'][0]['segments']] == [t['segment_id'] for t in e['targets']]


def test_untranslated_book_unknown_similar_and_mixed_input(corpus):
    index, e = corpus
    shalat = next(e for e in index[0].values() if e['kitab_id'] == '02' and len(e['text']) > 100
                  and len(index[1][e['text']]) == 1)
    assert text_lookup(shalat['text'])['counts'] == {'terjemahan_belum_tersedia': 1}
    unknown = 'هذا نص جديد خارج قاعدة البيانات'
    for text in (unknown, e['text'][:-1], e['text'] + ' جديد', e['text'].replace(' ', '', 1)):
        assert not text_lookup(text)['pairs']
    report = text_lookup(e['text'] + '\n\n' + unknown + '\n\n' + shalat['text'])
    assert len(report['pairs']) == 1 and report['total'] == 3
    assert report['counts'] == {'tersedia': 1, 'tidak_cocok': 1, 'terjemahan_belum_tersedia': 1}


def test_all_duplicate_segment_groups_are_ambiguous_without_identity(corpus):
    index, _ = corpus
    duplicates = [text for text, choices in index[2].items() if len(choices) > 1]
    assert len(duplicates) >= 7
    for text in duplicates:
        report = text_lookup(text)
        assert not report['pairs'] and report['counts'] == {'ambigu': 1}


@pytest.mark.parametrize('field,value', [('id', 'FQDEMO_01_99999'), ('chunk_id', 'WRONG'),
    ('paragraph_id', 'P999_PAR001'), ('page', '999'), ('dataset_version', 'wrong'), ('kitab', 'Shalat')])
def test_forged_or_conflicting_metadata_cannot_authorize_content(corpus, field, value):
    _, e = corpus
    frame = pd.DataFrame({'arabic': [e['text']], field: [value]})
    report = m.lookup(csv_result(frame, 'arabic'), dataframe=frame, column='arabic', preview_drafts=True)
    assert not report['pairs'] and report['counts'] == {'tidak_cocok': 1}


@pytest.mark.parametrize('case', ['stale_csv', 'failed_row', 'different_model_base', 'failed_txt', 'stale_manual'])
def test_saved_predictions_must_match_and_successful(corpus, case):
    _, e = corpus
    text = e['text']
    if case in ('stale_csv', 'failed_row', 'different_model_base'):
        frame = pd.DataFrame({'arabic': [text], 'note': ['before']})
        result = csv_result(frame, 'arabic')
        if case == 'stale_csv': result['dataframe'].loc[0, 'note'] = 'after'
        if case == 'failed_row': result['dataframe'].loc[0, 'TEST_status'] = 'gagal'
        if case == 'different_model_base': result['dataframe'].loc[0, 'TEST_prediction'] += ' خطأ'
        report = m.lookup(result, dataframe=frame, column='arabic', preview_drafts=True)
    else:
        result = text_result(text)
        if case == 'failed_txt': result.update(input_type='txt', status_summary={'gagal': 1})
        else: result['input_text'] += ' خطأ'
        report = m.lookup(result, text=text, preview_drafts=True)
    assert not report['pairs']


def test_predicted_marks_remain_exact_and_blank_boundaries_are_not_joined(corpus):
    _, e = corpus
    text = e['text']
    prediction = ''.join(c + '\u064e' if '\u0621' <= c <= '\u064a' else c for c in text)
    result = text_result(text); result['prediction'] = prediction
    report = m.lookup(result, text=text, preview_drafts=True)
    assert report['pairs'][0]['segments'][0]['prediction'] == prediction
    words = text.split(); broken = ' '.join(words[:4]) + '\n\n' + ' '.join(words[4:])
    assert not text_lookup(broken)['pairs']


def test_duplicate_input_cannot_double_whole_paragraph(corpus):
    _, e = corpus
    report = text_lookup(e['text'] + '\n\n' + e['text'])
    assert not report['pairs'] and report['counts'] == {'paragraf_tidak_lengkap': 2}


def test_limits_cache_and_missing_canonical_source(corpus, monkeypatch, tmp_path):
    assert not text_lookup('x' * 250_001)['pairs']
    assert 'error' in text_lookup('x' * 250_001)
    before = m._index.cache_info()
    text_lookup(corpus[1]['text'])
    assert m._index.cache_info().maxsize == 1 and m._index.cache_info().hits > before.hits
    monkeypatch.setattr(r, 'DEMO', tmp_path)
    assert 'error' in text_lookup(corpus[1]['text'])


def test_additional_path_preserves_final_review_gate(corpus, tmp_path, monkeypatch):
    import json
    _, e = corpus
    unit = deepcopy(e['unit'])
    unit['verification'] = {'status': 'verified', 'reviewer': 'TEST_ONLY',
        'reviewed_at': '2026-10-23T00:00:00+07:00',
        'reviewed_text_sha256': r.sha_text(unit['translation']['text_indonesian']),
        'reviewed_target_digest': unit['target_digest']}
    path = tmp_path / 'TEST_ONLY.jsonl'
    monkeypatch.setattr(r, 'ORIGINAL', tmp_path)
    monkeypatch.setattr(r, 'TRANSLATIONS_PATH', path)
    path.write_text(json.dumps(unit, ensure_ascii=False) + '\n', encoding='utf-8')
    assert len(text_lookup(e['text'], preview=False)['pairs']) == 1
    unit['translation']['text_indonesian'] += ' TEST_ONLY_STALE_REVIEW'
    path.write_text(json.dumps(unit, ensure_ascii=False) + '\n', encoding='utf-8')
    assert not text_lookup(e['text'], preview=False)['pairs']


def test_app_whole_real_thaharah_txt_pages_and_independent_manual_state(corpus):
    from test_ui_translation_panel import app_ready, upload, open_panel
    import inference_engine as backend
    text = (r.DEMO / 'TXT/01_Thaharah.txt').read_text(encoding='utf-8-sig')
    app = app_ready()
    file_id = upload(app, 'Thaharah.txt', text.encode())
    with patch.object(backend, 'process_uploaded_file', wraps=backend.process_uploaded_file) as infer:
        app.button(key='process_file').click().run()
        assert not app.exception and infer.call_count == 1
        before = app.session_state.file_result['download_bytes']
        report = m.lookup(app.session_state.file_result, text=text, preview_drafts=True)
        assert len(report['pairs']) == 315 and report['counts']['ambigu'] == 2
        open_panel(app, file_id)
        app.session_state[f'translation_reference_{file_id}'] = True
        app.checkbox(key=f'translation_reference_draft_{file_id}').check().run()
        for number in (1, 16, 32, 1):
            app.session_state[f'translation_reference_{file_id}'] = True
            app.selectbox(key=f'translation_reference_page_{file_id}').select(number).run()
            assert not app.exception
            expected = report['pairs'][(number - 1) * 10:number * 10]
            assert len([item for item in app.text if item.value.startswith('Paragraf:')]) == len(expected) <= 10
            for pair in expected:
                assert any(item.value == pair['unit']['translation']['text_indonesian'] for item in app.text)
                assert any(item.value == pair['segments'][0]['prediction'] for item in app.text)
        assert infer.call_count == 1 and app.session_state.file_result['download_bytes'] == before
        # Both tabs render on a full rerun; the manual panel must not reset TXT's page.
        # AppTest does not retain native expander open state between widget runs.
        app.session_state[f'translation_reference_{file_id}'] = True
        app.text_area(key='_manual_input').input(corpus[1]['text']).run()
        app.session_state[f'translation_reference_{file_id}'] = True
        app.button(key='process_manual').click().run()
        app.session_state[f'translation_reference_{file_id}'] = True
        app.selectbox(key=f'translation_reference_page_{file_id}').select(16).run()
        app.session_state[f'translation_reference_{file_id}'] = True
        app.run()
        assert app.selectbox(key=f'translation_reference_page_{file_id}').value == 16
        assert infer.call_count == 1 and app.session_state.file_result['download_bytes'] == before


@pytest.mark.parametrize('mode', ['csv', 'txt', 'manual'])
def test_app_actual_backend_content_lookup_without_reinference_or_export_changes(corpus, mode):
    from test_ui_translation_panel import app_ready, upload, open_panel
    import inference_engine as backend
    _, e = corpus
    text = e['text']
    app = app_ready()
    if mode == 'manual':
        app.text_area(key='_manual_input').input(text).run()
        file_id = 'manual'
    else:
        data = (pd.DataFrame({'arabic': [text]}).to_csv(index=False).encode() if mode == 'csv' else text.encode())
        file_id = upload(app, 'ordinary.' + mode, data)
    method = 'predict_long_text' if mode == 'manual' else 'process_uploaded_file'
    with patch.object(backend, method, wraps=getattr(backend, method)) as infer:
        app.button(key='process_manual' if mode == 'manual' else 'process_file').click().run()
        assert not app.exception and infer.call_count == 1
        result = app.session_state.manual_result if mode == 'manual' else app.session_state.file_result
        before = deepcopy(result)
        open_panel(app, file_id)
        assert any(item.value == 'Terjemahan belum tersedia' for item in app.info)
        app.session_state[f'translation_reference_{file_id}'] = True
        app.checkbox(key=f'translation_reference_draft_{file_id}').check().run()
        assert not app.exception
        assert any(item.value == e['unit']['translation']['text_indonesian'] for item in app.text)
        assert any(item.value == r.CONTENT_DRAFT_LABEL for item in app.caption)
        prediction = (result['dataframe'].iloc[0][result['output_columns']['prediction']]
                      if mode == 'csv' else result['prediction'])
        assert any(item.value == prediction for item in app.text)
        for _ in range(2):
            open_panel(app, file_id, False); open_panel(app, file_id)
        assert infer.call_count == 1
        if mode == 'manual':
            assert app.session_state.manual_result == before
        else:
            assert app.session_state.file_result['download_bytes'] == before['download_bytes']
            app.button(key='prepare_queue_zip').click().run()
            with ZipFile(BytesIO(app.session_state.queue_zip)) as archive:
                assert all(e['unit']['translation']['text_indonesian'].encode() not in archive.read(n)
                           for n in archive.namelist())
            assert infer.call_count == 1
