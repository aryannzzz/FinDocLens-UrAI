"""Raw-cell exact match against the *AI-drafted* baseline_v2 gold TSV (development sample only; not human verified)."""
from __future__ import annotations
import csv
from collections import defaultdict, deque
from pathlib import Path

from .compare import norm_label, norm_raw

GOLD = Path(__file__).resolve().parents[1] / "baseline_v2" / "tests" / "gold_rows.tsv"


def read_gold(path=GOLD):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def score_against_gold(pred, gold=None):
    gold = gold or read_gold()
    grows = [g for g in gold if g["type"] != "section"]
    n_gold_cells = len(grows) * 2
    queues = defaultdict(deque)
    for t in pred["tables"]:
        for r in t["rows"]:
            vals = [c for c in sorted(r["cells"], key=lambda c: c["column_index"]) if c["column_index"] >= 0 and c["role"] != "other"]
            if any(c["raw"] is not None for c in vals):
                queues[norm_label(r["label"])].append(vals)
    correct = matched = rows_found = 0
    for g in grows:
        label = norm_label(g["path"].split("/")[-1])
        if not queues[label]:
            continue
        rows_found += 1
        vals = queues[label].popleft()
        for j, key in enumerate(("raw_2025", "raw_2026")):
            if j < len(vals) and vals[j]["raw"] is not None:
                matched += 1
                correct += norm_raw(vals[j]["raw"]) == norm_raw(g[key])
    n_pred = sum(1 for t in pred["tables"] for r in t["rows"] for c in r["cells"]
                 if c["column_index"] >= 0 and c["raw"] is not None and c["role"] != "other")
    return {"gold_rows": len(grows), "rows_matched_by_label": rows_found, "gold_cells": n_gold_cells,
            "cells_correct": correct, "cells_matched": matched, "pred_cells": n_pred,
            "recall_correct_over_gold": round(correct / n_gold_cells, 4),
            "precision_correct_over_pred": round(correct / max(1, n_pred), 4),
            "gold_provenance": "AI-drafted, not human-verified"}
