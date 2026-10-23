"""Field-scoped human import: provenance, unresolved decisions, denominators and replay."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from benchmark.common import ROOT, read_json, sha256
from benchmark.human_reference import build, check, compile_reference
from benchmark.human_evaluate import evaluate_subset, run, verify


def fixture(did='original', bulk=False):
    path = ROOT/f'benchmark/gold/{did}.json'
    gold = read_json(path)
    identities = {did: dict(gold_sha256=sha256(path), export_sha256='export', attestation_sha256='attestation')}
    decisions = []
    for table in gold['tables']:
        for row in table['rows']:
            for c in row['cells']:
                decisions.append(dict(key=f"{did}:{row['row_id']}:{c['column_index']}", document_id=did,
                                      source_sha256=gold['source_sha256'], input_sha256=gold['input_sha256'],
                                      gold_sha256=sha256(path), source_page_index=gold['source_page_index'], selected_page_index=0,
                                      table_id=table['table_id'], row_id=row['row_id'], column_index=c['column_index'],
                                      bbox=c['bbox'], expected_raw=c['raw'], expected_value=c['value'], expected_status=c['status'],
                                      decision='unreviewed', correction=None))
    export = dict(reviewer='Test human fixture', reviewed_at='2026-10-23T00:00:00Z', type='human_review_decisions', decisions=decisions)
    attestation = dict(reviewer=export['reviewer'], document_ids=[did], accept_all_row_labels=bulk,
                       accept_exported_unreviewed_cell_values=bulk, reviewed_cell_fields=['raw', 'value', 'status'])
    return gold, export, attestation, identities


def imported(gold, export, attestation, identities):
    return compile_reference(export, attestation, {gold['document_id']: gold}, identities)[gold['document_id']]


class HumanImport(unittest.TestCase):
    def test_only_explicit_acceptance_without_bulk_attestation(self):
        g, e, a, ids = fixture()
        original = deepcopy(g)
        e['decisions'][0]['decision'] = 'accepted'
        d = imported(g, e, a, ids)
        self.assertEqual(d['human_checked_cells'], 1)
        self.assertEqual(d['human_checked_labels'], 0)
        self.assertEqual(d['counts']['effective_decisions']['unreviewed'], 73)
        self.assertEqual(g, original)

    def test_blanket_acceptance_preserves_exported_unreviewed_states_and_glyphs(self):
        g, e, a, ids = fixture(bulk=True)
        before = deepcopy(e)
        d = imported(g, e, a, ids)
        self.assertEqual((d['human_checked_cells'], d['human_checked_labels']), (74, 43))
        self.assertTrue(all(x['exported_decision'] == 'unreviewed' and x['effective_decision'] == 'accepted'
                            for x in d['decision_ledger']))
        raws = {c['raw'] for t in d['tables'] for r in t['rows'] for c in r['cells']}
        self.assertTrue({'△0', '－', '△2,979'} <= raws)
        self.assertEqual(e, before)
        self.assertFalse(d['blind_test'])
        self.assertFalse(d['scope']['tables_complete'])
        self.assertEqual(d['counts']['human_headers'], 0)

    def test_unreadable_unresolved_and_pending_corrections_survive_blanket_acceptance(self):
        g, e, a, ids = fixture(bulk=True)
        for d, status in zip(e['decisions'], ['accepted', 'unreadable', 'correction_needed', 'unresolved', 'corrected', 'corrected']):
            d['decision'] = status
        e['decisions'][2]['correction'] = 'Maybe 123? Needs another look'
        e['decisions'][4]['correction'] = 'Free text is not a finalized correction'
        e['decisions'][5]['correction'] = dict(raw='＋12.50', value='12.5', status='observed')
        d = imported(g, e, a, ids)
        self.assertEqual(d['human_checked_cells'], 70)
        self.assertEqual([x['effective_decision'] for x in d['decision_ledger'][:6]],
                         ['accepted', 'unreadable', 'correction_needed', 'unresolved', 'unresolved', 'corrected'])
        corrected = next(c for t in d['tables'] for r in t['rows'] for c in r['cells'] if c['human_review']['decision'] == 'corrected')
        self.assertEqual(corrected['raw'], '＋12.50')
        self.assertEqual(corrected['value'], '12.5')
        self.assertEqual(d['decision_ledger'][2]['original_export_entry'], e['decisions'][2])

    def test_missing_export_entries_are_not_bulk_accepted(self):
        g, e, a, ids = fixture(bulk=True)
        e['decisions'].pop()
        d = imported(g, e, a, ids)
        self.assertEqual(d['human_checked_cells'], 73)
        self.assertEqual(d['decision_ledger'][-1]['effective_decision'], 'missing_from_export')

    def test_unreviewed_correction_note_is_not_silently_accepted(self):
        g, e, a, ids = fixture(bulk=True)
        e['decisions'][0]['correction'] = 'Unresolved token'
        d = imported(g, e, a, ids)
        self.assertEqual(d['human_checked_cells'], 73)
        self.assertEqual(d['decision_ledger'][0]['effective_decision'], 'unresolved')

    def test_zero_resolved_content_is_not_called_human_verified(self):
        g, e, a, ids = fixture()
        d = imported(g, e, a, ids)
        self.assertEqual(d['annotation_status'], 'ai_draft')
        self.assertEqual(d['human_checked_cells'], 0)

    def test_stale_source_reference_coordinates_and_raw_are_rejected(self):
        for field, value in [('source_sha256', 'wrong'), ('gold_sha256', 'wrong'), ('expected_raw', 'wrong'),
                             ('bbox', [0, 0, 1, 1]), ('table_id', 'wrong')]:
            with self.subTest(field=field):
                g, e, a, ids = fixture()
                e['decisions'][0][field] = value
                with self.assertRaisesRegex(ValueError, field):
                    imported(g, e, a, ids)

    def test_duplicate_and_unknown_cells_are_rejected(self):
        g, e, a, ids = fixture()
        e['decisions'].append(deepcopy(e['decisions'][0]))
        with self.assertRaisesRegex(ValueError, 'Duplicate/unknown'):
            imported(g, e, a, ids)
        e['decisions'].pop()
        e['decisions'][0]['key'] = 'wrong'
        with self.assertRaisesRegex(ValueError, 'Duplicate/unknown'):
            imported(g, e, a, ids)

    def test_automated_test_exports_and_inconsistent_attestations_are_rejected(self):
        g, e, a, ids = fixture()
        e['reviewer'] = 'AUTOMATED_UI_TEST_NOT_HUMAN'
        with self.assertRaisesRegex(ValueError, 'Automated'):
            imported(g, e, a, ids)
        g, e, a, ids = fixture(bulk=True)
        a['accept_all_row_labels'] = 'false'
        with self.assertRaisesRegex(ValueError, 'boolean'):
            imported(g, e, a, ids)
        a['accept_all_row_labels'] = True
        a['reviewed_cell_fields'] = ['raw']
        with self.assertRaisesRegex(ValueError, 'scope'):
            imported(g, e, a, ids)

    def test_correction_cannot_turn_dash_into_null_observed_value(self):
        g, e, a, ids = fixture()
        e['decisions'][0].update(decision='corrected', correction=dict(raw='－', value=None, status='observed'))
        with self.assertRaisesRegex(ValueError, 'Observed correction'):
            imported(g, e, a, ids)
        e['decisions'][0]['correction'] = dict(raw='1', value=True, status='observed')
        with self.assertRaisesRegex(ValueError, 'finite numeric'):
            imported(g, e, a, ids)


class HumanSubsetMetrics(unittest.TestCase):
    def test_missing_cells_and_failed_predictions_keep_full_denominators(self):
        g, e, a, ids = fixture(bulk=True)
        d = imported(g, e, a, ids)
        pred = deepcopy(g)
        pred['status'] = 'partial'
        pred['tables'][0]['rows'].pop(2)
        r = evaluate_subset(d, pred)
        self.assertEqual(r['metrics']['numeric_raw'], dict(correct=72, total=74, rate=72/74))
        pred['tables'] = []
        pred['status'] = 'error'
        r = evaluate_subset(d, pred)
        self.assertEqual(r['metrics']['numeric_raw'], dict(correct=0, total=74, rate=0.0))
        self.assertEqual(r['missing_reviewed_cells'], 74)

    def test_negative_zero_and_dash_status_are_not_repaired(self):
        g, e, a, ids = fixture(bulk=True)
        d = imported(g, e, a, ids)
        pred = deepcopy(g)
        pred['status'] = 'success'
        for row in pred['tables'][0]['rows']:
            for cell in row['cells']:
                if cell['raw'] in {'△0', '－'}:
                    cell.update(raw='0', value=0, status='observed')
        r = evaluate_subset(d, pred)
        self.assertEqual(r['metrics']['numeric_raw']['correct'], 71)
        self.assertEqual(r['metrics']['numeric_value_status']['correct'], 71)

    def test_human_content_does_not_certify_periods_or_full_semantics(self):
        g, e, a, ids = fixture(bulk=True)
        d = imported(g, e, a, ids)
        pred = deepcopy(g)
        for table in pred['tables']:
            for row in table['rows']:
                for c in row['cells']:
                    c['period'] = '1900'
        r = evaluate_subset(d, pred)
        self.assertEqual(r['metrics']['numeric_value_status']['correct'], 74)
        self.assertEqual(r['unverified_period_diagnostics']['printed_header_association']['correct'], 0)
        self.assertEqual(r['unscored_human_axes']['period_accuracy']['total'], 0)

    def test_daiwabo_inferred_periods_are_separate_and_not_human_period_gold(self):
        g, e, a, ids = fixture('daiwabo_p10', bulk=True)
        d = imported(g, e, a, ids)
        pred = deepcopy(g)
        for c in [c for r in pred['tables'][2]['rows'] for c in r['cells']]:
            c['period'] = None
        r = evaluate_subset(d, pred)
        self.assertEqual(r['metrics']['raw_content']['total'], 67)
        self.assertEqual(r['metrics']['numeric_raw']['correct'], 63)
        self.assertEqual(r['unverified_period_diagnostics']['inferred_unprinted_header'], dict(correct=0, total=12, rate=0.0))
        self.assertEqual(d['counts']['human_periods'], 0)

    def test_flattened_daiwabo_table_cannot_get_full_reconstruction_credit(self):
        d = check(ROOT/'benchmark/human_gold/v1')['daiwabo_p10']
        pred = read_json(ROOT/'runs/native_grid/daiwabo_p10/p0fix2_main/cold/prediction.json')
        table = deepcopy(pred['tables'][0])
        table['bbox'] = [0, 0, 960, 540]
        table['rows'] = [r for t in pred['tables'] for r in t['rows']]
        pred['tables'] = [table]
        r = evaluate_subset(d, pred)
        self.assertEqual(r['metrics']['numeric_raw']['total'], 63)
        self.assertLess(r['metrics']['numeric_raw']['correct'], 63)

    def test_actual_version_and_scores_rebuild_byte_for_byte_without_inference(self):
        decisions = ROOT/'review/human_signoff/human_review_decisions.json'
        attestation = ROOT/'review/human_signoff/attestation_v1.json'
        config = ROOT/'review/human_signoff/evaluation_v1.json'
        with tempfile.TemporaryDirectory() as tmp:
            rebuilt = Path(tmp)/'v1'
            build(decisions, attestation, rebuilt)
            for p in (ROOT/'benchmark/human_gold/v1').glob('*.json'):
                self.assertEqual(sha256(p), sha256(rebuilt/p.name), p.name)
            scores = Path(tmp)/'scores'
            run(rebuilt, config, scores)
            verify(rebuilt, config, scores)
            for p in (ROOT/'results/human_v1').rglob('*.json'):
                self.assertEqual(sha256(p), sha256(scores/p.relative_to(ROOT/'results/human_v1')), str(p))
            with self.assertRaisesRegex(ValueError, 'create-only'):
                build(decisions, attestation, rebuilt)


if __name__ == '__main__':
    unittest.main()
