"""Legacy CSV ordinals/chunks must never bypass exact canonical identity checks."""
from copy import deepcopy
from io import BytesIO
from unittest.mock import patch
from zipfile import ZipFile

import pandas as pd
import pytest

from test_translation_matching import csv_result
import translation_matching as m
import translation_reference as r


@pytest.fixture(scope='module')
def entry():
    index = m._index(m._signature())
    return next(e for e in index[0].values() if e['kitab_id'] == '02' and e['draft_ok']
                and len(e['text']) > 200 and len(index[1][e['text']]) == 1
                and len(e['targets']) > 1)


def legacy(text, pieces=2):
    words = text.split()
    cuts = [len(words) * i // pieces for i in range(pieces + 1)]
    return pd.DataFrame([{'id': str(i + 7), 'bab': 'Shalat', 'jenis': 'teks',
                          'baris_sumber': '715', 'segmen': str(i + 1),
                          'teks_gundul': ' '.join(words[cuts[i]:cuts[i + 1]])}
                         for i in range(pieces)])


def lookup(frame, result=None, preview=True):
    return m.lookup(csv_result(frame, 'teks_gundul') if result is None else result,
                    dataframe=frame, column='teks_gundul', preview_drafts=preview)


@pytest.mark.parametrize('ordinal', ['2', '359', '0002'])
def test_local_ordinal_can_match_unique_content_without_fabricating_id(entry, ordinal):
    frame = pd.DataFrame({'id': [ordinal], 'teks_gundul': [entry['text']]})
    report = lookup(frame)
    assert report['counts'] == {'tersedia': 1}
    assert report['pairs'][0]['unit'] == entry['unit']
    assert report['pairs'][0]['segments'][0]['segment_id'] == ', '.join(t['segment_id'] for t in entry['targets'])


@pytest.mark.parametrize('identity', ['FQDEMO_02_99999', 'FQDEMO_01_00002', 'FQDEMO_02_bad', 'LOCAL_2', '٢'])
def test_explicit_or_unrecognized_identity_is_never_ignored(entry, identity):
    frame = pd.DataFrame({'id': [identity], 'teks_gundul': [entry['text']]})
    assert lookup(frame)['counts'] == {'tidak_cocok': 1}


def test_legacy_whole_paragraph_reconstruction_keeps_saved_predictions(entry):
    frame = legacy(entry['text'], 3)
    result = csv_result(frame, 'teks_gundul')
    pred = result['output_columns']['prediction']
    result['dataframe'][pred] = [''.join(c + '\u064e' if '\u0621' <= c <= '\u064a' else c for c in x)
                                 for x in frame.teks_gundul]
    before_frame = frame.copy(deep=True)
    before = result['dataframe'].copy(deep=True)
    result['download_bytes'] = b'EXISTING_EXPORT_BYTES'
    report = lookup(frame, result)
    assert report['total'] == 3 and report['counts'] == {'tersedia': 3}
    assert len(report['pairs']) == 1
    pair = report['pairs'][0]
    assert pair['unit'] == entry['unit'] and pair['input_parts'] == 3
    assert len(pair['segments']) == 1
    assert pair['segments'][0]['prediction'] == ' '.join(before[pred])
    pd.testing.assert_frame_equal(frame, before_frame)
    pd.testing.assert_frame_equal(result['dataframe'], before)
    assert result['download_bytes'] == b'EXISTING_EXPORT_BYTES'
    assert lookup(frame, preview=False)['counts'] == {'belum_terverifikasi': 3}


@pytest.mark.parametrize('case', ['reversed', 'missing', 'duplicate_chunk', 'gap', 'id_gap',
                                 'id_duplicate', 'other_source', 'other_kind', 'other_book',
                                 'noncontiguous', 'changed_text', 'forged_page', 'forged_paragraph',
                                 'forged_version', 'forged_chunk'])
def test_invalid_legacy_group_cannot_authorize_a_paragraph(entry, case):
    frame = legacy(entry['text'], 3)
    if case == 'reversed': frame = frame.iloc[::-1].reset_index(drop=True)
    elif case == 'missing': frame = frame.iloc[1:]
    elif case == 'duplicate_chunk': frame.loc[1, 'segmen'] = '1'
    elif case == 'gap': frame.loc[1, 'segmen'] = '4'
    elif case == 'id_gap': frame.loc[1, 'id'] = '999'
    elif case == 'id_duplicate': frame.loc[1, 'id'] = '7'
    elif case == 'other_source': frame.loc[1, 'baris_sumber'] = '716'
    elif case == 'other_kind': frame.loc[1, 'jenis'] = 'judul_kitab'
    elif case == 'other_book': frame.loc[1, 'bab'] = 'Thaharah'
    elif case == 'noncontiguous':
        other = legacy('هذا نص خارج الكتاب', 1); other['baris_sumber'] = '716'
        frame = pd.concat([frame.iloc[:1], other, frame.iloc[1:]], ignore_index=True)
    elif case == 'changed_text': frame.loc[1, 'teks_gundul'] += ' لا'
    else:
        field, value = {'forged_page': ('page', '999'), 'forged_paragraph': ('paragraph_id', 'P999_PAR001'),
                        'forged_version': ('dataset_version', 'wrong'), 'forged_chunk': ('chunk_id', 'WRONG')}[case]
        frame[field] = ''; frame.loc[1, field] = value
    report = lookup(frame)
    assert not report.get('error') and not report['pairs']
    assert sum(report['counts'].values()) == len(frame)


@pytest.mark.parametrize('case', ['failed_chunk', 'changed_prediction', 'stale_input'])
def test_legacy_reconstruction_cannot_use_failed_or_stale_predictions(entry, case):
    frame = legacy(entry['text'], 3)
    result = csv_result(frame, 'teks_gundul')
    if case == 'failed_chunk': result['dataframe'].loc[1, 'TEST_status'] = 'gagal'
    elif case == 'changed_prediction': result['dataframe'].loc[1, 'TEST_prediction'] += ' لا'
    else: result['dataframe'].loc[1, 'baris_sumber'] = '716'
    report = lookup(frame, result)
    assert not report['pairs']
    if case != 'stale_input': assert report['counts'] == {'prediksi_tidak_sesuai': 3}
    else: assert report.get('error')


def test_legacy_schema_is_required_for_reconstruction(entry):
    frame = legacy(entry['text'])
    for field in ('baris_sumber', 'segmen', 'jenis', 'bab'):
        assert not lookup(frame.drop(columns=field))['pairs']
    renamed = frame.rename(columns={'teks_gundul': 'arabic'})
    assert not m.lookup(csv_result(renamed, 'arabic'), dataframe=renamed,
                        column='arabic', preview_drafts=True)['pairs']


def test_numeric_ids_do_not_disambiguate_identical_titles_or_duplicate_input(entry):
    index = m._index(m._signature())
    title = next(text for text, options in index[1].items() if len(options) > 1)
    frame = legacy(title, 1)
    assert lookup(frame)['counts'] == {'ambigu': 1}
    frame = pd.concat([legacy(entry['text'], 1), legacy(entry['text'], 1)], ignore_index=True)
    frame.loc[1, ['id', 'baris_sumber']] = ['8', '716']
    assert lookup(frame)['counts'] == {'paragraf_tidak_lengkap': 2}


def test_ayah_marker_is_preserved_even_in_identified_legacy_adapter():
    e = m._index(m._signature())[0]['P107_PAR002']
    assert '\u06dd' in e['text']
    assert lookup(legacy(e['text'], 3))['pairs'][0]['unit'] == e['unit']
    missing = legacy(e['text'].replace('\u06dd', ''), 3)
    assert lookup(missing)['counts'] == {'tidak_cocok': 3}
    assert m.normalize('\u06dd') == '\u06dd'


def test_valid_and_forged_canonical_id_remain_strict_with_numeric_neighbors():
    frame = pd.read_csv(r.DEMO / 'CSV/02_Shalat.csv', dtype=str, keep_default_na=False).iloc[[1]].copy()
    valid = lookup(frame)
    assert valid['counts'] == {'tersedia': 1}
    expected = valid['pairs'][0]['unit']
    frame['id'] = 'FQDEMO_01_00002'
    assert lookup(frame)['counts'] == {'tidak_cocok': 1}
    frame['id'] = '2'
    assert lookup(frame)['pairs'][0]['unit'] == expected


def test_real_legacy_csv_app_pages_use_single_inference_and_preserve_exports():
    """Real uploaded legacy schema, actual inference, all page identities checked."""
    from test_ui_translation_panel import app_ready, upload, open_panel, has_text, translation_values
    import inference_engine as backend
    # Build the old export shape from canonical paragraphs, independently of
    # availability of the user's Downloads directory on other machines.
    entries = m._index(m._signature())[0]
    chosen = [e for e in entries.values() if e['kitab_id'] == '02' and e['draft_ok']
              and len(e['text']) > 80][:21]
    frames = []; ordinal = 1
    for source, e in enumerate(chosen, 1):
        frame = legacy(e['text'], 2)
        frame['id'] = [str(ordinal), str(ordinal + 1)]; ordinal += 2
        frame['baris_sumber'] = str(source)
        frames.append(frame)
    frame = pd.concat(frames, ignore_index=True)
    data = frame.to_csv(index=False).encode('utf-8-sig')
    app = app_ready(); fid = upload(app, 'legacy-shalat.csv', data)
    with patch.object(backend, 'process_uploaded_file', wraps=backend.process_uploaded_file) as infer:
        app.button(key='process_file').click().run()
        assert not app.exception and infer.call_count == 1
        before = deepcopy(app.session_state.file_result)
        app.button(key='prepare_queue_zip').click().run()
        archive_before = app.session_state.queue_zip
        open_panel(app, fid)
        report = lookup(frame, before)
        assert len(report['pairs']) == 21 and report['counts'] == {'tersedia': 42}
        for page in (1, 2, 3, 1):
            app.selectbox(key=f'translation_reference_page_{fid}').select(page).run()
            current = report['pairs'][(page - 1) * 10:page * 10]
            assert len(translation_values(app)) == len(current)
            for pair in current:
                assert has_text(app, pair['unit']['translation']['text_indonesian'])
                assert has_text(app, pair['segments'][0]['prediction'])
        open_panel(app, fid, False); open_panel(app, fid)
        assert infer.call_count == 1
        pd.testing.assert_frame_equal(app.session_state.file_result['dataframe'], before['dataframe'])
        assert app.session_state.file_result['download_bytes'] == before['download_bytes']
        assert app.session_state.queue_zip == archive_before
        with ZipFile(BytesIO(archive_before)) as archive:
            for pair in report['pairs']:
                assert all(pair['unit']['translation']['text_indonesian'].encode() not in archive.read(name)
                           for name in archive.namelist())
