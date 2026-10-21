"""Synthetic display fixtures are NOT translations or evidence of book permission."""
from copy import deepcopy
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import sys
from unittest.mock import patch

import pandas as pd
import pytest

APP = Path(__file__).resolve().parents[1] / 'streamlit_app'
sys.path.insert(0, str(APP))
import translation_reference as r

STAMP = '2026-10-22T12:00:00+07:00'
SENTINEL = 'TEST_DATA_NOT_A_TRANSLATION <script>TEST_ONLY</script>'


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj), encoding='utf-8')


@pytest.fixture
def display_fixture(tmp_path, monkeypatch):
    w = r._workflow()
    local = tmp_path / '.local'
    # ASCII metadata fixtures only; no Arabic/Indonesian book text is fabricated.
    rows = [{'id': f'FQDEMO_01_{i:05d}', 'chunk_id': f'TEST_CHUNK_{i}', 'page': '1',
             'teks_gundul': f'TEST_PART_{i}'} for i in (1, 2)]
    frame = pd.DataFrame(rows)
    data = frame.to_csv(index=False).encode()
    full = ''.join(row['teks_gundul'] for row in rows)
    refs, offset = {}, 0
    for row in rows:
        refs[row['id']] = dict(row, paragraph_id='TEST_PARAGRAPH', source_record_1based='1',
                              source_start=str(offset), source_end_exclusive=str(offset + len(row['teks_gundul'])),
                              text_diacritized=row['teks_gundul'])
        offset += len(row['teks_gundul'])
    raw = {'page': '1', 'text_diacritized': full}
    context = {'version': r.VERSION, 'demo': {row['id']: row for row in rows}, 'refs': refs,
               'paragraphs': {'TEST_PARAGRAPH': list(refs.values())}, 'raw': {'1': raw}, 'raw_rows': [raw],
               'paragraph_map': {'TEST_PARAGRAPH': {'page': '1', 'source_start': '0',
                   'source_end_exclusive': str(len(full)), 'source_sha256': w.sha_text(full), 'source_record_1based': '1'}}}
    targets = [w.target_for(row['id'], context) for row in rows]
    parts = [{'locator_id': 'TEST_LOCATOR', 'source_id': 'primary', 'source_url': w.PRIMARY,
              'target_segment_id': rows[0]['id'], 'target_bare_span': {'start': 0, 'end_exclusive': 1},
              'arabic_lines': [0, 1], 'indonesian_lines': [2, 3], 'relation': 'TEST_ONLY',
              'locator_status': 'candidate_rendered_lines_not_stable_anchor'}]
    registry = {'status': 'documented', 'test_only': 'MOCKED_RIGHTS_NOT_REAL_PERMISSION'}
    unit = {'schema_version': '2.0.0', 'unit_id': 'FQTRV2_TEST_PARAGRAPH', 'dataset_version': r.VERSION,
            'paragraph_id': 'TEST_PARAGRAPH', 'targets': targets, 'target_digest': w.fingerprint(targets),
            'arabic_text': full, 'arabic_gundul': full, 'unit_types': ['complete_paragraph'],
            'alignment_status': 'candidate_match', 'source_parts': parts, 'source_digest': w.fingerprint(parts),
            'alignment_review': {'decision': 'aligned', 'reviewer': 'TEST_ONLY', 'reviewed_at': STAMP,
                'note': 'TEST_ONLY', 'source_ranges': [{'locator_id': 'TEST_LOCATOR', 'boundary_description': 'TEST_ONLY'}]},
            'translation': {'text_indonesian': SENTINEL, 'translator': 'TEST_ONLY', 'source_id': 'primary',
                'source_locator_ids': ['TEST_LOCATOR'], 'checked_by': 'TEST_ONLY', 'checked_at': STAMP,
                'checked_text_sha256': w.sha_text(SENTINEL)},
            'permission_registry_digest': w.fingerprint(registry),
            'verification': {'status': 'verified', 'reviewer': 'TEST_ONLY', 'reviewed_at': STAMP,
                'reviewed_text_sha256': w.sha_text(SENTINEL), 'reviewed_target_digest': w.fingerprint(targets),
                'reviewed_source_digest': w.fingerprint(parts)}, 'publication_ready': False}
    path = local / 'display/units/test_only.json'
    write(path, unit)
    manifest = {'schema_version': '1.0', 'dataset_version': r.VERSION, 'csv_sha256': sha256(data).hexdigest(),
                'permission_registry_digest': w.fingerprint(registry), 'approvals': [{
                    'unit_id': unit['unit_id'], 'file': 'units/test_only.json', 'sha256': w.sha_file(path),
                    'decision': 'approved_for_display', 'reviewer': 'TEST_ONLY', 'reviewed_at': STAMP}]}
    write(local / 'permission_registry.json', registry)
    write(local / 'display/manifest.json', manifest)
    monkeypatch.setattr(r, 'V2', tmp_path)
    monkeypatch.setattr(r, 'CSV_SHA256', sha256(data).hexdigest())
    monkeypatch.setattr(r, '_workflow', lambda: w)
    monkeypatch.setattr(w, 'load_context', lambda *args: deepcopy(context))
    # Explicit mock for display-content tests. No grant for the real primary is invented.
    def mock_rights(workflow, value, folder):
        if value != registry or value.get('status') != 'documented':
            raise ValueError('TEST_ONLY permission changed')
    monkeypatch.setattr(r, '_rights', mock_rights)
    return {'w': w, 'local': local, 'data': data, 'frame': frame, 'unit': unit, 'manifest': manifest,
            'path': path, 'registry': registry, 'context': context}


def load(f):
    return r.display_units(f['data'], f['frame'], 'teks_gundul')


def update_unit(f):
    write(f['path'], f['unit'])
    f['manifest']['approvals'][0]['sha256'] = f['w'].sha_file(f['path'])
    write(f['local'] / 'display/manifest.json', f['manifest'])


def test_verified_synthetic_unit_displays_once_for_two_segments(display_fixture):
    result = load(display_fixture)
    assert len(result) == 1 and len(result[0]['targets']) == 2
    assert result[0]['translation']['text_indonesian'] == SENTINEL
    assert result[0]['publication_ready'] is False  # Preparation hold is never promoted.


@pytest.mark.parametrize('case', ['status', 'text', 'paragraph', 'segment', 'hash', 'chunk', 'version',
    'source', 'target_digest', 'checked_hash', 'review_hash', 'reviewer', 'alignment', 'permission_digest',
    'missing_segment', 'reversed_segments', 'unknown_field', 'publication'])
def test_ineligible_unit_never_displays(display_fixture, case):
    f = display_fixture
    u = f['unit']
    if case == 'status': u['verification']['status'] = 'needs_review'
    elif case == 'text': u['translation']['text_indonesian'] = None
    elif case == 'paragraph': u['paragraph_id'] = 'WRONG'
    elif case == 'segment': u['targets'][0]['segment_id'] = 'WRONG'
    elif case == 'hash': u['targets'][0]['arabic_gundul_sha256'] = '0' * 64
    elif case == 'chunk': u['targets'][0]['chunk_id'] = 'WRONG'
    elif case == 'version': u['dataset_version'] = 'fqdemo-' + '0' * 64
    elif case == 'source': u['source_parts'][0]['source_url'] = 'https://invalid.example/'
    elif case == 'target_digest': u['target_digest'] = '0' * 64
    elif case == 'checked_hash': u['translation']['checked_text_sha256'] = '0' * 64
    elif case == 'review_hash': u['verification']['reviewed_source_digest'] = '0' * 64
    elif case == 'reviewer': u['verification']['reviewer'] = None
    elif case == 'alignment': u['alignment_review']['decision'] = 'needs_review'
    elif case == 'permission_digest': u['permission_registry_digest'] = '0' * 64
    elif case == 'missing_segment': u['targets'].pop()
    elif case == 'reversed_segments': u['targets'].reverse()
    elif case == 'publication': u['publication_ready'] = True
    else: u['hidden_payload'] = SENTINEL
    update_unit(f)
    assert load(f) == []


@pytest.mark.parametrize('case', ['manifest_missing', 'manifest_version', 'manifest_permission', 'manifest_duplicate',
    'manifest_file_hash', 'unapproved', 'no_display_reviewer', 'traversal', 'symlink', 'oversized', 'corrupt', 'csv_changed',
    'csv_renamed_column', 'csv_duplicate_id', 'csv_hash_text', 'context_version', 'rights_revoked'])
def test_catalog_and_input_fail_closed(display_fixture, case):
    f = display_fixture
    m = f['manifest']
    if case == 'manifest_missing':
        (f['local'] / 'display/manifest.json').unlink()
    elif case == 'manifest_version': m['dataset_version'] = 'WRONG'
    elif case == 'manifest_permission': m['permission_registry_digest'] = '0' * 64
    elif case == 'manifest_duplicate': m['approvals'].append(deepcopy(m['approvals'][0]))
    elif case == 'manifest_file_hash': m['approvals'][0]['sha256'] = '0' * 64
    elif case == 'unapproved': m['approvals'][0]['decision'] = 'needs_review'
    elif case == 'no_display_reviewer': m['approvals'][0]['reviewer'] = None
    elif case == 'traversal': m['approvals'][0]['file'] = '../../outside.json'
    elif case == 'symlink':
        # Path.resolve also rejects a directory junction/symlink if present.
        outside = f['local'] / 'outside.json'
        write(outside, f['unit'])
        try: (f['local'] / 'display/units/link.json').symlink_to(outside)
        except OSError: pytest.skip('Windows symlink creation unavailable')
        m['approvals'][0]['file'] = 'units/link.json'
    elif case == 'oversized': f['path'].write_bytes(b'X' * (r.MAX_JSON_BYTES + 1))
    elif case == 'corrupt': f['path'].write_text('{', encoding='utf-8')
    elif case == 'csv_changed': f['data'] += b'\n'
    elif case == 'csv_renamed_column': f['frame'].rename(columns={'teks_gundul': 'judul_arab'}, inplace=True)
    elif case == 'csv_duplicate_id': f['frame'].loc[1, 'id'] = f['frame'].loc[0, 'id']
    elif case == 'csv_hash_text': f['frame'].loc[0, 'teks_gundul'] += 'X'
    elif case == 'context_version': f['context']['version'] = 'WRONG'
    elif case == 'rights_revoked': write(f['local'] / 'permission_registry.json', {'status': 'user_reported_unverified'})
    if case != 'manifest_missing': write(f['local'] / 'display/manifest.json', m)
    assert load(f) == []


def test_permission_gate_precedes_any_unit_or_manifest_read(display_fixture, monkeypatch):
    f = display_fixture
    def blocked(*args): raise ValueError('No verified rights')
    monkeypatch.setattr(r, '_rights', blocked)
    with patch.object(r, '_read_document', wraps=r._read_document) as reads:
        assert load(f) == []
    assert [Path(c.args[0]).name for c in reads.call_args_list] == ['permission_registry.json']


def test_rights_rechecked_without_cached_translation(display_fixture):
    f = display_fixture
    assert load(f)
    write(f['local'] / 'permission_registry.json', {'status': 'user_reported_unverified'})
    assert load(f) == []


def test_partial_catalog_failure_keeps_valid_reference(display_fixture):
    f = display_fixture
    invalid = deepcopy(f['manifest']['approvals'][0])
    invalid.update(unit_id='MISSING', file='units/missing.json')
    f['manifest']['approvals'].append(invalid)
    write(f['local'] / 'display/manifest.json', f['manifest'])
    assert len(load(f)) == 1


def test_json_duplicate_keys_rejected(tmp_path):
    path = tmp_path / 'test.json'
    path.write_text('{"status":1,"status":2}', encoding='utf-8')
    with pytest.raises(ValueError, match='Duplicate'): r._read_json(path)


def test_real_unverified_pilot_returns_unavailable_without_reading_units():
    path = r.ROOT / 'data/demo_fathul_qorib_per_bab/CSV/01_Thaharah.csv'
    if not path.exists(): pytest.skip('Private demo dataset unavailable')
    data = path.read_bytes()
    frame = pd.read_csv(BytesIO(data), dtype=str, keep_default_na=False)
    with patch.object(r, '_read_document', wraps=r._read_document) as reads:
        assert r.display_units(data, frame, 'teks_gundul') == []
    assert [Path(c.args[0]).name for c in reads.call_args_list] == ['permission_registry.json']


@pytest.mark.parametrize('scope', ['storage', 'display'])
def test_both_rights_scopes_required(tmp_path, scope):
    w = r._workflow()
    (tmp_path / 'evidence').mkdir()
    (tmp_path / 'evidence/test_only.txt').write_text('TEST_ONLY_NOT_A_PERMISSION', encoding='utf-8')
    registry = {'status': 'documented', 'evidence_file': 'evidence/test_only.txt'}
    def gate(registry, source, required, local):
        if required == scope: raise ValueError('Missing ' + scope)
    with patch.object(w, 'check_rights', side_effect=gate):
        with pytest.raises(ValueError): r._rights(w, registry, tmp_path)
