"""Contract entrypoint: findoclens `native_grid` (rule-based, CPU). Use `--entrypoint adapters.native_grid:extract`."""
from adapters._base import base_metadata, make_extract

BENCHMARK_METADATA = base_metadata("native_grid")
extract = make_extract("native_grid", "native_grid")
