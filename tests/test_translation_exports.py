"""Additional exports preserve bindings, all original rows and legacy payloads."""
from copy import deepcopy
from io import BytesIO
from unittest.mock import patch
from zipfile import ZipFile

import pandas as pd
import pytest

from test_translation_matching import csv_result, text_result
from test_translation_legacy_csv import legacy
import translation_exports as x
import translation_matching as m
import translation_reference as r
import upload_queue as q


@pytest.fixture(scope='module')
def entry():
    index = m._index(m._signature())
    return next(e for e in index[0].values() if e['kitab_id'] == '02' and e['draft_ok']
                and len(e['targets']) > 1 and len(index[1][e['text']]) == 1)


def exports(frame, result=None):
    return x.build_exports(csv_result(frame, 'teks_gundul') if result is None else result,
                           dataframe=frame, column='teks_gundul')


def test_optional_trace_does_not_change_any_matching_decision(entry):
    frame = legacy(entry['text'], 3); result = csv_result(frame, 'teks_gundul')
    ordinary = m.lookup(result, dataframe=frame, column='teks_gundul', preview_drafts=True)
    detailed = m.lookup(result, dataframe=frame, column='teks_gundul', preview_drafts=True, include_parts=True)
    assert {k:v for k,v in detailed.items() if k != 'parts'} == ordinary
    assert detailed['parts'][0]['rows'] == [0,1,2]
    assert detailed['parts'][0]['paragraph_id'] == entry['unit']['paragraph_id']


def test_legacy_chunks_export_translation_once_with_row_relationships(entry):
    frame = legacy(entry['text'], 3); result = csv_result(frame, 'teks_gundul')
    before = result['dataframe'].copy(deep=True)
    bundle = exports(frame, result)
    assert len(bundle['records']) == bundle['matched'] == 1
    record = bundle['records'][0]
    assert record['rows'] == [0,1,2] and record['arabic'] == ' '.join(frame.teks_gundul)
    assert record['translation'] == entry['unit']['translation']['text_indonesian']
    text = bundle['txt'].decode('utf-8')
    assert text.count(x.NOTICE) == 1 and text.count(record['translation']) == 1
    out = pd.read_csv(BytesIO(bundle['csv']), dtype=str, keep_default_na=False)
    assert len(out) == len(frame)
    pd.testing.assert_frame_equal(out[list(before.columns)], before)
    c = bundle['columns']
    assert list(out[c['terjemahan_indonesia_v3']]) == [record['translation'], '', '']
    assert list(out[c['canonical_paragraph_id']]) == [entry['unit']['paragraph_id']] * 3
    assert list(out[c['baris_awal_terjemahan_v3']]) == ['1'] * 3
    pd.testing.assert_frame_equal(result['dataframe'], before)


@pytest.mark.parametrize('case', ['wrong_id', 'ambiguous', 'unknown', 'missing_marker', 'partial'])
def test_unavailable_parts_keep_arabic_and_never_guess_a_translation(entry, case):
    text = entry['text']; frame = pd.DataFrame({'id':['2'], 'teks_gundul':[text]})
    expected = 'tidak_cocok'
    if case == 'wrong_id': frame['id'] = 'FQDEMO_02_99999'
    elif case == 'ambiguous': frame['teks_gundul'] = '[ أنواع المياه ]'; expected='ambigu'
    elif case == 'unknown': frame['teks_gundul'] = 'هذا نص خارج الكتاب'
    elif case == 'missing_marker':
        frame = legacy(m._index(m._signature())[0]['P107_PAR002']['text'].replace('\u06dd', ''), 3)
    else:
        book = r.load_catalog()['books'][2]; context = r.load_context(book)
        frame['teks_gundul'] = context['demo'][entry['targets'][0]['segment_id']]['teks_gundul']
        expected = 'paragraf_tidak_lengkap'
    bundle = exports(frame)
    assert bundle['matched'] == 0 and set(bundle['counts']) == {expected}
    assert all(not record['translation'] for record in bundle['records'])
    assert m.normalize(' '.join(rec['arabic'] for rec in bundle['records'])) == m.normalize(' '.join(frame.teks_gundul))
    out = pd.read_csv(BytesIO(bundle['csv']), dtype=str, keep_default_na=False)
    assert len(out) == len(frame) and not out[bundle['columns']['terjemahan_indonesia_v3']].any()


@pytest.mark.parametrize('case', ['unchanged', 'marks_only', 'substantive', 'empty'])
def test_manual_active_correction_is_exported_without_stale_translation(entry, case):
    text = entry['text']; result = text_result(text)
    correction = {'unchanged': text, 'marks_only': text.replace('ا', 'اَ'),
                  'substantive': text + ' لا', 'empty': ''}[case]
    before = deepcopy(result)
    bundle = x.build_exports(result, text=text, active_text=correction)
    assert result == before
    assert m.normalize(' '.join(rec['arabic'] for rec in bundle['records'])) == m.normalize(correction)
    assert bundle['matched'] == (1 if case in ('unchanged','marks_only') else 0)
    if case in ('substantive','empty'):
        assert bundle['counts'] == {'koreksi_teks_berubah':1}
        assert entry['unit']['translation']['text_indonesian'] not in bundle['txt'].decode()


def test_column_collisions_formula_safety_and_unmatched_rows(entry):
    frame = pd.DataFrame({'id':['2','3'], 'teks_gundul':[entry['text'],'هذا نص آخر'],
                          'terjemahan_indonesia_v3':['USER_TRANSLATION', '=1+1'],
                          'canonical_paragraph_id':['USER_ID','USER_ID_2'], 'info':['=CMD()', '-12']})
    before = frame.copy(deep=True); bundle = exports(frame)
    assert bundle['columns']['terjemahan_indonesia_v3'] != 'terjemahan_indonesia_v3'
    assert bundle['columns']['canonical_paragraph_id'] != 'canonical_paragraph_id'
    out = pd.read_csv(BytesIO(bundle['csv']), dtype=str, keep_default_na=False)
    assert out.terjemahan_indonesia_v3.tolist() == ['USER_TRANSLATION','\t=1+1']
    assert out['info'].tolist() == ['\t=CMD()', '-12']
    assert out[bundle['columns']['terjemahan_indonesia_v3']].iloc[1] == ''
    pd.testing.assert_frame_equal(frame, before)


def test_correction_to_another_known_paragraph_cannot_reuse_or_switch_reference(entry):
    other=next(e for e in m._index(m._signature())[0].values()
               if e['draft_ok'] and e['unit']!=entry['unit'] and len(e['text'])>100)
    bundle=x.build_exports(text_result(entry['text']),text=entry['text'],active_text=other['text'])
    assert bundle['matched']==0 and bundle['records'][0]['arabic']==other['text']
    assert bundle['counts']=={'koreksi_teks_berubah':1}


def test_missing_saved_prediction_binding_retains_all_csv_rows_without_translations(entry):
    frame=legacy(entry['text'],3);result=csv_result(frame,'teks_gundul')
    result['dataframe'].loc[0,'baris_sumber']='999'
    bundle=exports(frame,result)
    assert bundle['matched']==0 and len(bundle['records'])==3
    assert bundle['counts']=={'prediksi_tidak_sesuai':3}
    assert len(pd.read_csv(BytesIO(bundle['csv'])))==3


def test_cache_binds_sources_metadata_predictions_and_does_not_reinfer(entry):
    frame = legacy(entry['text'], 3); result = csv_result(frame, 'teks_gundul'); state={}
    with patch.object(m, 'lookup', wraps=m.lookup) as lookup:
        a=x.cached_report(state,result,dataframe=frame,column='teks_gundul')
        b=x.cached_report(state,result,dataframe=frame,column='teks_gundul')
        assert a is b and lookup.call_count == 1
        result['dataframe'].loc[0,'TEST_prediction'] += ' لا'
        invalid=x.cached_report(state,result,dataframe=frame,column='teks_gundul')
        assert not invalid['pairs'] and lookup.call_count == 2


def test_real_canonical_csv_full_book_and_txt_have_complete_exports(canonical_txt):
    frame = pd.read_csv(r.DEMO/'CSV/02_Shalat.csv',dtype=str,keep_default_na=False)
    csv = exports(frame)
    assert csv['matched']==len(csv['records'])==320
    assert len(pd.read_csv(BytesIO(csv['csv'])))==356
    text=canonical_txt('02')
    txt=x.build_exports(text_result(text,'txt'),text=text)
    assert txt['matched']==len(txt['records'])==320
    assert txt['txt'].decode('utf-8').count(x.NOTICE)==1


def test_additional_zip_keeps_all_legacy_members_safe_names_and_pending_status(entry):
    frame=legacy(entry['text'],3); result=csv_result(frame,'teks_gundul')
    # Real exports always have this backend field; the test result stays synthetic.
    result['download_bytes']=b'ORIGINAL_BACKEND_CSV'
    entries={}
    for i,name in enumerate(['../same.csv','..\\same.csv']):
        entries[str(i)]={'upload_snapshot':{'name':name,'size':20},'file_result':result,'csv_column':'teks_gundul',
                        'upload_validation_cache':{'validation':{'success':True,'dataframe':frame}},'export_bytes':None}
    entries['pending']={'upload_snapshot':{'name':'pending.txt','size':10},'file_result':None}
    with patch('zipfile.time.localtime',return_value=(2026,10,28,12,0,0,2,301,0)):
        before=q.build_zip(entries)
        additional=x.build_zip(entries)
        assert q.build_zip(entries)==before
    with ZipFile(BytesIO(before)) as old, ZipFile(BytesIO(additional)) as new:
        assert len(new.namelist())==len({n.casefold() for n in new.namelist()})
        assert all('/' not in n and '\\' not in n for n in new.namelist())
        assert all(old.read(n)==new.read(n) for n in old.namelist())
        assert 'ringkasan_status.csv' in new.namelist() and 'ringkasan_terjemahan_v3.csv' in new.namelist()
        assert new.testzip() is None
        assert sum(n.endswith('.txt') and n.startswith('hasil_v3_') for n in new.namelist())==2
        assert entry['unit']['translation']['text_indonesian'].encode() in new.read('hasil_v3_001_same.txt')


def test_export_memory_limit_fails_without_touching_result(entry):
    frame=legacy(entry['text'],3); result=csv_result(frame,'teks_gundul'); before=deepcopy(result)
    with patch.object(q,'MAX_EXPORT_BYTES',1),pytest.raises(ValueError,match='32 MiB'):
        exports(frame,result)
    pd.testing.assert_frame_equal(result['dataframe'],before['dataframe'])
