"""Validate reference completeness, evidence, immutable hashes and source-family splits."""
import json
from pathlib import Path

from benchmark.common import ROOT, frozen_check, read_json, sha256


def validate_reference(gold):
    errors = []
    if gold.get('annotation_status') not in {'ai_draft', 'human_verified', 'partially_human_verified'}:
        errors.append('Annotation confidence missing')
    if gold.get('annotation_status') == 'human_verified' and not gold.get('verification', {}).get('reviewer'):
        errors.append('Human verification needs named reviewer')
    total_cells = sum(len(r.get('cells', [])) for t in gold.get('tables', []) for r in t.get('rows', []))
    if gold.get('annotation_status') == 'human_verified' and gold.get('human_checked_cells') != total_cells:
        errors.append('Human verification requires every reference cell checked')
    if not all(gold.get('scope', {}).get(k) is True for k in ('tables_complete', 'rows_complete', 'cells_complete')):
        errors.append('Reference completeness scope missing')
    if not gold.get('tables'):
        errors.append('No annotated tables')
    row_ids = set()
    for table in gold.get('tables', []):
        if not table.get('bbox') or not table.get('rows'):
            errors.append('Table without evidence/rows')
        leaf = [h for h in table.get('headers', []) if h.get('kind', 'leaf') == 'leaf']
        expected = {h['column_index'] for h in leaf}
        if len(expected) != len(leaf):
            errors.append('Duplicate physical header columns')
        for row in table.get('rows', []):
            if row['row_id'] in row_ids:
                errors.append('Duplicate row ID')
            row_ids.add(row['row_id'])
            if not row.get('raw_label') or not row.get('bbox') or not row.get('label_bbox'):
                errors.append('Row label/evidence absent')
            columns = [c['column_index'] for c in row['cells']]
            if row['type'] != 'section' and (set(columns) != expected or len(columns) != len(set(columns))):
                errors.append(f"Incomplete cell slots in {row['row_id']}")
            for cell in row['cells']:
                if any(k not in cell for k in ('raw', 'value', 'status', 'role', 'period', 'bbox')):
                    errors.append('Required cell field missing')
                if not cell.get('bbox'):
                    errors.append('Reference cell needs visual region even when absent')
                if cell.get('value') is None and cell.get('status') == 'observed':
                    errors.append('Null observed value lacks explanation')
    return errors


def main():
    errors = [f'Frozen v2 changed: {p}' for p in frozen_check()]
    for path, digest in read_json(ROOT/'benchmark/gold/SHA256.json').items():
        if sha256(ROOT/path) != digest:
            errors.append(f'Reference changed after freeze: {path}')
        errors.extend(f'{path}: {e}' for e in validate_reference(read_json(ROOT/path)))
    families = {}
    for filename in ('manifest.jsonl', 'adversarial_manifest.jsonl'):
        for line in (ROOT/'benchmark'/filename).read_text().splitlines():
            e = json.loads(line)
            families.setdefault(e['source_family'], set()).add(e['split'])
            if e['status'] == 'available' and sha256(ROOT/e['input_path']) != e['input_sha256']:
                errors.append(f"Input hash mismatch: {e['document_id']}")
    errors += [f'Split leakage for {family}: {splits}' for family, splits in families.items() if len(splits) > 1]
    if errors:
        raise SystemExit('\n'.join(errors))
    print('PASS: frozen v2, reference hashes, complete reference cell slots, evidence boxes, source-family split isolation')


if __name__ == '__main__':
    main()
