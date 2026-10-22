"""Adapter / contract-integration tests (no model dependencies). Model-backend adapters are exercised by the benchmark runs."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from adapters.canonical import convert, map_status, month_end
from adapters.contract import check_prediction
from benchmark.common import sha256
from benchmark.evaluate import evaluate
from findoclens.backends import native_grid, native_v2

SRC = ROOT / "baseline_v2" / "source.pdf"
CTX = dict(document_id="original", source_sha256=sha256(SRC), input_sha256=sha256(SRC))


def cell(k, raw, value, status, role="amount", bbox=(0, 0, 1, 1), period="2025-03"):
    return dict(column_index=k, header_id=None, period=period, role=role, raw=raw, value=value, status=status,
                bbox=list(bbox) if bbox else None, backend="x", evidence_kind="native_pdf", notes=[])


def native(headers, rows, ncols=2, status="ok", issues=()):
    return dict(page_bbox=[0, 0, 100, 100], status=status, issues=list(issues), model_revision="m", capabilities={},
                tables=[dict(table_id="t0", bbox=[0, 0, 50, 50], reading_order=0, headers=headers, rows=rows, issues=[],
                             unit=None, n_data_columns=ncols, capabilities={}, checks=[], grid=None)])


def header(i, text, cols, row=0, role="amount", period=None, span=None):
    return dict(header_id=f"h{i}", text=text, period=period, role=role, bbox=[0, 0, 1, 1], colspan=span or len(cols), rowspan=1,
                row_start=row, col_start=cols[0], column_indices=cols)


def row(i, label, cells, typ="item", parent=()):
    return dict(row_index=i, label=label, raw_label=label, parent_path=list(parent), bbox=[0, 0, 9, 9], type=typ, cells=cells)


class Conversion(unittest.TestCase):
    def test_month_end(self):
        self.assertEqual(month_end("2025-03"), "2025-03-31")
        self.assertEqual(month_end("2024-02"), "2024-02-29")
        self.assertEqual(month_end("2025-12-31"), "2025-12-31")
        self.assertIsNone(month_end(None))

    def test_status_mapping_never_upgrades_failures(self):
        self.assertEqual(map_status("ok", []), "success")
        self.assertEqual(map_status("ok", [{"severity": "info"}]), "success")
        self.assertEqual(map_status("ok", [{"severity": "warning"}]), "partial")
        self.assertEqual(map_status("failed", []), "abstained")
        self.assertEqual(map_status("no_tables", []), "abstained")
        self.assertEqual(map_status("needs_visual_review", []), "partial")

    def test_glyphs_and_null_statuses_pass_through_unchanged(self):
        n = native([header(0, "2025/3", [0]), header(1, "2026/3", [1])],
                   [row(0, "貸倒引当金", [cell(0, "△0", 0, "negative_zero"), cell(1, "－", None, "not_reported")])])
        out = convert(n, CTX, backend="b")
        cells = out["tables"][0]["rows"][0]["cells"]
        self.assertEqual([c["raw"] for c in cells], ["△0", "－"])
        self.assertEqual([c["status"] for c in cells], ["negative_zero", "not_reported"])
        self.assertIsNone(cells[1]["value"])
        self.assertEqual(check_prediction(out), [])

    def test_grouped_headers_have_leaf_per_column_and_parent_links(self):
        hs = [header(0, "2025年3月期", [0, 1], row=0, period="2025-03"), header(1, "2026年3月期", [2, 3], row=0, period="2026-03"),
              header(2, "金額", [0], row=1), header(3, "構成比", [1], row=1, role="composition_pct"),
              header(4, "金額", [2], row=1), header(5, "構成比", [3], row=1, role="composition_pct")]
        rows = [row(0, "a", [cell(k, "1", 1, "observed") for k in range(4)])]
        out = convert(native(hs, rows, ncols=4), CTX, backend="b")
        heads = out["tables"][0]["headers"]
        groups = [h for h in heads if h["kind"] == "group"]
        leaves = [h for h in heads if h["kind"] == "leaf"]
        self.assertEqual([(g["column_index"], g["colspan"]) for g in groups], [(0, 2), (2, 2)])
        self.assertEqual(sorted(l["column_index"] for l in leaves), [0, 1, 2, 3])
        self.assertEqual({l["column_index"]: l["parent_id"] for l in leaves}[2], groups[1]["header_id"])
        self.assertEqual(check_prediction(out), [])

    def test_missing_header_is_not_guessed(self):
        out = convert(native([], [row(0, "a", [cell(0, "1", 1, "observed", period=None)])], ncols=1), CTX, backend="b")
        leaf = out["tables"][0]["headers"][0]
        self.assertIsNone(leaf["role"])
        self.assertIsNone(leaf["text"])
        self.assertIn("no_header_cell_found", leaf["capability_status"])

    def test_text_outside_columns_is_kept_after_last_data_column(self):
        c = cell(-1, "→主に増加", None, "observed", role="other", period=None)
        out = convert(native([header(0, "x", [0])], [row(0, "a", [cell(0, "1", 1, "observed"), c])], ncols=1), CTX, backend="b")
        extra = out["tables"][0]["rows"][0]["cells"][1]
        self.assertEqual((extra["column_index"], extra["raw"], extra["value"], extra["role"]), (1, "→主に増加", "→主に増加", "other"))

    def test_change_period_only_inferred_when_unambiguous(self):
        hs = [header(0, "2025/3", [0], period="2025-03"), header(1, "2025/12", [1], period="2025-12"),
              header(2, "増減", [2], role="change_amount")]
        rows = [row(0, "a", [cell(0, "1", 1, "observed", period="2025-03"), cell(1, "2", 2, "observed", period="2025-12"),
                             cell(2, "+1", 1, "observed", role="change_amount", period=None)])]
        out = convert(native(hs, rows, ncols=3), CTX, backend="b")
        self.assertEqual(out["tables"][0]["headers"][2]["period"], "2025-12-31_vs_2025-03-31")

    def test_section_rows_forward_no_placeholder_slots(self):
        sec = row(0, "資産の部", [cell(0, None, None, "absent_text_cell", bbox=None), cell(1, None, None, "absent_text_cell", bbox=None)], typ="section")
        out = convert(native([header(0, "a", [0]), header(1, "b", [1])], [sec, row(1, "x", [cell(0, "1", 1, "observed"), cell(1, "2", 2, "observed")])]), CTX, backend="b")
        self.assertEqual(out["tables"][0]["rows"][0]["cells"], [])
        self.assertEqual(check_prediction(out), [])

    def test_declared_missing_hierarchy_downgrades_success_to_partial(self):
        n = native([header(0, "a", [0])], [row(0, "x", [cell(0, "1", 1, "observed")])], ncols=1)
        n["tables"][0]["issues"] = [{"severity": "info", "code": "hierarchy_not_inferred"}]
        self.assertEqual(convert(n, CTX, backend="b")["status"], "partial")
        n["tables"][0]["issues"] = []
        self.assertEqual(convert(n, CTX, backend="b")["status"], "success")

    def test_empty_extraction_abstains(self):
        out = convert(native([], [], ncols=0), CTX, backend="b")
        self.assertEqual(out["status"], "abstained")


class EndToEndNative(unittest.TestCase):
    def setUp(self):
        self.gold = json.loads((ROOT / "benchmark/gold/original.json").read_text())

    def test_native_grid_original_is_contract_compliant_and_scores_all_cells(self):
        p = convert(native_grid.extract(SRC, 0).to_dict(), CTX, backend="native_grid")
        self.assertEqual(check_prediction(p), [])
        m = evaluate(self.gold, p)["metrics"]
        self.assertEqual(m["numeric_raw_exact"]["correct"], 74)
        self.assertEqual(m["rows"]["matched"], 43)

    def test_native_v2_original_is_contract_compliant(self):
        p = convert(native_v2.extract(SRC, 0).to_dict(), CTX, backend="native_v2")
        self.assertEqual(check_prediction(p), [])
        self.assertEqual(evaluate(self.gold, p)["metrics"]["numeric_raw_exact"]["correct"], 74)

    def test_identity_mismatch_is_rejected_by_the_evaluator(self):
        p = convert(native_grid.extract(SRC, 0).to_dict(), dict(CTX, source_sha256="0" * 64), backend="native_grid")
        with self.assertRaises(ValueError):
            evaluate(self.gold, p)


class OcrFlags(unittest.TestCase):
    def test_variant_glyphs_are_flagged_not_rewritten(self):
        from findoclens.ocr_flags import suspect_variant_chars
        self.assertEqual(suspect_variant_chars("流動資產"), {"產": "産"})
        self.assertEqual(suspect_variant_chars("受取手形及び壳掛金"), {"壳": "売"})
        self.assertEqual(suspect_variant_chars("流動資産"), {})          # the correct Japanese form is never flagged
        self.assertEqual(suspect_variant_chars("売掛金"), {})


class Regression(unittest.TestCase):
    def test_footnote_marker_stays_in_the_label(self):
        path = ROOT / "benchmark/data/adversarial/footnote_marker/page.pdf"
        if not path.exists():
            self.skipTest("adversarial inputs not materialized")
        p = native_grid.extract(path, 0).to_dict()
        labels = [r["label"] for r in p["tables"][0]["rows"]]
        self.assertIn("売掛金*1", labels)

    def test_left_aligned_grouped_headers_are_read_with_flagged_spans(self):
        path = ROOT / "benchmark/data/adversarial/grouped_two/page.pdf"
        if not path.exists():
            self.skipTest("adversarial inputs not materialized")
        p = native_grid.extract(path, 0).to_dict()
        self.assertEqual(p["meta"]["column_alignment"], "left")
        t = p["tables"][0]
        self.assertEqual(len(t["rows"]), 4)
        groups = [h for h in t["headers"] if len(h["column_indices"]) > 1]
        self.assertEqual([(h["text"], h["column_indices"], h["span_note"]) for h in groups],
                         [("2025年3月期", [0, 1], "extended_to_uncovered_columns"), ("2026年3月期", [2, 3], "extended_to_uncovered_columns")])
        self.assertTrue(any(i["code"] == "header_span_inferred" for i in t["issues"]))

    def test_right_aligned_pages_keep_right_alignment(self):
        self.assertEqual(native_grid.extract(SRC, 0).meta["column_alignment"], "right")

    def test_total_is_sibling_of_its_heading(self):
        p = native_grid.extract(SRC, 0).to_dict()
        r = next(r for r in p["tables"][0]["rows"] if r["label"] == "流動資産合計")
        self.assertEqual(r["parent_path"], ["資産の部"])


if __name__ == "__main__":
    unittest.main()
