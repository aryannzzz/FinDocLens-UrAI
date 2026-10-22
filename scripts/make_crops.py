"""Render evidence crops of a page region with predicted boxes overlaid.

    python scripts/make_crops.py <pdf> <page> <prediction.json> <out.png> --bbox x0,y0,x1,y1 [--dpi 160]
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from findoclens.render import draw_evidence

ap = argparse.ArgumentParser()
ap.add_argument("pdf")
ap.add_argument("page", type=int)
ap.add_argument("pred")
ap.add_argument("out")
ap.add_argument("--bbox")
ap.add_argument("--dpi", type=int, default=160)
a = ap.parse_args()
pred = json.loads(Path(a.pred).read_text())
crop = [float(x) for x in a.bbox.split(",")] if a.bbox else None
print(draw_evidence(a.pdf, a.page, pred, a.out, dpi=a.dpi, crop=crop))
