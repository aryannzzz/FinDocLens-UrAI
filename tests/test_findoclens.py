"""Deterministic tests for the track-B package. Holdout PDFs are optional (skipped if not downloaded)."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from findoclens.amounts import parse_token, looks_numeric
from findoclens.backends import native_grid, native_v2
from findoclens.compare import compare_pair, token_recall, reference_tokens
from findoclens.goldcheck import score_against_gold
from findoclens.schema import n_numeric_cells
from findoclens.validator import validate_prediction
from findoclens.variants import raster_pdf

SRC = ROOT / "baseline_v2" / "source.pdf"
ELECOM = ROOT / "data" / "pdfs" / "elecom.pdf"
DAIWA = ROOT / "data" / "pdfs" / "daiwabo.pdf"


class Amounts(unittest.TestCase):
    def test_negative_triangle(self):
        self.assertEqual(parse_token("△3,634,165"), (-3634165, "observed", None))

    def test_negative_zero_is_not_plain_zero(self):
        self.assertEqual(parse_token("△0")[:2], (0, "negative_zero"))

    def test_dash_is_not_zero(self):
        self.assertEqual(parse_token("－")[:2], (None, "not_reported"))

    def test_plus_and_decimal_and_percent(self):
        self.assertEqual(parse_token("+17,426"), (17426, "observed", "change_amount"))
        self.assertEqual(parse_token("12.5%")[2], "composition_pct")
        self.assertEqual(parse_token("△1.5%")[:2], (-1.5, "observed"))

    def test_non_numeric_is_unreadable_not_zero(self):
        self.assertEqual(parse_token("12O3")[:2], (None, "unreadable"))
        self.assertFalse(looks_numeric("流動資産"))


class NativeOnOriginal(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.g = validate_prediction(native_grid.extract(SRC, 0).to_dict())
        cls.v = native_v2.extract(SRC, 0).to_dict()

    def test_gold_74_of_74(self):
        s = score_against_gold(self.g)
        self.assertEqual((s["cells_correct"], s["gold_cells"], s["pred_cells"]), (74, 74, 74))

    def test_v2_adapter_unchanged_behaviour(self):
        self.assertEqual(score_against_gold(self.v)["cells_correct"], 74)

    def test_grid_agrees_with_v2_exactly(self):
        self.assertEqual(compare_pair(self.g, self.v)["n_value_mismatch"], 0)

    def test_every_cell_has_evidence_and_glyph_fidelity(self):
        raws = [c["raw"] for r in self.g["tables"][0]["rows"] for c in r["cells"]]
        self.assertIn("△2,979", raws)
        for r in self.g["tables"][0]["rows"]:
            for c in r["cells"]:
                if c["status"] != "absent_text_cell":
                    self.assertTrue(c["bbox"])

    def test_header_periods_and_unit(self):
        t = self.g["tables"][0]
        self.assertEqual(sorted({h["period"] for h in t["headers"]}), ["2025-03-31", "2026-03-31"])
        self.assertEqual(t["unit"], "千円")

    def test_validator_never_changes_cells(self):
        raw = native_grid.extract(SRC, 0).to_dict()
        cells = lambda d: json.dumps([[r["cells"] for r in t["rows"]] for t in d["tables"]], sort_keys=True)
        before = cells(raw)
        validate_prediction(raw)
        self.assertEqual(cells(raw), before)


class Raster(unittest.TestCase):
    def test_raster_fails_closed_for_native_backends(self):
        pdf = raster_pdf(SRC, 0, 100, "unit_test_raster")
        for b in (native_grid, native_v2):
            p = b.extract(pdf, 0)
            self.assertEqual(p.status, "failed")
            self.assertEqual(n_numeric_cells(p.to_dict()), 0)
            self.assertTrue(any(i["code"] == "needs_visual_fallback" for i in p.issues))


class Perturbations(unittest.TestCase):
    """Same-source transformations from the frozen baseline benchmark (not independent-template evidence)."""
    @classmethod
    def setUpClass(cls):
        # The repo-level `benchmark/` package (evaluation harness) shadows baseline_v2/benchmark.py, so load the
        # frozen generators by file path under a distinct module name.
        import importlib.util
        sys.path.insert(0, str(ROOT / "baseline_v2"))
        spec = importlib.util.spec_from_file_location("frozen_v2_benchmark", ROOT / "baseline_v2" / "benchmark.py")
        cls.b = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.b)

    def test_missing_cell_is_reported_not_dropped(self):
        p = native_grid.extract(self.b.remove_one_cell(), 0).to_dict()
        t = p["tables"][0]
        row = next(r for r in t["rows"] if r["label"] == "売掛金")
        self.assertEqual(row["cells"][0]["status"], "absent_text_cell")
        self.assertTrue(any(i["code"] == "partial_data_row" and i["label"] == "売掛金" for i in t["issues"]))

    def test_lost_negative_sign_raises_arithmetic_alarm(self):
        p = validate_prediction(native_grid.extract(self.b.remove_negative_marker(), 0).to_dict())
        self.assertTrue(any(i["code"] == "arithmetic_violation" for i in p["issues"]))

    def test_scaled_and_noisy_pages_keep_all_74_cells(self):
        for v in (self.b.make_variant("scaled_79", scale=.79, offset=(100, 45)),
                  self.b.make_variant("distractor_footer", scale=.91, offset=(90, 33), with_noise=True)):
            s = score_against_gold(native_grid.extract(v, 0).to_dict())
            self.assertEqual(s["cells_correct"], 74)


class Router(unittest.TestCase):
    def test_raster_without_models_needs_visual_review_and_invents_nothing(self):
        from findoclens.router import route
        pdf = raster_pdf(SRC, 0, 100, "unit_test_router_raster")
        d = route(pdf, 0, "runs/_test", allow_models=False)
        self.assertEqual(d["status"], "needs_visual_review")
        self.assertEqual(n_numeric_cells(d), 0)
        self.assertTrue(any("raster_like" in x for x in d["meta"]["routing"]["decisions"]))

    def test_clean_native_page_is_accepted_without_models(self):
        from findoclens.router import route
        d = route(SRC, 0, "runs/_test", allow_models=False)
        self.assertEqual(d["status"], "ok")
        self.assertTrue(any("native_accept" in x for x in d["meta"]["routing"]["decisions"]))

    def test_text_layer_reference_ignores_page_number_footer(self):
        from findoclens.compare import text_layer_reference
        ref = text_layer_reference(SRC, 0)
        self.assertEqual(sum(ref.values()), 74)


@unittest.skipUnless(DAIWA.exists(), "Daiwabo holdout PDF not downloaded")
class RouterDaiwabo(unittest.TestCase):
    def test_v2_false_assurance_is_logged(self):
        from findoclens.router import route
        d = route(DAIWA, 9, "runs/_test", allow_models=False)
        self.assertEqual(len(d["tables"]), 3)
        self.assertTrue(any("false assurance" in x for x in d["meta"]["routing"]["decisions"]))


@unittest.skipUnless(ELECOM.exists(), "ELECOM holdout PDF not downloaded")
class Elecom(unittest.TestCase):
    def test_two_columns_hierarchy_and_unit(self):
        p = validate_prediction(native_grid.extract(ELECOM, 8).to_dict())
        t = p["tables"][0]
        self.assertEqual((len(p["tables"]), t["n_data_columns"], t["unit"]), (1, 2, "百万円"))
        self.assertEqual(sum(r["type"] != "section" for r in t["rows"]), 28)
        total = next(r for r in t["rows"] if r["label"] == "資産合計")
        self.assertEqual([c["raw"] for c in total["cells"]], ["114,740", "145,205"])
        neg = next(r for r in t["rows"] if r["label"] == "貸倒引当金")
        self.assertEqual([c["raw"] for c in neg["cells"]], ["△4", "△4"])
        self.assertFalse(any(c["status"] == "violation" for c in t["checks"]))


@unittest.skipUnless(DAIWA.exists(), "Daiwabo holdout PDF not downloaded")
class Daiwabo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = validate_prediction(native_grid.extract(DAIWA, 9).to_dict())

    def test_three_separate_tables(self):
        self.assertEqual(len(self.p["tables"]), 3)
        self.assertEqual([t["n_data_columns"] for t in self.p["tables"]], [3, 3, 3])
        self.assertEqual([sum(r["type"] != "section" for r in t["rows"]) for t in self.p["tables"]], [8, 9, 4])

    def test_roles_periods_and_signs(self):
        t = self.p["tables"][0]
        row = next(r for r in t["rows"] if r["label"] == "現金及び預金")
        self.assertEqual([(c["raw"], c["role"], c["period"]) for c in row["cells"]],
                         [("55,421", "amount", "2025-03"), ("12,410", "amount", "2025-12"), ("△43,010", "change_amount", None)])
        self.assertEqual(row["cells"][2]["value"], -43010)

    def test_explanatory_text_is_kept_not_dropped(self):
        t = self.p["tables"][2]
        notes = [c["raw"] for r in t["rows"] for c in r["cells"] if c["role"] == "other"]
        self.assertTrue(any("主に商品在庫の増加に伴う減少" in n for n in notes))

    def test_delta_and_identity_checks_run_without_violation(self):
        checks = [c for t in self.p["tables"] for c in t["checks"]]
        self.assertTrue(any(c["kind"] == "delta" for c in checks))
        self.assertTrue(any(c["kind"] == "identity" for c in checks))
        self.assertFalse(any(c["status"] == "violation" for c in checks))

    def test_frozen_v2_is_detected_as_false_assurance(self):
        v = native_v2.extract(DAIWA, 9).to_dict()
        self.assertEqual(len(v["tables"]), 1)   # v2 merges the side-by-side tables
        self.assertGreater(compare_pair(self.p, v)["n_value_mismatch"], 0)


if __name__ == "__main__":
    unittest.main()
