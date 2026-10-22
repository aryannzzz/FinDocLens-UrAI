"""Contract entrypoint: findoclens `native_v2` (rule-based, CPU). Use `--entrypoint adapters.native_v2:extract`."""
from adapters._base import base_metadata, make_extract

BENCHMARK_METADATA = base_metadata("native_v2")
extract = make_extract("native_v2", "native_v2")
