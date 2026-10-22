"""Red-team the evaluator, not the parser: known counting and fidelity traps."""
from copy import deepcopy
import itertools
import random
import unittest

from benchmark.evaluate import aggregate, assignment, evaluate


def fixture():
    rows = []
    for index, (label, parent, raw, value, status) in enumerate([
        ('その他', ['流動資産'], '△0', 0, 'negative_zero'),
        ('その他', ['固定資産'], '－', None, 'not_reported'),
        ('資産合計', [], '+1,234.50', '1234.5', 'observed'),
    ]):
        rows.append(dict(row_id=f'r{index}', row_index=index, label=label, raw_label=label,
                         parent_path=parent, bbox=[0, 20+index*20, 100, 40+index*20],
                         cells=[dict(column_index=0, period='2025', role='amount', raw=raw,
                                     value=value, status=status, bbox=[50, 20+index*20, 100, 40+index*20])]))
    gold = dict(document_id='test', source_sha256='source', annotation_status='ai_draft', human_checked_cells=0,
                scope=dict(tables_complete=True, rows_complete=True, cells_complete=True),
                tables=[dict(table_id='t', page=1, bbox=[0, 0, 100, 100], rows=rows,
                             headers=[dict(header_id='c0', column_index=0, period='2025', role='amount')])])
    pred = deepcopy(gold)
    pred['status'] = 'success'
    return gold, pred


class EvaluatorTests(unittest.TestCase):
    def test_perfect_draft_remains_draft(self):
        g, p = fixture()
        r = evaluate(g, p)
        self.assertEqual(r['metrics']['raw_cell_exact'], dict(correct=3, total=3, rate=1.))
        self.assertEqual(r['reference_status'], 'ai_draft')

    def test_tail_deletion_keeps_denominator(self):
        g, p = fixture()
        p['tables'][0]['rows'].pop()
        m = evaluate(g, p)['metrics']
        self.assertEqual((m['raw_cell_exact']['correct'], m['raw_cell_exact']['total']), (2, 3))
        self.assertEqual(m['silent_omission_rate']['correct'], 1)
        self.assertTrue(m['false_assurance'])

    def test_head_deletion_does_not_shift_following_rows(self):
        g, p = fixture()
        p['tables'][0]['rows'].pop(0)
        self.assertEqual(evaluate(g, p)['metrics']['raw_cell_exact']['correct'], 2)

    def test_duplicate_prediction_cannot_reuse_gold(self):
        g, p = fixture()
        p['tables'][0]['rows'].append(deepcopy(p['tables'][0]['rows'][0]))
        m = evaluate(g, p)['metrics']
        self.assertEqual(m['spurious_rows'], 1)
        self.assertEqual(m['rows']['precision'], .75)
        self.assertEqual(m['raw_precision_all_predicted']['total'], 4)

    def test_reordered_duplicates_match_context_geometry(self):
        g, p = fixture()
        p['tables'][0]['rows'].reverse()
        self.assertEqual(evaluate(g, p)['metrics']['raw_cell_exact']['correct'], 3)

    def test_row_order_assessed_separately(self):
        g, p = fixture()
        for r in p['tables'][0]['rows']:
            r['row_index'] = 20
        m = evaluate(g, p)['metrics']
        self.assertEqual(m['raw_cell_exact']['correct'], 3)
        self.assertEqual(m['row_order_accuracy']['correct'], 0)

    def test_sign_erasure_not_semantically_equal(self):
        g, p = fixture()
        p['tables'][0]['rows'][0]['cells'][0].update(raw='0', status='observed')
        m = evaluate(g, p)['metrics']
        self.assertEqual(m['semantic_cell_exact']['correct'], 2)
        self.assertEqual(m['raw_cell_exact']['correct'], 2)

    def test_dash_never_equals_zero(self):
        g, p = fixture()
        p['tables'][0]['rows'][1]['cells'][0].update(raw='0', value=0, status='observed')
        self.assertEqual(evaluate(g, p)['metrics']['semantic_cell_exact']['correct'], 2)

    def test_decimal_value_and_plus_glyph_are_separate(self):
        g, p = fixture()
        p['tables'][0]['rows'][2]['cells'][0].update(raw='1234.50', value=1234.5)
        m = evaluate(g, p)['metrics']
        self.assertEqual(m['raw_cell_exact']['correct'], 2)
        self.assertEqual(m['semantic_cell_exact']['correct'], 3)

    def test_typed_value_not_rederived_from_correct_raw(self):
        g, p = fixture()
        p['tables'][0]['rows'][2]['cells'][0]['value'] = 12345
        self.assertEqual(evaluate(g, p)['metrics']['semantic_cell_exact']['correct'], 2)

    def test_missing_status_invalid(self):
        g, p = fixture()
        del p['tables'][0]['rows'][0]['cells'][0]['status']
        self.assertEqual(evaluate(g, p)['metrics']['invalid_matched_cells'], 1)

    def test_empty_failure_counts_all_cells(self):
        g, p = fixture()
        p.update(tables=[], status='error', issues=['OOM'])
        m = evaluate(g, p)['metrics']
        self.assertEqual(m['missing_cells']['correct'], 3)
        self.assertEqual(m['raw_cell_exact']['rate'], 0)
        self.assertEqual(m['silent_omission_rate']['correct'], 0)

    def test_empty_success_is_false_assurance(self):
        g, p = fixture()
        p['tables'] = []
        self.assertTrue(evaluate(g, p)['metrics']['false_assurance'])

    def test_unrelated_warning_cannot_hide_silent_omissions(self):
        g, p = fixture()
        p['issues'] = [dict(code='financial_reconciliation_failure', severity='warning')]
        p['tables'][0]['rows'].pop()
        self.assertEqual(evaluate(g, p)['metrics']['silent_omission_rate']['correct'], 1)

    def test_header_wrong_does_not_reassign_numeric_cells(self):
        g, p = fixture()
        p['tables'][0]['headers'][0]['role'] = 'composition_pct'
        m = evaluate(g, p)['metrics']
        self.assertEqual(m['header_role_accuracy']['correct'], 0)
        self.assertEqual(m['raw_cell_exact']['correct'], 3)

    def test_group_span_is_not_approximated_from_values(self):
        g, p = fixture()
        h = dict(kind='group', text='2025', period='2025', column_index=0, colspan=2, rowspan=1)
        g['tables'][0]['headers'].append(h)
        m = evaluate(g, p)['metrics']
        self.assertEqual(m['grouped_headers']['gold'], 1)
        self.assertEqual(m['grouped_headers']['matched'], 0)

    def test_group_parent_assignment_is_assessed(self):
        g, p = fixture()
        for d in (g, p):
            d['tables'][0]['headers'] += [dict(header_id='g0', kind='group', text='2025', period='2025', column_index=0, colspan=2, rowspan=1)]
            d['tables'][0]['headers'][0]['parent_id'] = 'g0'
        p['tables'][0]['headers'][0]['parent_id'] = 'missing_group'
        m = evaluate(g, p)['metrics']
        self.assertEqual(m['grouped_headers']['matched'], 1)
        self.assertEqual(m['header_parent_accuracy']['correct'], 0)

    def test_malformed_prediction_is_rejected_explicitly(self):
        g, p = fixture()
        p['tables'][0]['rows'] = ['not a row object']
        with self.assertRaises(ValueError):
            evaluate(g, p)

    def test_extra_table_count(self):
        g, p = fixture()
        p['tables'].append(deepcopy(p['tables'][0]))
        m = evaluate(g, p)['metrics']
        self.assertEqual(m['extra_tables'], 1)
        self.assertEqual(m['tables']['precision'], .5)

    def test_merged_side_by_side_table_only_matches_one(self):
        g, p = fixture()
        other = deepcopy(g['tables'][0])
        other['bbox'] = [110, 0, 210, 100]
        g['tables'].append(other)
        p['tables'][0]['bbox'] = [0, 0, 210, 100]
        self.assertEqual(evaluate(g, p)['metrics']['tables']['recall'], .5)

    def test_page_identity_prevents_matching(self):
        g, p = fixture()
        p['tables'][0]['page'] = 2
        self.assertEqual(evaluate(g, p)['metrics']['tables']['matched'], 0)

    def test_provenance_mismatch_rejected(self):
        g, p = fixture()
        p['source_sha256'] = 'wrong'
        with self.assertRaises(ValueError):
            evaluate(g, p)

    def test_zero_gold_does_not_count_as_success(self):
        g, p = fixture()
        g['tables'] = []
        with self.assertRaises(ValueError):
            evaluate(g, p)

    def test_duplicate_cell_column_is_ambiguous(self):
        g, p = fixture()
        row = p['tables'][0]['rows'][0]
        row['cells'].append(deepcopy(row['cells'][0]))
        self.assertEqual(evaluate(g, p)['metrics']['cell_coverage']['correct'], 2)

    def test_correct_abstention_on_injected_missing(self):
        g, p = fixture()
        for d in (g, p):
            d['tables'][0]['rows'][0]['cells'][0].update(raw=None, value=None, status='absent_text_cell')
        self.assertEqual(evaluate(g, p)['metrics']['correct_abstention']['rate'], 1.)

    def test_hierarchy_edges_distinguish_identical_labels(self):
        g, p = fixture()
        p['tables'][0]['rows'][1]['parent_path'] = ['流動資産']
        self.assertEqual(evaluate(g, p)['metrics']['hierarchy_edges']['matched'], 1)

    def test_micro_aggregate_counts_failed_page(self):
        g, p = fixture()
        one = evaluate(g, p)
        p.update(tables=[], status='timeout')
        two = evaluate(g, p)
        result = aggregate([one, two])
        self.assertEqual(result['raw_cell_exact']['rate'], .5)
        self.assertEqual(result['run_statuses']['timeout'], 1)

    def test_whitespace_policy_keeps_signs_and_labels(self):
        g, p = fixture()
        p['tables'][0]['rows'][0]['label'] = 'そ の 他'
        p['tables'][0]['rows'][0]['cells'][0]['raw'] = '△ 0'
        self.assertEqual(evaluate(g, p)['metrics']['raw_cell_exact']['correct'], 3)

    def test_assignment_against_exhaustive_small_matrices(self):
        rng = random.Random(481)
        for n in range(1, 5):
            for m in range(1, 5):
                scores = [[rng.randrange(5) for _ in range(m)] for _ in range(n)]
                candidates = [list(r)+[0]*n for r in scores]
                optimum = max(sum(candidates[i][p[i]] for i in range(n))
                              for p in itertools.permutations(range(m+n), n))
                pairs = assignment(scores)
                self.assertEqual(sum(scores[i][j] for i, j in pairs), optimum)
                self.assertEqual(len({j for _, j in pairs}), len(pairs))


if __name__ == '__main__':
    unittest.main()
