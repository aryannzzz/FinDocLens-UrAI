"""Conservative arithmetic diagnostics. Never edits a prediction; reports checks with a named tolerance policy."""
from __future__ import annotations
import re

POLICY = "rounding_allowance=max(1, n_addends) displayed units (named policy ROUND_N_ADDENDS)"
TOTAL_RE = re.compile(r"合計$|総計$")


def _val(cell):
    return cell.get("value") if cell and cell.get("status") in ("observed", "negative_zero") else None


def _cmp(name, kind, tid, col, period, reported, parts, n_addends, **extra):
    calc = sum(parts)
    diff = reported - calc
    tol = max(1, n_addends)
    status = "pass" if diff == 0 else ("within_rounding" if abs(diff) <= tol else "violation")
    return {"name": name, "kind": kind, "table_id": tid, "column": col, "period": period, "reported": reported,
            "calculated": calc, "difference": diff, "tolerance": tol, "policy": POLICY, "status": status, **extra}


def validate_table(t: dict) -> list:
    checks, rows, tid = [], t["rows"], t["table_id"]
    ncol = t.get("n_data_columns", 0)

    def col_cells(c):
        return [r["cells"][c] if c < len(r["cells"]) and r["cells"][c]["column_index"] == c else None for r in rows]
    # 1. delta = current - previous where columns are semantically identified
    roles = {}
    for r in rows:
        for c in r["cells"]:
            if c["column_index"] >= 0:
                roles.setdefault(c["column_index"], (c["role"], c["period"]))
    amount_cols = sorted([(p, c) for c, (ro, p) in roles.items() if ro == "amount" and p], key=lambda x: x[0])
    change_cols = [c for c, (ro, _) in roles.items() if ro == "change_amount"]
    if len(amount_cols) >= 2 and len(change_cols) == 1:
        (p0, c0), (p1, c1), ch = amount_cols[-2], amount_cols[-1], change_cols[0]
        for r in rows:
            cells = {c["column_index"]: c for c in r["cells"]}
            a, b, d = _val(cells.get(c0)), _val(cells.get(c1)), _val(cells.get(ch))
            if None in (a, b, d):
                continue
            k = _cmp(f"delta={p1}-{p0}: {r['label']}", "delta", tid, ch, p1, d, [b, -a], 1, row_index=r["row_index"])
            checks.append(k)
    # 2. subtotal: X合計 == sum(direct item children of X) when hierarchy is present
    for r in rows:
        if r["type"] != "total" or not r["label"] or not TOTAL_RE.search(r["label"]):
            continue
        head = TOTAL_RE.sub("", r["label"])
        parent = r["parent_path"]
        i1 = rows.index(r)
        # children share the total's own indent level: their parent_path is the *section* path (parent + [head])
        path = parent if (parent and parent[-1] == head) else parent + [head]
        section = next((s for s in rows[:i1] if s["label"] == head and s["type"] == "section"
                        and s["parent_path"] + [head] == path), None)
        if section is None:
            continue
        i0 = rows.index(section)
        body = rows[i0 + 1:i1]
        kids = [x for x in body if x["parent_path"] == path and x["type"] in ("item", "total")]
        if not kids:
            continue
        if any("減価償却累計額" in (x["label"] or "") for x in body):
            checks.append({"name": f"subtotal: {r['label']}", "kind": "subtotal", "table_id": tid, "status": "skipped",
                           "reason": "gross + accumulated-depreciation -> net structure not modelled by the generic validator", "row_index": r["row_index"]})
            continue
        for ci in range(ncol):
            tot = _val(r["cells"][ci]) if ci < len(r["cells"]) else None
            vs = [_val(k["cells"][ci]) if ci < len(k["cells"]) else None for k in kids]
            role = r["cells"][ci]["role"] if ci < len(r["cells"]) else None
            if tot is None or None in vs or role != "amount":
                continue
            checks.append(_cmp(f"subtotal: {r['label']}", "subtotal", tid, ci, r["cells"][ci]["period"], tot, vs,
                               len(vs), row_index=r["row_index"], addends=[k["label"] for k in kids]))
    return checks


def validate_prediction(pred: dict) -> dict:
    """Annotate pred['tables'][*]['checks'] and add issues for violations. Cell values are untouched."""
    for t in pred["tables"]:
        t["checks"] = [c for c in t.get("checks", []) if c.get("source") == "backend"] + validate_table(t)
    # page-level identity: 資産合計 == 負債純資産合計 (same column index/period across tables)
    tots = {}
    for t in pred["tables"]:
        for r in t["rows"]:
            if r["label"] in ("資産合計", "負債純資産合計", "負債及び純資産合計") and r["type"] == "total":
                tots.setdefault(r["label"] != "資産合計", []).append((t, r))
    for (ta, ra) in tots.get(False, []):
        for (tb, rb) in tots.get(True, []):
            if ta is tb:
                continue
            for ca in ra["cells"]:
                cb = next((c for c in rb["cells"] if c["period"] and c["period"] == ca["period"] and c["role"] == "amount"), None)
                if cb and ca["role"] == "amount" and _val(ca) is not None and _val(cb) is not None:
                    ta["checks"].append(_cmp("assets total == liabilities+net assets total", "identity", ta["table_id"],
                                             ca["column_index"], ca["period"], _val(ca), [_val(cb)], 1,
                                             other_table=tb["table_id"]))
    for t in pred["tables"]:
        for c in t["checks"]:
            if c["status"] == "violation":
                pred["issues"].append({"severity": "warning", "code": "arithmetic_violation", "table_id": t["table_id"],
                                       "check": c["name"], "difference": c["difference"],
                                       "note": "diagnostic only; value not altered, may be rounding or extraction error"})
    return pred
