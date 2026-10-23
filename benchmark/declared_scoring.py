"""Stored-prediction content accuracy against declared human-verified v3. No inference."""
import argparse
from collections import defaultdict
from copy import deepcopy
from pathlib import Path

from benchmark.common import ROOT, read_json, sha256, write_json
from benchmark.evaluate import ratio
from benchmark.human_evaluate import evaluate_subset
from benchmark.human_reference import VERSION as LEGACY_SCHEMA
from benchmark.human_declaration import check, CLASS

VERSION = 'declared-content-evaluator-3'
SCOPES = {'human_verified_content_accuracy': {CLASS}}
AXES = ('raw_content', 'value_status', 'numeric_raw', 'numeric_value_status',
        'text_raw', 'text_value_status', 'cell_coverage')


def score_scope(doc, prediction, scope):
    if scope not in SCOPES:
        raise ValueError('Unknown provenance scope')
    masked = deepcopy(doc)
    # Reuse content alignment only; never certify structural annotations.
    masked['schema_version'] = LEGACY_SCHEMA
    masked['human_checked_cells'] = 0
    masked['human_checked_labels'] = 0
    row_ids = []
    for table in masked['tables']:
        for row in table['rows']:
            row['label_review']['decision'] = 'unreviewed'
            row['cells'] = [c for c in row['cells'] if c['human_review']['classification'] in SCOPES[scope]]
            masked['human_checked_cells'] += len(row['cells'])
            if row['cells']:
                row_ids.append(dict(table_id=table['table_id'], row_id=row['row_id'],
                                    column_indices=[c['column_index'] for c in row['cells']]))
    result = evaluate_subset(masked, prediction)
    result['metrics'] = {name: result['metrics'][name] for name in AXES}
    result.update(provenance_scope=scope,
                  interpretation='Accuracy against personally source-verified cell contents, bulk recorded by explicit user declaration; structure unreviewed',
                  evaluation_status='scored' if masked['human_checked_cells'] else 'no_cells_in_this_scope',
                  individually_documented_label_decisions=0,
                  alignment_context_rows=row_ids)
    return result


def compute(reference, config_path):
    documents, catalog = check(reference)
    manifest = read_json(Path(reference)/'manifest.json')
    config = read_json(config_path)
    declaration = read_json(ROOT/manifest['declaration']['path'])
    if config.get('reference_export_sha256') != declaration['original_export_sha256']:
        raise ValueError('Wrong original export in score selection')
    if config.get('reference_declaration_sha256') != manifest['declaration']['sha256']:
        raise ValueError('Wrong reviewer declaration in score selection')
    sets = config.get('sets', [])
    if not sets or len({s['name'] for s in sets}) != len(sets):
        raise ValueError('Need nonempty uniquely named score sets')
    reports, aggregate, period_context = {}, {}, {}
    for selection in sets:
        name = selection['name']
        backends = selection['backends']
        if not backends or len(set(backends)) != len(backends):
            raise ValueError('Need nonempty unique backends')
        if any(not n or not all(c.isalnum() or c in '-_' for c in n) for n in [name]+backends):
            raise ValueError('Invalid set/backend name')
        expected = {(b, d) for b in backends for d in documents}
        seen = set()
        grouped = defaultdict(lambda: defaultdict(list))
        for item in selection['predictions']:
            pair = item['backend'], item['document_id']
            if pair in seen or pair not in expected:
                raise ValueError('Duplicate/unexpected prediction')
            seen.add(pair)
            path = ROOT/item['path']
            if sha256(path) != item['sha256']:
                raise ValueError(f'Stored prediction changed: {path}')
            prediction = read_json(path)
            if prediction.get('backend') != item['backend']:
                raise ValueError('Wrong prediction backend')
            scopes = {scope: score_scope(documents[item['document_id']], prediction, scope) for scope in SCOPES}
            report = dict(document_id=item['document_id'], backend=item['backend'],
                          prediction_path=item['path'], prediction_sha256=item['sha256'],
                          source_run_id=path.parents[1].name,
                          reference_sha256=sha256(Path(reference)/(item['document_id']+'.json')),
                          evaluator_version=VERSION, scopes=scopes, blind_test=False)
            reports[f"reports/{name}/{item['backend']}/{item['document_id']}.json"] = report
            for scope, result in scopes.items():
                grouped[scope][item['backend']].append(result)
        if seen != expected:
            raise ValueError(f'Missing predictions: {sorted(expected-seen)}; denominators cannot shrink')
        aggregate[name] = {scope: {b: {axis: ratio(sum(r['metrics'][axis]['correct'] for r in rs),
                                                   sum(r['metrics'][axis]['total'] for r in rs)) for axis in AXES}
                                    for b, rs in sorted(backends_map.items())}
                           for scope, backends_map in grouped.items()}
        period_context[name] = {}
        for b, rs in grouped['human_verified_content_accuracy'].items():
            bases = sorted({basis for r in rs for basis in r['unverified_period_diagnostics']})
            period_context[name][b] = {basis: ratio(sum(r['unverified_period_diagnostics'].get(basis, {}).get('correct', 0) for r in rs),
                                                    sum(r['unverified_period_diagnostics'].get(basis, {}).get('total', 0) for r in rs))
                                       for basis in bases}
    summary = dict(schema_version=VERSION, reference_version=manifest['version'],
                   reference_lock_sha256=sha256(Path(reference)/'SHA256.json'),
                   selection_sha256=sha256(config_path), declaration_sha256=manifest['declaration']['sha256'],
                   class_counts=manifest['class_counts'], individually_documented_label_decisions=0,
                   user_attested_labels=manifest['user_attested_labels'],
                   documents={did: dict(counts=d['counts'], source_kind=d['source_kind'],
                                        issuer_relation=d['issuer_relation'], blind_test=False) for did, d in documents.items()},
                   scores=aggregate, unverified_period_diagnostics=period_context,
                   inference_run=False, cohort='development_exposed_source', blind_test=False,
                   caveat='197 cell contents are human-verified by explicit project-author declaration, bulk recorded without per-cell click/timestamp claims. This is development-exposed content accuracy, not full table accuracy or blind generalization. All structure and inferred periods remain unreviewed.')
    return reports, summary


def run(reference, config_path, out):
    out = Path(out)
    if out.exists():
        raise ValueError(f'Score outputs are create-only: {out}')
    reports, summary = compute(reference, config_path)
    for name, report in reports.items():
        write_json(out/name, report)
    write_json(out/'summary.json', summary)
    write_json(out/'SHA256.json', {str(p.relative_to(out)): sha256(p) for p in sorted(out.rglob('*.json'))})
    return summary


def verify(reference, config_path, out):
    out = Path(out)
    for name, digest in read_json(out/'SHA256.json').items():
        if sha256(out/name) != digest:
            raise ValueError(f'Score artifact changed: {name}')
    reports, summary = compute(reference, config_path)
    for name, expected in {**reports, 'summary.json': summary}.items():
        if read_json(out/name) != expected:
            raise ValueError(f'Score artifact does not reproduce: {name}')
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    summary = (verify if args.verify else run)(args.reference, args.config, args.out)
    print(summary['class_counts'])


if __name__ == '__main__':
    main()
