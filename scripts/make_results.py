"""Collect stored benchmark runs into results/*.json|csv and Markdown tables. Reads artifacts only; recomputes nothing but the
label-free diagnostics (benchmark/diagnostics.py), which are pure functions of the stored prediction + reference.

    python scripts/make_results.py --set native_grid=int1 --set native_grid=fin1 ...   (RUN is a run-id prefix: <prefix>_main/_adv/_raster)
    python scripts/make_results.py --config results/config.json
Outputs: results/results.json, results/results.csv, results/tables.md
"""
import argparse
import csv
import json
import statistics
from pathlib import Path

from benchmark.diagnostics import diagnose

ROOT = Path(__file__).resolve().parents[1]
MANIFESTS = {"main": "benchmark/manifest.jsonl", "adv": "benchmark/adversarial_manifest.jsonl", "raster": "benchmark/raster_manifest.jsonl"}
LAYOUT = {
    "original": "native text; 1 table, 2 columns; development page",
    "elecom_p9": "native text; 1 table, 2 columns; independent issuer, similar template",
    "daiwabo_p10": "native slide; 3 tables (side by side + lower table), 3 columns",
    "omron_p13": "native; grouped headers, composition %, 5 columns (source blocked)",
    "elecom_p9_scan200": "raster only (200 dpi), no text layer; ELECOM page",
    "daiwabo_p10_scan200": "raster only (200 dpi), no text layer; Daiwabo slide",
    "scan_150": "raster only (150 dpi); original page", "scan_200": "raster only (200 dpi); original page",
    "text_layer_deleted": "raster only (300 dpi); original page", "missing_cell": "one visible cell erased (digital)",
    "sign_erasure": "one △ glyph erased (digital)", "rotation_90": "PDF /Rotate 90 metadata", "tiny_cjk": "page scaled to 50 %",
    "footnote_marker": "'*1' marker appended to one label", "grouped_two": "synthetic; grouped period headers, amount+% columns",
    "grouped_three": "synthetic; 3 sub-columns per period", "merged_headers": "synthetic; 3 header levels",
    "side_by_side": "synthetic; 2 side-by-side tables", "vertical_spacing": "synthetic; vertically stacked CJK labels",
}


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def entries():
    out = {}
    for split, path in MANIFESTS.items():
        if (ROOT / path).exists():
            for line in (ROOT / path).read_text().splitlines():
                e = json.loads(line)
                out[e["document_id"]] = dict(e, _split_key=split)
    return out


def rate(d):
    return None if not d["total"] else d["correct"] / d["total"]


def collect(sets):
    ents, rows = entries(), []
    for backend, prefix in sets:
        for did, e in ents.items():
            folder = ROOT / "runs" / backend / did / f"{prefix}_{e['_split_key']}"
            if not (folder / "metadata.json").exists():
                continue
            meta = load(folder / "metadata.json")
            row = dict(backend=backend, run=prefix, doc_id=did, layout=LAYOUT.get(did, e.get("difficulty", "")), split=e["split"],
                       source_kind=e.get("source_kind"), issuer_relation=e.get("issuer_relation"), reference_status=e.get("human_audit_status"),
                       human_checked_cells=e.get("human_checked_cells", 0), run_status=meta.get("status"))
            if meta.get("status") == "unavailable":
                rows.append(row)
                continue
            cold = folder / "cold"
            m = load(cold / "metrics.json")["metrics"] if (cold / "metrics.json").exists() else None
            ms = meta.get("measurements") or []
            warm = [x["time_ms"] for x in ms[1:] if x.get("time_ms") is not None and x.get("status") in ("success", "partial", "abstained")]
            row.update(cold_ms=meta.get("cold_time_ms"), warm_median_ms=statistics.median(warm) if len(warm) >= 3 else None,
                       warm_n=len(warm), warm_all_ms=warm, peak_rss_mb=ms[0].get("peak_memory_mb") if ms else None,
                       peak_gpu_mb=ms[0].get("peak_gpu_allocation_mb") if ms else None, device=(ms[0].get("device") if ms else None),
                       metrics_path=str((cold / "metrics.json").relative_to(ROOT)), prediction_path=str((cold / "prediction.json").relative_to(ROOT)),
                       error=(ms[0].get("error") or "")[-300:] if ms and ms[0].get("status") in ("error", "oom", "timeout") else None)
            if m:
                gp = ROOT / e.get("gold_path", f"benchmark/gold/{did}.json")
                diag = diagnose(load(gp), load(cold / "prediction.json"))
                row.update(
                    tables_matched=m["tables"]["matched"], tables_gold=m["tables"]["gold"], tables_pred=m["tables"]["predicted"], extra_tables=m["extra_tables"],
                    table_f1=m["tables"]["f1"], rows_matched=m["rows"]["matched"], rows_gold=m["rows"]["gold"], rows_pred=m["rows"]["predicted"],
                    row_f1=m["rows"]["f1"], spurious_rows=m["spurious_rows"], numeric_raw=m["numeric_raw_exact"], numeric_semantic=m["numeric_semantic_exact"],
                    all_raw=m["raw_cell_exact"], coverage=m["cell_coverage"], raw_precision_pred=m["raw_precision_all_predicted"], header_leaf=m["header_role_accuracy"],
                    groups=dict(m["grouped_headers"]), group_parents=m["header_parent_accuracy"], hierarchy=dict(m["hierarchy_edges"]),
                    label_exact=m["raw_label_exact"], row_order=m["row_order_accuracy"], silent=m["silent_omission_rate"], missing=m["missing_cells"],
                    abstention=m["abstention_rate"], correct_abstention=m["correct_abstention"], false_assurance=m["false_assurance"],
                    diag=diag, errors_n=len(load(cold / "metrics.json")["errors"]))
            rows.append(row)
    return rows


def pct(d):
    if d is None or d.get("total") in (None, 0):
        return "n/a"
    return f"{d['correct']}/{d['total']} ({100 * d['correct'] / d['total']:.0f}%)"


def frac(c, t):
    return "n/a" if not t else f"{c}/{t}"


def ms(x):
    return "–" if x is None else (f"{x / 1000:.1f} s" if x >= 1000 else f"{x:.0f} ms")


def mb(x):
    return "–" if x is None else f"{x:.0f}"


def md_main(rows, docs, backends, title):
    lines = [f"#### {title}", "", "| doc | backend | status | tables (matched/gold, extra) | row F1 (P/R) | numeric cells exact (raw) | typed value+status | leaf headers | groups | hierarchy edges | silent omissions | false assurance | cold | warm median | peak RSS MB |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for d in docs:
        for b in backends:
            r = next((x for x in rows if x["doc_id"] == d and x["backend"] == b), None)
            if not r:
                continue
            if "numeric_raw" not in r:
                lines.append(f"| {d} | {b} | {r['run_status']} | – | – | – | – | – | – | – | – | – | – | – | – |")
                continue
            p = r["rows_matched"] / r["rows_pred"] if r["rows_pred"] else None
            rc = r["rows_matched"] / r["rows_gold"] if r["rows_gold"] else None
            lines.append(f"| {d} | {b} | {r['run_status']} | {r['tables_matched']}/{r['tables_gold']}, +{r['extra_tables']} | {r['row_f1']:.2f} ({'n/a' if p is None else f'{p:.2f}'}/{rc:.2f}) | "
                         f"{pct(r['numeric_raw'])} | {pct(r['numeric_semantic'])} | {pct(r['header_leaf'])} | {frac(r['groups']['matched'], r['groups']['gold'])} | "
                         f"{frac(r['hierarchy']['matched'], r['hierarchy']['gold'])} | {pct(r['silent'])} | {'**YES**' if r['false_assurance'] else 'no'} | {ms(r['cold_ms'])} | {ms(r['warm_median_ms'])} | {mb(r['peak_rss_mb'])} |")
    return "\n".join(lines)


def md_diag(rows, docs, backends, title):
    lines = [f"#### {title}", "", "| doc | backend | numeric tokens found anywhere (recall) | token precision | gold rows whose full numeric tuple appears | …and label also exact |", "|---|---|---|---|---|---|"]
    for d in docs:
        for b in backends:
            r = next((x for x in rows if x["doc_id"] == d and x["backend"] == b and "diag" in x), None)
            if not r:
                continue
            g = r["diag"]
            lines.append(f"| {d} | {b} | {pct(g['token_recall'])} | {pct(g['token_precision'])} | {pct(g['row_tuple_recall'])} | {frac(g['label_exact_given_tuple']['correct'], g['label_exact_given_tuple']['total'])} |")
    return "\n".join(lines)


def md_cohort(rows, backends):
    lines = ["| backend | cohort (all pages with a reference) | pages | numeric raw exact | cell coverage | rows matched/gold | tables matched/gold | silent omissions | false-assurance pages |", "|---|---|---|---|---|---|---|---|---|"]
    cohorts = [("independent-issuer source pages (ELECOM, Daiwabo)", lambda r: r["doc_id"] in ("elecom_p9", "daiwabo_p10")),
               ("original development page", lambda r: r["doc_id"] == "original"),
               ("raster derivatives, independent pages", lambda r: r["doc_id"].endswith("_scan200")),
               ("raster controls, original page", lambda r: r["doc_id"] in ("scan_150", "scan_200", "text_layer_deleted")),
               ("digital perturbations, original page", lambda r: r["doc_id"] in ("missing_cell", "sign_erasure", "rotation_90", "tiny_cjk", "footnote_marker")),
               ("synthetic layout controls", lambda r: r["doc_id"] in ("grouped_two", "grouped_three", "merged_headers", "side_by_side", "vertical_spacing"))]
    for b in backends:
        for name, f in cohorts:
            sel = [r for r in rows if r["backend"] == b and "numeric_raw" in r and f(r)]
            if not sel:
                continue
            s = lambda k: (sum(r[k]["correct"] for r in sel), sum(r[k]["total"] for r in sel))
            nr, cv, sl = s("numeric_raw"), s("coverage"), s("silent")
            lines.append(f"| {b} | {name} | {len(sel)} | {frac(*nr)} ({100 * nr[0] / nr[1]:.0f}%) | {frac(*cv)} | {sum(r['rows_matched'] for r in sel)}/{sum(r['rows_gold'] for r in sel)} | "
                         f"{sum(r['tables_matched'] for r in sel)}/{sum(r['tables_gold'] for r in sel)} | {frac(*sl)} | {sum(r['false_assurance'] for r in sel)}/{len(sel)} |")
    return "\n".join(lines)


def md_latency(rows, backends, docs):
    lines = ["| backend | device | cold, median over pages (min–max) | warm median over pages (n pages) | peak RSS MB, max over pages (harness `ru_maxrss`, worker process) | peak GPU MB |", "|---|---|---|---|---|---|"]
    for b in backends:
        sel = [r for r in rows if r["backend"] == b and r["doc_id"] in docs and r.get("cold_ms") is not None]
        if not sel:
            continue
        cold = [r["cold_ms"] for r in sel]
        warm = [r["warm_median_ms"] for r in sel if r.get("warm_median_ms") is not None]
        rss = [r["peak_rss_mb"] for r in sel if r.get("peak_rss_mb")]
        lines.append(f"| {b} | {sel[0].get('device') or 'cpu'} | {ms(statistics.median(cold))} ({ms(min(cold))}–{ms(max(cold))}) | "
                     f"{ms(statistics.median(warm)) if warm else '–'} ({len(warm)}) | {mb(max(rss)) if rss else '–'} | N/A (no usable GPU) |")
    return "\n".join(lines)


def md_before_after(rows_a, rows_b, backend, docs, la, lb):
    lines = [f"| doc | {la}: rows / numeric exact / leaf headers / groups / hierarchy / silent | {lb}: rows / numeric exact / leaf headers / groups / hierarchy / silent |", "|---|---|---|"]
    def cell(r):
        if not r or "numeric_raw" not in r:
            return "–"
        return (f"{r['rows_matched']}/{r['rows_gold']} / {r['numeric_raw']['correct']}/{r['numeric_raw']['total']} / {r['header_leaf']['correct']}/{r['header_leaf']['total']} / "
                f"{r['groups']['matched']}/{r['groups']['gold']} / {r['hierarchy']['matched']}/{r['hierarchy']['gold']} / {r['silent']['correct']}/{r['silent']['total']}")
    for d in docs:
        a = next((x for x in rows_a if x["backend"] == backend and x["doc_id"] == d), None)
        b = next((x for x in rows_b if x["backend"] == backend and x["doc_id"] == d), None)
        lines.append(f"| {d} | {cell(a)} | {cell(b)} |")
    return "\n".join(lines)


MAIN_DOCS = ["original", "elecom_p9", "daiwabo_p10"]
RASTER_DOCS = ["scan_200", "elecom_p9_scan200", "daiwabo_p10_scan200"]
CONTROL_DOCS = ["scan_150", "text_layer_deleted", "missing_cell", "sign_erasure", "rotation_90", "tiny_cjk", "footnote_marker",
                "grouped_two", "grouped_three", "merged_headers", "side_by_side", "vertical_spacing"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", action="append", default=[], help="backend=run_prefix (final results)")
    ap.add_argument("--before", action="append", default=[], help="backend=run_prefix (earlier code state, for before/after)")
    ap.add_argument("--out", default="results")
    a = ap.parse_args()
    sets = [tuple(s.split("=", 1)) for s in a.set]
    rows = collect(sets)
    before = collect([tuple(s.split("=", 1)) for s in a.before])
    out = ROOT / a.out
    out.mkdir(exist_ok=True)
    (out / "results.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "results_before.json").write_text(json.dumps(before, ensure_ascii=False, indent=1), encoding="utf-8")
    flat = [{k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v) for k, v in r.items()} for r in rows]
    keys = sorted({k for r in flat for k in r})
    with open(out / "results.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(flat)
    backends = []
    for b, _ in sets:
        if b not in backends:
            backends.append(b)
    parts = ["<!-- generated by scripts/make_results.py; do not edit by hand -->", "",
             md_main(rows, MAIN_DOCS, backends, "A. Digital pages: original (development), ELECOM p9, Daiwabo p10 (AI-drafted references, 0 human-verified cells)"), "",
             md_main(rows, RASTER_DOCS, backends, "B. Raster-only pages (200 dpi, no text layer)"), "",
             md_diag(rows, MAIN_DOCS + RASTER_DOCS, backends, "C. Label-independent diagnostics (complements the strict label-matched scores)"), "",
             "#### D. Cohort aggregates (micro, denominators shown; every page with a reference is included, failures count as zero)", "", md_cohort(rows, backends), "",
             "#### E. Latency and memory (CPU only)", "", md_latency(rows, backends, MAIN_DOCS), "",
             md_main(rows, CONTROL_DOCS, backends, "F. Controls (perturbed original page and synthetic layouts; development split)"), ""]
    (out / "tables.md").write_text("\n".join(parts), encoding="utf-8")
    ba = ["#### G. native_grid before / after the integration-stage fixes", "", md_before_after(before, rows, "native_grid", MAIN_DOCS + RASTER_DOCS + CONTROL_DOCS, "before (int1)", "after (fin1)")]
    (out / "before_after.md").write_text("\n".join(ba), encoding="utf-8")
    print(f"{len(rows)} rows ({len(before)} before) -> {out}/results.json, results.csv, tables.md, before_after.md")


if __name__ == "__main__":
    main()
