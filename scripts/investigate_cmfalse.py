"""Why does Docling `do_cell_matching=False` return empty cells on the Daiwabo slide but not on the other pages?

Run in the model venv:  .venv-docling/bin/python scripts/investigate_cmfalse.py <pdf> <out.json>
For each predicted TableFormer cell box it counts the PDF text-layer words whose centre lies inside the box, under three
coordinate hypotheses (as reported / y-flipped / scaled by page-size ratio). Pure diagnosis: nothing is written back.
"""
import json
import sys

import fitz

sys.path.insert(0, ".")
from findoclens.backends.docling_backend import get_converter

pdf, out = sys.argv[1], sys.argv[2]
page = fitz.open(pdf)[0]
words = [(w[:4], w[4]) for w in page.get_text("words")]
res = {}
for cm in (False, True):
    conv, _ = get_converter(cm, None, "accurate", None, None)
    doc = conv.convert(pdf, page_range=(1, 1)).document
    pg = doc.pages[1]
    item = doc.tables[0]
    H = pg.size.height
    cells = item.data.table_cells
    stats = dict(page_size_docling=[pg.size.width, pg.size.height], page_size_pdf=[page.rect.width, page.rect.height], n_cells=len(cells),
                 n_text=sum(bool(c.text.strip()) for c in cells), n_table_prov=len(item.prov), table_bbox=str(item.prov[0].bbox) if item.prov else None)
    for name, tf in (("as_reported_topleft", lambda b: b.to_top_left_origin(H)), ("raw", lambda b: b)):
        hits = 0
        boxes = 0
        for c in cells:
            if c.bbox is None:
                continue
            b = tf(c.bbox)
            boxes += 1
            hits += any(b.l <= (w[0] + w[2]) / 2 <= b.r and b.t <= (w[1] + w[3]) / 2 <= b.b for w, _ in words)
        stats[f"cells_with_a_pdf_word_inside[{name}]"] = f"{hits}/{boxes}"
    stats["sample_cell_boxes"] = [str(c.bbox) for c in cells[:3]]
    stats["sample_texts"] = [c.text for c in cells if c.text.strip()][:6]
    res[f"cell_matching={cm}"] = stats
json.dump(res, open(out, "w"), ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False, indent=1))
