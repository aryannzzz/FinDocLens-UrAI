"""LEGACY v1 comparison, retained for replay; not all included cells are human-verified.

For individually reviewed accuracy versus bulk user-approved agreement, use
benchmark.review_scoring with provenance v2. Never run inference here.

Does not promote AI table boundaries/header periods/hierarchy to human gold.
One-to-one table/row matching uses inherited source geometry as declared context.
No numeric values are used for matching. Missing reviewed slots remain in totals.
"""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path

from benchmark.common import ROOT, read_json, sha256, write_json
from benchmark.evaluate import assignment, iou, norm, ratio, semantic, validate_prediction_shape
from benchmark.human_reference import check, VERSION

EVALUATOR_VERSION = 'human-field-mask-1'
AXES = ('raw_content', 'value_status', 'numeric_raw', 'numeric_value_status', 'text_raw',
        'text_value_status', 'cell_coverage', 'reviewed_label_recall', 'reviewed_raw_label_exact')


def evaluate_subset(gold, pred):
    validate_prediction_shape(pred)
    if gold.get('schema_version') != VERSION:
        raise ValueError('Use the separate human-content reference, not full AI gold')
    for field in ('document_id', 'source_sha256', 'input_sha256'):
        if gold.get(field) != pred.get(field):
            raise ValueError(f'Prediction/reference {field} mismatch')
    gt, pt = gold['tables'], pred.get('tables', [])
    table_map = dict(assignment([[iou(g.get('bbox'), p.get('bbox'))
                                  if g.get('page', 1) == p.get('page', 1) and iou(g.get('bbox'), p.get('bbox')) >= .1 else 0
                                  for p in pt] for g in gt]))
    counts, periods, errors = Counter(), defaultdict(Counter), []
    for ti, table in enumerate(gt):
        pr = pt[table_map[ti]].get('rows', []) if ti in table_map else []
        # Context/parent paths are not human-certified and do not break ties here.
        # Matching is independent of predicted/gold values and column semantics.
        pairs = dict(assignment([[(100+10*iou(row.get('bbox'), prow.get('bbox'))+1/(1+abs(ri-pi)))
                                  if norm(row['label']) == norm(prow.get('label')) else 0
                                  for pi, prow in enumerate(pr)] for ri, row in enumerate(table['rows'])]))
        for ri, row in enumerate(table['rows']):
            prow = pr[pairs[ri]] if ri in pairs else {}
            if row.get('label_review', {}).get('decision') == 'accepted':
                counts['labels'] += 1
                counts['labels_matched'] += ri in pairs
                counts['raw_labels'] += row['raw_label'] == prow.get('raw_label')
            for cell in row['cells']:
                if cell.get('human_review', {}).get('decision') not in {'accepted', 'corrected'}:
                    raise ValueError('Unaccepted cell entered human score denominator')
                counts['cells'] += 1
                numeric = cell['role'] != 'other'
                counts['numeric' if numeric else 'text'] += 1
                candidates = [p for p in prow.get('cells', []) if p.get('column_index') == cell['column_index']]
                pc = candidates[0] if len(candidates) == 1 else None
                found = pc is not None
                raw = found and 'raw' in pc and norm(pc['raw']) == norm(cell['raw'])
                typed = found and semantic(cell, pc)
                counts['matched'] += found
                counts['raw'] += raw
                counts['typed'] += typed
                counts['numeric_raw' if numeric else 'text_raw'] += raw
                counts['numeric_typed' if numeric else 'text_typed'] += typed
                if numeric:
                    basis = cell['period_provenance']['basis']
                    periods[basis]['total'] += 1
                    periods[basis]['correct'] += found and pc.get('period') == cell.get('period')
                if not raw or not typed:
                    errors.append(dict(table_id=table['table_id'], row_id=row['row_id'], column_index=cell['column_index'],
                                       kind='missing_reviewed_cell' if not found else 'reviewed_content_mismatch',
                                       expected_raw=cell['raw'], expected_value=cell['value'], expected_status=cell['status'],
                                       predicted_raw=pc.get('raw') if found else None,
                                       predicted_value=pc.get('value') if found else None,
                                       predicted_status=pc.get('status') if found else None))
    if counts['cells'] != gold['human_checked_cells'] or counts['labels'] != gold['human_checked_labels']:
        raise ValueError('Human scope/count mismatch')
    metrics = dict(raw_content=ratio(counts['raw'], counts['cells']), value_status=ratio(counts['typed'], counts['cells']),
                   numeric_raw=ratio(counts['numeric_raw'], counts['numeric']),
                   numeric_value_status=ratio(counts['numeric_typed'], counts['numeric']),
                   text_raw=ratio(counts['text_raw'], counts['text']), text_value_status=ratio(counts['text_typed'], counts['text']),
                   cell_coverage=ratio(counts['matched'], counts['cells']),
                   reviewed_label_recall=ratio(counts['labels_matched'], counts['labels']),
                   reviewed_raw_label_exact=ratio(counts['raw_labels'], counts['labels']))
    return dict(document_id=gold['document_id'], reference_status=gold['annotation_status'],
                source_kind=gold['source_kind'], issuer_relation=gold['issuer_relation'], source_family=gold['source_family'],
                run_status=pred.get('status', 'unspecified'), blind_test=False, cohort=gold['evaluation_cohort'],
                metrics=metrics, missing_reviewed_cells=counts['cells']-counts['matched'], errors=errors,
                unverified_period_diagnostics={key: ratio(c['correct'], c['total']) for key, c in sorted(periods.items())},
                unscored_human_axes=dict(header_accuracy=dict(total=0, reason='No explicit header verification'),
                                         period_accuracy=dict(total=0, reason='No period verification; inferred lower-table periods are not observed gold'),
                                         hierarchy_accuracy=dict(total=0, reason='Label acceptance does not verify parent paths'),
                                         detection_accuracy=dict(total=0, reason='Completeness and table boundaries remain AI context')),
                matching_policy='One-to-one table IoU >= .1; normalized label equality; row geometry/order break ties; physical column. Geometry is inherited AI context, not a human localization score.',
                whitespace_policy='Remove Unicode whitespace only for raw/normalized labels; preserve monetary glyphs, punctuation and signs')


def compute(reference, config_path):
    documents = check(reference)
    config = read_json(config_path)
    if not config.get('sets') or len({s['name'] for s in config['sets']}) != len(config['sets']):
        raise ValueError('Evaluation needs nonempty, uniquely named sets')
    export_hash = read_json(Path(reference)/'manifest.json')['export_sha256']
    if config.get('reference_export_sha256') != export_hash:
        raise ValueError('Evaluation selection is bound to a different review export')
    reports, groups, periods = {}, {}, {}
    for selection in config['sets']:
        name = selection['name']
        if not name or not all(c.isalnum() or c in '-_' for c in name):
            raise ValueError('Invalid evaluation set name')
        if not selection.get('backends') or len(set(selection['backends'])) != len(selection['backends']):
            raise ValueError('Evaluation needs nonempty, unique backend names')
        if any(not b or not all(c.isalnum() or c in '-_' for c in b) for b in selection['backends']):
            raise ValueError('Invalid backend name')
        seen = set()
        by_backend, backend_periods = defaultdict(list), defaultdict(lambda: defaultdict(Counter))
        expected = {(b, d) for b in selection['backends'] for d in documents}
        for item in selection['predictions']:
            pair = item['backend'], item['document_id']
            if pair in seen or pair not in expected:
                raise ValueError('Duplicate or unexpected backend/document selection')
            seen.add(pair)
            path = ROOT/item['path']
            if sha256(path) != item['sha256']:
                raise ValueError(f'Stored prediction hash mismatch: {path}')
            pred = read_json(path)
            if pred.get('backend') != item['backend']:
                raise ValueError(f'Prediction backend mismatch: {path}')
            report = evaluate_subset(documents[item['document_id']], pred)
            report.update(prediction_path=item['path'], prediction_sha256=item['sha256'],
                          source_run_id=path.parents[1].name,
                          reference_sha256=sha256(Path(reference)/(item['document_id']+'.json')),
                          evaluator_version=EVALUATOR_VERSION)
            reports[f"reports/{name}/{item['backend']}/{item['document_id']}.json"] = report
            by_backend[item['backend']].append(report)
            for basis, value in report['unverified_period_diagnostics'].items():
                backend_periods[item['backend']][basis].update({k: value[k] for k in ('correct', 'total')})
        if seen != expected:
            raise ValueError(f'Missing prediction selections: {sorted(expected-seen)}; no silent denominator reduction')
        groups[name] = {b: {axis: ratio(sum(r['metrics'][axis]['correct'] for r in rs),
                                       sum(r['metrics'][axis]['total'] for r in rs)) for axis in AXES}
                        for b, rs in sorted(by_backend.items())}
        periods[name] = {b: {basis: ratio(v['correct'], v['total']) for basis, v in sorted(values.items())}
                         for b, values in sorted(backend_periods.items())}
    summary = dict(schema_version=EVALUATOR_VERSION, reference_version=read_json(Path(reference)/'manifest.json')['version'],
                   reference_export_sha256=export_hash, reference_lock_sha256=sha256(Path(reference)/'SHA256.json'),
                   selection_sha256=sha256(config_path), cohort='development_exposed_source', blind_test=False,
                   evaluated_fields=['raw', 'value', 'status', 'label', 'raw_label'], inference_run=False,
                   documents={did: dict(cells=d['human_checked_cells'], labels=d['human_checked_labels'], counts=d['counts'],
                                        source_kind=d['source_kind'], issuer_relation=d['issuer_relation'], source_family=d['source_family'])
                              for did, d in documents.items()},
                   scores=groups, unverified_period_diagnostics=periods,
                   caveat='Human content acceptance is not header, period, hierarchy, bounding-box or completeness certification. Source pages were exposed during development; this is not a blind test. Original performance measurements are unchanged.')
    return reports, summary


def run(reference, config_path, out):
    out = Path(out)
    if out.exists():
        raise ValueError(f'Evaluation outputs are create-only: {out}')
    reports, summary = compute(reference, config_path)
    for path, report in reports.items():
        write_json(out/path, report)
    write_json(out/'summary.json', summary)
    write_json(out/'SHA256.json', {str(p.relative_to(out)): sha256(p) for p in sorted(out.rglob('*.json'))})
    return summary


def verify(reference, config_path, out):
    out = Path(out)
    for name, digest in read_json(out/'SHA256.json').items():
        if sha256(out/name) != digest:
            raise ValueError(f'Score output changed: {name}')
    reports, summary = compute(reference, config_path)
    for path, report in {**reports, 'summary.json': summary}.items():
        if read_json(out/path) != report:
            raise ValueError(f'Stored subset score does not reproduce: {path}')
    return summary


def main():
    import sys
    print('LEGACY v1: the 197-cell comparison is user-approved reference agreement, not 197 individually human-verified cells. Use benchmark.review_scoring.', file=sys.stderr)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    summary = (verify if args.verify else run)(args.reference, args.config, args.out)
    print(json.dumps(summary['scores'], ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
