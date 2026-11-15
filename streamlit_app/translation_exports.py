"""Additional V3 exports. Never imports inference or modifies legacy exports."""
from collections import Counter
from hashlib import sha256
from io import BytesIO
from zipfile import ZipFile

import pandas as pd

import translation_matching as matching
import translation_reference as reference
import upload_queue as queue
from file_safety import spreadsheet_safe_csv

NOTICE = 'Terjemahan V3 merupakan draf berbantuan AI yang belum diverifikasi ahli.'
CSV_RULE = ('Terjemahan ditulis sekali pada baris pertama kelompok; baris lanjutannya '
            'mempertahankan ID paragraf dan nomor baris pertama terjemahan (berbasis 1). '
            'Kolom pengguna tidak ditimpa; benturan nama diberi akhiran angka.')


def match_key(result, dataframe=None, column=None, text=None):
    """Content-bound session key, invalidated by sources, predictions or metadata."""
    payload = {key: result.get(key) for key in ('success', 'input_type', 'input_text', 'prediction',
                                               'status_summary', 'text_column', 'output_columns', 'message')}
    data = result.get('download_bytes')
    payload['download_sha256'] = sha256(data).hexdigest() if isinstance(data, bytes) else None
    payload.update(column=column, text=text)
    for key, frame in (('input', dataframe), ('output', result.get('dataframe'))):
        if frame is not None:
            payload[key] = {'columns': list(frame.columns), 'rows': frame.to_dict('records')}
    return reference.fingerprint(payload), matching._signature()


def cached_report(state, result, *, dataframe=None, column=None, text=None, lookup=None):
    """One bounded active report, shared with the content-matching panel."""
    try:
        token = match_key(result, dataframe, column, text)
    except (OSError, ValueError, TypeError):
        return (lookup or matching.lookup)(result, dataframe=dataframe, column=column,
                                           text=text, preview_drafts=True, include_parts=True)
    cached = state.get('v3_export_matching')
    if cached is None or cached['token'] != token:
        report = (lookup or matching.lookup)(result, dataframe=dataframe, column=column,
                                             text=text, preview_drafts=True, include_parts=True)
        cached = {'token': token, 'report': report}
        retained = queue.retained_bytes(state.get('upload_files', {})) + queue.retained_bytes(cached)
        retained += len(state.get('queue_zip') or b'') + len((state.get('v3_export_zip') or {}).get('data', b''))
        if queue.retained_bytes(cached) <= queue.MAX_EXPORT_BYTES and retained <= queue.MAX_RETAINED_BYTES:
            state['v3_export_matching'] = cached
    return cached['report']


def _unique_column(name, columns):
    candidate, number = name, 1
    while candidate in columns:
        candidate = f'{name}_{number}'; number += 1
    columns.add(candidate)
    return candidate


def _text_document(records):
    blocks = [NOTICE]
    for i, record in enumerate(records, 1):
        label = record['paragraph_id'] or f'Bagian masukan {i}'
        block = f'Paragraf: {label}\nStatus pencocokan: {record["status"]}\n\nArab Berharakat:\n{record["arabic"]}'
        if record['translation']:
            block += '\n\nTerjemahan Indonesia:\n' + record['translation']
        if record.get('source_note'):
            block += '\n\nCatatan sumber:\n' + record['source_note']
        blocks.append(block)
    return ('\n\n---\n\n'.join(blocks) + '\n').encode('utf-8')


def build_exports(result, *, dataframe=None, column=None, text=None, active_text=None, report=None):
    """Format only exact eligible matches; preserve every original CSV row.

    Mark-only corrections bind through the same matcher to the active text.
    Substantive corrections retain the entire correction, with no stale pairing.
    """
    if not result or result.get('success') is not True:
        raise ValueError('Hasil tersimpan belum tersedia untuk ekspor.')
    corrected = active_text is not None and active_text != result.get('prediction')
    substantive = corrected and matching.normalize(active_text) != matching.normalize(result['prediction'])
    if substantive:
        records = [{'paragraph_id': '', 'arabic': active_text, 'translation': '',
                    'status': 'koreksi_teks_berubah', 'rows': [], 'source_note': ''}]
        report = {'pairs': [], 'counts': {'koreksi_teks_berubah': 1}, 'total': 1}
    else:
        bound_result = dict(result, prediction=active_text) if corrected else result
        if report is None or corrected:
            report = matching.lookup(bound_result, dataframe=dataframe, column=column, text=text,
                                      preview_drafts=True, include_parts=True)
        parts = report.get('parts', [])
        by_pid = {p['unit']['paragraph_id']: p for p in report['pairs']}
        records, seen = [], set()
        for part in parts:
            pid, status = part['paragraph_id'], part['status']
            pair = by_pid.get(pid) if status == 'tersedia' else None
            if pair is not None:
                if pid in seen:
                    continue
                seen.add(pid)
                associated = [p for p in parts if p['paragraph_id'] == pid and p['status'] == 'tersedia']
                rows = sorted(row for p in associated for row in p['rows'])
                unit = pair['unit']
                records.append({'paragraph_id': pid,
                    'arabic': ' '.join(s['prediction'] for s in pair['segments']),
                    'translation': unit['translation']['text_indonesian'], 'status': status,
                    'rows': rows, 'source_note': unit.get('source_note', ''),
                    'verification_status': unit['verification']['status']})
            else:
                arabic = part['prediction']
                if dataframe is not None:
                    pred = result['output_columns']['prediction']
                    arabic = ' '.join(str(result['dataframe'].iloc[i][pred]) for i in part['rows'])
                records.append({'paragraph_id': pid, 'arabic': arabic or '', 'translation': '',
                                'status': status, 'rows': part['rows'], 'source_note': ''})
        if not parts:
            # A failed binding must never authorize any translation. Retain the
            # complete saved Arabic instead of silently omitting failed input.
            status = 'prediksi_tidak_sesuai' if report.get('error') else 'tidak_cocok'
            if dataframe is not None:
                pred = result['output_columns']['prediction']
                records = [{'paragraph_id': '', 'arabic': str(row[pred]), 'translation': '',
                            'status': status, 'rows': [i], 'source_note': ''}
                           for i, (_, row) in enumerate(result['dataframe'].iterrows())]
            else:
                records = [{'paragraph_id': '', 'arabic': bound_result['prediction'], 'translation': '',
                            'status': status, 'rows': [], 'source_note': ''}]
    txt = _text_document(records)
    if dataframe is not None:
        output = result['dataframe'].copy(deep=True)
    else:
        output = pd.DataFrame({'arab_berharakat': [r['arabic'] for r in records]})
    columns = set(output.columns)
    added = {name: _unique_column(name, columns) for name in (
        'canonical_paragraph_id', 'terjemahan_indonesia_v3', 'status_pencocokan_v3',
        'baris_awal_terjemahan_v3', 'status_verifikasi_v3', 'catatan_sumber_v3')}
    for name in added.values():
        output[name] = ''
    for position, record in enumerate(records):
        rows = record['rows'] if dataframe is not None else [position]
        for row in rows:
            values = {'canonical_paragraph_id': record['paragraph_id'], 'status_pencocokan_v3': record['status'],
                      'baris_awal_terjemahan_v3': str(min(rows) + 1) if record['translation'] else '',
                      'status_verifikasi_v3': record.get('verification_status', '')}
            if row == min(rows):
                values.update(terjemahan_indonesia_v3=record['translation'], catatan_sumber_v3=record['source_note'])
            for name, value in values.items():
                output.iat[row, output.columns.get_loc(added[name])] = value
    csv = spreadsheet_safe_csv(output)
    if len(txt) + len(csv) > queue.MAX_EXPORT_BYTES:
        raise ValueError('Ekspor dengan terjemahan melampaui batas 32 MiB.')
    return {'txt': txt, 'csv': csv, 'records': records, 'columns': added,
            'counts': dict(Counter(r['status'] for r in records)),
            'matched': sum(bool(r['translation']) for r in records), 'report': report}


def build_zip(entries):
    """Keep original members/statuses and append explicit, separately named V3 files."""
    original = queue.build_zip(entries)
    buffer = BytesIO(original)
    summary = []
    with ZipFile(buffer, 'a') as archive:
        total = sum(info.file_size for info in archive.infolist())
        def add(name, data):
            nonlocal total
            total += len(data)
            if total > queue.MAX_EXPORT_BYTES:
                raise ValueError('ZIP dengan terjemahan melampaui batas 32 MiB.')
            archive.writestr(name, data)
        add('KETERANGAN_TERJEMAHAN_V3.txt', (NOTICE + '\n\n' + CSV_RULE + '\n').encode('utf-8'))
        for number, entry in enumerate(entries.values(), 1):
            snapshot = entry['upload_snapshot']; result = entry.get('file_result') or {}
            status, _ = queue.entry_status(entry)
            row = {'berkas': snapshot['name'], 'status_pemrosesan': status, 'paragraf_cocok': 0,
                   'status_pencocokan': 'berkas_tidak_valid' if status == 'Tidak valid' else 'belum_diproses'}
            if result.get('success'):
                validation = (entry.get('upload_validation_cache') or {}).get('validation', {})
                csv_input = result.get('input_type') == 'csv'
                frame = validation.get('dataframe') if csv_input else None
                if csv_input and frame is None:
                    raise ValueError('Sumber CSV tersimpan belum tersedia untuk ZIP terjemahan.')
                bundle = build_exports(result, dataframe=frame, column=entry.get('csv_column'), text=validation.get('text'))
                row.update(paragraf_cocok=bundle['matched'], status_pencocokan=str(bundle['counts']))
                if bundle['matched']:
                    for suffix in ('txt', 'csv'):
                        name = queue.safe_output_name(snapshot['name'], suffix, f'v3_{number:03d}')
                        add(name, bundle[suffix])
            elif result:
                row['status_pencocokan'] = 'pemrosesan_gagal'
            summary.append(row)
        add('ringkasan_terjemahan_v3.csv', spreadsheet_safe_csv(pd.DataFrame(summary)))
    return buffer.getvalue()
