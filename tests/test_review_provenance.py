"""Bulk user approval cannot inflate individually reviewed accuracy denominators."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from benchmark.common import ROOT, read_json, sha256
from benchmark.review_provenance import build, check, classify, inputs, INDIVIDUAL, BULK
from benchmark.review_scoring import run, verify, score_scope

REF = ROOT/'benchmark/human_gold/v2'
CONFIG = ROOT/'review/human_signoff/evaluation_v2.json'
CLARIFICATION = ROOT/'review/human_signoff/clarification_v2.json'


class CorrectedReviewProvenance(unittest.TestCase):
    def test_class_counts_and_individual_keys_follow_export_not_bulk_attestation(self):
        docs, catalog = check(REF)
        export = read_json(ROOT/'review/human_signoff/human_review_decisions.json')
        expected = {d['key'] for d in export['decisions'] if d['decision'] == 'accepted'}
        actual = {c['key'] for c in catalog if c['classification'] == INDIVIDUAL}
        self.assertEqual(actual, expected)
        self.assertEqual(len(actual), 51)
        self.assertEqual(sum(c['classification'] == BULK for c in catalog), 146)
        self.assertEqual(sum(d['human_checked_cells'] for d in docs.values()), 51)
        self.assertEqual(sum(d['user_approved_cells'] for d in docs.values()), 197)
        self.assertEqual(sum(d['human_checked_labels'] for d in docs.values()), 0)
        self.assertEqual(sum(d['user_attested_labels'] for d in docs.values()), 98)
        self.assertEqual(len({(c['document_id'], c['row_id']) for c in catalog if c['classification'] == INDIVIDUAL}), 26)
        risky = [c for c in catalog if c['raw'] and (c['raw'][0] in '△▲+＋' or c['raw'] in {'－', '—', '–', '-'})]
        self.assertEqual(len(risky), 37)
        self.assertEqual(sum(c['classification'] == BULK for c in risky), 31)

    def test_one_reviewed_cell_does_not_certify_the_other_cell_in_its_row(self):
        _, catalog = check(REF)
        lookup = {c['key']: c for c in catalog}
        self.assertEqual(lookup['original:assets_r016:1']['classification'], INDIVIDUAL)
        self.assertEqual(lookup['original:assets_r016:0']['classification'], BULK)
        self.assertFalse(any(c['document_id'] == 'daiwabo_p10' and c['classification'] == INDIVIDUAL for c in catalog))

    def test_original_export_and_v1_ledger_are_unchanged(self):
        docs, _ = check(REF)
        for did, doc in docs.items():
            base = read_json(ROOT/f'benchmark/human_gold/v1/{did}.json')
            self.assertEqual(doc['decision_ledger'], base['decision_ledger'])
        clarification = read_json(CLARIFICATION)
        self.assertEqual(sha256(ROOT/'review/human_signoff/human_review_decisions.json'), clarification['export_sha256'])
        self.assertEqual(sha256(ROOT/'benchmark/human_gold/v1/SHA256.json'), clarification['base_reference_lock_sha256'])

    def test_bulk_cells_have_no_individual_fields_or_invented_review_times(self):
        docs, _ = check(REF)
        for doc in docs.values():
            for table in doc['tables']:
                for row in table['rows']:
                    for c in row['cells']:
                        if c['human_review']['classification'] == BULK:
                            self.assertFalse(c['human_review']['individually_reviewed'])
                            self.assertEqual(c['human_review']['reviewed_fields'], [])
                            self.assertIsNone(c['human_review']['individual_reviewed_at'])
                            self.assertEqual(c['annotation_status'], 'user_approved_ai_draft')

    def test_structure_and_daiwabo_periods_remain_unreviewed(self):
        docs, _ = check(REF)
        self.assertEqual(sum(d['counts']['unreviewed_header_annotations'] for d in docs.values()), 14)
        self.assertEqual(sum(d['counts']['unreviewed_period_assignments'] for d in docs.values()), 193)
        self.assertEqual(docs['daiwabo_p10']['counts']['inferred_unprinted_period_assignments'], 12)
        for doc in docs.values():
            self.assertEqual(doc['counts']['human_periods'], 0)
            self.assertFalse(doc['scope']['tables_complete'])
            self.assertIs(doc['blind_test'], False)

    def test_wrong_ai_evidence_cannot_support_bulk_ai_cross_check_claim(self):
        clarification, base, export, audit = inputs(CLARIFICATION)
        audit = deepcopy(audit)
        audit['human_verified'] = True
        with self.assertRaisesRegex(ValueError, 'AI audit'):
            classify(base, export, audit, clarification)
        audit['human_verified'] = False
        next(c for c in audit['cells'] if c['document'] == 'daiwabo_p10')['raw'] = 'wrong'
        with self.assertRaisesRegex(ValueError, 'Bulk AI cross-check'):
            classify(base, export, audit, clarification)

    def test_missing_predictions_keep_individual_denominator_and_daiwabo_is_not_100_percent(self):
        docs, _ = check(REF)
        pred = read_json(ROOT/'runs/native_grid/original/p0fix2_main/cold/prediction.json')
        pred.update(tables=[], status='error')
        result = score_scope(docs['original'], pred, 'individually_reviewed_accuracy')
        self.assertEqual(result['metrics']['raw_content'], dict(correct=0, total=31, rate=0.0))
        dai = read_json(ROOT/'runs/native_grid/daiwabo_p10/p0fix2_main/cold/prediction.json')
        result = score_scope(docs['daiwabo_p10'], dai, 'individually_reviewed_accuracy')
        self.assertEqual(result['metrics']['raw_content'], dict(correct=0, total=0, rate=None))
        self.assertEqual(result['evaluation_status'], 'no_cells_in_this_scope')

    def test_bulk_value_errors_do_not_change_individually_reviewed_accuracy(self):
        docs, _ = check(REF)
        pred = read_json(ROOT/'runs/native_grid/original/p0fix2_main/cold/prediction.json')
        row = next(r for t in pred['tables'] for r in t['rows'] if r['label'] == '建物及び構築物')
        row['cells'][0].update(raw='WRONG', value=-1)
        individual = score_scope(docs['original'], pred, 'individually_reviewed_accuracy')
        full = score_scope(docs['original'], pred, 'full_user_approved_agreement')
        self.assertEqual(individual['metrics']['raw_content']['correct'], 31)
        self.assertLess(full['metrics']['raw_content']['correct'], 74)

    def test_full_comparison_values_are_preserved_but_confidence_is_renamed(self):
        old = read_json(ROOT/'results/human_v1/summary.json')
        new = read_json(ROOT/'results/human_v2/summary.json')
        for name, backends in old['scores'].items():
            for backend, metrics in backends.items():
                current = new['scores'][name]['full_user_approved_agreement'][backend]
                for axis, value in current.items():
                    self.assertEqual(value, metrics[axis])
                individual = new['scores'][name]['individually_reviewed_accuracy'][backend]
                self.assertEqual(individual['raw_content'], dict(correct=51, total=51, rate=1.0))

    def test_reference_and_all_scores_reproduce_without_inference(self):
        with tempfile.TemporaryDirectory() as tmp:
            rebuilt = Path(tmp)/'v2'
            build(CLARIFICATION, rebuilt)
            for p in REF.iterdir():
                if p.is_file():
                    self.assertEqual(sha256(p), sha256(rebuilt/p.name), p.name)
            scores = Path(tmp)/'scores'
            run(rebuilt, CONFIG, scores)
            verify(rebuilt, CONFIG, scores)
            for p in (ROOT/'results/human_v2').rglob('*.json'):
                self.assertEqual(sha256(p), sha256(scores/p.relative_to(ROOT/'results/human_v2')), str(p))
            with self.assertRaisesRegex(ValueError, 'create-only'):
                build(CLARIFICATION, rebuilt)
            from scripts.report_review_provenance import render
            self.assertEqual(render(REF, ROOT/'results/human_v2'), (ROOT/'docs/HUMAN_REVIEW_RESULTS.md').read_text())


if __name__ == '__main__':
    unittest.main()
