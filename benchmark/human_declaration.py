"""Create-only content verification snapshot from an explicit reviewer declaration.

Bulk recording is not bulk approval without inspection. The declaration attests
personal source inspection; historical UI events are preserved, never invented.
No parser/model is loaded. Structure remains unreviewed.
"""
import argparse
from copy import deepcopy
from pathlib import Path

from benchmark.common import ROOT, read_json, sha256, write_json
from benchmark.review_provenance import check as check_v2

VERSION = 'human-visual-declaration-3'
CLASS = 'human_visually_verified_by_explicit_declaration'
METHOD = 'direct_visual_comparison_with_original_source_pdf_images'
RECORDING = 'bulk_entry_based_on_explicit_user_declaration'


def artifacts(declaration_path):
    declaration_path = Path(declaration_path)
    declaration = read_json(declaration_path)
    if (declaration.get('verification_method') != METHOD or declaration.get('recording_method') != RECORDING
            or declaration.get('structural_annotations_verified') is not False
            or declaration.get('verification_completed_at') is not None
            or declaration.get('scope', {}).get('verified_fields') != ['raw', 'value', 'status']):
        raise ValueError('Unsupported declaration method/scope or invented verification time')
    base_path = ROOT/declaration['base_reference']
    if sha256(base_path/'SHA256.json') != declaration['base_reference_lock_sha256']:
        raise ValueError('Historical reference changed')
    base, old_catalog = check_v2(base_path)
    export_path = ROOT/declaration['original_export']
    if sha256(export_path) != declaration['original_export_sha256']:
        raise ValueError('Original review export changed')
    export = read_json(export_path)
    if declaration['reviewer'] != export['reviewer']:
        raise ValueError('Reviewer identity differs from historical export')
    expected = declaration['scope']['documents']
    exported = {d['key']: d for d in export['decisions']}
    if len(exported) != len(export['decisions']) or set(expected) != set(base):
        raise ValueError('Duplicate keys or document scope mismatch')
    declaration_hash = sha256(declaration_path)
    declaration_ref = dict(path=str(declaration_path.resolve().relative_to(ROOT)), sha256=declaration_hash)
    files, catalog, decisions = {}, [], []
    for did, previous in base.items():
        doc = deepcopy(previous)
        count = 0
        for table in doc['tables']:
            for row in table['rows']:
                for cell in row['cells']:
                    key = f"{did}:{row['row_id']}:{cell['column_index']}"
                    e = exported[key]
                    # Unresolved corrections must never disappear under blanket acceptance.
                    if e['decision'] not in {'accepted', 'unreviewed'} or e.get('correction'):
                        raise ValueError(f'Unresolved historical decision requires explicit resolution: {key}')
                    if (cell['raw'], cell['value'], cell['status']) != (e['expected_raw'], e['expected_value'], e['expected_status']):
                        raise ValueError(f'Declaration cannot change a reference value: {key}')
                    if (e['input_sha256'], e['source_sha256']) != (doc['input_sha256'], doc['source_sha256']):
                        raise ValueError(f'Declaration source mismatch: {key}')
                    history = deepcopy(cell['human_review'])
                    cell.update(annotation_status='human_verified_cell_content', human_review=dict(
                        decision='accepted', classification=CLASS, reviewed_fields=['raw', 'value', 'status'],
                        reviewer=declaration['reviewer'], verification_method=METHOD, recording_method=RECORDING,
                        declaration=declaration_ref, verification_completed_at=None,
                        historical_v2_review=history))
                    # No edits to period/header/row/geometry/role annotations.
                    d = {k: deepcopy(v) for k, v in e.items() if k not in {'reviewed_at', 'decision', 'correction'}}
                    d.update(decision='accepted', correction=None, verification_method=METHOD,
                             recording_method=RECORDING, declaration=declaration_ref,
                             historical_exported_decision=e['decision'])
                    decisions.append(d)
                    catalog.append(dict(key=key, document_id=did, table_id=table['table_id'], row_id=row['row_id'],
                                        row_label=row['raw_label'], column_index=cell['column_index'],
                                        raw=cell['raw'], value=cell['value'], status=cell['status'], role=cell['role'],
                                        classification=CLASS, historical_v2_classification=history['classification'],
                                        source_page_index=doc['source_page_index'], input_sha256=doc['input_sha256'],
                                        source_sha256=doc['source_sha256'], bbox=cell['bbox'],
                                        period_basis=cell['period_provenance']['basis']))
                    count += 1
        if count != expected[did]['cell_count'] or any(doc[k] != expected[did][k]
                for k in ('input_sha256', 'source_sha256', 'source_page_index')):
            raise ValueError(f'Declaration document scope mismatch: {did}')
        doc.update(schema_version=VERSION, annotation_status='human_verified_cell_contents_structure_unreviewed',
                   human_checked_cells=count, user_approved_cells=count, bulk_user_approved_cells=0,
                   verification=dict(reviewer=declaration['reviewer'], verification_method=METHOD,
                                     recording_method=RECORDING, declaration=declaration_ref,
                                     verification_completed_at=None, structural_verification=False),
                   scope=dict(tables_complete=False, rows_complete=False, cells_complete=False,
                              annotated_cell_contents_verified=True,
                              note='All annotated cell contents verified by the reviewer declaration. Exhaustiveness, structure, header links, roles and inferred periods are not certified.'))
        historical_counts = doc['counts']
        doc['counts'] = dict(human_verified_cell_contents=count,
                            numeric=sum(c['document_id'] == did and c['role'] != 'other' for c in catalog),
                            text=sum(c['document_id'] == did and c['role'] == 'other' for c in catalog),
                            historical_v2_counts=historical_counts,
                            **{k: historical_counts[k] for k in ('unreviewed_header_annotations', 'unreviewed_period_assignments',
                               'inferred_unprinted_period_assignments', 'human_headers', 'human_periods', 'human_hierarchy_edges')})
        doc['acceptance_record_v3'] = dict(declaration=declaration_ref, accepted_cell_keys=[d['key'] for d in decisions if d['document_id'] == did],
                                           recording_method=RECORDING, per_cell_click_events_created=False)
        files[f'{did}.json'] = doc
    if set(exported) != {c['key'] for c in catalog} or len(catalog) != declaration['scope']['cell_count']:
        raise ValueError('Declaration/export/reference cell scopes differ')
    if (sum(c['role'] != 'other' for c in catalog) != declaration['scope']['financial_cells'] or
            sum(c['role'] == 'other' for c in catalog) != declaration['scope']['text_cells']):
        raise ValueError('Declaration financial/text denominators differ')
    seed = dict(type='human_review_decisions', reviewer=declaration['reviewer'], declaration=declaration_ref,
                verification_method=METHOD, recording_method=RECORDING, decisions=sorted(decisions, key=lambda d: d['key']),
                note='Bulk recorded from explicit personal visual-verification declaration. No per-cell click events or review times are asserted. Structure remains unreviewed.')
    files.update({'cell_catalog.json': sorted(catalog, key=lambda c: c['key']), 'accepted_decisions.json': seed,
                  'manifest.json': dict(schema_version=VERSION, version='v3', declaration=declaration_ref,
                    base_reference=declaration['base_reference'], original_export_preserved=True,
                    original_decision_ledgers_preserved=True, human_checked_cells=len(catalog),
                    verification_method=METHOD, recording_method=RECORDING,
                    verification_completed_at=None, structural_annotations_human_verified=False, blind_test=False,
                    class_counts={CLASS: len(catalog)}, user_attested_labels=sum(d['user_attested_labels'] for d in base.values()),
                    individually_documented_label_decisions=0,
                    documents={did: dict(path=f'{did}.json', cell_count=expected[did]['cell_count'],
                                         input_sha256=base[did]['input_sha256'], counts=files[f'{did}.json']['counts']) for did in base},
                    cell_catalog='cell_catalog.json', review_decisions='accepted_decisions.json')})
    return files


def build(declaration_path, out):
    out = Path(out)
    if out.exists():
        raise ValueError(f'Reference versions are create-only: {out}')
    files = artifacts(declaration_path)
    for name, data in files.items():
        write_json(out/name, data)
    write_json(out/'SHA256.json', {name: sha256(out/name) for name in sorted(files)})
    return files


def check(folder):
    folder = Path(folder)
    lock = read_json(folder/'SHA256.json')
    for name, digest in lock.items():
        if sha256(folder/name) != digest:
            raise ValueError(f'v3 reference changed: {name}')
    manifest = read_json(folder/'manifest.json')
    declaration_path = ROOT/manifest['declaration']['path']
    if sha256(declaration_path) != manifest['declaration']['sha256']:
        raise ValueError('Reviewer declaration changed')
    files = artifacts(declaration_path)
    if set(lock) != set(files):
        raise ValueError('Reference file scope changed')
    for name, expected in files.items():
        if read_json(folder/name) != expected:
            raise ValueError(f'v3 reference does not reproduce: {name}')
    return {did: files[item['path']] for did, item in manifest['documents'].items()}, files['cell_catalog.json']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--declaration', type=Path)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--check', type=Path)
    args = parser.parse_args()
    if args.check:
        docs, catalog = check(args.check)
        print(f'Verified {len(catalog)} declared human-reviewed cell contents; structure unreviewed')
    elif args.declaration and args.out:
        build(args.declaration, args.out)
        print('Created v3 without changing historical references or source values')
    else:
        parser.error('Provide --check, or --declaration and --out')


if __name__ == '__main__':
    main()
