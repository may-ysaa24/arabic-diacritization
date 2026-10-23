"""V3: verified original translations, matched to exact demo paragraphs.

Read-only; no internet, permission registry, inference, or automatic verification.
"""
from collections import Counter, defaultdict
from datetime import datetime
from hashlib import sha256
from io import StringIO
import csv
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / 'data/demo_fathul_qorib_per_bab'
CATALOG_PATH = ROOT / 'references/fathul_qorib/dataset_version.json'
ORIGINAL = ROOT / 'references/fathul_qorib/original'
TRANSLATIONS_PATH = ORIGINAL / 'translations.jsonl'
VERSION = 'fqdemo-v3-073ba6ffbf7c3a38a5cc431764719f1683f395e87275d62402c531ecd28dfabb'
MAX_JSON_BYTES = 256 * 1024
MAX_REFERENCE_BYTES = 8 * 1024 * 1024
MAX_UNITS = 3000
DRAFT_STATUS = 'draft_needs_review'
DRAFT_LABEL = 'Draf terjemahan berbantuan AI, belum diverifikasi'
CONTENT_DRAFT_LABEL = 'Draf terjemahan, belum diverifikasi'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha_text(value):
    return sha256(value.encode('utf-8')).hexdigest()


def fingerprint(value):
    return sha_text(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')))


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'Duplicate JSON property')
        result[key] = value
    return result


def _read_bytes(path, limit):
    with Path(path).open('rb') as stream:
        data = stream.read(limit + 1)
    require(len(data) <= limit, 'Reference exceeds size limit')
    return data


def _read_json(path):
    return json.loads(_read_bytes(path, MAX_JSON_BYTES).decode('utf-8'), object_pairs_hook=_unique_object)


def is_demo_csv(dataframe, column):
    # Visibility hint only. Exact dataset matching happens below.
    return (column == 'teks_gundul' and dataframe.columns.is_unique
            and {'id', 'chunk_id', 'page', 'teks_gundul'} <= set(dataframe.columns)
            and 0 < len(dataframe) <= 10000
            and all(isinstance(value, str) and re.fullmatch(r'FQDEMO_\d{2}_\d{5}', value)
                    for value in dataframe['id']))


def load_catalog():
    catalog = _read_json(CATALOG_PATH)
    require(set(catalog) == {'schema_version', 'dataset_version', 'books',
                            'paragraph_map_sha256', 'raw_source_sha256'}, 'Unknown catalog fields')
    require(catalog['schema_version'] == '3.0' and catalog['dataset_version'] == VERSION, 'Wrong catalog version')
    core = {k: catalog[k] for k in ('books', 'paragraph_map_sha256', 'raw_source_sha256')}
    require('fqdemo-v3-' + fingerprint(core) == VERSION, 'Changed dataset catalog')
    require([b['kitab_id'] for b in catalog['books']] == [f'{i:02d}' for i in range(17)], 'Invalid book identities')
    for book in catalog['books']:
        name = book['dataset']['file']
        require(isinstance(name, str) and Path(name).name == name and '/' not in name and '\\' not in name,
                'Unsafe source filename')
    return catalog


def match_demo_book(upload_data, dataframe, column):
    """Exact CSV bytes and decoded rows. A filename or a similar sentence never matches."""
    try:
        if not is_demo_csv(dataframe, column) or not isinstance(upload_data, bytes):
            return None
        require(len(upload_data) <= 5 * 1024 * 1024, 'Upload too large')
        catalog = load_catalog()
        book = next((b for b in catalog['books'] if b['dataset']['sha256'] == sha256(upload_data).hexdigest()), None)
        if book is None:
            return None
        expected = book['dataset']
        require(list(dataframe.columns) == expected['columns'] and len(dataframe) == expected['row_count'], 'Changed CSV shape')
        rows = [[str(v) for v in row] for row in dataframe.itertuples(index=False, name=None)]
        require(fingerprint(rows) == expected['rows_sha256'], 'Changed CSV rows')
        return book
    except (ValueError, KeyError, TypeError, AttributeError, OSError):
        return None


def _csv(path, digest):
    data = _read_bytes(path, MAX_REFERENCE_BYTES)
    require(sha256(data).hexdigest() == digest, 'Changed local dataset source')
    return list(csv.DictReader(StringIO(data.decode('utf-8-sig'), newline='')))


def _index(rows, key):
    result = {row[key]: row for row in rows}
    require(len(result) == len(rows), 'Duplicate source identity')
    return result


def load_context(book):
    """Reuse the existing local Arabic reference, paragraph map and raw source."""
    catalog = load_catalog()
    name = book['dataset']['file']
    demo = _index(_csv(DEMO / 'CSV' / name, book['dataset']['sha256']), 'id')
    refs = _index(_csv(DEMO / 'Referensi_Berharakat' / name, book['arabic_reference_sha256']), 'id')
    require(set(demo) == set(refs), 'CSV/reference IDs differ')
    raw_rows = _csv(DEMO / 'Laporan_Audit/Sumber/dataset_drive.csv', catalog['raw_source_sha256'])
    raw = _index(raw_rows, 'page')
    pmap = _index(_csv(DEMO / 'Laporan_Audit/PETA_PARAGRAF.csv', catalog['paragraph_map_sha256']), 'paragraph_id')
    paragraphs = defaultdict(list)
    for row in refs.values():
        paragraphs[row['paragraph_id']].append(row)
    context = {'version': VERSION, 'demo': demo, 'refs': refs, 'raw': raw,
               'raw_rows': raw_rows, 'paragraph_map': pmap, 'paragraphs': dict(paragraphs)}
    for paragraph_id, rows in paragraphs.items():
        rows.sort(key=lambda row: int(row['source_start']))
        p = pmap[paragraph_id]
        require(int(p['kitab_id']) == int(book['kitab_id']), 'Paragraph belongs to another book')
        targets = [target_for(row['id'], context) for row in rows]
        require(targets[0]['source_span']['start'] == int(p['source_start'])
                and targets[-1]['source_span']['end_exclusive'] == int(p['source_end_exclusive'])
                and all(a['source_span']['end_exclusive'] == b['source_span']['start']
                        for a, b in zip(targets, targets[1:])), 'Incomplete paragraph coverage')
    return context


def target_for(segment_id, context):
    r, d = context['refs'][segment_id], context['demo'][segment_id]
    p = context['paragraph_map'][r['paragraph_id']]
    page = context['raw'][r['page']]['text_diacritized']
    start, end = int(r['source_start']), int(r['source_end_exclusive'])
    pa, pb = int(p['source_start']), int(p['source_end_exclusive'])
    require(r['page'] == d['page'] == p['page'] and r['chunk_id'] == d['chunk_id'], 'Page/chunk mismatch')
    require(r['teks_gundul'] == d['teks_gundul'], 'Bare text mismatch')
    require(pa <= start < end <= pb <= len(page) and page[start:end] == r['text_diacritized'], 'Invalid Arabic source span')
    require(sha_text(page[pa:pb]) == p['source_sha256'], 'Paragraph hash mismatch')
    source_record = int(r['source_record_1based'])
    require(0 < source_record <= len(context['raw_rows'])
            and context['raw_rows'][source_record - 1]['page'] == r['page']
            and source_record == int(p['source_record_1based']), 'Wrong source record')
    return {'segment_id': segment_id, 'paragraph_id': r['paragraph_id'], 'chunk_id': r['chunk_id'],
            'pdf_page': int(r['page']), 'source_record_1based': source_record,
            'source_span': {'start': start, 'end_exclusive': end},
            'arabic_text_sha256': sha_text(r['text_diacritized']), 'arabic_gundul_sha256': sha_text(r['teks_gundul'])}


def validate_unit(unit, context, *, preview_drafts=False):
    """The same exact paragraph checks apply to final and opt-in draft reading."""
    fields = {'schema_version', 'unit_id', 'dataset_version', 'paragraph_id', 'section',
              'targets', 'target_digest', 'translation', 'verification'}
    require(set(unit) in (fields, fields | {'source_note'}), 'Unknown unit fields')
    require(isinstance(unit.get('source_note', ''), str) and len(unit.get('source_note', '')) <= 4000,
            'Invalid source note')
    require(unit['schema_version'] == '3.0' and unit['dataset_version'] == context['version'] == VERSION, 'Wrong unit version')
    paragraph_id = unit['paragraph_id']
    require(unit['unit_id'] == 'FQTR3_' + paragraph_id, 'Unit/paragraph mismatch')
    rows = context['paragraphs'][paragraph_id]
    targets = [target_for(row['id'], context) for row in rows]
    require(unit['targets'] == targets and unit['target_digest'] == fingerprint(targets), 'Wrong paragraph targets')
    require(isinstance(unit['section'], str) and len(unit['section']) <= 500, 'Invalid section label')
    translation, review = unit['translation'], unit['verification']
    require(set(translation) == {'origin', 'text_indonesian', 'translator'}
            and translation['origin'] in ('original', 'ai_assisted_original'), 'Original authorship required')
    text = translation['text_indonesian']
    require(isinstance(text, str) and 0 < len(text.strip()) <= 50000
            and isinstance(translation['translator'], str) and translation['translator'].strip(), 'Missing original text/author')
    require(set(review) == {'status', 'reviewer', 'reviewed_at', 'reviewed_text_sha256', 'reviewed_target_digest'}, 'Invalid review fields')
    if preview_drafts and review['status'] == DRAFT_STATUS:
        require(translation['origin'] == 'ai_assisted_original'
                and all(review[key] is None for key in review if key != 'status'),
                'Draft cannot claim completed human verification')
        return
    require(review['status'] == 'verified' and isinstance(review['reviewer'], str) and review['reviewer'].strip(), 'Human verification required')
    require(isinstance(review['reviewed_at'], str) and datetime.fromisoformat(review['reviewed_at'].replace('Z', '+00:00')).tzinfo is not None, 'Missing zoned review date')
    require(review['reviewed_text_sha256'] == sha_text(text)
            and review['reviewed_target_digest'] == fingerprint(targets), 'Review is stale')


def read_units():
    """Bounded original records; eligibility is always checked by validate_unit."""
    require(TRANSLATIONS_PATH.resolve().is_relative_to(ORIGINAL.resolve()), 'Translation outside original storage')
    data = _read_bytes(TRANSLATIONS_PATH, MAX_REFERENCE_BYTES)
    lines = data.decode('utf-8').splitlines()
    require(len(lines) <= MAX_UNITS, 'Too many reference units')
    units = []
    for line in lines:
        if not line.strip():
            continue
        try:
            require(len(line.encode('utf-8')) <= MAX_JSON_BYTES, 'Unit too large')
            unit = json.loads(line, object_pairs_hook=_unique_object)
            if isinstance(unit, dict):
                units.append(unit)
        except (ValueError, TypeError):
            continue
    return units


def display_units(upload_data, dataframe, column, *, preview_drafts=False):
    """Final references by default; explicit local preview may include labeled drafts."""
    try:
        book = match_demo_book(upload_data, dataframe, column)
        if book is None or not TRANSLATIONS_PATH.exists():
            return []
        units = read_units()
        ids = Counter(u.get('unit_id') for u in units if isinstance(u.get('unit_id'), str))
        paragraphs = Counter(u.get('paragraph_id') for u in units if isinstance(u.get('paragraph_id'), str))
        context = load_context(book)
        result = []
        for unit in units:
            try:
                require(ids[unit['unit_id']] == 1 and paragraphs[unit['paragraph_id']] == 1, 'Conflicting units')
                validate_unit(unit, context, preview_drafts=preview_drafts)
                result.append(unit)
            except (ValueError, TypeError, KeyError, AttributeError):
                continue
        result.sort(key=lambda unit: (unit['targets'][0]['source_record_1based'], unit['targets'][0]['source_span']['start']))
        return result
    except (ValueError, KeyError, TypeError, AttributeError, OSError):
        return []
