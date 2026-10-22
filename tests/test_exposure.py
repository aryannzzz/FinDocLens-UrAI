"""Containment for review finding 3: no page may be presented as a blind holdout merely because its manifest split says 'holdout'."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class Exposure(unittest.TestCase):
    def test_every_holdout_page_has_an_explicit_exposure_record_and_none_is_a_blind_test(self):
        exposure = json.loads((ROOT / "benchmark/exposure.json").read_text(encoding="utf-8"))
        holdout = [json.loads(l)["document_id"] for l in (ROOT / "benchmark/manifest.jsonl").read_text().splitlines()
                   if l.strip() and json.loads(l)["split"] == "holdout"]
        self.assertTrue(holdout)
        for doc in holdout:
            self.assertIn(doc, exposure)
            self.assertIs(exposure[doc]["blind_test"], False)
            self.assertTrue(exposure[doc]["evidence"])

    def test_references_are_still_unverified_drafts(self):
        for p in (ROOT / "benchmark/gold").glob("*.json"):
            g = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(g, dict) and "tables" in g:
                self.assertEqual(g.get("annotation_status"), "ai_draft", p.name)
                self.assertEqual(g.get("human_checked_cells", 0), 0, p.name)


if __name__ == "__main__":
    unittest.main()
