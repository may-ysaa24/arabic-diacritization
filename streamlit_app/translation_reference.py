"""Read-only, fail-closed display adapter for curated V2 reference units.

No inference, network, translation generation, draft promotion, or export.
Only a separate, manually approved display manifest can expose a V2 unit.
"""
from functools import lru_cache
from hashlib import sha256
from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
V2 = ROOT / 'references/fathul_qorib/pilot_thaharah_10_v2'
VERSION = 'fqdemo-792a1dcaed5818be82452479129e6ce2d4c3a25015634f389baac44634c794b5'
CSV_SHA256 = 'e14c1c70e9596ab28467f50c1dbae222c4663c92a46ef8dde63b424509a42e03'
MAX_JSON_BYTES = 256 * 1024
MAX_UNITS = 100


def is_demo_csv(dataframe, column):
    """UI visibility hint only; this does NOT authorize reference matching."""
    return (column == 'teks_gundul' and {'id', 'chunk_id', 'page', 'teks_gundul'} <= set(dataframe.columns)
            and 0 < len(dataframe) <= 10000
            and all(isinstance(value, str) and re.fullmatch(r'FQDEMO_\d{2}_\d{5}', value)
                    for value in dataframe['id']))


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key')
        result[key] = value
    return result


def _read_document(path):
    with Path(path).open('rb') as stream:
        data = stream.read(MAX_JSON_BYTES + 1)
    if len(data) > MAX_JSON_BYTES:
        raise ValueError('Reference metadata exceeds size limit')
    return json.loads(data.decode('utf-8'), object_pairs_hook=_unique_object), sha256(data).hexdigest()


def _read_json(path):
    return _read_document(path)[0]


@lru_cache(maxsize=1)
def _workflow():
    # Cache code only, never rights, evidence, manifests, or translation payloads.
    spec = spec_from_file_location('_fq_reference_workflow', V2 / 'workflow.py')
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _rights(workflow, registry, local):
    workflow.require(registry['status'] == 'documented', 'Permission is not documented')
    evidence = workflow.confined(local / 'evidence', local / registry['evidence_file'])
    workflow.require(evidence.stat().st_size <= 10 * 1024 * 1024, 'Evidence too large')
    for scope in ('storage', 'display'):
        workflow.check_rights(registry, 'primary', scope, local)


def _display_units(upload_data, dataframe, column, local, workflow, context_loader):
    """Internal injectable seam used by synthetic tests; production paths are fixed."""
    from jsonschema import ValidationError

    if not is_demo_csv(dataframe, column) or sha256(upload_data).hexdigest() != CSV_SHA256:
        return []
    local = Path(local).resolve()
    registry = _read_json(workflow.confined(local, local / 'permission_registry.json'))
    # Gate before reading ANY reference text (including unpublished draft JSONL).
    _rights(workflow, registry, local)
    permission_digest = workflow.fingerprint(registry)
    display = workflow.confined(local, local / 'display')
    manifest = _read_json(workflow.confined(display, display / 'manifest.json'))
    workflow.require(manifest['schema_version'] == '1.0' and manifest['dataset_version'] == VERSION
                     and manifest['csv_sha256'] == CSV_SHA256
                     and manifest['permission_registry_digest'] == permission_digest, 'Unapproved display catalog')
    approvals = manifest['approvals']
    workflow.require(isinstance(approvals, list) and 0 < len(approvals) <= MAX_UNITS, 'Invalid catalog size')
    workflow.require(len({a['unit_id'] for a in approvals}) == len(approvals), 'Duplicate display approval')
    context = context_loader()
    workflow.require(context['version'] == VERSION, 'Unsupported dataset version')
    rows = dataframe.to_dict('records')
    workflow.require(len(rows) == len(context['demo']) and len({r['id'] for r in rows}) == len(rows), 'Changed CSV IDs')
    for row in rows:
        expected = context['demo'][row['id']]
        workflow.require(all(str(row[key]) == expected[key] for key in ('id', 'chunk_id', 'page', 'teks_gundul')), 'Changed CSV target')
    result = []
    seen = set()
    for approval in approvals:
        # An approval is an explicit human display decision, independent of the
        # V2 draft's publication_ready=false hold. It never permits redistribution.
        try:
            workflow.require(approval['decision'] == 'approved_for_display'
                             and isinstance(approval['reviewer'], str) and approval['reviewer'].strip(), 'Display review required')
            workflow.check_time(approval['reviewed_at'])
            unit_path = workflow.confined(display / 'units', display / approval['file'])
            unit, file_digest = _read_document(unit_path)
            workflow.require(file_digest == approval['sha256'], 'Changed display unit')
            workflow.require(unit['unit_id'] == approval['unit_id']
                             and unit['permission_registry_digest'] == permission_digest
                             and unit['verification']['status'] == 'verified', 'Ineligible reference')
            workflow.validate_collection([unit], context)
            ids = [target['segment_id'] for target in unit['targets']]
            workflow.require(not (seen & set(ids)), 'Overlapping display units')
            seen.update(ids)
            result.append(unit)
        except (ValueError, KeyError, TypeError, OSError, ValidationError):
            # A bad approved file must not expose its text or block other units.
            continue
    # Recheck rights after IO. No session/global cache can retain a revoked grant.
    current = _read_json(workflow.confined(local, local / 'permission_registry.json'))
    workflow.require(workflow.fingerprint(current) == permission_digest, 'Permission changed during read')
    _rights(workflow, current, local)
    return result


def display_units(upload_data, dataframe, column):
    """Return eligible whole-paragraph units, or an empty list without text leakage."""
    try:
        workflow = _workflow()
        return _display_units(upload_data, dataframe, column, V2 / '.local', workflow,
                              lambda: workflow.load_context(ROOT, V2.parent / 'pilot_thaharah_10'))
    except (ValueError, KeyError, TypeError, OSError, ImportError, AttributeError):
        return []
