"""Bind already-authorized reference paragraphs to stored CSV predictions.

No inference, normalization, reference loading, permission promotion, or exports.
Call only with units returned by translation_reference.display_units.
"""
from hashlib import sha256

from translation_reference import VERSION, DRAFT_STATUS


def prediction_pairs(units, dataframe, result, *, preview_drafts=False):
    """Fail closed on stale/cross-file results; never substitute reference Arabic.

    Original rows must be identical, including their order. Targets are ordered
    by the verified paragraph, not by text similarity. Keep predictions separate
    so stripping at inference chunk boundaries cannot silently join two words.
    """
    try:
        if (not result or result.get('success') is not True
                or result.get('input_type') != 'csv'
                or result.get('text_column') != 'teks_gundul'
                or not dataframe.columns.is_unique):
            return []
        output = result['dataframe']
        columns = result['output_columns']
        prediction, status = columns['prediction'], columns['status']
        if (not output.columns.is_unique or prediction == status
                or prediction in dataframe.columns or status in dataframe.columns
                or output[list(dataframe.columns)].to_dict('records') != dataframe.to_dict('records')):
            return []
        rows = output.to_dict('records')
        by_id = {row['id']: row for row in rows}
        if len(by_id) != len(rows):
            return []
        pairs, seen = [], set()
        for unit in units:
            try:
                allowed = ('verified', DRAFT_STATUS) if preview_drafts else ('verified',)
                if unit['dataset_version'] != VERSION or unit['verification']['status'] not in allowed:
                    continue
                targets, segments = unit['targets'], []
                ids = [target['segment_id'] for target in targets]
                if not ids or len(set(ids)) != len(ids) or seen.intersection(ids):
                    continue
                for target in targets:
                    row = by_id[target['segment_id']]
                    if (target['paragraph_id'] != unit['paragraph_id']
                            or row['chunk_id'] != target['chunk_id']
                            or str(row['page']) != str(target['pdf_page'])
                            or sha256(row['teks_gundul'].encode('utf-8')).hexdigest() != target['arabic_gundul_sha256']
                            or row[status] != 'berhasil'
                            or not isinstance(row[prediction], str) or not row[prediction].strip()):
                        break
                    segments.append({'segment_id': row['id'], 'prediction': row[prediction]})
                if len(segments) != len(targets):
                    continue  # An incomplete paragraph never gets a whole-paragraph translation.
                pairs.append({'unit': unit, 'segments': segments, 'kitab': by_id[ids[0]].get('kitab', '')})
                seen.update(ids)
            except (KeyError, TypeError, AttributeError):
                continue
        return pairs
    except (KeyError, TypeError, AttributeError, ValueError):
        return []
