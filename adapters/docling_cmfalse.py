"""Contract entrypoint: Docling TableFormer (ACCURATE), do_cell_matching=False, text layer, OCR off (CPU)."""
from adapters._base import docling_metadata, make_extract

BENCHMARK_METADATA = docling_metadata("docling", do_cell_matching=False)
extract = make_extract("docling_cmfalse", "docling", opts=dict(cell_matching=False))
