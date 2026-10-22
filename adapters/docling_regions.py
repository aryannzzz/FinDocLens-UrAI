"""Ablation entrypoint: native_grid region proposals + Docling TableFormer per region (cell matching on), CPU."""
from adapters._base import docling_metadata, make_extract

BENCHMARK_METADATA = docling_metadata("docling_regions", do_cell_matching=True,
                                      hybrid="native_grid proposes table regions from the text layer; Docling structure per region")
extract = make_extract("docling_regions", "docling_regions", opts=dict(cell_matching=True))
