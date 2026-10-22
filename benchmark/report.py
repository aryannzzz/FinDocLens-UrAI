"""Build a compact, measured Markdown report from saved outcomes only."""
import argparse
from pathlib import Path

from benchmark.common import ROOT, read_json, sha256, write_json


def fraction(item):
    return f"{item['correct']}/{item['total']}" if 'correct' in item else f"{item['matched']}/{item['gold']}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--summary', nargs='+', required=True)
    parser.add_argument('--out', default='benchmark/reports/measured.md')
    args = parser.parse_args()
    lines = ['# Measured benchmark (AI-drafted references)', '',
             'All cell and structure scores below are provisional agreement with AI-drafted references. Human-verified cells: **0**. No OCR/VLM backend was run in this workstream.', '',
             '| Run / document | Outcome | Tables matched/gold | Rows matched/gold | Numeric raw exact/gold | Header roles/gold | Cold process ms | Warm median ms (3) | Cold peak RSS MiB |',
             '|---|---|---:|---:|---:|---:|---:|---:|---:|']
    stability = []
    for path in args.summary:
        summary = read_json(path)
        for meta in summary['documents']:
            doc = meta['source']['document_id']
            if not meta.get('metrics_path'):
                lines.append(f"| {summary['run_id']} / {doc} | {meta['status']} | — | — | — | — | — | — | — |")
                continue
            m = read_json(ROOT/meta['metrics_path'])['metrics']
            cold = meta['measurements'][0]
            latency = f"{meta['cold_time_ms']:.2f}" if meta['cold_time_ms'] is not None else 'unmeasured'
            warm = f"{meta['warm_median_ms']:.2f}" if meta.get('warm_median_ms') is not None else 'unmeasured'
            memory = f"{cold['peak_memory_mb']:.2f}" if cold.get('peak_memory_mb') is not None else 'unmeasured'
            lines.append(f"| {summary['run_id']} / {doc} | {meta['status']} | {fraction(m['tables'])} | {fraction(m['rows'])} | {fraction(m['numeric_raw_exact'])} | {fraction(m['header_role_accuracy'])} | {latency} | {warm} | {memory} |")
            folder = (ROOT/meta['metrics_path']).parent.parent
            hashes = {p.parent.name: sha256(p) for p in sorted(folder.glob('*/prediction.json'))}
            stability.append(dict(document_id=doc, run_id=summary['run_id'], prediction_sha256=hashes,
                                  identical_predictions=len(set(hashes.values())) == 1))
    lines += ['', 'The cold total covers backend import/load, 200dpi render plus cold PNG export, extraction, evaluation projection and JSON serialization. Warm trials keep the same interpreter/backend but reopen and render the PDF; they do not export another PNG. `process_wall_ms` additionally captures interpreter startup. These are process-cold measurements, with no claim of a cleared OS disk cache. Acquisition, annotation and scoring are excluded.', '',
              'RSS is Linux process-lifetime `ru_maxrss`, including rendering. Warm high-water marks are cumulative and cannot be interpreted as incremental memory. All v2 extraction used the CPU. The recorded `nvidia-smi` probe failed to communicate with the driver; GPU memory is null/unmeasured. No driver or system package changes were attempted.', '',
              'ELECOM is a genuinely different issuer, but its layout is similar to the development page. Its 56/56 tokens therefore do not establish heterogeneous-layout reliability. The hierarchy disagreement is `その他（純額）`: v2 attaches it under `建設仮勘定`, while the source-based draft places it directly under `有形固定資産`. Human review is still required.', '',
              'Daiwabo exposes the layout failure: 1/3 table regions matched, 1/21 rows matched, 8 spurious rows, and 65/67 cell slots omitted without a specific omission warning. Only 2/63 numeric tokens match the draft. The lower table contains four additional explanatory text cells, which are included in all-cell metrics and excluded from numeric-only metrics. A generic unit/header/financial warning does not excuse a silent omission.', '',
              'OMRON was attempted twice and returned HTTP 403. It remains an unavailable candidate, with no fabricated source hash, gold denominator, latency or score. There are two available independent source pages out of three requested candidates. This availability denominator is distinct from the known-cell accuracy denominator.', '',
              'The missing-cell control expects an explicit missing status and achieves 1/1 correct abstention. Sign erasure changes the visible source: the derived reference expects positive `2,979`; the original reference stays `△2,979`. Rotation is PDF rotation metadata with unchanged native coordinates, so success does not establish recognition of physically rotated raster text. Scan/text-layer controls retain their full gold denominators and score zero after explicit abstention.', '',
              'Synthetic grouped columns, nested merged headers, side-by-side tables, decimals/plus/dash/negative-zero tokens, and vertical CJK spacing are development controls. They are not independent-company evidence. The five synthetic layouts abstained; no TEDS, GriTS, CER, statistical significance or model leaderboard is claimed.', '',
              'Review gate status: independent issuer sourcing **met for two pages**; independent human gold **pending**; original sign/dash regression **met**; heterogeneous numeric/grouped-header extraction **fails**; no silent omission **fails on Daiwabo**; readable source crops **generated and AI-inspected, human review pending**.', '',
              'Next steps: review every row and header plus at least 20 numeric cells per independent page in `benchmark/review/index.html`; export named human decisions; version any correction with old/new token, reason, crop and frozen reference hash. Obtain the OMRON source through an authorized local download. Plug the separately owned backends into `docs/BENCHMARK_ADAPTER_CONTRACT.md`, preserving raw results and reporting failures against these same references.']
    Path(args.out).write_text('\n'.join(lines)+'\n', encoding='utf-8')
    write_json(ROOT/'benchmark/reports/prediction_stability.json', stability)
    print(args.out)


if __name__ == '__main__':
    main()
