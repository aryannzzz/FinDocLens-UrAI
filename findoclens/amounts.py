"""Exact monetary/percentage token semantics for Japanese financial tables.

`raw` is always preserved by callers; this module only derives `value` and `status`.
A bare dash is `not_reported` (null), never zero. `△0` is `negative_zero` (value 0).
"""
from __future__ import annotations
import re
import unicodedata

NEG = "△▲−-－ー"          # leading negative glyphs (full-width minus / prolonged-sound mark included)
_DASH_ONLY = {"－", "—", "–", "-", "―", "ー", "−"}
_NUM = r"(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?"
AMOUNT_RE = re.compile(rf"^[△▲−\-]?[+＋]?{_NUM}%?$|^[+＋]{_NUM}%?$|^[△▲−\-]?{_NUM}[%％]$")
FRAGMENT_RE = re.compile(r"^[△▲−－—–\-+＋\d,，.%％]+$")


def is_placeholder(raw: str) -> bool:
    return raw.strip() in _DASH_ONLY


def looks_numeric(raw: str) -> bool:
    s = unicodedata.normalize("NFKC", raw.strip()).replace(" ", "")
    s2 = raw.strip().replace(" ", "")
    return bool(is_placeholder(raw) or AMOUNT_RE.fullmatch(s) or AMOUNT_RE.fullmatch(s2)
                or AMOUNT_RE.fullmatch(s.replace("△", "-").replace("▲", "-")))


def parse_token(raw: str):
    """Return (value, status, role_hint). Never raises; unparseable text -> (None,'unreadable'|'uncertain')."""
    if raw is None or not raw.strip():
        return None, "absent_text_cell", None
    if is_placeholder(raw):
        return None, "not_reported", None
    s = unicodedata.normalize("NFKC", raw.strip()).replace(" ", "").replace("，", ",")
    s = s.replace("△", "-").replace("▲", "-").replace("−", "-").replace("－", "-")
    pct = s.endswith("%")
    s = s.rstrip("%")
    m = re.fullmatch(rf"([+-]?)({_NUM})", s)
    if not m:
        return None, "unreadable", None
    sign, body = m.groups()
    num = float(body.replace(",", "")) if "." in body else int(body.replace(",", ""))
    neg = sign == "-"
    if neg:
        num = -num
    explicit_plus = sign == "+"
    status = "negative_zero" if neg and num == 0 else "observed"
    hint = "composition_pct" if pct else ("change_amount" if explicit_plus else None)
    return num, status, hint
