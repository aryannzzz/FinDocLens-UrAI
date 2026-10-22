"""P0 regression tests for the independent review's four high-severity findings (review/independent_20261022/REVIEW.md).

Each test was written to fail on the reviewed code (3695030) and pass after the fix. They use synthetic text-layer pages
only (no model, no downloaded source pages), so they run in a clean checkout.
"""
from copy import deepcopy
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace as S

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tests.synthetic_pdf import ISO, PERIODS, default_rows, make_pdf, native_cells
from adapters.canonical import _leaf_and_groups, convert
from adapters.contract import check_prediction
from benchmark.common import sha256
from benchmark.evaluate import evaluate
from findoclens.backends import native_grid
from findoclens.backends.docling_backend import _map_table
from findoclens.router import route

TMP = tempfile.TemporaryDirectory(prefix="fdl-p0-")


def pdf(name, tables):
    p = Path(TMP.name) / f"{name}.pdf"
    truth = make_pdf(p, tables)
    return p, truth


def two_col(**kw):
    return dict(x0=25, ncol=2, headers=list(PERIODS), rows=default_rows(2, **kw))


def canonical(path, native):
    ctx = dict(document_id=Path(path).stem, source_sha256=sha256(path), input_sha256=sha256(path))
    return convert(native, ctx, backend="native_grid")


def cells_by_label(pred):
    return {r["label"]: [c["raw"] for c in r["cells"] if c["column_index"] >= 0] for t in pred["tables"] for r in t["rows"]}


def codes(pred):
    return [i["code"] for i in pred["issues"]] + [i["code"] for t in pred["tables"] for i in t.get("issues", [])]


# --------------------------------------------------------------------------------------------------------------- finding 1
class YearLikeAmounts(unittest.TestCase):
    def test_amounts_2025_2026_are_not_dropped(self):
        p, _ = pdf("year_amounts", [two_col(first_row=("2025", "2026"))])
        n = native_grid.extract(p).to_dict()
        self.assertEqual(cells_by_label(n)["現金"], ["2025", "2026"])
        self.assertEqual(len(n["tables"][0]["rows"]), 4)

    def test_year_amounts_keep_numeric_type_and_physical_columns(self):
        p, _ = pdf("year_amounts_b", [two_col(first_row=("2025", "2026"))])
        row = native_grid.extract(p).to_dict()["tables"][0]["rows"][0]
        self.assertEqual([(c["column_index"], c["value"], c["status"]) for c in row["cells"]],
                         [(0, 2025, "observed"), (1, 2026, "observed")])

    def test_bare_year_header_line_remains_header_not_data(self):
        t = two_col()
        t.update(headers=None, extra_header=["2025", "2026"])
        p, _ = pdf("year_header", [t])
        n = native_grid.extract(p).to_dict()
        self.assertEqual(len(n["tables"][0]["rows"]), 4)
        self.assertEqual(sorted(h["text"] for h in n["tables"][0]["headers"]), ["2025", "2026"])
        self.assertNotIn(["2025", "2026"], list(cells_by_label(n).values()))

    def test_labelled_year_like_row_next_to_header_is_flagged_not_silent(self):
        t = two_col()
        t.update(headers=None, extra_header=["2025", "2026"], header_label="科目")
        p, _ = pdf("year_ambiguous", [t])
        n = native_grid.extract(p).to_dict()
        flagged = [i for i in n["issues"] + n["tables"][0]["issues"] if i["code"] == "year_like_tokens_ambiguous"]
        self.assertTrue(flagged, "a label + bare-year row above the data cannot be classified from tokens alone; it must be flagged")
        self.assertEqual(flagged[0]["severity"], "warning")
        self.assertNotEqual(canonical(p, n)["status"], "success")

    def test_year_amount_page_is_not_reported_as_success_if_anything_is_missing(self):
        p, _ = pdf("year_amounts_c", [two_col(first_row=("2025", "2026"))])
        out = canonical(p, native_grid.extract(p).to_dict())
        self.assertEqual(sum(len(r["cells"]) for r in out["tables"][0]["rows"]), 8)


class OneColumnTables(unittest.TestCase):
    def test_standalone_one_column_table(self):
        p, _ = pdf("one_col", [dict(x0=25, ncol=1, headers=["2025/3"], rows=default_rows(1))])
        n = native_grid.extract(p).to_dict()
        self.assertEqual(len(n["tables"]), 1)
        self.assertEqual(cells_by_label(n), {"現金": ["310"], "売掛金": ["340"], "棚卸資産": ["370"], "その他": ["400"]})
        self.assertEqual(n["tables"][0]["n_data_columns"], 1)

    def test_one_column_beside_two_column_table_neither_merged_nor_omitted(self):
        p, _ = pdf("mixed", [two_col(), dict(x0=430, ncol=1, headers=["2025/3"], rows=default_rows(1))])
        n = native_grid.extract(p).to_dict()
        self.assertEqual([t["n_data_columns"] for t in n["tables"]], [2, 1])
        self.assertEqual([len(t["rows"]) for t in n["tables"]], [4, 4])
        self.assertEqual(sum(len(r["cells"]) for t in n["tables"] for r in t["rows"]), 12)
        left, right = n["tables"]
        self.assertLess(left["bbox"][2], right["bbox"][0], "tables must not overlap or merge")

    def test_single_value_row_inside_two_column_table_stays_in_that_table(self):
        rows = default_rows(2)
        rows[2] = (rows[2][0], [rows[2][1][1]])         # one value printed in the right column only
        t = dict(x0=25, ncol=2, headers=list(PERIODS), rows=rows)
        p, _ = pdf("partial_row", [t])
        n = native_grid.extract(p).to_dict()
        self.assertEqual(len(n["tables"]), 1)
        self.assertEqual(len(n["tables"][0]["rows"]), 4)
        self.assertTrue(any(i["code"] == "partial_data_row" for i in n["tables"][0]["issues"]))

    def test_one_column_table_is_not_invented_from_two_stray_numbers(self):
        rows = default_rows(1)[:2]
        p, _ = pdf("two_rows", [two_col(), dict(x0=430, ncol=1, headers=["2025/3"], rows=rows)])
        n = native_grid.extract(p).to_dict()
        self.assertEqual(len(n["tables"]), 1)


class CompletenessReconciliation(unittest.TestCase):
    def setUp(self):
        # a 2-row single-column block beside a good table: below the 3-row table rule, so it cannot become a table
        rows = default_rows(1)[:2]
        self.path, _ = pdf("block_missing", [two_col(), dict(x0=430, ncol=1, headers=["2025/3"], rows=rows)])
        self.native = native_grid.extract(self.path).to_dict()

    def test_unassigned_numeric_tokens_in_a_column_stack_are_a_warning_with_locations(self):
        issue = next(i for i in self.native["issues"] if i["code"] == "unassigned_numeric_tokens")
        self.assertEqual(issue["severity"], "warning")
        self.assertEqual(issue["count"], 2)
        self.assertEqual([t["raw"] for t in issue["tokens"]], ["310", "340"])
        self.assertTrue(all(len(t["bbox"]) == 4 for t in issue["tokens"]))

    def test_canonical_status_is_not_success_and_names_the_review_reason(self):
        out = canonical(self.path, self.native)
        self.assertEqual(out["status"], "partial")
        self.assertTrue(out["review_required"])
        self.assertIn("unassigned_numeric_tokens", out["review_reasons"])
        self.assertEqual(check_prediction(out), [])

    def test_isolated_page_numbers_do_not_trigger_review(self):
        p, _ = pdf("clean", [two_col()])
        n = native_grid.extract(p).to_dict()
        self.assertFalse(any(i["severity"] == "warning" for i in n["issues"]))
        self.assertEqual(canonical(p, n)["status"], "success")
        self.assertFalse(canonical(p, n)["review_required"])


class RouterCompleteness(unittest.TestCase):
    def test_router_does_not_accept_a_page_with_unassigned_table_content(self):
        rows = default_rows(1)[:2]
        p, _ = pdf("router_missing", [two_col(), dict(x0=430, ncol=1, headers=["2025/3"], rows=rows)])
        r = route(p, allow_models=False)
        self.assertEqual(r["status"], "needs_visual_review")
        self.assertNotIn("native_accept", " ".join(r["meta"]["routing"]["decisions"]))

    def test_router_reconciles_tokens_of_whatever_backend_it_returns(self):
        from findoclens.coverage import reconcile_prediction
        rows = default_rows(1)[:2]
        p, _ = pdf("router_cov", [two_col(), dict(x0=430, ncol=1, headers=["2025/3"], rows=rows)])
        pred = native_grid.extract(p).to_dict()
        rec = reconcile_prediction(str(p), pred)
        self.assertEqual(sorted(t["raw"] for t in rec["significant"]), ["310", "340"])
        self.assertEqual(rec["covered"], 8)

    def test_router_still_accepts_a_clean_page_and_the_mixed_page(self):
        p, _ = pdf("router_clean", [two_col(), dict(x0=430, ncol=1, headers=["2025/3"], rows=default_rows(1))])
        r = route(p, allow_models=False)
        self.assertEqual(r["status"], "ok")
        self.assertEqual(len(r["tables"]), 2)


# --------------------------------------------------------------------------------------------------------------- finding 2
def gold_and_pred():
    def headers():
        return [dict(header_id=f"c{k}", kind="leaf", column_index=k, text=PERIODS[k], period=ISO[k], role="amount",
                     bbox=[100 + k * 80, 10, 150 + k * 80, 20]) for k in range(2)]
    rows = []
    for i, (label, vals) in enumerate(default_rows(2)):
        cells = [dict(column_index=k, header_id=f"c{k}", period=ISO[k], role="amount", raw=raw, value=int(raw),
                      status="observed", bbox=[100 + k * 80, 30 + i * 20, 150 + k * 80, 40 + i * 20]) for k, raw in enumerate(vals)]
        rows.append(dict(row_id=f"r{i}", row_index=i, label=label, raw_label=label, parent_path=[],
                         bbox=[10, 30 + i * 20, 250, 40 + i * 20], type="item", cells=cells))
    gold = dict(document_id="d", source_sha256="s", annotation_status="ai_draft", human_checked_cells=0,
                scope=dict(tables_complete=True, rows_complete=True, cells_complete=True),
                tables=[dict(table_id="t", page=1, bbox=[0, 0, 300, 120], headers=headers(), rows=rows)])
    pred = deepcopy(gold)
    pred["status"] = "success"
    return gold, pred


def metrics(gold, pred):
    return evaluate(gold, pred)["metrics"]


class EvaluatorStructure(unittest.TestCase):
    def test_perfect_prediction_scores_full_on_every_axis(self):
        g, p = gold_and_pred()
        m = metrics(g, p)
        for k in ("cell_period_accuracy", "cell_role_accuracy", "cell_header_link_accuracy", "cell_structure_exact",
                  "cell_evidence_localization", "numeric_raw_exact", "cell_coverage"):
            self.assertEqual((m[k]["correct"], m[k]["total"]), (8, 8), k)
        self.assertFalse(m["false_assurance"])

    def test_wrong_periods_roles_and_links_hit_structure_not_value_scores(self):
        g, p = gold_and_pred()
        for r in p["tables"][0]["rows"]:
            for c in r["cells"]:
                c.update(period="1900-01-01", role="composition_pct", header_id="nonexistent")
        m = metrics(g, p)
        self.assertEqual(m["numeric_raw_exact"]["correct"], 8)              # value fidelity is a separate axis
        self.assertEqual(m["cell_coverage"]["correct"], 8)                  # and so is alignment
        self.assertEqual(m["cell_period_accuracy"]["correct"], 0)
        self.assertEqual(m["cell_role_accuracy"]["correct"], 0)
        self.assertEqual(m["cell_header_link_accuracy"]["correct"], 0)
        self.assertEqual(m["cell_structure_exact"]["correct"], 0)
        self.assertTrue(m["false_assurance"])

    def test_header_link_to_the_wrong_existing_column_is_wrong(self):
        g, p = gold_and_pred()
        for r in p["tables"][0]["rows"]:
            r["cells"][0]["header_id"] = "c1"
        m = metrics(g, p)
        self.assertEqual(m["cell_header_link_accuracy"]["correct"], 4)
        self.assertEqual(m["cell_structure_exact"]["correct"], 4)

    def test_link_credit_follows_the_header_not_its_id_spelling(self):
        g, p = gold_and_pred()
        for h in p["tables"][0]["headers"]:
            h["header_id"] = "pred_" + h["header_id"]
        for r in p["tables"][0]["rows"]:
            for c in r["cells"]:
                c["header_id"] = "pred_" + c["header_id"]
        self.assertEqual(metrics(g, p)["cell_header_link_accuracy"]["correct"], 8)

    def test_missing_cell_gets_no_credit_on_any_axis_even_if_its_value_appears_elsewhere(self):
        g, p = gold_and_pred()
        r0, r1 = p["tables"][0]["rows"][:2]
        moved = r0["cells"].pop(1)                       # gold r0/c1 absent from its slot ...
        r1["cells"].append(dict(moved, column_index=5))  # ... but the same value + context sits in another row, wrong slot
        m = metrics(g, p)
        for k in ("cell_coverage", "numeric_raw_exact", "numeric_semantic_exact", "cell_period_accuracy",
                  "cell_role_accuracy", "cell_header_link_accuracy", "cell_structure_exact", "cell_evidence_localization"):
            self.assertEqual(m[k]["correct"], 7, k)
            self.assertEqual(m[k]["total"], 8, k)
        self.assertEqual(m["missing_cells"]["correct"], 1)

    def test_row_order_and_localization_errors_are_false_assurance(self):
        g, p = gold_and_pred()
        t = p["tables"][0]
        t["rows"].reverse()
        for i, r in enumerate(t["rows"]):
            r["row_index"] = i
        m = metrics(g, p)
        self.assertLess(m["row_order_accuracy"]["correct"], 4)
        self.assertTrue(m["false_assurance"])
        g, p = gold_and_pred()
        for r in p["tables"][0]["rows"]:
            for c in r["cells"]:
                c["bbox"] = [0, 0, 1, 1]
        m = metrics(g, p)
        self.assertEqual(m["cell_evidence_localization"]["correct"], 0)
        self.assertEqual(m["numeric_raw_exact"]["correct"], 8)
        self.assertTrue(m["false_assurance"])

    def test_extra_headers_count_against_precision_even_in_unmatched_tables(self):
        g, p = gold_and_pred()
        extra = deepcopy(p["tables"][0])
        extra["bbox"] = [1000, 1000, 1100, 1100]
        p["tables"].append(extra)
        m = metrics(g, p)
        self.assertEqual(m["extra_tables"], 1)
        self.assertEqual((m["header_role_precision"]["correct"], m["header_role_precision"]["total"]), (2, 4))
        self.assertTrue(m["false_assurance"])


class EvaluatorOmissionScope(unittest.TestCase):
    def deleted_tail(self):
        g, p = gold_and_pred()
        p["tables"][0]["rows"].pop()
        return g, p

    def silent(self, g, p):
        return metrics(g, p)["silent_omission_rate"]["correct"]

    def test_baseline_deletion_is_silent(self):
        self.assertEqual(self.silent(*self.deleted_tail()), 2)

    def test_unrelated_region_warning_does_not_suppress(self):
        g, p = self.deleted_tail()
        p["issues"] = [dict(code="omitted_table", region=9, bbox=[1000, 1000, 1100, 1100])]
        self.assertEqual(self.silent(g, p), 2)

    def test_unlocated_and_unlabelled_omission_warning_does_not_suppress_but_is_reported(self):
        g, p = self.deleted_tail()
        p["issues"] = [dict(code="partial_data_row", severity="warning")]
        m = metrics(g, p)
        self.assertEqual(m["silent_omission_rate"]["correct"], 2)
        self.assertEqual(m["unscoped_omission_warnings"], 1)

    def test_warning_about_a_different_row_label_does_not_suppress(self):
        g, p = self.deleted_tail()
        p["tables"][0]["issues"] = [dict(code="partial_data_row", label="現金", row_index=0)]
        self.assertEqual(self.silent(g, p), 2)

    def test_warning_located_on_the_missing_row_does_suppress(self):
        g, p = self.deleted_tail()
        p["issues"] = [dict(code="omitted_table", bbox=[0, 90, 300, 125])]
        self.assertEqual(self.silent(g, p), 0)
        g, p = self.deleted_tail()
        p["issues"] = [dict(code="unassigned_numeric_tokens", count=2,
                            tokens=[dict(raw="400", bbox=[100, 90, 150, 100]), dict(raw="411", bbox=[180, 90, 230, 100])])]
        self.assertEqual(self.silent(g, p), 0)

    def test_label_scoped_warning_on_the_missing_row_does_suppress(self):
        g, p = self.deleted_tail()
        p["tables"][0]["issues"] = [dict(code="partial_data_row", label="その他")]
        self.assertEqual(self.silent(g, p), 0)

    def test_global_failure_statuses_still_cover_everything(self):
        g, p = self.deleted_tail()
        p["status"] = "abstained"
        self.assertEqual(self.silent(g, p), 0)


# --------------------------------------------------------------------------------------------------------------- finding 4
def cell(r, c, text, r1=None, c1=None, header=False):
    return S(start_row_offset_idx=r, end_row_offset_idx=r1 if r1 is not None else r + 1, start_col_offset_idx=c,
             end_col_offset_idx=c1 if c1 is not None else c + 1, text=text, column_header=header, bbox=None)


def table(cells, nr, nc):
    return _map_table(S(data=S(num_rows=nr, num_cols=nc, table_cells=cells), prov=[]), 0, 400, None)


class MergedCells(unittest.TestCase):
    def head(self):
        return [cell(0, 0, "科目", header=True), cell(0, 1, "2025/3", header=True), cell(0, 2, "2026/3", header=True)]

    def test_body_label_spanning_two_rows_reaches_both_rows(self):
        t = table(self.head() + [cell(1, 0, "現金", r1=3), cell(1, 1, "10"), cell(1, 2, "20"), cell(2, 1, "30"), cell(2, 2, "40")], 3, 3)
        self.assertEqual([r.label for r in t.rows], ["現金", "現金"])
        self.assertEqual(t.rows[0].raw_label, "現金")
        self.assertIsNone(t.rows[1].raw_label, "the second row does not print the label; it is inherited, not printed")
        issue = next(i for i in t.issues if i["code"] == "body_rowspan_label_inherited")
        self.assertEqual((issue["severity"], issue["rows"], issue["label"]), ("warning", [0, 1], "現金"))

    def test_numeric_body_cell_with_rowspan_is_flagged_and_not_copied(self):
        t = table(self.head() + [cell(1, 0, "現金"), cell(1, 1, "10", r1=3), cell(1, 2, "20"), cell(2, 0, "預金"), cell(2, 2, "40")], 3, 3)
        self.assertEqual(t.rows[1].cells[0].status, "absent_text_cell")       # nothing printed there; never invented
        self.assertTrue(any(i["code"] == "body_cell_span_unsupported" and i["rows"] == [0, 1] and i["columns"] == [0]
                            for i in t.issues))

    def test_numeric_body_cell_with_colspan_is_flagged(self):
        t = table(self.head() + [cell(1, 0, "現金"), cell(1, 1, "10", c1=3)], 2, 3)
        self.assertTrue(any(i["code"] == "body_cell_span_unsupported" and i["columns"] == [0, 1] for i in t.issues))

    def test_plain_table_has_no_span_issue(self):
        t = table(self.head() + [cell(1, 0, "現金"), cell(1, 1, "10"), cell(1, 2, "20")], 2, 3)
        self.assertFalse(any("span" in i["code"] or "inherited" in i["code"] for i in t.issues))


def hdr(hid, text, cols, row, period=None, role="amount"):
    return dict(header_id=hid, text=text, column_indices=cols, row_start=row, period=period, role=role, bbox=None,
                rowspan=1, colspan=len(cols))


class NestedHeaders(unittest.TestCase):
    def test_equal_span_groups_chain_outer_to_inner_to_leaf(self):
        heads = [hdr("outer", "連結", [0, 1], 0), hdr("inner", "2025年3月期", [0, 1], 1, "2025-03"),
                 hdr("amount", "金額", [0], 2, "2025-03"), hdr("pct", "構成比", [1], 2, "2025-03", "composition_pct")]
        out = _leaf_and_groups(dict(table_id="t", headers=heads), 2, {})
        by_native = {h.get("native_header_id"): h for h in out if h.get("native_header_id")}
        gid = lambda n: by_native[n]["header_id"]
        self.assertNotIn("parent_id", by_native["outer"])
        self.assertEqual(by_native["inner"]["parent_id"], gid("outer"))
        leaves = {h["column_index"]: h for h in out if h["kind"] == "leaf"}
        self.assertEqual(leaves[0]["parent_id"], gid("inner"))
        self.assertEqual(leaves[1]["parent_id"], gid("inner"))

    def test_nested_unequal_groups_still_pick_the_smallest_enclosing_group(self):
        heads = [hdr("outer", "連結", [0, 1, 2], 0), hdr("inner", "当期", [0, 1], 1),
                 hdr("a", "金額", [0], 2), hdr("b", "比率", [1], 2), hdr("c", "前期", [2], 2)]
        out = _leaf_and_groups(dict(table_id="t", headers=heads), 3, {})
        by_native = {h.get("native_header_id"): h for h in out if h.get("native_header_id")}
        leaves = {h["column_index"]: h for h in out if h["kind"] == "leaf"}
        self.assertEqual(leaves[0]["parent_id"], by_native["inner"]["header_id"])
        self.assertEqual(leaves[2]["parent_id"], by_native["outer"]["header_id"])
        self.assertEqual(by_native["inner"]["parent_id"], by_native["outer"]["header_id"])

    def test_header_vertically_merged_over_two_lines_keeps_its_rowspan_and_parent(self):
        heads = [hdr("grp", "連結", [0, 1], 0)]
        tall = hdr("tall", "金額", [0], 1)
        tall["rowspan"] = 2
        heads += [tall, hdr("b", "比率", [1], 2)]
        out = _leaf_and_groups(dict(table_id="t", headers=heads), 2, {})
        leaf0 = next(h for h in out if h["kind"] == "leaf" and h["column_index"] == 0)
        grp = next(h for h in out if h["kind"] == "group")
        self.assertEqual(leaf0["rowspan"], 2)
        self.assertEqual(leaf0["parent_id"], grp["header_id"])


if __name__ == "__main__":
    unittest.main()
