# adapters/

Backend adapters live in `findoclens/backends/` (one `extract(pdf, page_index, **opts) -> DocumentPrediction` per backend, registry in
`findoclens/backends/__init__.py`). This directory is intentionally a pointer so that Codex/integration code can look for adapters here
without duplicating them. Usage from another harness:

```python
from findoclens import backends
pred = backends.get("native_grid")("data/pdfs/daiwabo.pdf", 9).to_dict()      # model backends: run via findoclens.runner in .venv-docling
```
