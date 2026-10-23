"""Create/check an immutable, field-scoped human reference; never edit AI gold.

Free-text correction_needed notes are unresolved. A corrected decision must carry
an explicit {raw,value,status} correction object. Bulk attestations only accept
exported unreviewed content; unreadable/unresolved/missing entries stay excluded.
"""
import argparse
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path

from benchmark.common import ROOT, read_json, sha256, write_json
from benchmark.evaluate import decimal

VERSION = 'human-content-subset-1'
FIELDS = ('raw', 'value', 'status')
DECISIONS = {'accepted', 'corrected', 'correction_needed', 'unreadable', 'unreviewed', 'unresolved'}


def same(a, b):
    return json.dumps(a, sort_keys=True, ensure_ascii=False) == json.dumps(b, sort_keys=True, ensure_ascii=False)


def relative(path):
    return str(Path(path).resolve().relative_to(ROOT.resolve()))


def period_basis(table, cell):
    if cell.get('role') == 'other' or cell.get('period') is None:
        return 'no_period'
    header = next((h for h in table['headers'] if h['header_id'] == cell.get('header_id')), None)
    if not header or not header.get('text') or 'implicit_unprinted' in str(header.get('status', '')):
        return 'inferred_unprinted_header'
    if cell.get('role') == 'change_amount' or '_vs_' in str(cell.get('period')):
        return 'inferred_change_interval'
    return 'printed_header_association'


def compile_reference(export, attestation, originals, identities):
    """Pure import. originals/identities come from pinned references, never predictions."""
    if not export.get('reviewer', '').strip() or not export.get('reviewed_at'):
        raise ValueError('Export needs a named human reviewer and timestamp')
    if export.get('type') != 'human_review_decisions' or not isinstance(export.get('decisions'), list):
        raise ValueError('Not a review decision export')
    if 'AUTOMATED_UI_TEST' in export['reviewer']:
        raise ValueError('Automated test decisions cannot establish human verification')
    if attestation and attestation.get('reviewer') != export['reviewer']:
        raise ValueError('Attestation/export reviewer mismatch')
    attestation = attestation or {}
    for flag in ('accept_all_row_labels', 'accept_exported_unreviewed_cell_values'):
        if flag in attestation and not isinstance(attestation[flag], bool):
            raise ValueError(f'Attestation {flag} must be a boolean')
    if attestation.get('accept_exported_unreviewed_cell_values') and set(attestation.get('reviewed_cell_fields', [])) != set(FIELDS):
        raise ValueError('Bulk cell acceptance must explicitly scope raw/value/status')
    scope_ids = attestation.get('document_ids', [])
    if not set(scope_ids) <= set(originals):
        raise ValueError('Attestation includes unknown documents')
    slots = {}
    for did, gold in originals.items():
        for table in gold['tables']:
            for row in table['rows']:
                for cell in row['cells']:
                    key = f"{did}:{row['row_id']}:{cell['column_index']}"
                    slots[key] = (did, table, row, cell)
    exported = {}
    for decision in export['decisions']:
        key = decision.get('key')
        if key in exported or key not in slots:
            raise ValueError(f'Duplicate/unknown decision key: {key}')
        did, table, row, cell = slots[key]
        gold, identity = originals[did], identities[did]
        expected = dict(document_id=did, source_sha256=gold['source_sha256'], input_sha256=gold['input_sha256'],
                        gold_sha256=identity['gold_sha256'], source_page_index=gold['source_page_index'],
                        selected_page_index=0, table_id=table['table_id'], row_id=row['row_id'],
                        column_index=cell['column_index'], bbox=cell['bbox'], expected_raw=cell['raw'],
                        expected_value=cell['value'], expected_status=cell['status'])
        for field, value in expected.items():
            if field not in decision or not same(decision[field], value):
                raise ValueError(f'Stale/mismatching {field}: {key}')
        if decision.get('decision') not in DECISIONS:
            raise ValueError(f'Unknown decision status: {key}')
        exported[key] = decision
    documents = {}
    for did, gold in originals.items():
        out = deepcopy(gold)
        out.update(schema_version=VERSION, annotation_status='partially_human_verified',
                   human_checked_cells=0, human_checked_labels=0, blind_test=False,
                   source_kind=identities[did].get('source_kind', 'source'),
                   source_family=identities[did].get('source_family', 'unspecified'),
                   issuer_relation=identities[did].get('issuer_relation', 'unspecified'),
                   evaluation_cohort='development_exposed_source',
                   verification=dict(reviewer=export['reviewer'], export_reviewed_at=export['reviewed_at'],
                                     export_sha256=identities[did]['export_sha256'],
                                     attestation_sha256=identities[did].get('attestation_sha256'),
                                     reviewed_cell_fields=list(FIELDS),
                                     excluded_fields=['period', 'role', 'header_id', 'headers', 'units', 'hierarchy',
                                                      'table_boundaries', 'source_boxes', 'completeness']),
                   scope=dict(tables_complete=False, rows_complete=False, cells_complete=False,
                              note='Only accepted content/labels are human-reviewed. AI geometry, hierarchy, headers and completeness are alignment context, not human gold.'),
                   derived_from=deepcopy(identities[did]), decision_ledger=[],
                   label_review_basis='reviewer_attestation' if did in scope_ids and attestation.get('accept_all_row_labels') else 'unreviewed')
        label_accept = out['label_review_basis'] == 'reviewer_attestation'
        for table in out['tables']:
            for header in table['headers']:
                header['human_review_status'] = 'unreviewed'
                header['source_observability'] = 'printed' if header.get('text') and header.get('bbox') else 'implicit_unprinted'
            for row in table['rows']:
                row['label_review'] = dict(decision='accepted' if label_accept else 'unreviewed',
                                           basis=out['label_review_basis'], fields=['label', 'raw_label'] if label_accept else [])
                out['human_checked_labels'] += label_accept
                kept = []
                for cell in row['cells']:
                    key = f"{did}:{row['row_id']}:{cell['column_index']}"
                    original = exported.get(key)
                    decision = original.get('decision') if original else 'missing_from_export'
                    effective, basis = decision, 'export'
                    issue = None
                    if decision == 'unreviewed' and original.get('correction'):
                        effective, issue = 'unresolved', 'Unreviewed correction note needs adjudication'
                    elif decision == 'unreviewed' and did in scope_ids and attestation.get('accept_exported_unreviewed_cell_values'):
                        effective, basis = 'accepted', 'reviewer_bulk_attestation'
                    if effective == 'corrected':
                        correction = original.get('correction')
                        if not isinstance(correction, dict) or set(correction) != set(FIELDS):
                            effective, issue = 'unresolved', 'Corrected needs an explicit raw/value/status object; no free-text guessing'
                        else:
                            for field in FIELDS:
                                cell[field] = deepcopy(correction[field])
                            if not isinstance(cell['raw'], (str, type(None))) or cell['status'] not in {
                                'observed', 'negative_zero', 'not_reported', 'absent_text_cell', 'uncertain', 'unreadable', 'unparseable'}:
                                raise ValueError(f'Invalid structured correction: {key}')
                            if cell['status'] in {'not_reported', 'absent_text_cell', 'unreadable'} and cell['value'] is not None:
                                raise ValueError(f'Null-status correction carries a value: {key}')
                            if cell['status'] == 'observed' and (cell['raw'] is None or cell['value'] is None):
                                raise ValueError(f'Observed correction needs raw and value: {key}')
                            if cell['status'] == 'negative_zero' and (isinstance(cell['value'], bool) or cell['value'] != 0):
                                raise ValueError(f'Negative-zero correction must have numeric value zero: {key}')
                            if cell['role'] != 'other' and cell['status'] in {'observed', 'negative_zero'} and decimal(cell['value']) is None:
                                raise ValueError(f'Financial correction needs a finite numeric value: {key}')
                    eligible = effective in {'accepted', 'corrected'}
                    review = dict(key=key, exported_decision=decision, effective_decision=effective,
                                  basis=basis, included_in_content_metrics=eligible, issue=issue,
                                  original_export_entry=deepcopy(original))
                    out['decision_ledger'].append(review)
                    if not eligible:
                        continue
                    cell['annotation_status'] = 'partially_human_verified'
                    cell['human_review'] = dict(decision=effective, basis=basis, reviewed_fields=list(FIELDS),
                                               exported_decision=decision, reviewer=export['reviewer'],
                                               original_content={k: deepcopy(slots[key][3][k]) for k in FIELDS})
                    cell['period_provenance'] = dict(basis=period_basis(table, cell), human_review_status='unreviewed',
                                                     included_in_human_metrics=False)
                    kept.append(cell)
                    out['human_checked_cells'] += 1
                row['cells'] = kept
        out['counts'] = dict(exported_decisions=dict(Counter(x['exported_decision'] for x in out['decision_ledger'])),
                             effective_decisions=dict(Counter(x['effective_decision'] for x in out['decision_ledger'])),
                             human_numeric_cells=sum(c['role'] != 'other' for t in out['tables'] for r in t['rows'] for c in r['cells']),
                             human_text_cells=sum(c['role'] == 'other' for t in out['tables'] for r in t['rows'] for c in r['cells']),
                             human_headers=0, human_periods=0, human_hierarchy_edges=0,
                             period_context=dict(Counter(c['period_provenance']['basis'] for t in out['tables'] for r in t['rows'] for c in r['cells'])))
        if not out['human_checked_cells'] and not out['human_checked_labels']:
            out['annotation_status'] = 'ai_draft'
        documents[did] = out
    return documents


def build(decisions_path, attestation_path, out):
    out = Path(out)
    if out.exists():
        raise ValueError(f'Reference versions are create-only: {out}')
    export = read_json(decisions_path)
    attestation = read_json(attestation_path) if attestation_path else {}
    export_hash = sha256(decisions_path)
    if attestation and attestation.get('export_sha256') != export_hash:
        raise ValueError('Attestation is bound to a different export')
    entries = {e['document_id']: e for e in map(json.loads, (ROOT/'benchmark/manifest.jsonl').read_text().splitlines())}
    dids = sorted({d['document_id'] for d in export['decisions']} | set(attestation.get('document_ids', [])))
    if not dids:
        raise ValueError('No reviewed source documents in export/attestation')
    originals, identities = {}, {}
    for did in dids:
        if did not in entries or entries[did]['status'] != 'available':
            raise ValueError(f'Unavailable source: {did}')
        gold_path = ROOT/f'benchmark/gold/{did}.json'
        gold = read_json(gold_path)
        for field in ('source_sha256', 'input_sha256', 'source_page_index'):
            if gold.get(field) != entries[did].get(field):
                raise ValueError(f'Manifest/reference {field} mismatch: {did}')
        input_path = ROOT/entries[did]['input_path']
        if sha256(input_path) != gold['input_sha256']:
            raise ValueError(f'Source PDF hash mismatch: {did}')
        originals[did] = gold
        identities[did] = dict(gold_path=relative(gold_path), gold_sha256=sha256(gold_path),
                               export_path=relative(decisions_path), export_sha256=export_hash,
                               attestation_path=relative(attestation_path) if attestation_path else None,
                               attestation_sha256=sha256(attestation_path) if attestation_path else None,
                               input_path=entries[did]['input_path'], input_sha256=gold['input_sha256'],
                               source_kind=entries[did]['source_kind'], source_family=entries[did]['source_family'],
                               issuer_relation=entries[did]['issuer_relation'])
    documents = compile_reference(export, attestation, originals, identities)
    out.mkdir(parents=True)
    for did, doc in documents.items():
        write_json(out/f'{did}.json', doc)
    write_json(out/'manifest.json', dict(schema_version=VERSION, version=out.name,
                                        export_path=relative(decisions_path), export_sha256=export_hash,
                                        attestation_path=relative(attestation_path) if attestation_path else None,
                                        attestation_sha256=sha256(attestation_path) if attestation_path else None,
                                        documents={did: dict(path=f'{did}.json', cells=d['human_checked_cells'], labels=d['human_checked_labels'],
                                                             source_kind=d['source_kind'], source_family=d['source_family'],
                                                             issuer_relation=d['issuer_relation'],
                                                             counts=d['counts'], blind_test=False) for did, d in documents.items()}))
    write_json(out/'SHA256.json', {p.name: sha256(p) for p in sorted(out.glob('*.json'))})
    return documents


def check(folder):
    folder = Path(folder)
    locks = read_json(folder/'SHA256.json')
    for name, digest in locks.items():
        if sha256(folder/name) != digest:
            raise ValueError(f'Human reference changed after freeze: {name}')
    manifest = read_json(folder/'manifest.json')
    for kind in ('export', 'attestation'):
        if manifest.get(kind+'_path') and sha256(ROOT/manifest[kind+'_path']) != manifest[kind+'_sha256']:
            raise ValueError(f'Changed review input: {kind}')
    docs, originals, identities = {}, {}, {}
    for did, info in manifest['documents'].items():
        doc = read_json(folder/info['path'])
        source = doc['derived_from']
        for kind in ('gold', 'input'):
            if sha256(ROOT/source[kind+'_path']) != source[kind+'_sha256']:
                raise ValueError(f'Changed {kind}: {did}')
        docs[did], originals[did], identities[did] = doc, read_json(ROOT/source['gold_path']), source
    rebuilt = compile_reference(read_json(ROOT/manifest['export_path']),
                                read_json(ROOT/manifest['attestation_path']) if manifest.get('attestation_path') else {}, originals, identities)
    if not same(docs, rebuilt):
        raise ValueError('Human reference does not reproduce from the archived decisions and attestation')
    return docs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--decisions', type=Path)
    parser.add_argument('--attestation', type=Path)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--check', type=Path)
    args = parser.parse_args()
    if args.check:
        docs = check(args.check)
    else:
        if not args.decisions or not args.out:
            parser.error('--decisions and --out are required when creating a version')
        docs = build(args.decisions, args.attestation, args.out)
    print(json.dumps({did: dict(cells=d['human_checked_cells'], labels=d['human_checked_labels'], counts=d['counts'])
                      for did, d in docs.items()}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
