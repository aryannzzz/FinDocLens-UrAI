"""Reproduce router/span probes and compare new runs with fin1 without writing old artifacts."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
from types import SimpleNamespace as S

from adapters.canonical import _leaf_and_groups
from benchmark.common import ROOT, commit, read_json, utc
from benchmark.evaluate import aggregate
from findoclens.backends.docling_backend import _map_table
from findoclens.router import route


def spans():
    def cell(r, col, text, r1=None, header=False):
        return S(start_row_offset_idx=r, end_row_offset_idx=r1 if r1 is not None else r+1,
                 start_col_offset_idx=col, end_col_offset_idx=col+1, text=text, column_header=header, bbox=None)
    cells = [cell(0, 0, '科目', header=True), cell(0, 1, '2025/3', header=True), cell(0, 2, '2026/3', header=True),
             cell(1, 0, '現金', r1=3), cell(1, 1, '10'), cell(1, 2, '20'), cell(2, 1, '30'), cell(2, 2, '40')]
    table = _map_table(S(data=S(num_rows=3, num_cols=3, table_cells=cells), prov=[]), 0, 400, None)
    heads = [dict(header_id='outer', column_indices=[0, 1], text='連結', row_start=0, period=None),
             dict(header_id='inner', column_indices=[0, 1], text='2025年3月期', row_start=1, period='2025-03'),
             dict(header_id='amount', column_indices=[0], text='金額', row_start=2, period='2025-03', role='amount'),
             dict(header_id='pct', column_indices=[1], text='構成比', row_start=2, period='2025-03', role='composition_pct')]
    for h in heads:
        h.update(rowspan=1, colspan=len(h['column_indices']), bbox=None)
    reference_spans = []
    for path in (ROOT/'benchmark/gold').rglob('*.json'):
        g = read_json(path)
        if isinstance(g, dict):
            reference_spans += [dict(path=str(path.relative_to(ROOT)), header=h) for t in g.get('tables', [])
                                for h in t.get('headers', []) if h.get('rowspan', 1) > 1]
    return dict(body_rowspan=dict(raw_grid=table.grid,
                                 mapped_rows=[dict(label=r.label, cells=[c.raw for c in r.cells]) for r in table.rows]),
                equal_span_header_groups=_leaf_and_groups(dict(table_id='t', headers=heads), 2, {}),
                reference_headers_with_rowspan_gt_one=reference_spans)


def cohorts():
    errors, count = [], 0
    for path in (ROOT/'benchmark/reports').glob('*_fin1_*.json'):
        summary = read_json(path)
        if 'cohorts' not in summary:
            continue
        groups = defaultdict(list)
        for entry in summary['documents']:
            if not entry.get('metrics_path'):
                continue
            report = read_json(ROOT/entry['metrics_path'])
            src = report['source']
            key = '/'.join([src['split'], src['issuer_relation'], src['source_kind'], report['reference_status']])
            groups[key].append(report)
        count += 1
        if {k: aggregate(v) for k, v in groups.items()} != summary['cohorts']:
            errors.append(str(path.relative_to(ROOT)))
    return dict(summaries=count, cohort_mismatches=errors)


def fresh_runs(prefix):
    rows, differences, core_differences = [], [], []
    for path in sorted((ROOT/'runs').glob(f'*/*/{prefix}_*/cold/metrics.json')):
        report = read_json(path)
        backend, did = path.parents[3].name, path.parents[2].name
        suffix = path.parents[1].name.rsplit('_', 1)[-1]
        oldpath = ROOT/f'runs/{backend}/{did}/fin1_{suffix}/cold/metrics.json'
        if oldpath.exists():
            old = read_json(oldpath)
            fields = [k for k in report['metrics'] if old['metrics'].get(k) != report['metrics'][k]]
            if fields:
                differences.append(dict(path=str(path.relative_to(ROOT)), fields=fields))
            p = read_json(path.parent/'prediction.json')
            op = read_json(oldpath.parent/'prediction.json')
            # Extraction data, including table geometry and raw glyphs; excludes timing/provenance.
            if (p['tables'], p['status'], p['issues']) != (op['tables'], op['status'], op['issues']):
                core_differences.append(str(path.relative_to(ROOT)))
        m = report['metrics']
        meta, measurement = read_json(path.parent.parent/'metadata.json'), read_json(path.parent/'measurement.json')
        rows.append(dict(backend=backend, document=did, set=suffix, status=report['run_status'],
                         raw=m['numeric_raw_exact'], all_raw=m['raw_cell_exact'], rows=m['rows'], tables=m['tables'],
                         headers=m['header_role_accuracy'], hierarchy=m['hierarchy_edges'],
                         cold_ms=measurement['time_ms'], warm_median_ms=meta['warm_median_ms'],
                         rss_mb=measurement['peak_memory_mb'], artifact=str(path.relative_to(ROOT))))
    return dict(pages=len(rows), metric_differences=differences, extraction_differences=core_differences, rows=rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--run-prefix', default='independent_review_20261022')
    args = ap.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    router = {}
    for name in ('review_year_amount', 'review_mixed_columns'):
        p = route(ROOT/f'runs/native_grid/{name}/independent_review_20261022/page.pdf', allow_models=False)
        router[name] = dict(status=p['status'], decisions=p['meta']['routing']['decisions'], issues=p['issues'])
    out = dict(timestamp=utc(), git_commit=commit(), router=router, spans=spans(), cohorts=cohorts(), fresh=fresh_runs(args.run_prefix))
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(dict(cohorts=out['cohorts'], fresh_pages=out['fresh']['pages'],
                         metric_differences=out['fresh']['metric_differences'],
                         extraction_differences=out['fresh']['extraction_differences']), indent=2))


if __name__ == '__main__':
    main()
