"""Ablation entrypoint: Docling + RapidOCR PP-OCRv6 *medium* det/rec (vs `small` in docling_rapidocr), Japanese, CPU."""
from adapters._base import docling_metadata, make_extract

BENCHMARK_METADATA = docling_metadata("ocr_rapid", ocr=True, do_cell_matching=True)
BENCHMARK_METADATA["ocr"] = "RapidOCR lang=iso:ja, PP-OCRv6 medium det/rec onnx (force_full_page_ocr)"
extract = make_extract("docling_rapidocr_medium", "ocr_rapid", opts=dict(cell_matching=True, ocr_model_size="medium"))
