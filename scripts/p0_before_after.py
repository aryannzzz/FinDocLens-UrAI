"""Before/after evidence for the independent review's four high-severity findings. Reads artifacts and runs the CURRENT code on the
review's retained probe inputs; the "before" numbers are the review's own stored measurements (never recomputed or overwritten)
and, for the evaluator, the pre-fix evaluator loaded verbatim from git (`90f5e50:benchmark/evaluate.py`).

    python scripts/p0_before_after.py --out-json results/p0/before_after.json --out-md docs/P0_BEFORE_AFTER.md [--after-run p0fix2]
"""
import argparse
import importlib.util
import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace as S

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from adapters.canonical import _leaf_and_groups, convert
from benchmark.common import read_json
from benchmark.evaluate import evaluate as evaluate_v2
from findoclens.backends import native_grid
from findoclens.backends.docling_backend import _map_table
from findoclens.coverage import reconcile_prediction
from findoclens.router import route

REVIEW = ROOT / "review/independent_20261022"
PRE_FIX_EVALUATOR_COMMIT = "90f5e50"


def load_v1_evaluator():
    src = subprocess.run(["git", "show", f"{PRE_FIX_EVALUATOR_COMMIT}:benchmark/evaluate.py"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    spec = importlib.util.spec_from_loader("evaluate_v1", loader=None)
    mod = importlib.util.module_from_spec(spec)
    exec(compile(src, "evaluate_v1.py", "exec"), mod.__dict__)
    return mod.evaluate


def frac(r):
    return "n/a" if r is None else f"{r['correct']}/{r['total']}"


# ------------------------------------------------------------------------------------------------------- finding 1
def finding1():
    audit, add = read_json(REVIEW / "audit.json"), read_json(REVIEW / "additional_probes.json")
    rows = []
    for name in ("review_two_columns", "review_year_amount", "review_one_column", "review_mixed_columns"):
        d = ROOT / f"runs/native_grid/{name}/independent_review_20261022"
        gold = read_json(d / "synthetic_truth.json")
        pdf = d / "page.pdf"
        nat = native_grid.extract(pdf).to_dict()
        pred = convert(nat, dict(document_id=gold["document_id"], source_sha256=gold["source_sha256"], input_sha256=gold["input_sha256"]), backend="native_grid")
        m = evaluate_v2(gold, pred)["metrics"]
        r = route(pdf, allow_models=False)
        old_rec = reconcile_prediction(pdf, read_json(d / "native_result.json"))       # the router's check, applied to the PRE-FIX native output
        before = audit["native_probes"][name]
        bm = before["metrics"]
        brouter = add["router"].get(name)
        rows.append(dict(
            case=name, gold_cells=m["gold_cells"], gold_tables=m["tables"]["gold"],
            before=dict(cells=frac(bm["raw_cell_exact"]), tables=f"{bm['tables']['matched']}/{bm['tables']['gold']} (predicted {bm['tables']['predicted']})",
                        status=before["status"], issues=[i["code"] for i in before["issues"]], router=brouter["status"] if brouter else None,
                        route=(brouter["decisions"][-1] if brouter else None)),
            after=dict(cells=frac(m["raw_cell_exact"]), tables=f"{m['tables']['matched']}/{m['tables']['gold']} (predicted {m['tables']['predicted']})",
                       status=pred["status"], review_required=pred["review_required"], review_reasons=pred["review_reasons"],
                       warnings=sorted({i["code"] for i in pred["issues"] if i["severity"] == "warning"} |
                                       {i["code"] for t in pred["tables"] for i in t["issues"] if i["severity"] == "warning"}),
                       silent=frac(m["silent_omission_rate"]), router=r["status"], route=r["meta"]["routing"]["decisions"][-1],
                       structure=frac(m["cell_structure_exact"]), localization=frac(m["cell_evidence_localization"]),
                       prefix_output_reconciliation=f"{len(old_rec['significant'])} significant source numeric tokens in no cell "
                                                    f"({old_rec['covered']}/{old_rec['total']} covered) -> router would return needs_visual_review"
                                                    if old_rec["significant"] else f"{old_rec['covered']}/{old_rec['total']} covered, nothing significant missing")))
    return rows


# ------------------------------------------------------------------------------------------------------- finding 2
def evaluator_variants():
    v1 = load_v1_evaluator()
    g = read_json(ROOT / "benchmark/gold/original.json")
    base = deepcopy(g)
    base["status"] = "success"
    variants = {}

    def cells(p):
        return [c for t in p["tables"] for r in t["rows"] for c in r["cells"]]
    p = deepcopy(base)
    for c in cells(p):
        c.update(period="1900-01-01", role="composition_pct", header_id="wrong")
    variants["all periods wrong, roles wrong, header links dangling"] = p
    p = deepcopy(base)
    for t in p["tables"]:
        t["rows"].reverse()
        for i, r in enumerate(t["rows"]):
            r["row_index"] = i
    variants["rows reversed and re-indexed"] = p
    p = deepcopy(base)
    for c in cells(p):
        c["bbox"] = [0, 0, 1, 1]
    for t in p["tables"]:
        t["headers"].append(dict(header_id="extra", column_index=999, text="extra", period="1900", role="amount", kind="leaf"))
    variants["every evidence box [0,0,1,1] + an extra header"] = p
    p = deepcopy(base)
    p["tables"][0]["rows"].pop()
    variants["last row deleted (no warning)"] = p
    q = deepcopy(p)
    q["issues"] = [dict(code="omitted_table", region=999, bbox=[0, 0, 1, 1])]
    variants["last row deleted + omitted_table warning for an unrelated region"] = q
    q = deepcopy(p)
    q["issues"] = [dict(code="partial_data_row", severity="warning")]
    variants["last row deleted + unlabelled, unlocated partial_data_row warning"] = q
    p = deepcopy(base)
    extra = deepcopy(p["tables"][0])
    extra["bbox"] = [1000, 1000, 1100, 1100]
    p["tables"].append(extra)
    variants["unmatched duplicate table (with its 2 headers)"] = p
    p = deepcopy(base)
    t = p["tables"][0]
    last = t["rows"][-1]
    moved = last["cells"].pop()
    t["rows"][0]["cells"].append(dict(moved, column_index=9))
    variants["one cell removed, same value + context placed in another row's extra slot"] = p
    out = []
    for name, pred in variants.items():
        a, b = v1(g, pred)["metrics"], evaluate_v2(g, pred)["metrics"]
        out.append(dict(variant=name,
                        before=dict(raw=frac(a["raw_cell_exact"]), order=frac(a["row_order_accuracy"]), silent=a["silent_omission_rate"]["correct"],
                                    header_precision=frac(a["header_role_precision"]), false_assurance=a["false_assurance"]),
                        after=dict(raw=frac(b["raw_cell_exact"]), order=frac(b["row_order_accuracy"]), silent=b["silent_omission_rate"]["correct"],
                                   header_precision=frac(b["header_role_precision"]), period=frac(b["cell_period_accuracy"]), role=frac(b["cell_role_accuracy"]),
                                   link=frac(b["cell_header_link_accuracy"]), structure=frac(b["cell_structure_exact"]),
                                   localization=frac(b["cell_evidence_localization"]), false_assurance=b["false_assurance"],
                                   reasons=b["false_assurance_reasons"], unscoped_warnings=b["unscoped_omission_warnings"])))
    return out


# ------------------------------------------------------------------------------------------------------- finding 4
def finding4():
    def cell(r, col, text, r1=None, header=False):
        return S(start_row_offset_idx=r, end_row_offset_idx=r1 if r1 is not None else r + 1, start_col_offset_idx=col,
                 end_col_offset_idx=col + 1, text=text, column_header=header, bbox=None)
    cells = [cell(0, 0, "科目", header=True), cell(0, 1, "2025/3", header=True), cell(0, 2, "2026/3", header=True),
             cell(1, 0, "現金", r1=3), cell(1, 1, "10"), cell(1, 2, "20"), cell(2, 1, "30"), cell(2, 2, "40")]
    table = _map_table(S(data=S(num_rows=3, num_cols=3, table_cells=cells), prov=[]), 0, 400, None)
    heads = [dict(header_id="outer", column_indices=[0, 1], text="連結", row_start=0, period=None),
             dict(header_id="inner", column_indices=[0, 1], text="2025年3月期", row_start=1, period="2025-03"),
             dict(header_id="amount", column_indices=[0], text="金額", row_start=2, period="2025-03", role="amount"),
             dict(header_id="pct", column_indices=[1], text="構成比", row_start=2, period="2025-03", role="composition_pct")]
    for h in heads:
        h.update(rowspan=1, colspan=len(h["column_indices"]), bbox=None)
    after_groups = _leaf_and_groups(dict(table_id="t", headers=heads), 2, {})
    spans_before = read_json(REVIEW / "additional_probes.json")["spans"]
    key = {h["header_id"]: h.get("native_header_id") or h["header_id"] for h in after_groups}
    parents = {key[h["header_id"]]: (key.get(h.get("parent_id")) if h.get("parent_id") else None) for h in after_groups}
    before_parents = {}
    for h in spans_before["equal_span_header_groups"]:
        k = h.get("native_header_id") or h["header_id"]
        before_parents[k] = h.get("parent_id")
    return dict(
        body_rowspan=dict(before=[dict(label=r["label"], cells=r["cells"]) for r in spans_before["body_rowspan"]["mapped_rows"]],
                          after=[dict(label=r.label, raw_label=r.raw_label, cells=[c.raw for c in r.cells]) for r in table.rows],
                          issues=[dict(code=i["code"], severity=i["severity"], rows=i.get("rows"), label=i.get("label")) for i in table.issues if "span" in i["code"] or "inherited" in i["code"]]),
        equal_span_headers=dict(before_parent_ids=before_parents, after_parent_ids=parents))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-json", type=Path, required=True)
    ap.add_argument("--out-md", type=Path, required=True)
    args = ap.parse_args()
    out = dict(finding1=finding1(), finding2=evaluator_variants(), finding4=finding4())
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    L = ["# P0 before / after (generated by `scripts/p0_before_after.py`; do not edit by hand)", "",
         f"*Before* = the review's stored measurements (`review/independent_20261022/`, code `3695030`+`fb8481d`) and the evaluator exactly as at `{PRE_FIX_EVALUATOR_COMMIT}`. "
         "*After* = current code on the same retained inputs. All inputs are synthetic/AI-authored controls; none is in the benchmark denominator.", "",
         "## Finding 1 — silent data loss on ordinary inputs", "",
         "| case | gold tables / cells | before: cells · tables · status · issues · router | after: cells · tables · status · warnings · silent · router | router's token reconciliation applied to the pre-fix output |", "|---|---|---|---|---|"]
    for r in out["finding1"]:
        b, a = r["before"], r["after"]
        L.append(f"| `{r['case']}` | {r['gold_tables']} / {r['gold_cells']} | {b['cells']} · {b['tables']} · `{b['status']}` · {b['issues'] or '—'} · router `{b['router']}` | "
                 f"{a['cells']} · {a['tables']} · `{a['status']}` · {a['warnings'] or '—'} · silent {a['silent']} · router `{a['router']}` | {a['prefix_output_reconciliation']} |")
    L += ["", "## Finding 2 — evaluator blind spots (74-cell original reference, one mutation at a time)", "",
          "| mutation | before (v1): raw · order · silent · false assurance | after (v2): raw · order · silent · period · role · link · structure · localization · header precision · false assurance |", "|---|---|---|"]
    for v in out["finding2"]:
        b, a = v["before"], v["after"]
        L.append(f"| {v['variant']} | {b['raw']} · {b['order']} · {b['silent']} · {b['false_assurance']} | {a['raw']} · {a['order']} · {a['silent']} · {a['period']} · {a['role']} · "
                 f"{a['link']} · {a['structure']} · {a['localization']} · {a['header_precision']} · **{a['false_assurance']}** {a['reasons'] or ''} |")
    f4 = out["finding4"]
    L += ["", "## Finding 4 — merged cells / nested headers (deterministic mapper probes)", "",
          f"* Body label merged over two rows — before: rows {[(r['label']) for r in f4['body_rowspan']['before']]}; after: "
          f"{[(r['label'], r['raw_label']) for r in f4['body_rowspan']['after'][:2]]} with issues {f4['body_rowspan']['issues']}.",
          f"* Outer group and year group over the same two columns — before, parent of each header: `{f4['equal_span_headers']['before_parent_ids']}`; after: `{f4['equal_span_headers']['after_parent_ids']}`.", ""]
    args.out_md.write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
