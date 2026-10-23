"""Explicit source-review declarations change provenance, never source contents/history."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from benchmark.common import ROOT, read_json, sha256
from benchmark.human_declaration import artifacts, build, check, CLASS, RECORDING
from benchmark.declared_scoring import run, verify, score_scope
from benchmark import review_site

REF = ROOT/'benchmark/human_gold/v3'
DECLARATION = ROOT/'review/human_signoff/declaration_v3.json'
CONFIG = ROOT/'review/human_signoff/evaluation_v3.json'


class DeclaredVisualReview(unittest.TestCase):
    def test_all_197_contents_accepted_and_no_new_cell_click_times(self):
        docs, catalog = check(REF)
        self.assertEqual({did:d['human_checked_cells'] for did,d in docs.items()}, dict(original=74, elecom_p9=56, daiwabo_p10=67))
        self.assertEqual(len(catalog), 197)
        self.assertEqual(len({c['key'] for c in catalog}), 197)
        self.assertEqual(sum(c['role'] != 'other' for c in catalog), 193)
        for doc in docs.values():
            for t in doc['tables']:
                for row in t['rows']:
                    for cell in row['cells']:
                        r = cell['human_review']
                        self.assertEqual(r['decision'], 'accepted')
                        self.assertEqual(r['classification'], CLASS)
                        self.assertEqual(r['recording_method'], RECORDING)
                        self.assertIsNone(r['verification_completed_at'])
                        self.assertNotIn('individual_reviewed_at', r)
        seed = read_json(REF/'accepted_decisions.json')
        self.assertTrue(all(d['decision'] == 'accepted' and 'reviewed_at' not in d for d in seed['decisions']))

    def test_history_contents_and_unreviewed_structure_are_preserved(self):
        docs, catalog = check(REF)
        for did, doc in docs.items():
            old = read_json(ROOT/f'benchmark/human_gold/v2/{did}.json')
            self.assertEqual(doc['decision_ledger'], old['decision_ledger'])
            self.assertEqual(doc['counts']['historical_v2_counts'], old['counts'])
            expected = deepcopy(doc['tables'])
            for t, ot in zip(expected, old['tables']):
                self.assertEqual(t['headers'], ot['headers'])
                for r, o in zip(t['rows'], ot['rows']):
                    for c, oc in zip(r['cells'], o['cells']):
                        self.assertEqual(c['human_review']['historical_v2_review'], oc['human_review'])
                        c['human_review'] = oc['human_review']
                        c['annotation_status'] = oc['annotation_status']
            self.assertEqual(expected, old['tables'])
            self.assertEqual(doc['human_checked_labels'], 0)
            self.assertEqual(doc['counts']['human_periods'], 0)
            self.assertFalse(doc['blind_test'])
            self.assertFalse(doc['scope']['tables_complete'])
        self.assertEqual(sum(c['period_basis'] == 'inferred_unprinted_header' for c in catalog), 12)
        self.assertEqual(sum(d['counts']['unreviewed_header_annotations'] for d in docs.values()), 14)
        self.assertEqual(sum(d['counts']['unreviewed_period_assignments'] for d in docs.values()), 193)
        self.assertEqual(sha256(ROOT/'review/human_signoff/human_review_decisions.json'), read_json(DECLARATION)['original_export_sha256'])

    def test_declared_scores_retain_full_denominator_and_original_numbers(self):
        docs, _ = check(REF)
        pred = read_json(ROOT/'runs/native_grid/daiwabo_p10/p0fix2_main/cold/prediction.json')
        result = score_scope(docs['daiwabo_p10'], pred, 'human_verified_content_accuracy')
        self.assertEqual(result['metrics']['raw_content']['correct'], 63)
        self.assertEqual(result['metrics']['raw_content']['total'], 67)
        pred.update(tables=[], status='error')
        missing = score_scope(docs['daiwabo_p10'], pred, 'human_verified_content_accuracy')
        self.assertEqual(missing['metrics']['raw_content'], dict(correct=0, total=67, rate=0.0))
        self.assertEqual(missing['metrics']['numeric_raw']['total'], 63)
        self.assertEqual(missing['metrics']['text_raw']['total'], 4)
        old = read_json(ROOT/'results/human_v2/summary.json')
        new = verify(REF, CONFIG, ROOT/'results/human_v3')
        for name in old['scores']:
            self.assertEqual(new['scores'][name]['human_verified_content_accuracy'], old['scores'][name]['full_user_approved_agreement'])

    def test_wrong_scope_method_unresolved_decisions_or_times_cannot_be_certified(self):
        declaration = read_json(DECLARATION)
        def fake(path):
            return declaration if Path(path) == DECLARATION else read_json(path)
        for key, value in [('recording_method','197_manual_clicks'), ('structural_annotations_verified',True), ('verification_completed_at','invented')]:
            with self.subTest(key=key), patch('benchmark.human_declaration.read_json', side_effect=fake):
                original = declaration[key]
                declaration[key] = value
                with self.assertRaises(ValueError):
                    artifacts(DECLARATION)
                declaration[key] = original
        export_path = ROOT/declaration['original_export']
        export = read_json(export_path)
        export['decisions'][0]['decision'] = 'unreadable'
        with patch('benchmark.human_declaration.read_json', side_effect=lambda path: export if Path(path) == export_path else read_json(path)):
            with self.assertRaisesRegex(ValueError, 'Unresolved'):
                artifacts(DECLARATION)

    def test_reference_scores_and_report_reproduce_byte_for_byte(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)/'v3'
            build(DECLARATION, target)
            check(target)
            for p in REF.iterdir():
                self.assertEqual(sha256(p), sha256(target/p.name), p.name)
            scores = Path(tmp)/'scores'
            run(target, CONFIG, scores)
            verify(target, CONFIG, scores)
            for p in (ROOT/'results/human_v3').rglob('*.json'):
                self.assertEqual(sha256(p), sha256(scores/p.relative_to(ROOT/'results/human_v3')))
            with self.assertRaisesRegex(ValueError, 'create-only'):
                build(DECLARATION, target)
        from scripts.report_human_declaration import render
        self.assertEqual(render(), (ROOT/'docs/HUMAN_REVIEW_RESULTS.md').read_text())

    def test_ui_embeds_declaration_acceptances_without_rewriting_ai_tables(self):
        self.assertEqual(review_site.check(), [])
        html = (ROOT/'benchmark/review/index.html').read_text()
        marker = '<script id="review-data" type="application/json">'
        embedded = json.loads(html.split(marker,1)[1].split('</script>',1)[0])
        self.assertEqual(len(embedded['decisions']),197)
        self.assertTrue(all(d['decision']=='accepted' for d in embedded['decisions']))
        self.assertEqual(embedded['review_declaration']['reviewer'], 'Aryan Jain')
        for doc in embedded['documents']:
            self.assertEqual(doc['tables'], read_json(ROOT/f"benchmark/gold/{doc['id']}.json")['tables'])
        # A forged acceptance/default or stale declaration must fail asset checks.
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)/'review'
            target.mkdir()
            # The image/input paths are rooted in the real folder; patch only HTML read.
            tampered = html.replace('"decision": "accepted"', '"decision": "unreviewed"', 1)
            original = Path.read_text
            def read_text(path, *args, **kwargs):
                return tampered if path == ROOT/'benchmark/review/index.html' else original(path,*args,**kwargs)
            with patch.object(Path, 'read_text', read_text):
                self.assertTrue(any('decisions/declaration' in e for e in review_site.check()))


if __name__ == '__main__':
    unittest.main()
