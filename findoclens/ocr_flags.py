"""Review flags for OCR text. Flags only: this module never rewrites a character.

OCR engines trained mostly on Chinese text sometimes emit the traditional/simplified-Chinese form of a kanji that Japanese
filings print in its modern Japanese form (産→產, 売→壳). Those forms do not occur in ordinary Japanese financial text, so a
hit is a strong (not conclusive) signal that the recognised string differs from the printed one. The raw OCR text is kept
exactly as recognised; the issue lists the suspected Japanese form for the human reviewer.
"""
from __future__ import annotations

# character recognised -> Japanese form it is usually a misreading of (non-Japanese forms only)
SUSPECT_VARIANTS = {
    # traditional-Chinese forms (Japanese uses the right-hand form)
    "產": "産", "壳": "売", "賣": "売", "總": "総", "擔": "担", "價": "価", "對": "対", "發": "発", "實": "実", "圖": "図", "與": "与",
    "區": "区", "稅": "税", "經": "経", "營": "営", "圓": "円", "數": "数", "證": "証", "關": "関", "變": "変", "讓": "譲", "體": "体",
    "會": "会", "國": "国", "學": "学", "當": "当",
    # simplified-Chinese forms
    "产": "産", "卖": "売", "总": "総", "价": "価", "对": "対", "发": "発", "实": "実", "图": "図", "税": "税", "经": "経", "营": "営",
    "数": "数", "证": "証", "关": "関", "变": "変", "会": "会", "国": "国", "学": "学",
}
# keep only entries that actually differ from the Japanese form (税/数/会/国/学 simplified == Japanese in places)
SUSPECT_VARIANTS = {k: v for k, v in SUSPECT_VARIANTS.items() if k != v}


def suspect_variant_chars(text: str) -> dict:
    return {c: SUSPECT_VARIANTS[c] for c in dict.fromkeys(text or "") if c in SUSPECT_VARIANTS}
