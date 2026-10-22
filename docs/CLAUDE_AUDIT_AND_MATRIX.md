# Track B — technical audit and experiment matrix (written before backend work, 2026-10-22)

## Machine audit (measured, `findoclens.runinfo.hardware()` + shell)
| item | observed |
|---|---|
| CPU | 12th Gen Intel i5-12450H, 12 threads |
| RAM | 15.7 GiB total, **~3.5–4.6 GiB available** at start (desktop session using the rest), 15 GiB swap (6 GiB in use) |
| Disk | `/` 97 GB, **4.2 GB free at start (96% used)** → hard budget for venvs + model weights |
| GPU | Intel Alder Lake iGPU + NVIDIA PCI device `25ac` present, **`nvidia-smi` fails ("couldn't communicate with the NVIDIA driver")**; `/dev/nvidia*` nodes exist but the driver is not usable. Per AGENTS.md the driver was **not touched**. All model runs are therefore CPU-only; no VRAM number can be reported. |
| Python | 3.13.5 (conda) for native backends; `uv` venv `.venv-docling` (Python 3.12, CPU torch) for model backends |
| Network | PyPI / HuggingFace / JPX reachable (slow, ~1 MB/s observed); `omron.com` returns Akamai *Access Denied* |

## Source audit
* `source.pdf` (dev), ELECOM p9 (`elecom`), Daiwabo p10 (`daiwabo`) downloaded, SHA-256 in `data/manifest.json`. **OMRON: blocked** (Akamai HTML error page saved as `omron.ACCESS_DENIED.html`, not a PDF) → no OMRON results exist anywhere in this report.
* All three PDFs have native text layers (no raster pages in the wild set) → scan behaviour can only be tested on **synthetic rasterisations** of these pages (same-source, so they are *not* independent-template evidence; they *are* a valid OCR test because the text layer gives exact reference strings).
* Frozen v2 on ELECOM: runs, 34 rows (but `unit_not_detected`, spurious reconciliation warning). On Daiwabo: runs, **status looks successful but output is wrong** (labels merged across the two side-by-side tables, +増減 amounts glued into labels, only 9 rows from 21) → "false assurance" test case for the router.

## Backend candidates and decision
| id | backend | feasibility here | decision |
|---|---|---|---|
| B0 | `native_v2` frozen adapter | trivial | **implement** (baseline) |
| B1 | `native_grid` generalised text-layer grid (N columns, multi-table, colspan headers, roles) | cheap, high payoff for cross-layout | **implement** |
| B2 | Docling TableFormer ACCURATE, `do_cell_matching` True/False | CPU torch ~190 MB + weights; slow but feasible | **implement + measure** both flags |
| B3 | Docling + OCR (RapidOCR/EasyOCR-ja) on rasterised page | needs OCR weights; CPU | **attempt** (scan fallback) |
| B4 | PaddleOCR-VL-1.6 full pipeline | needs paddlepaddle + ~2–4 GB weights, ≥ several GB RAM; disk 4 GB free, no GPU | **one limited attempt, expected blocked**; record exactly why |
| B5 | Tesseract `jpn` | needs system package/traineddata (sudo) – not installed | skip unless cheap |
| R | adaptive router (`--backend auto`) | cheap | **implement** |
| V | conservative validator | cheap | **implement** |

## Experiment matrix (what will be run; results go in `docs/CLAUDE_RESULTS.md`)
Documents × variants: `source` (dev), `elecom` p9, `daiwabo` p10 — each as *native* page and, where OCR is relevant, *rasterised 200-dpi image-only PDF* (`variant=raster200`).

| backend \ doc | source | elecom | daiwabo | source-raster | elecom-raster | daiwabo-raster |
|---|---|---|---|---|---|---|
| native_v2 | run | run | run | expect fail-closed | expect fail-closed | expect fail-closed |
| native_grid | run | run | run | expect fail-closed | " | " |
| docling (cell_matching=True) | run | run | run | (OCR off → expect no cells) | | |
| docling (cell_matching=False) | run | run | run | | | |
| docling + OCR | – | – | – | run | run | run |
| PaddleOCR-VL-1.6 | one attempt on `source` | | | | | |
| auto (router) | run | run | run | run | run | run |

Metrics per cell: tables found, rows, numeric cells, **cell recall/precision against PDF-text-layer tokens** (valid reference for digital pages and for rasterisations of them), raw-cell exact vs the AI-drafted `baseline_v2/tests/gold_rows.tsv` for `source` only (**AI-drafted, not human-verified**), arithmetic checks, cold/warm time, peak RSS. Holdout gold is owned by Codex; here holdout numbers are *agreement/recall vs text layer* only.

Hypothesis under test: *native text is fastest and most faithful on good digital tables but fails on raster pages / complex layouts; conditional model-backed structure/OCR raises coverage without hurting source fidelity.*
