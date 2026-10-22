# Environment used for the reported runs (22 Oct 2026)

| item | value |
|---|---|
| machine | 12th-gen Intel Core i5-12450H (12 logical CPUs), 15.7 GiB RAM shared with a desktop session (≈2.4–4.5 GiB *available* during runs), swap in use |
| OS | Linux 7.0.11-76070011-generic x86_64 |
| GPU | **none usable**: `nvidia-smi` → "couldn't communicate with the NVIDIA driver" (logged in every run's `metadata.json`). Driver, CUDA and system packages untouched. Every model number is CPU; **peak GPU memory was never measured.** |
| disk | `/` 97 GB, 99 % used (≈1.1 GB free at the end). The OCR "medium" ablation added 139 MB of ONNX models; PaddleOCR-VL weights (≈2.3 GB with runtime) were **not** downloaded |
| native/harness Python | 3.13.5 (`.venv`, `--system-site-packages`): PyMuPDF 1.27.2.3, Pillow 12.0.0, numpy 2.2.6 (`requirements.txt`) |
| model Python | 3.12.13 (`.venv-docling`, 112 pinned packages in `requirements-models.lock.txt`): docling 2.141.0, docling-core 2.103.1, docling-ibm-models 4.0.4, docling-parse 7.22.4, torch 2.14.1+cpu, torchvision 0.29.1+cpu, transformers 5.20.2, rapidocr 3.10.0, onnxruntime 1.31.0, PyMuPDF 1.28.2 |
| Docling layout model | `docling-project/docling-layout-heron` @ `8f39ad3c0b4c58e9c2d2c84a38465abf757272d8` |
| Docling table model | `docling-project/docling-models` @ `fc0f2d45e2218ea24bce5045f58a389aed16dc23` (TableFormer, `TableFormerMode.ACCURATE`) |
| OCR models (RapidOCR, `lang=iso:ja`) | small (default): `PP-OCRv6_det_small.onnx` sha256 `090f04ab…`, `PP-OCRv6_rec_small.onnx` `6f327246…`; medium (ablation): `PP-OCRv6_det_medium.onnx` `92078b73…`, `PP-OCRv6_rec_medium.onnx` `eef44482…`; angle classifier `ch_ppocr_mobile_v2.0_cls_mobile.onnx` `e47acedf…` |
| harness | `benchmark/` (Codex), unchanged except that `benchmark/run.py` now passes `BENCHMARK_RUN_DIR` to the worker so adapters can store raw model output beside each trial |

## Two interpreters, on purpose
Native backends and the evaluator run in `.venv` (small, ~100 MB RSS). Docling backends run in `.venv-docling` because torch/Docling
must stay out of the system Python. The harness measures the **worker process** RSS (`ru_maxrss`), so for Docling runs the reported RSS
includes the model stack; for `auto`, whose model work happens in a child process, the child's peak is recorded in `provenance`.
`HF_HOME` points at `.cache/hf` (symlink to the downloaded Hugging Face cache) and `HF_HUB_OFFLINE=1` during runs.

## Timing definitions
* *cold*: first call in a fresh worker process. Includes interpreter start of the backend module, lazy model construction (disclosed in
  `provenance.lazy_load_on_first_call`), a 200-dpi page render for evidence, extraction, projection and JSON writing. The OS file cache is not flushed.
* *warm*: median of repeated calls in the same process (3 repetitions on the main and raster sets; **1** repetition on the adversarial set for
  Docling backends, so no warm median is reported there). The PDF is re-opened and re-rendered each time.
* One cold sample per page; no confidence intervals. Background desktop load was not controlled, so cold Docling times vary by ±20 % between
  otherwise identical runs (compare `int1_*` and `fin1_*`).
