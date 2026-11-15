"""Upload presentation uses existing processing, binding, and byte-for-byte exports."""
from copy import deepcopy
from unittest.mock import patch

import pandas as pd
import pytest

from test_ui_translation_panel import app_ready, upload, open_panel, translation_values, has_text
import inference_engine as backend
import translation_reference as reference
from upload_design import file_row
from translation_panel import visible_page_numbers


@pytest.mark.parametrize('kind', ['txt', 'csv'])
def test_choose_view_before_processing_and_reuse_saved_result(kind):
    path = reference.DEMO / 'CSV/01_Thaharah.csv'
    if not path.exists(): pytest.skip('Local canonical dataset unavailable')
    text = pd.read_csv(path, dtype=str, keep_default_na=False).iloc[25]['teks_gundul']
    data = text.encode() if kind == 'txt' else pd.DataFrame({'arabic':[text]}).to_csv(index=False).encode()
    app = app_ready()
    with patch.object(backend, 'process_uploaded_file', wraps=backend.process_uploaded_file) as infer:
        file_id = upload(app, 'source.' + kind, data)
        open_panel(app, file_id)
        assert infer.call_count == 0 and app.session_state.file_result is None
        assert len([e for e in app.button_group if e.key == f'translation_reference_view_{file_id}']) == 1
        app.button(key='process_file').click().run()
        assert not app.exception and infer.call_count == 1 and len(translation_values(app)) == 1
        before = deepcopy(app.session_state.file_result)
        for _ in range(2):
            open_panel(app, file_id, False)
            assert not translation_values(app)
            open_panel(app, file_id)
            assert len(translation_values(app)) == 1
        assert infer.call_count == 1
        assert app.session_state.file_result['download_bytes'] == before['download_bytes']
        assert not any('Pratinjau draf lokal' in e.label for e in app.checkbox)


def test_row_is_escaped_and_uses_actual_size_and_validation_status():
    entry = {'upload_snapshot': {'name':'<img src=x onerror=alert(1)>.txt', 'size':42},
             'upload_validation_cache': {'validation':{'success':True}}, 'file_result':None}
    body = file_row(entry, active=True)
    assert '<img ' not in body and '&lt;img ' in body
    assert 'TXT · 42 byte' in body and 'Valid · Siap diproses' in body
    entry['upload_validation_cache']['validation'] = {'success':False, 'message':'Berkas kosong.'}
    body = file_row(entry)
    assert 'Tidak valid' in body and 'Berkas kosong.' in body and 'Siap diproses' not in body


def test_remove_inactive_row_keeps_active_result_and_clears_zip_without_inference():
    app = app_ready()
    first = upload(app, 'first.txt', 'الحمد لله'.encode())
    second = upload(app, 'second.txt', 'رب العالمين'.encode())
    with patch.object(backend, 'process_uploaded_file', wraps=backend.process_uploaded_file) as infer:
        app.button(key='process_all_files').click().run()
        app.button(key='prepare_queue_zip').click().run()
        before = app.session_state.file_result['download_bytes']
        app.button(key=f'remove_upload_{second}').click().run()
        assert not app.exception and list(app.session_state.upload_files) == [first]
        assert app.session_state.active_upload_id == first
        assert app.session_state.file_result['download_bytes'] == before
        assert app.session_state.queue_zip is None and infer.call_count == 2


def test_partial_csv_translation_has_complete_arabic_without_false_full_coverage():
    path = reference.DEMO / 'CSV/01_Thaharah.csv'
    if not path.exists(): pytest.skip('Local canonical dataset unavailable')
    text = pd.read_csv(path, dtype=str, keep_default_na=False).iloc[25]['teks_gundul']
    app = app_ready()
    file_id = upload(app, 'partial.csv', pd.DataFrame({'arabic':[text, 'السلام عليكم']}).to_csv(index=False).encode())
    open_panel(app, file_id)
    app.button(key='process_file').click().run()
    assert not app.exception and len(translation_values(app)) == 1
    assert any('1 dari 2 bagian masukan' in e.value for e in app.caption)
    assert any(e.label == 'Hasil Arab lengkap' for e in app.expander)
    result = app.session_state.file_result
    column = result['output_columns']['prediction']
    assert all(has_text(app, value) for value in result['dataframe'][column])


@pytest.mark.parametrize('counts,title', [
    ({'berhasil':1,'gagal':1}, 'Selesai dengan kegagalan sebagian'),
    ({'non_arab':1}, 'Selesai tanpa prediksi')])
def test_file_summary_never_calls_partial_or_unpredicted_output_fully_successful(counts, title):
    app = app_ready()
    upload(app, 'result.txt', 'الحمد لله'.encode())
    app.button(key='process_file').click().run()
    # Only presentation state in this test session; no source/model writes.
    app.session_state.file_result['status_summary'] = counts
    app.run()
    body = next(e.proto.body for e in app.get('html') if 'processing-summary-file' in e.proto.body)
    assert title in body and 'Berhasil diproses</h3>' not in body


@pytest.mark.parametrize('page,pages', [(1,1), (1,2), (2,2), (1,32), (2,32), (16,32), (31,32), (32,32)])
def test_numbered_pagination_is_bounded_and_keeps_current_and_adjacent_pages(page, pages):
    numbers = visible_page_numbers(page, pages)
    assert numbers == sorted(set(numbers)) and len(numbers) <= 5
    assert {1, page, pages} <= set(numbers)
    assert all(1 <= number <= pages for number in numbers)
    assert set(range(max(1, page-1), min(pages, page+1)+1)) <= set(numbers)


@pytest.mark.parametrize('kind,count', [('txt','2 baris teks'), ('csv','2 baris data')])
def test_queue_row_counts_use_validated_data_not_guessed_paragraphs(kind, count):
    validation = {'success':True, 'text':'a\nb\n', 'dataframe':pd.DataFrame({'x':['a','b']})}
    entry = {'upload_snapshot':{'name':'file.'+kind, 'size':42},
             'upload_validation_cache':{'validation':validation}, 'file_result':None}
    assert count in file_row(entry) and 'paragraf' not in file_row(entry)


def test_top_process_button_uses_the_latest_column_from_active_settings():
    app = app_ready()
    upload(app, 'columns.csv', pd.DataFrame({'teks_gundul':['الحمد لله'], 'other':['رب العالمين']}).to_csv(index=False).encode())
    with patch.object(backend, 'process_uploaded_file', wraps=backend.process_uploaded_file) as infer:
        app.selectbox(key='_csv_column').select('other').run()
        assert app.session_state.file_result is None and infer.call_count == 0
        app.button(key='process_file').click().run()
        saved = app.session_state.file_result
        assert not app.exception and saved['success'] and infer.call_count == 1
        assert saved['dataframe']['other'].tolist() == ['رب العالمين']
        assert app.session_state.file_result_signature[2] == 'other'
        app.selectbox(key='_csv_column').select('teks_gundul').run()
        assert app.session_state.file_result is None and infer.call_count == 1
