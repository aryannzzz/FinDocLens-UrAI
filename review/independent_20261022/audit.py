"""Independent, non-mutating audit of fin1 metrics plus synthetic failure probes.

Run from the repository root with PYTHONPATH=. .venv/bin/python
review/independent_20261022/audit.py --out review/independent_20261022/audit.json
Existing output files are never replaced. No reference annotation is written.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import time

import fitz

from adapters.canonical import convert
from adapters.contract import check_prediction
from benchmark.common import ROOT, commit, frozen_check, read_json, sha256, utc
from benchmark.evaluate import evaluate
from benchmark.run import hardware
from findoclens.backends import native_grid


def reference_entries():
    return {e['document_id']: e for name in ('manifest', 'adversarial_manifest', 'raster_manifest')
            for e in map(json.loads, (ROOT / f'benchmark/{name}.jsonl').read_text().splitlines())}


def saved_audit():
    entries = reference_entries()
    totals = dict(predictions=0, metric_mismatches=[], contract_violations=[], hash_errors=[],
                  raw_artifact_hashes_checked=0, nondeterministic=[])
    for path in sorted((ROOT / 'runs').glob('*/*/fin1_*/cold/prediction.json')):
        did = path.parents[2].name
        entry = entries[did]
        gold_path = ROOT / entry.get('gold_path', f'benchmark/gold/{did}.json')
        g = read_json(gold_path)
        core_hashes = set()
        for trial in sorted(path.parent.parent.glob('*/prediction.json')):
            if trial.parent.name == 'raw':
                continue
            p, old = read_json(trial), read_json(trial.parent / 'metrics.json')
            totals['predictions'] += 1
            fresh = evaluate(g, p)['metrics']
            if fresh != old['metrics']:
                totals['metric_mismatches'].append(str(trial.relative_to(ROOT)))
            violations = check_prediction(p)
            if violations:
                totals['contract_violations'].append(dict(path=str(trial.relative_to(ROOT)), violations=violations))
            if old.get('gold_sha256') != sha256(gold_path) or old.get('prediction_sha256') != sha256(trial):
                totals['hash_errors'].append(str(trial.relative_to(ROOT)))
            canonical = {k: v for k, v in p.items() if k != 'provenance'}
            core_hashes.add(hashlib.sha256(json.dumps(canonical, sort_keys=True).encode()).hexdigest())
            provenance = p.get('provenance', {})
            for artifact in (provenance.get('raw_artifacts', {}) if isinstance(provenance, dict) else {}).values():
                totals['raw_artifact_hashes_checked'] += 1
                f = path.parent.parent / artifact['path']
                if not f.exists() or sha256(f) != artifact['sha256']:
                    totals['hash_errors'].append(str(f.relative_to(ROOT)))
        if len(core_hashes) > 1:
            totals['nondeterministic'].append(str(path.parent.parent.relative_to(ROOT)))
    return totals


def evaluator_probes():
    g = read_json(ROOT / 'benchmark/gold/original.json')
    base = deepcopy(g)
    base['status'] = 'success'
    variants = {}
    p = deepcopy(base)
    for t in p['tables']:
        for r in t['rows']:
            for c in r['cells']:
                c.update(period='1900-01-01', role='composition_pct', header_id='wrong')
    variants['all_cell_periods_roles_links_wrong'] = p
    p = deepcopy(base)
    for t in p['tables']:
        t['rows'].reverse()
        for i, r in enumerate(t['rows']):
            r['row_index'] = i
    variants['rows_reversed_and_reindexed'] = p
    p = deepcopy(base)
    for t in p['tables']:
        for r in t['rows']:
            for c in r['cells']:
                c['bbox'] = [0, 0, 1, 1]
        t['headers'].append(dict(header_id='extra', column_index=999, text='extra', period='1900', role='amount'))
    variants['invalid_evidence_and_extra_header'] = p
    p = deepcopy(base)
    p['tables'][0]['rows'].pop()
    variants['tail_row_deleted'] = p
    p = deepcopy(p)
    p['issues'] = [dict(code='omitted_table', region=999, bbox=[0, 0, 1, 1])]
    variants['tail_deleted_unrelated_region_warning'] = p
    p = deepcopy(base)
    extra = deepcopy(p['tables'][0])
    extra['bbox'] = [1000, 1000, 1100, 1100]
    p['tables'].append(extra)
    variants['extra_unmatched_table_headers'] = p
    out = {name: evaluate(g, p)['metrics'] for name, p in variants.items()}
    assert out['tail_row_deleted']['raw_cell_exact']['total'] == 74
    assert out['all_cell_periods_roles_links_wrong']['false_assurance'] is False
    assert out['rows_reversed_and_reindexed']['row_order_accuracy']['correct'] == 1
    return out


def synthetic_probe(folder, name, *, years=False, one_column=False, extra_single=False):
    """New deterministic visual truth; labels/values declared before calling the parser."""
    folder.mkdir(parents=True, exist_ok=True)
    pdf = folder / 'page.pdf'
    if pdf.exists():
        raise FileExistsError(pdf)
    doc = fitz.open()
    page = doc.new_page(width=800, height=500)
    font = fitz.Font('japan')

    def text(x, y, s):
        page.insert_text((x, y), s, fontname='japan', fontsize=11)
        return [x, y - 11 * font.ascender, x + font.text_length(s, fontsize=11), y - 11 * font.descender]

    truth = []
    def add_table(x0, ncol, tag):
        text(x0, 45, '（百万円）')
        headers = []
        for k in range(ncol):
            box = text(x0 + 160 + k * 85, 75, ('2025/3', '2026/3')[k])
            headers.append(dict(header_id=f'c{k}', column_index=k, period=('2025-03-31', '2026-03-31')[k],
                                role='amount', bbox=box, text=('2025/3', '2026/3')[k], kind='leaf'))
        rows = []
        for i, label in enumerate(('現金', '売掛金', '棚卸資産', 'その他')):
            y = 120 + i * 55
            lb = text(x0, y, label)
            cells = []
            for k in range(ncol):
                raw = str(2025 + k if years and i == 0 else 310 + i * 30 + k * 11)
                box = text(x0 + 160 + k * 85, y, raw)
                cells.append(dict(column_index=k, header_id=f'c{k}', period=headers[k]['period'], role='amount',
                                  raw=raw, value=int(raw), status='observed', bbox=box))
            rows.append(dict(row_id=f'{tag}_{i}', row_index=i, label=label, raw_label=label,
                             parent_path=[], type='item', label_bbox=lb, bbox=[x0, y-15, x0+335, y+5], cells=cells))
        truth.append(dict(table_id=tag, page=1, bbox=[x0, 60, x0+335, 300], headers=headers, rows=rows))
    add_table(25, 1 if one_column else 2, 'left')
    if extra_single:
        add_table(430, 1, 'right')
    doc.save(pdf, no_new_id=True)
    doc.close()
    digest = sha256(pdf)
    ctx = dict(document_id=name, source_sha256=digest, input_sha256=digest)
    gold = dict(**ctx, source_kind='synthetic', issuer_relation='not_applicable_synthetic', split='review_only',
                source_family='independent_review_layout_controls',
                scope=dict(tables_complete=True, rows_complete=True, cells_complete=True),
                annotation_status='ai_draft', human_checked_cells=0, tables=truth)
    start = time.perf_counter()
    native = native_grid.extract(pdf).to_dict()
    p = convert(native, ctx, backend='native_grid')
    result = dict(metrics=evaluate(gold, p)['metrics'], status=p['status'], elapsed_ms=(time.perf_counter()-start)*1000,
                  input_sha256=digest, issues=p['issues'], native_meta=native['meta'])
    for f, obj in [('synthetic_truth.json', gold), ('prediction.json', p), ('native_result.json', native)]:
        (folder / f).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')
    page = fitz.open(pdf)[0]
    page.get_pixmap(dpi=100).save(folder / 'page.png')
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--probe-run-id', default='independent_review_20261022', help='Use a new ID to repeat synthetic generation')
    args = ap.parse_args()
    if not args.probe_run_id or not all(c.isalnum() or c in '-_.' for c in args.probe_run_id) or args.probe_run_id in ('.', '..'):
        ap.error('Invalid probe run ID')
    if args.out.exists():
        raise FileExistsError(args.out)
    start = time.perf_counter()
    result = dict(timestamp=utc(), git_commit=commit(), frozen_changes=frozen_check(), environment=hardware(),
                  reference_status='AI draft; independent AI review is not human certification',
                  saved=saved_audit(), evaluator_probes=evaluator_probes())
    result['native_probes'] = {name: synthetic_probe(ROOT / 'runs/native_grid' / name / args.probe_run_id, name, **opts)
                               for name, opts in [('review_two_columns', {}), ('review_year_amount', dict(years=True)),
                                                  ('review_one_column', dict(one_column=True)),
                                                  ('review_mixed_columns', dict(extra_single=True))]}
    result['elapsed_ms'] = (time.perf_counter()-start)*1000
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(dict(saved=result['saved'], native={k: dict(status=v['status'], raw=v['metrics']['numeric_raw_exact'],
                       silent=v['metrics']['silent_omission_rate']) for k, v in result['native_probes'].items()}), indent=2))


if __name__ == '__main__':
    main()
