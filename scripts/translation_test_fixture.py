"""Test-only original text. Never a translation of the book or a real review."""
from io import BytesIO
import json
from pathlib import Path

import pandas as pd

STAMP = '2026-10-22T12:00:00+07:00'
SENTINEL = 'DATA UJI SINTETIS ? BUKAN TERJEMAHAN KITAB. <script>TEST_ONLY</script>'


def write_units(path, units):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(''.join(json.dumps(u, ensure_ascii=False) + '\n' for u in units), encoding='utf-8')


def build_fixture(folder, reference):
    """Use real immutable demo identities; only the Indonesian sentinel is synthetic."""
    book = reference.load_catalog()['books'][1]
    data = (reference.DEMO / 'CSV' / book['dataset']['file']).read_bytes()
    frame = pd.read_csv(BytesIO(data), dtype=str, keep_default_na=False)
    context = reference.load_context(book)
    paragraph_id = 'P026_PAR003'  # Actual paragraph split across IDs 00027 and 00028.
    targets = [reference.target_for(row['id'], context) for row in context['paragraphs'][paragraph_id]]
    unit = {'schema_version': '3.0', 'unit_id': 'FQTR3_' + paragraph_id,
            'dataset_version': reference.VERSION, 'paragraph_id': paragraph_id,
            'section': 'DATA UJI SINTETIS', 'targets': targets,
            'target_digest': reference.fingerprint(targets),
            'translation': {'origin': 'original', 'text_indonesian': SENTINEL, 'translator': 'TEST_ONLY'},
            'verification': {'status': 'verified', 'reviewer': 'TEST_ONLY', 'reviewed_at': STAMP,
                'reviewed_text_sha256': reference.sha_text(SENTINEL),
                'reviewed_target_digest': reference.fingerprint(targets)}}
    path = Path(folder) / 'translations.jsonl'
    write_units(path, [unit])
    return {'w': reference, 'path': path, 'data': data, 'frame': frame, 'unit': unit, 'context': context}
