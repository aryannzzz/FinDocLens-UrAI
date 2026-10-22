"""Label-independent diagnostics that complement (never replace) the strict evaluator.

The primary evaluator matches rows by exact label, so one mis-read kanji turns a row's correct numbers into "missing cells".
These diagnostics separate that effect from numeric fidelity. They use the same references, the same whitespace-only
normalisation and report numerator/denominator. They are not part of the contract's leaderboard.

  token_recall / token_precision : multiset of non-null raw cell strings of numeric columns (location-free)
  row_tuple_recall               : gold rows whose exact tuple of numeric raws appears as some predicted row's tuple
                                   (rows whose every numeric cell is null/absent are excluded from the denominator)
  label_exact_given_tuple        : among tuple-matched rows, how many also carry the exact gold label
"""
from collections import Counter
import re


def _norm(x):
    return re.sub(r"\s+", "", x) if isinstance(x, str) else x


def _num_cells(row):
    return sorted((c for c in row.get("cells", []) if c.get("role") != "other"), key=lambda c: c["column_index"])


def _tuple(row):
    cells = _num_cells(row)
    if not any(c.get("raw") for c in cells):
        return None
    return tuple(_norm(c.get("raw")) for c in cells)


def diagnose(gold, pred):
    g_rows = [(t["table_id"], r) for t in gold["tables"] for r in t["rows"]]
    p_rows = [(t.get("table_id"), r) for t in pred.get("tables", []) for r in t.get("rows", [])]
    g_tok = Counter(_norm(c["raw"]) for _, r in g_rows for c in _num_cells(r) if c.get("raw"))
    p_tok = Counter(_norm(c["raw"]) for _, r in p_rows for c in _num_cells(r) if c.get("raw"))
    hit = sum((g_tok & p_tok).values())
    p_tuples = Counter(t for t in (_tuple(r) for _, r in p_rows) if t)
    by_tuple = {}
    for _, r in p_rows:
        t = _tuple(r)
        if t:
            by_tuple.setdefault(t, []).append(r)
    matched = labeled = 0
    denominator = 0
    avail = Counter(p_tuples)
    for _, r in g_rows:
        t = _tuple(r)
        if not t:
            continue
        denominator += 1
        if avail[t] > 0:
            avail[t] -= 1
            matched += 1
            labeled += any(_norm(c.get("label")) == _norm(r["label"]) for c in by_tuple[t])
    return dict(token_recall=dict(correct=hit, total=sum(g_tok.values())),
                token_precision=dict(correct=hit, total=sum(p_tok.values())),
                row_tuple_recall=dict(correct=matched, total=denominator),
                label_exact_given_tuple=dict(correct=labeled, total=matched))
