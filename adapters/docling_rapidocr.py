"""Contract entrypoint: Docling TableFormer + RapidOCR (Japanese, full-page OCR), cell matching on (CPU)."""
from adapters._base import docling_metadata, make_extract

BENCHMARK_METADATA = docling_metadata("ocr_rapid", ocr=True, do_cell_matching=True)
extract = make_extract("docling_rapidocr", "ocr_rapid", opts=dict(cell_matching=True))
