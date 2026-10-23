"""Exact canonical content lookup, separate from inference and research exports.

Matching policy v1: NFC, remove U+064B..0652 / U+0670, collapse whitespace.
Keep tatweel, hamza, alif variants, ya/maqsura, ta marbuta, digits and punctuation.
No fuzzy match, substring search, spelling repair, or generated translations.
"""
from collections import Counter, defaultdict
from bisect import bisect_left, bisect_right
from functools import lru_cache
import re
import unicodedata

import translation_reference as ref

MAX_INPUT = 1_000_000
MAX_ROWS = 10_000
MARKS = re.compile('[\u064b-\u0652\u0670]')


def normalize(text):
    return ' '.join(MARKS.sub('', unicodedata.normalize('NFC', text)).split())


def _signature():
    catalog = ref.load_catalog()
    paths = [ref.CATALOG_PATH, ref.TRANSLATIONS_PATH,
             ref.DEMO / 'Laporan_Audit/PETA_PARAGRAF.csv',
             ref.DEMO / 'Laporan_Audit/Sumber/dataset_drive.csv']
    for book in catalog['books']:
        paths.extend(ref.DEMO / folder / book['dataset']['file']
                     for folder in ('CSV', 'Referensi_Berharakat'))
    return tuple((str(p.resolve()), p.stat().st_mtime_ns, p.stat().st_ctime_ns, p.stat().st_size) for p in paths)


@lru_cache(maxsize=1)
def _index(signature):
    # One bounded process-wide index. No uploads, predictions, or user state cached.
    units = ref.read_units()
    counts = Counter(u.get('paragraph_id') for u in units if isinstance(u.get('paragraph_id'), str))
    unit_counts = Counter(u.get('unit_id') for u in units if isinstance(u.get('unit_id'), str))
    by_paragraph = {u['paragraph_id']: u for u in units
                    if isinstance(u.get('paragraph_id'), str) and counts[u['paragraph_id']] == 1
                    and unit_counts.get(u.get('unit_id')) == 1}
    entries, paragraphs, segments = {}, defaultdict(list), defaultdict(list)
    for book in ref.load_catalog()['books']:
        context = ref.load_context(book)  # Revalidates hashes and all source spans.
        for pid, rows in context['paragraphs'].items():
            targets = [ref.target_for(row['id'], context) for row in rows]
            text = normalize(''.join(row['text_diacritized'] for row in rows))
            unit = by_paragraph.get(pid)
            draft_ok = final_ok = False
            if unit is not None:
                for preview in (False, True):
                    try:
                        ref.validate_unit(unit, context, preview_drafts=preview)
                        if preview:
                            draft_ok = True
                        else:
                            final_ok = True
                    except (ValueError, TypeError, KeyError, AttributeError):
                        pass
            entries[pid] = {'targets': targets, 'text': text, 'unit': unit,
                            'draft_ok': draft_ok, 'final_ok': final_ok,
                            'kitab': book['dataset']['kitab'], 'kitab_id': book['kitab_id']}
            paragraphs[text].append((pid, tuple(t['segment_id'] for t in targets)))
            for row in rows:
                segments[normalize(row['teks_gundul'])].append((pid, (row['id'],)))
    # Search includes untranslated books: translation availability never breaks ties.
    prefixes = defaultdict(list)
    for text in paragraphs:
        if text:
            prefixes[text.split()[0]].append(text)
    return entries, paragraphs, segments, prefixes


def _candidates(text, metadata, index):
    entries, paragraphs, segments, _ = index
    key = normalize(text)
    matches = {*paragraphs.get(key, ()), *segments.get(key, ())}
    for name in ('dataset_version', 'id', 'paragraph_id', 'chunk_id', 'page', 'kitab_id', 'kitab'):
        value = metadata.get(name, '')
        if value == '':
            continue
        def consistent(candidate):
            pid, ids = candidate
            entry = entries[pid]
            targets = [t for t in entry['targets'] if t['segment_id'] in ids]
            expected = {'dataset_version': ref.VERSION, 'paragraph_id': pid,
                        'kitab_id': entry['kitab_id'], 'kitab': entry['kitab']}
            if name in expected:
                return value == expected[name]
            if name == 'id':
                return len(ids) == 1 and value == ids[0]
            if name == 'chunk_id':
                return len(targets) == 1 and value == targets[0]['chunk_id']
            return all(value == str(t['pdf_page']) for t in targets)
        matches = {c for c in matches if consistent(c)}
    return matches


def _text_parts(text, index):
    """Blank lines delimit blocks. Soft wraps may join whole lines, never words.

    If a block is not a whole paragraph, try complete line spans. Never search
    inside a line, cross blank lines, or use a substring of a source paragraph.
    """
    parts = []
    _, paragraphs, _, prefixes = index
    for block in re.finditer(r'\S[^\r\n]*(?:\r?\n(?![ \t]*\r?\n)[^\r\n]*)*', text):
        value = block.group()
        if normalize(value) in paragraphs:
            parts.append({'text': value, 'span': block.span(), 'metadata': {}})
            continue
        lines = list(re.finditer(r'[^\r\n]+', value))
        i = 0
        while i < len(lines):
            if not lines[i].group().strip():
                i += 1
                continue
            start, end = lines[i].span()
            first = normalize(lines[i].group()).split()
            possible = prefixes.get(first[0], ()) if first else ()
            found = []
            for j in range(i, len(lines)):
                end = lines[j].end()
                key = normalize(value[start:end])
                possible = [p for p in possible if p == key or p.startswith(key + ' ')]
                if not possible:
                    break
                if key in paragraphs:
                    found.append((j, end))
            if len(found) == 1:
                last, end = found[0]
            else:
                last, end = i, lines[i].end()
            parts.append({'text': value[start:end], 'span': (block.start() + start, block.start() + end),
                          'metadata': {}, 'boundary_ambiguous': len(found) > 1})
            i = last + 1
    return parts


def _projection(text):
    """Base-letter alignment ONLY for slicing saved model output, not matching.

    Mirrors documented inference removal of tatweel/dagger alif and whitespace.
    Preserve original output slices, including predicted marks, using offsets.
    """
    chars, spans = [], []
    for cluster in re.finditer(r'.[\u0300-\u036f\u064b-\u065f\u0670]*', text, re.S):
        for char in MARKS.sub('', unicodedata.normalize('NFC', cluster.group())).replace('\u0640', ''):
            if char.isspace():
                if chars and chars[-1] != ' ':
                    chars.append(' ')
                    spans.append(cluster.span())
            else:
                chars.append(char)
                spans.append(cluster.span())
    if chars and chars[-1] == ' ':
        chars.pop(); spans.pop()
    return ''.join(chars), spans


def _bind(parts, result, dataframe, column, text):
    if not result or result.get('success') is not True:
        raise ValueError('Hasil prediksi tersimpan belum tersedia')
    if dataframe is not None:
        output, columns = result['dataframe'], result['output_columns']
        pred, status = columns['prediction'], columns['status']
        ref.require(result.get('input_type') == 'csv' and result.get('text_column') == column
                    and output.columns.is_unique and pred != status
                    and pred not in dataframe.columns and status not in dataframe.columns
                    and output[list(dataframe.columns)].to_dict('records') == dataframe.to_dict('records'),
                    'Hasil CSV tersimpan tidak sesuai input aktif')
        for part in parts:
            if not part['candidates']:
                part['prediction'] = None
                continue
            row = output.iloc[part['row']]
            value = row[pred]
            part['prediction'] = (value if row[status] == 'berhasil' and isinstance(value, str)
                                  and _projection(value)[0] == _projection(part['text'])[0] else None)
        return
    prediction = result.get('prediction')
    ref.require(isinstance(prediction, str) and not result.get('status_summary', {}).get('gagal'),
                'Prediksi teks belum lengkap')
    if result.get('input_type') != 'txt':
        ref.require(isinstance(result.get('input_text'), str)
                    and _projection(result['input_text'])[0] == _projection(text)[0], 'Hasil manual sudah kedaluwarsa')
    original, source_spans = _projection(text)
    predicted, pred_spans = _projection(prediction)
    ref.require(original == predicted, 'Prediksi tersimpan tidak sesuai teks aktif')
    starts = [a for a, _ in source_spans]
    ends = [b for _, b in source_spans]
    for part in parts:
        start, end = part['span']
        lo, hi = bisect_left(starts, start), bisect_right(ends, end)
        while lo < hi and original[lo] == ' ':
            lo += 1
        while lo < hi and original[hi - 1] == ' ':
            hi -= 1
        part['prediction'] = prediction[pred_spans[lo][0]:pred_spans[hi - 1][1]] if lo < hi else None


def lookup(result, *, dataframe=None, column=None, text=None, preview_drafts=False):
    """Return eligible complete paragraphs and explicit per-input status counts.

    Canonical identities are evidence, not user authority: even IDs require exact
    normalized content, and supplied identity fields must be mutually consistent.
    """
    report = {'pairs': [], 'counts': {}, 'total': 0}
    try:
        index = _index(_signature())
        entries = index[0]
        if dataframe is not None:
            ref.require(dataframe.columns.is_unique and column in dataframe.columns
                        and len(dataframe) <= MAX_ROWS and dataframe.size <= 100_000, 'CSV melampaui batas pencocokan')
            records = dataframe.to_dict('records')
            ref.require(all(isinstance(row[column], str) for row in records)
                        and sum(len(row[column]) for row in records) <= MAX_INPUT, 'Teks CSV melampaui batas')
            parts = [{'text': row[column], 'metadata': row, 'row': i} for i, row in enumerate(records)]
        else:
            ref.require(isinstance(text, str) and len(text) <= 250_000
                        and len(text.splitlines()) <= MAX_ROWS, 'Teks melampaui batas pencocokan')
            parts = _text_parts(text, index)
        report['total'] = len(parts)
        for part in parts:
            part['candidates'] = _candidates(part['text'], part['metadata'], index)
        _bind(parts, result, dataframe, column, text)
        groups, statuses = defaultdict(list), {}
        for i, part in enumerate(parts):
            candidates = part['candidates']
            if part.get('boundary_ambiguous') or len(candidates) > 1:
                statuses[i] = 'ambigu'
            elif not candidates:
                statuses[i] = 'tidak_cocok'
            elif not part['prediction']:
                statuses[i] = 'prediksi_tidak_sesuai'
            else:
                pid, ids = next(iter(candidates))
                groups[pid].append((i, ids))
        for pid, group in groups.items():
            entry = entries[pid]
            required = [t['segment_id'] for t in entry['targets']]
            provided = [sid for _, ids in group for sid in ids]
            status = ('paragraf_tidak_lengkap' if Counter(provided) != Counter(required) else
                      'tersedia' if entry['draft_ok' if preview_drafts else 'final_ok'] else
                      'belum_terverifikasi' if entry['draft_ok'] else 'terjemahan_belum_tersedia')
            for i, _ in group:
                statuses[i] = status
            if status == 'tersedia':
                order = {sid: n for n, sid in enumerate(required)}
                ordered = sorted(group, key=lambda item: min(order[sid] for sid in item[1]))
                report['pairs'].append({'unit': entry['unit'], 'kitab': entry['kitab'],
                    'segments': [{'segment_id': ', '.join(ids), 'prediction': parts[i]['prediction']} for i, ids in ordered],
                    'input_parts': len(group), 'first_input': min(i for i, _ in group)})
        report['pairs'].sort(key=lambda pair: pair['first_input'])
        report['counts'] = dict(Counter(statuses.values()))
    except (ValueError, KeyError, TypeError, AttributeError, OSError, IndexError) as error:
        report.update(pairs=[], error='Pencocokan referensi tidak tersedia: ' + str(error))
    return report
