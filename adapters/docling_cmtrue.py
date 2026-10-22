"""Contract entrypoint: Docling TableFormer (ACCURATE), do_cell_matching=True, text layer, OCR off (CPU)."""
from adapters._base import docling_metadata, make_extract

BENCHMARK_METADATA = docling_metadata("docling", do_cell_matching=True)
extract = make_extract("docling_cmtrue", "docling", opts=dict(cell_matching=True))
