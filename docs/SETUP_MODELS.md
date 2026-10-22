# Model backends: environment setup (optional)

Native backends (`native_v2`, `native_grid`, router, validator, tests) need only `PyMuPDF` (see `baseline_v2/requirements.txt`).

Model backends live in a **separate virtualenv** so Torch / Paddle never touch global Python:

```bash
uv venv .venv-docling --python 3.12
uv pip install --python .venv-docling/bin/python \
    --extra-index-url https://download.pytorch.org/whl/cpu --index-strategy unsafe-best-match \
    -r requirements-models.txt
```
The router/CLI call model backends through `FINDOCLENS_MODEL_PYTHON` (default `.venv-docling/bin/python`):
`python -m findoclens.runner docling <pdf> <page_index> --out runs`.

* CPU wheels only: on the development laptop `nvidia-smi` cannot reach the NVIDIA driver, and AGENTS.md forbids changing drivers.
* Disk is tight (≈3–4 GB free at start). Docling weights are downloaded to the HuggingFace cache on first run.
* PaddleOCR-VL would need its own venv (`.venv-paddle`) because Paddle and Torch pins conflict; see `docs/CLAUDE_RESULTS.md` for the attempt log.
