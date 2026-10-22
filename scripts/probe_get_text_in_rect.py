"""Probe Docling's page backend `get_text_in_rect` (the text source when do_cell_matching=False) on known word boxes.
.venv-docling/bin/python scripts/probe_get_text_in_rect.py <pdf> : compares, for every PDF word, the text the backend returns for the word's own box."""
import sys
from pathlib import Path

import fitz
from docling_core.types.doc import BoundingBox, CoordOrigin
from docling.backend.docling_parse_v4_backend import DoclingParseV4DocumentBackend
from docling.datamodel.base_models import InputFormat
from docling.datamodel.document import InputDocument

pdf = sys.argv[1]
words = fitz.open(pdf)[0].get_text("words")
in_doc = InputDocument(path_or_stream=Path(pdf), format=InputFormat.PDF, backend=DoclingParseV4DocumentBackend)
page = next(iter(in_doc._backend.iter_pages()))
H = page.get_size().height
seg = page.get_segmented_page()
print("textline cells:", len(seg.textline_cells), "word cells:", len(seg.word_cells), "char cells:", len(seg.char_cells))
print("longest textline texts:", sorted((c.text for c in seg.textline_cells), key=len)[-3:])
ok = empty = other = 0
examples = []
for w in words:
    b = BoundingBox(l=w[0], t=w[1], r=w[2], b=w[3], coord_origin=CoordOrigin.TOPLEFT)
    t = page.get_text_in_rect(b).strip()
    if not t:
        empty += 1
        if len(examples) < 5:
            examples.append(("EMPTY", w[4], [round(v, 1) for v in w[:4]]))
    elif t.replace(" ", "") == w[4].replace(" ", ""):
        ok += 1
    else:
        other += 1
        if len(examples) < 10:
            examples.append((t[:30], w[4], [round(v, 1) for v in w[:4]]))
print(dict(page_height=H, words=len(words), exact=ok, empty=empty, different=other))
print(examples)
