"""One-to-one evaluation with fixed gold denominators and explicit failures.

Only whitespace is removed for label/raw matching. Raw tokens are never rewritten.
Table matching uses page + bbox IoU >= .1 (maximum weight assignment). Rows
require equal whitespace-normalized labels; geometry/context/order break ties.
Financial cells align by physical column_index, never by predicted value or role.
"""
import argparse
from collections import Counter
from decimal import Decimal, InvalidOperation
import json
import math
import re

from benchmark.common import read_json, sha256, utc, write_json

ABSTAIN = {'absent_text_cell', 'unreadable', 'uncertain', 'unparseable'}
STATUSES = ABSTAIN | {'observed', 'negative_zero', 'not_reported'}
LOCALIZATION_IOU = .3       # predicted evidence box vs gold evidence box
EVALUATOR_VERSION = 2       # 2: structure/localization axes, scoped omission warnings, predicted-header denominators over all tables


def norm(value):
    return re.sub(r'\s+', '', value) if isinstance(value, str) else value


def iou(a, b):
    if not a or not b:
        return 0.0
    intersection = max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))
    union = (a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - intersection
    return intersection / union if union > 0 else 0.0


def assignment(scores):
    """Maximum-weight rectangular assignment, keeping only positive edges.

    Hungarian algorithm with dummy columns permits every gold item to abstain.
    No scipy/torch dependency and no greedy duplicate-row reuse.
    """
    n = len(scores)
    if not n or not scores[0]:
        return []
    original_m = len(scores[0])
    m = original_m + n
    u, v, p, way = [0.]*(n+1), [0.]*(m+1), [0]*(m+1), [0]*(m+1)
    for row in range(1, n+1):
        p[0] = row
        j0 = 0
        minimum, used = [float('inf')]*(m+1), [False]*(m+1)
        while True:
            used[j0] = True
            i0, delta, j1 = p[j0], float('inf'), 0
            for j in range(1, m+1):
                if used[j]:
                    continue
                weight = scores[i0-1][j-1] if j <= original_m else 0
                cost = -weight - u[i0] - v[j]
                if cost < minimum[j]:
                    minimum[j], way[j] = cost, j0
                if minimum[j] < delta:
                    delta, j1 = minimum[j], j
            for j in range(m+1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minimum[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while True:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
            if j0 == 0:
                break
    return [(p[j]-1, j-1) for j in range(1, original_m+1)
            if p[j] and scores[p[j]-1][j-1] > 0]


def ratio(numerator, denominator):
    return dict(correct=numerator, total=denominator,
                rate=numerator/denominator if denominator else None)


def prf(correct, gold, predicted):
    return dict(matched=correct, gold=gold, predicted=predicted,
                precision=correct/predicted if predicted else (0.0 if gold else None),
                recall=correct/gold if gold else None,
                f1=2*correct/(gold+predicted) if gold+predicted else None)


def decimal(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        number = Decimal(str(value))
        return number if number.is_finite() else None
    except InvalidOperation:
        return None


def semantic(gold, pred):
    if pred.get('status') != gold['status'] or 'value' not in pred:
        return False
    if gold['value'] is None:
        return pred['value'] is None
    if gold.get('role') == 'other':
        return isinstance(pred['value'], str) and pred['value'] == gold['value']
    return decimal(pred['value']) is not None and decimal(pred['value']) == decimal(gold['value'])


def edges(rows):
    result = Counter()
    for row in rows:
        parent = tuple(norm(x) for x in row.get('parent_path', []))
        if parent:
            result[(parent, parent+(norm(row.get('label', '')),))] += 1
    return result


def row_scores(gold, pred):
    return [[(100 + 10*iou(g.get('bbox'), p.get('bbox'))
              + (2 if list(map(norm, g.get('parent_path', []))) == list(map(norm, p.get('parent_path', []))) else 0)
              + 1/(1+abs(gi-pi))) if norm(g['label']) == norm(p.get('label')) else 0
             for pi, p in enumerate(pred)] for gi, g in enumerate(gold)]


# Issue codes that declare the whole extraction unusable: they cover every gold cell.
GLOBAL_FAILURE_CODES = {'empty_extraction', 'needs_visual_fallback', 'no_verified_data_rows', 'worker_failure', 'backend_exception'}
# Issue codes that declare "something is missing". They only cover a gold cell they can be tied to: by the row label, by a box
# (issue['bbox'] or the boxes of issue['tokens']) that overlaps the gold cell/row, or by being attached to the matched row itself.
OMISSION_CODES = {'partial_data_row', 'missing_displayed_cell', 'missing_cell', 'omitted_row', 'omitted_table',
                  'unassigned_numeric_tokens', 'source_numeric_tokens_not_in_output'}


def issue_code(issue):
    return issue.get('code') if isinstance(issue, dict) else issue


def issue_boxes(issue):
    if not isinstance(issue, dict):
        return []
    boxes = [issue['bbox']] if isinstance(issue.get('bbox'), list) and len(issue['bbox']) == 4 else []
    boxes += [t['bbox'] for t in issue.get('tokens', []) if isinstance(t, dict) and isinstance(t.get('bbox'), list) and len(t['bbox']) == 4]
    return boxes


def overlaps(a, b):
    return min(a[2], b[2]) > max(a[0], b[0]) and min(a[3], b[3]) > max(a[1], b[1])


def unscoped_omission_warnings(pred):
    """Omission warnings that name no row label, no box and no row: they say 'something is missing' but not what."""
    scopes = [pred] + [t for t in pred.get('tables', [])]
    return sum(1 for scope in scopes for i in scope.get('issues', [])
               if issue_code(i) in OMISSION_CODES and isinstance(i, dict) and i.get('label') is None and not issue_boxes(i))


def omission_alert(pred, table, row, label, boxes=()):
    """True when the prediction itself flags THIS gold cell/row as missing. A warning about another row, another region, or one
    that cannot be localised does not count; run-level failure statuses/codes cover everything."""
    if pred.get('status') in {'error', 'timeout', 'oom', 'abstained', 'unavailable'}:
        return True
    boxes = [b for b in boxes if isinstance(b, list) and len(b) == 4]
    for scope in (pred, table, row):
        for issue in scope.get('issues', []):
            code = issue_code(issue)
            if code in GLOBAL_FAILURE_CODES:
                return True
            if code not in OMISSION_CODES:
                continue
            target = issue.get('label') if isinstance(issue, dict) else None
            if target is not None and norm(target) == norm(label):
                return True
            if any(overlaps(a, b) for a in issue_boxes(issue) for b in boxes):
                return True
            if scope is row and row and target is None and not issue_boxes(issue):
                return True         # attached to the matched predicted row itself
    return False


def validate_prediction_shape(pred):
    if not isinstance(pred, dict) or not isinstance(pred.get('tables', []), list):
        raise ValueError('Prediction must be an object with a tables array')
    for table in pred.get('tables', []):
        if not isinstance(table, dict) or not isinstance(table.get('rows', []), list) or not isinstance(table.get('headers', []), list):
            raise ValueError('Table must have rows/headers arrays')
        for obj in [table] + table.get('rows', []) + table.get('headers', []):
            if not isinstance(obj, dict):
                raise ValueError('Rows and headers must be objects')
            box = obj.get('bbox')
            if box is not None and (not isinstance(box, list) or len(box) != 4 or
                                    not all(isinstance(v, (int, float)) and math.isfinite(v) for v in box)):
                raise ValueError('BBox must contain four finite PDF coordinates or null')
        for row in table.get('rows', []):
            if not isinstance(row.get('cells', []), list) or not all(isinstance(c, dict) for c in row.get('cells', [])):
                raise ValueError('Cells must be an array of objects')


def evaluate(gold, pred):
    validate_prediction_shape(pred)
    if not gold.get('tables') or not any(t.get('rows') for t in gold['tables']) or not gold.get('scope', {}).get('tables_complete'):
        raise ValueError('Gold needs nonempty tables and explicit complete-table scope')
    for key in ('document_id', 'source_sha256'):
        if not gold.get(key) or pred.get(key) != gold[key]:
            raise ValueError(f'Prediction/reference {key} mismatch')
    if gold.get('input_sha256') and pred.get('input_sha256') != gold['input_sha256']:
        raise ValueError('Prediction/reference input_sha256 mismatch')
    gt, pt = gold['tables'], pred.get('tables', [])
    table_pairs = assignment([[iou(g.get('bbox'), p.get('bbox'))
                               if g.get('page', 1) == p.get('page', 1) and iou(g.get('bbox'), p.get('bbox')) >= .1 else 0
                               for p in pt] for g in gt])
    table_map = dict(table_pairs)
    total_rows = sum(len(t['rows']) for t in gt)
    pred_rows = sum(len(t.get('rows', [])) for t in pt)
    total_cells = sum(len(r['cells']) for t in gt for r in t['rows'])
    pred_cells = sum(len(r.get('cells', [])) for t in pt for r in t.get('rows', []))
    count = Counter()
    errors, alignment = [], []
    gold_edges = sum(sum(edges(t['rows']).values()) for t in gt)
    pred_edges = sum(sum(edges(t.get('rows', [])).values()) for t in pt)
    for ti, table in enumerate(gt):
        predicted = pt[table_map[ti]] if ti in table_map else {}
        gr, pr = table['rows'], predicted.get('rows', [])
        row_pairs = assignment(row_scores(gr, pr))
        rm = dict(row_pairs)
        count['rows_matched'] += len(row_pairs)
        count['raw_labels_correct'] += sum(gr[gi].get('raw_label', gr[gi]['label']) == pr[pi].get('raw_label') for gi, pi in row_pairs)
        count['hierarchy_correct'] += sum((edges(gr) & edges(pr)).values())
        count['row_order_correct'] += sum(pr[pi].get('row_index') == gr[gi].get('row_index') for gi, pi in row_pairs)
        gh = table.get('headers', [])
        ph = predicted.get('headers', [])
        # Leaf header matching uses physical columns. Duplicate predictions stay in the precision denominator.
        leaf = [h for h in gh if h.get('kind', 'leaf') == 'leaf']
        pleaf = [h for h in ph if h.get('kind', 'leaf') == 'leaf']
        count['headers_gold'] += len(leaf)
        count['headers_predicted'] += len(pleaf)
        for h in leaf:
            candidates = [x for x in pleaf if x.get('column_index') == h['column_index']]
            count['headers_correct'] += bool(len(candidates) == 1 and all(candidates[0].get(k) == h.get(k) for k in ('period', 'role')))
        groups = [h for h in gh if h.get('kind') == 'group']
        pgroups = [h for h in ph if h.get('kind') == 'group']
        count['groups_gold'] += len(groups)
        count['groups_predicted'] += len(pgroups)
        group_pairs = assignment([[1 if all(norm(h.get(k)) == norm(p.get(k)) for k in
                                                   ('text', 'period', 'column_index', 'colspan', 'rowspan')) else 0
                                   for p in pgroups] for h in groups])
        count['groups_correct'] += len(group_pairs)
        def header_signature(h):
            return tuple(h.get(k) for k in ('kind', 'column_index', 'text', 'period', 'colspan', 'rowspan'))
        gold_ids = {h.get('header_id'): h for h in gh}
        pred_ids = {h.get('header_id'): h for h in ph}
        for h in gh:
            if not h.get('parent_id'):
                continue
            count['header_parents_gold'] += 1
            peers = [p for p in ph if p.get('kind', 'leaf') == h.get('kind', 'leaf') and
                     (p.get('column_index') == h.get('column_index') if h.get('kind', 'leaf') == 'leaf'
                      else header_signature(p) == header_signature(h))]
            if len(peers) == 1 and h['parent_id'] in gold_ids and peers[0].get('parent_id') in pred_ids:
                count['header_parents_correct'] += header_signature(gold_ids[h['parent_id']]) == header_signature(pred_ids[peers[0]['parent_id']])
        for gi, row in enumerate(gr):
            prow = pr[rm[gi]] if gi in rm else {}
            alignment.append(dict(table_id=table['table_id'], row_id=row['row_id'],
                                  predicted_row_index=prow.get('row_index'), matched=gi in rm))
            for cell in row['cells']:
                alert = omission_alert(pred, predicted, prow, row['label'], [cell.get('bbox'), row.get('bbox')] if not cell.get('bbox') else [cell['bbox']])
                is_numeric = cell.get('role') != 'other'
                count['numeric_gold'] += is_numeric
                candidates = [c for c in prow.get('cells', []) if c.get('column_index') == cell['column_index']]
                pc = candidates[0] if len(candidates) == 1 else None
                # structure axes (denominators are all gold cells, so a missing cell earns nothing on any of them)
                gold_link = gold_ids.get(cell.get('header_id')) if cell.get('header_id') is not None else None
                count['link_gold'] += is_numeric and gold_link is not None
                count['evidence_gold'] += bool(cell.get('bbox'))
                if pc is not None:
                    period_ok = pc.get('period') == cell.get('period')
                    role_ok = pc.get('role') == cell.get('role')
                    linked = pred_ids.get(pc.get('header_id'))
                    link_ok = gold_link is None or bool(linked is not None and linked.get('kind', 'leaf') == 'leaf' and
                                                        linked.get('column_index') == gold_link.get('column_index'))
                    count['period_correct'] += period_ok and is_numeric
                    count['role_correct'] += role_ok and is_numeric
                    count['link_correct'] += link_ok and is_numeric and gold_link is not None
                    count['structure_correct'] += period_ok and role_ok and link_ok and is_numeric
                    count['structure_errors'] += is_numeric and not (period_ok and role_ok and link_ok)
                    if cell.get('bbox'):
                        good = bool(pc.get('bbox')) and iou(cell['bbox'], pc['bbox']) >= LOCALIZATION_IOU
                        count['evidence_correct'] += good
                        count['evidence_misleading'] += bool(pc.get('bbox')) and not good
                event = dict(table_id=table['table_id'], row_id=row['row_id'], label=row['label'],
                             column_index=cell['column_index'], expected_raw=cell['raw'],
                             expected_status=cell['status'], bbox=cell.get('bbox'))
                if pc is None:
                    count['missing_cells'] += 1
                    count['silent_omissions'] += not alert
                    errors.append(dict(event, kind='missing_cell', predicted_raw=None))
                    continue
                count['matched_cells'] += 1
                exact = 'raw' in pc and norm(pc['raw']) == norm(cell['raw'])
                sem = semantic(cell, pc)
                count['raw_correct'] += exact
                count['semantic_correct'] += sem
                count['numeric_raw_correct'] += exact and is_numeric
                count['numeric_semantic_correct'] += sem and is_numeric
                count['abstentions'] += pc.get('status') in ABSTAIN
                count['correct_abstentions'] += cell['status'] in ABSTAIN and sem
                count['invalid_cells'] += pc.get('status') not in STATUSES or 'raw' not in pc or 'value' not in pc
                if not exact or not sem:
                    errors.append(dict(event, kind='cell_mismatch', predicted_raw=pc.get('raw'),
                                       predicted_value=pc.get('value'), predicted_status=pc.get('status')))
    for pi, p in enumerate(pt):         # headers of predicted tables that match no gold table are extra, not free
        if pi not in set(table_map.values()):
            count['headers_predicted'] += sum(h.get('kind', 'leaf') == 'leaf' for h in p.get('headers', []))
            count['groups_predicted'] += sum(h.get('kind') == 'group' for h in p.get('headers', []))
    # Include explicit abstentions in extraneous rows/cells in prediction-level rate.
    abstentions = sum(c.get('status') in ABSTAIN for t in pt for r in t.get('rows', []) for c in r.get('cells', []))
    expected_abstentions = sum(c['status'] in ABSTAIN for t in gt for r in t['rows'] for c in r['cells'])
    checks = dict(
        cell_errors=bool(errors), missing_tables=len(table_pairs) < len(gt), missing_rows=count['rows_matched'] < total_rows,
        extra_tables=len(pt) > len(table_pairs), extra_rows=pred_rows > count['rows_matched'],
        header_errors=count['headers_correct'] < count['headers_gold'],
        extra_headers=count['headers_predicted'] > count['headers_gold'],
        group_errors=count['groups_correct'] < count['groups_gold'] or count['groups_predicted'] > count['groups_gold'],
        header_parent_errors=count['header_parents_correct'] < count['header_parents_gold'],
        hierarchy_errors=count['hierarchy_correct'] < gold_edges,
        cell_structure_errors=bool(count['structure_errors']),
        row_order_errors=count['row_order_correct'] < count['rows_matched'],
        misleading_evidence_boxes=bool(count['evidence_misleading']))
    false_reasons = [k for k, v in checks.items() if v]
    metrics = dict(
        tables=prf(len(table_pairs), len(gt), len(pt)), extra_tables=len(pt)-len(table_pairs),
        unlocalizable_predicted_tables=sum(not t.get('bbox') for t in pt),
        rows=prf(count['rows_matched'], total_rows, pred_rows),
        missed_rows=total_rows-count['rows_matched'], spurious_rows=pred_rows-count['rows_matched'],
        raw_label_exact=ratio(count['raw_labels_correct'], total_rows),
        extraneous_row_rate=ratio(pred_rows-count['rows_matched'], pred_rows),
        row_order_accuracy=ratio(count['row_order_correct'], total_rows),
        cell_coverage=ratio(count['matched_cells'], total_cells),
        raw_cell_exact=ratio(count['raw_correct'], total_cells),
        raw_precision_on_matched=ratio(count['raw_correct'], count['matched_cells']),
        raw_precision_all_predicted=ratio(count['raw_correct'], pred_cells),
        semantic_cell_exact=ratio(count['semantic_correct'], total_cells),
        numeric_raw_exact=ratio(count['numeric_raw_correct'], count['numeric_gold']),
        numeric_semantic_exact=ratio(count['numeric_semantic_correct'], count['numeric_gold']),
        header_role_accuracy=ratio(count['headers_correct'], count['headers_gold']),
        header_role_precision=ratio(count['headers_correct'], count['headers_predicted']),
        grouped_headers=prf(count['groups_correct'], count['groups_gold'], count['groups_predicted']),
        header_parent_accuracy=ratio(count['header_parents_correct'], count['header_parents_gold']),
        hierarchy_edges=prf(count['hierarchy_correct'], gold_edges, pred_edges),
        abstention_rate=ratio(abstentions, pred_cells),
        correct_abstention=ratio(count['correct_abstentions'], expected_abstentions),
        missing_cells=ratio(count['missing_cells'], total_cells),
        silent_omission_rate=ratio(count['silent_omissions'], total_cells),
        invalid_matched_cells=count['invalid_cells'],
        cell_period_accuracy=ratio(count['period_correct'], count['numeric_gold']),
        cell_role_accuracy=ratio(count['role_correct'], count['numeric_gold']),
        cell_header_link_accuracy=ratio(count['link_correct'], count['link_gold']),
        cell_structure_exact=ratio(count['structure_correct'], count['numeric_gold']),
        cell_evidence_localization=ratio(count['evidence_correct'], count['evidence_gold']),
        unscoped_omission_warnings=unscoped_omission_warnings(pred),
        false_assurance=bool(pred.get('status') == 'success' and false_reasons),
        false_assurance_reasons=false_reasons if pred.get('status') == 'success' else [],
        warnings=pred.get('issues', []), gold_cells=total_cells, predicted_cells=pred_cells)
    return dict(document_id=gold['document_id'], evaluated_at=utc(), evaluator_version=EVALUATOR_VERSION,
                reference_status=gold.get('annotation_status', 'unknown'),
                human_checked_cells=gold.get('human_checked_cells', 0),
                scope=gold['scope'], run_status=pred.get('status', 'unspecified'),
                whitespace_policy='remove Unicode whitespace only; preserve glyphs, signs, punctuation and decimals',
                matching_policy=__doc__, metrics=metrics, errors=errors, alignment=alignment)


def aggregate(reports):
    """Micro counts, retaining failed pages in denominators; caller groups split/audit cohorts."""
    result = dict(documents=len(reports), run_statuses=dict(Counter(r['run_status'] for r in reports)),
                  reference_statuses=dict(Counter(r['reference_status'] for r in reports)))
    for name in ('raw_cell_exact', 'semantic_cell_exact', 'numeric_raw_exact', 'numeric_semantic_exact',
                 'cell_coverage', 'header_role_accuracy', 'header_parent_accuracy', 'raw_label_exact',
                 'row_order_accuracy', 'silent_omission_rate', 'missing_cells', 'correct_abstention',
                 'abstention_rate', 'raw_precision_all_predicted', 'extraneous_row_rate'):
        result[name] = ratio(sum(r['metrics'][name]['correct'] for r in reports),
                             sum(r['metrics'][name]['total'] for r in reports))
    for name in ('tables', 'rows', 'hierarchy_edges', 'grouped_headers'):
        result[name] = prf(*(sum(r['metrics'][name][key] for r in reports) for key in ('matched', 'gold', 'predicted')))
    for name in ('cell_period_accuracy', 'cell_role_accuracy', 'cell_header_link_accuracy', 'cell_structure_exact', 'cell_evidence_localization'):
        if all(name in r['metrics'] for r in reports):       # reports scored by evaluator v1 do not have these axes
            result[name] = ratio(sum(r['metrics'][name]['correct'] for r in reports), sum(r['metrics'][name]['total'] for r in reports))
    result['false_assurance_rate'] = ratio(sum(r['metrics']['false_assurance'] for r in reports), len(reports))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gold', required=True)
    parser.add_argument('--prediction', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--require-human', action='store_true')
    args = parser.parse_args()
    reference = read_json(args.gold)
    from benchmark.validate import validate_reference
    if args.require_human and (reference.get('annotation_status') != 'human_verified' or
                              not reference.get('verification', {}).get('reviewer') or validate_reference(reference)):
        parser.error('Reference is not independently human verified')
    report = evaluate(reference, read_json(args.prediction))
    report.update(gold_sha256=sha256(args.gold), prediction_sha256=sha256(args.prediction))
    write_json(args.out, report)
    print(json.dumps(report['metrics'], ensure_ascii=False, indent=2))
