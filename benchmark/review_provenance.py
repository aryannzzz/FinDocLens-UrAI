"""Version the distinction between individual source review and bulk approval.

The exported decisions and v1 ledger are immutable inputs. AI visual checks never
establish individual human verification. No parser/model is invoked here.
"""
import argparse
from collections import Counter
from copy import deepcopy
import csv
import io
from pathlib import Path

from benchmark.common import ROOT, read_json, sha256, write_json
from benchmark.human_reference import check as check_v1

VERSION = 'review-provenance-2'
INDIVIDUAL = 'individually_human_reviewed'
BULK = 'bulk_user_approved_ai_cross_checked'


def classify(base, export, audit, clarification):
    if audit.get('human_verified') is not False:
        raise ValueError('AI audit must explicitly disclaim human verification')
    exported = {e['key']: e for e in export['decisions']}
    if len(exported) != len(export['decisions']):
        raise ValueError('Duplicate export decision keys')
    ai_cells = {}
    for c in audit['cells']:
        key = f"{c['document']}:{c['row_id']}:{c['column_index']}"
        if key in ai_cells:
            raise ValueError('Duplicate AI-audit cell key')
        ai_cells[key] = c
    docs, catalog = {}, []
    for did, original in base.items():
        doc = deepcopy(original)
        doc.update(schema_version=VERSION, human_checked_cells=0, human_checked_labels=0,
                   bulk_user_approved_cells=0, user_approved_cells=0,
                   user_attested_labels=sum(r.get('label_review', {}).get('decision') == 'accepted'
                                            for t in original['tables'] for r in t['rows']),
                   label_review_basis='user_attestation_not_individually_logged',
                   verification=dict(reviewer=export['reviewer'], export_reviewed_at=export['reviewed_at'],
                                     classification_policy=clarification['policy'],
                                     individually_reviewed_fields=['raw', 'value', 'status'],
                                     structural_verification=False),
                   scope=dict(tables_complete=False, rows_complete=False, cells_complete=False,
                              note='51 exported individual acceptances across this version; bulk approval and AI checking are not individual human verification. Geometry/structure are unreviewed context.'))
        for table in doc['tables']:
            for header in table['headers']:
                header['human_review_status'] = 'unreviewed'
            for row in table['rows']:
                row['label_review'].update(basis='user_attestation_not_individually_logged', individually_recorded=False)
                for cell in row['cells']:
                    key = f"{did}:{row['row_id']}:{cell['column_index']}"
                    decision = exported.get(key)
                    if not decision:
                        raise ValueError(f'User-approved cell absent from export: {key}')
                    if decision['decision'] in {'accepted', 'corrected'}:
                        category = INDIVIDUAL
                    elif decision['decision'] == 'unreviewed' and cell['human_review']['basis'] == 'reviewer_bulk_attestation':
                        category = BULK
                    else:
                        raise ValueError(f'Unresolved/unreadable decision cannot become approved: {key}')
                    ai = ai_cells.get(key)
                    # In the supplied AI audit, `source_sha256` hashes the
                    # selected one-page PDF, not the original complete filing.
                    if category == BULK and (not ai or ai['raw'] != decision['expected_raw'] or
                                            ai['source_sha256'] != doc['input_sha256'] or
                                            ai.get('model_review_not_human') is not True or
                                            ai.get('independent_visual_check') != 'matches_rendered_source'):
                        raise ValueError(f'Bulk AI cross-check evidence does not match: {key}')
                    reviewed = category == INDIVIDUAL
                    cell['annotation_status'] = 'individually_reviewed_content' if reviewed else 'user_approved_ai_draft'
                    cell['human_review'] = dict(decision='corrected' if decision['decision'] == 'corrected' else 'accepted', classification=category,
                                               individually_reviewed=reviewed,
                                               reviewed_fields=['raw', 'value', 'status'] if reviewed else [],
                                               user_approved_fields=['raw', 'value', 'status'],
                                               exported_decision=decision['decision'], reviewer=export['reviewer'],
                                               individual_reviewed_at=decision.get('reviewed_at') if reviewed else None)
                    cell['period_provenance'].update(human_review_status='unreviewed', included_in_human_metrics=False)
                    doc['human_checked_cells'] += reviewed
                    doc['bulk_user_approved_cells'] += not reviewed
                    doc['user_approved_cells'] += 1
                    catalog.append(dict(key=key, classification=category, document_id=did, table_id=table['table_id'],
                                        row_id=row['row_id'], row_label=row['raw_label'], column_index=cell['column_index'],
                                        raw=cell['raw'], value=cell['value'], status=cell['status'],
                                        individual_reviewed_at=decision.get('reviewed_at') if reviewed else None,
                                        source_page_index=doc['source_page_index'], source_sha256=doc['source_sha256'],
                                        input_sha256=doc['input_sha256'], bbox=cell['bbox'],
                                        period_basis=cell['period_provenance']['basis']))
        # Deliberately preserve the entire old ledger, including its exported states.
        if doc['decision_ledger'] != original['decision_ledger']:
            raise ValueError('Original audit ledger changed')
        doc['annotation_status'] = 'mixed_individual_review_and_user_approval' if doc['human_checked_cells'] else 'user_approved_ai_draft'
        cells = [c for t in doc['tables'] for r in t['rows'] for c in r['cells']]
        doc['counts'] = dict(individually_human_reviewed=doc['human_checked_cells'],
                             bulk_user_approved_ai_cross_checked=doc['bulk_user_approved_cells'],
                             full_user_approved=doc['user_approved_cells'],
                             individually_documented_label_decisions=0, user_attested_labels=doc['user_attested_labels'],
                             individual_numeric=sum(c['human_review']['individually_reviewed'] and c['role'] != 'other' for c in cells),
                             bulk_numeric=sum(not c['human_review']['individually_reviewed'] and c['role'] != 'other' for c in cells),
                             bulk_text=sum(not c['human_review']['individually_reviewed'] and c['role'] == 'other' for c in cells),
                             unreviewed_header_annotations=sum(len(t['headers']) for t in doc['tables']),
                             unreviewed_period_assignments=sum(c.get('period') is not None for c in cells),
                             inferred_unprinted_period_assignments=sum(c['period_provenance']['basis'] == 'inferred_unprinted_header' for c in cells),
                             human_headers=0, human_periods=0, human_hierarchy_edges=0)
        docs[did] = doc
    counts = Counter(e['classification'] for e in catalog)
    if counts[INDIVIDUAL] != clarification['expected_individually_reviewed_cells'] or counts[BULK] != clarification['expected_bulk_user_approved_cells']:
        raise ValueError('Classified counts disagree with the reviewer clarification')
    return docs, sorted(catalog, key=lambda c: c['key'])


def individual_csv(catalog):
    stream = io.StringIO(newline='')
    fields = ['key', 'document_id', 'source_page_index', 'table_id', 'row_id', 'row_label', 'column_index',
              'raw', 'value', 'status', 'individual_reviewed_at']
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n')
    writer.writeheader()
    for entry in catalog:
        if entry['classification'] == INDIVIDUAL:
            writer.writerow({k: entry[k] for k in fields})
    return stream.getvalue()


def inputs(clarification_path):
    clarification = read_json(clarification_path)
    base_path = ROOT/clarification['base_reference']
    if sha256(base_path/'SHA256.json') != clarification['base_reference_lock_sha256']:
        raise ValueError('Base v1 reference changed')
    base = check_v1(base_path)
    manifest = read_json(base_path/'manifest.json')
    export = read_json(ROOT/manifest['export_path'])
    if clarification['reviewer'] != export['reviewer']:
        raise ValueError('Reviewer clarification/export identity mismatch')
    if sha256(ROOT/manifest['export_path']) != clarification['export_sha256']:
        raise ValueError('Clarification/export hash mismatch')
    audit_path = ROOT/clarification['ai_audit']
    if sha256(audit_path) != clarification['ai_audit_sha256']:
        raise ValueError('AI visual audit changed')
    return clarification, base, export, read_json(audit_path)


def build(clarification_path, out):
    out = Path(out)
    if out.exists():
        raise ValueError(f'Provenance versions are create-only: {out}')
    clarification, base, export, audit = inputs(clarification_path)
    docs, catalog = classify(base, export, audit, clarification)
    out.mkdir(parents=True)
    for did, doc in docs.items():
        write_json(out/f'{did}.json', doc)
    write_json(out/'cell_catalog.json', catalog)
    (out/'individually_reviewed_cells.csv').write_text(individual_csv(catalog), encoding='utf-8')
    write_json(out/'manifest.json', dict(schema_version=VERSION, version=out.name,
                                        clarification_path=str(Path(clarification_path).resolve().relative_to(ROOT)),
                                        clarification_sha256=sha256(clarification_path),
                                        base_reference=clarification['base_reference'],
                                        original_export_preserved=True, original_decision_ledgers_preserved=True,
                                        ai_audit_hash_kind='selected_pdf_input_sha256',
                                        class_counts=dict(Counter(e['classification'] for e in catalog)),
                                        human_checked_cells=sum(d['human_checked_cells'] for d in docs.values()),
                                        user_approved_cells=sum(d['user_approved_cells'] for d in docs.values()),
                                        individually_documented_label_decisions=0,
                                        user_attested_labels=sum(d['user_attested_labels'] for d in docs.values()),
                                        structural_annotations_human_verified=False, blind_test=False,
                                        cell_catalog='cell_catalog.json', individual_cell_list='individually_reviewed_cells.csv',
                                        documents={did: dict(path=f'{did}.json', counts=d['counts'],
                                                             source_kind=d['source_kind'], issuer_relation=d['issuer_relation'],
                                                             source_family=d['source_family']) for did, d in docs.items()}))
    write_json(out/'SHA256.json', {p.name: sha256(p) for p in sorted(out.iterdir()) if p.is_file()})
    return docs, catalog


def check(folder):
    folder = Path(folder)
    for name, digest in read_json(folder/'SHA256.json').items():
        if sha256(folder/name) != digest:
            raise ValueError(f'Provenance reference changed: {name}')
    manifest = read_json(folder/'manifest.json')
    path = ROOT/manifest['clarification_path']
    if sha256(path) != manifest['clarification_sha256']:
        raise ValueError('Reviewer clarification changed')
    clarification, base, export, audit = inputs(path)
    docs, catalog = classify(base, export, audit, clarification)
    if (manifest['class_counts'] != dict(Counter(c['classification'] for c in catalog)) or
            manifest['human_checked_cells'] != sum(d['human_checked_cells'] for d in docs.values()) or
            manifest['user_approved_cells'] != len(catalog)):
        raise ValueError('Manifest provenance denominators disagree with source decisions')
    for did, doc in docs.items():
        if read_json(folder/manifest['documents'][did]['path']) != doc:
            raise ValueError(f'Provenance classification does not reproduce: {did}')
    if read_json(folder/'cell_catalog.json') != catalog or (folder/'individually_reviewed_cells.csv').read_text() != individual_csv(catalog):
        raise ValueError('Individual cell catalog does not reproduce')
    return docs, catalog


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--clarification', type=Path)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--check', type=Path)
    args = parser.parse_args()
    if args.check:
        docs, catalog = check(args.check)
    else:
        if not args.clarification or not args.out:
            parser.error('--clarification and --out are required')
        docs, catalog = build(args.clarification, args.out)
    print(dict(Counter(c['classification'] for c in catalog)))


if __name__ == '__main__':
    main()
