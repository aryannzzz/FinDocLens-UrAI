# Track B results — measured, blocked, proposed (2026-10-22)

All numbers below come from `runs/summary.json` (regenerate: `python scripts/run_matrix.py [--rescore]`), per-run
`runs/<backend>/<doc>/run_manifest.json`, and `docs/logs/`. Nothing here is a human-verified accuracy: see *Threats to validity*.

## 0. One-paragraph verdict
On the three digital pages available (original + ELECOM p9 + Daiwabo p10), a text-layer parser that I generalised (`native_grid`)
reproduced every numeric token in ~13–50 ms and ~100 MB; Docling TableFormer (CPU) matched it on the two single-table pages
(74/74 and 56/56 tokens) but took ~7–14 s warm and ~1.4 GB, and on the 3-table Daiwabo slide it **flattened all tables into one grid and lost 4 of 63 tokens**
(`cell_matching=False` returned a table with **no text at all**). The frozen v2 parser looked successful on that slide (`status ok`) while
capturing **18 of 63** tokens. On image-only copies of the same pages every native backend failed closed (0 cells, explicit `needs_visual_fallback`),
and Docling + RapidOCR (Japanese path) recovered 72/74, 56/56, 59/63 numeric tokens with **no wrong digit**, but mis-read kanji labels (産→產) and dropped `－` placeholders.
The hypothesis is **partly supported** (native fastest/most faithful; fails on raster; model OCR adds coverage), **not supported** in its
"complex structure ⇒ need a model" form on these pages (the generalised native parser beat Docling on the complex slide), with the large caveat that
`native_grid` was developed while looking at these pages (see §6).

## 1. Hardware / environment limits (exact)
| item | value |
|---|---|
| CPU / RAM | i5-12450H (12 threads); 15.7 GiB total, only ≈2.4–3.9 GiB *available* during runs (desktop session), swap 6.6 GiB used |
| GPU | **none usable**: `nvidia-smi` → "couldn't communicate with the NVIDIA driver" (logged in every `run_manifest.json`). Driver untouched. All model numbers are **CPU, torch 2.14.1+cpu**. No VRAM measurement exists. |
| Disk | `/` 97 GB, **4.2 GB free at start → 1.3 GB free now (99% used)**; `.venv-docling` 1.5 GB, HF cache `.cache/hf` ≈0.5 GB |
| Network | PyPI/HF reachable but ≈0.1–1 MB/s: the Docling venv took ≈1 h to install (the first attempt stalled on three large wheels and was restarted); `omron.com` denied access |
| Docling | docling 2.141.0, docling-core 2.103.1, docling-ibm-models 4.0.4, docling-parse 7.22.4; layout `docling-project/docling-layout-heron@8f39ad3`, tables `docling-project/docling-models@fc0f2d4` (TableFormer, `TableFormerMode.ACCURATE`) |
| OCR | RapidOCR 3.10.0 + onnxruntime 1.31.0, `lang=iso:ja`; model files on disk: `PP-OCRv6_det_small.onnx`, `PP-OCRv6_rec_small.onnx` |

## 2. Measured: backend × document matrix
Reference for recall/precision = every numeric word in the PDF **text layer** of the digital page (page-number footer excluded;
`findoclens.compare.text_layer_reference`). Valid for digital pages and for rasterisations of those pages (here: 200-dpi PNG-in-PDF, no text layer).
It says nothing about labels, structure, roles. "dev-gold" = `baseline_v2/tests/gold_rows.tsv` (AI-drafted, **not human verified**, original page only).
Latency: `cold` = first call in a fresh process (includes converter construction/model load), `warm` = median of calls 2–3 in the same process, wall-clock;
RSS = process peak (`ru_maxrss`). `auto` rows time the whole routing call incl. model subprocess.

| backend | doc / variant | status | tables | rows | numeric tokens (ref) | recall | precision | dev-gold | cold ms | warm ms | peak RSS MB |
|---|---|---|---|---|---|---|---|---|---|---|---|
| native_v2 (frozen) | source digital | ok | 1 | 37 | 74 (74) | 1.000 | 1.000 | 74/74 | 45 | 19 | 58 |
| native_v2 | elecom digital | ok | 1 | 28 | 56 (56) | 1.000 | 1.000 | – | 59 | 19 | 93 |
| native_v2 | **daiwabo digital** | **ok (false assurance)** | **1 (of 3)** | 9 | **18 (63)** | **0.286** | 1.000 | – | 68 | 46 | 93 |
| native_v2 | any raster200 | failed (`needs_visual_fallback`) | 0 | 0 | 0 | 0 | – | 0/74 | 143–161 | 128–184 | 144–147 |
| native_grid | source digital | ok | 1 | 37 | 74 (74) | 1.000 | 1.000 | 74/74 | 26 | 35 | 97 |
| native_grid | elecom digital | ok | 1 | 28 | 56 (56) | 1.000 | 1.000 | – | 50 | 13 | 97 |
| native_grid | daiwabo digital | ok | 3 | 21 | 63 (63) | 1.000 | 1.000 | – | 53 | 48 | 97 |
| native_grid | any raster200 | failed (`needs_visual_fallback`) | 0 | 0 | 0 | 0 | – | 0/74 | 34–39 | 27–33 | 97–101 |
| Docling, cell_matching=True | source digital | ok | 1 | 37 | 74 (74) | 1.000 | 1.000 | 74/74 | 22 633 | 13 484 | 1 466 |
| Docling cm=True | elecom digital | ok | 1 | 28 | 56 (56) | 1.000 | 1.000 | – | 17 469 | 11 051 | 1 341 |
| Docling cm=True | **daiwabo digital** | ok* | **1 (of 3)** | 13 | **59 (63)** | 0.937 | 1.000 | – | 17 475 | 9 854 | 1 486 |
| Docling cm=True | any raster200 (OCR off) | **failed** (`table_without_numeric_cells`) | 1 | 0 | 0 | 0 | – | 0/74 | 17–23 k | 11–14 k | 1 534–1 600 |
| Docling, cell_matching=False | source digital | ok | 1 | 37 | 74 (74) | 1.000 | 1.000 | 74/74 | 85 369† | 8 687 | 1 388 |
| Docling cm=False | elecom digital | ok | 1 | 28 | 56 (56) | 1.000 | 1.000 | – | 12 654 | 7 115 | 1 344 |
| Docling cm=False | **daiwabo digital** | **failed** (table, **no cell text**) | 1 | 0 | 0 (63) | 0 | – | – | 12 119 | 7 532 | 1 382 |
| Docling + RapidOCR (ja) | source raster200 | ok | 1 | 37 | 72 (74) | 0.973 | 1.000 | 62/74‡ | 24 809 | 15 780 | 2 248 |
| Docling + RapidOCR | elecom raster200 | ok | 1 | 28 | 56 (56) | 1.000 | 1.000 | – | 21 787 | 14 743 | 2 188 |
| Docling + RapidOCR | daiwabo raster200 | ok* | 1 (of 3) | 13 | 59 (63) | 0.937 | 1.000 | – | 22 235 | 13 753 | 2 130 |
| **auto** (router, no models allowed unless needed) | source / elecom / daiwabo digital | ok / ok / ok | 1 / 1 / 3 | 37 / 28 / 21 | 74 / 56 / 63 | 1.000 | 1.000 | 74/74 | 45 / 70 / 88 (native accepted, no model) | – | – |
| auto | source / elecom / daiwabo raster200 | **needs_visual_review** (×3) | 1 | 37 / 28 / 13 | 72 / 56 / 59 | 0.973 / 1.000 / 0.937 | 1.000 | 62/74‡ | 23.9–25.9 k | – | – |
| auto `--verify` (native + Docling cross-check) | source / elecom / daiwabo digital | ok ×3 | 1 / 1 / 3 | 37 / 28 / 21 | 74 / 56 / 63 | 1.000 | 1.000 | 74/74 | 20.7 k / 18.7 k / 17.5 k | – | – |

\* Docling's mapping reports `ok` because it returned numeric cells; the table is wrong (§3.2). That is exactly why the router re-checks against the text layer.
† Single unexplained outlier; an immediate re-run of the same configuration gave 18.8 s cold / 10.5 s warm (memory/swap pressure is the suspected, unverified cause).
‡ Label-keyed matching; the 12 "wrong" cells are rows whose OCR'd *label* differs (産→產, below), not wrong digits — token precision is 1.000.

Peak GPU memory: **not measured (no usable GPU)**. The very first Docling run (a probe on ELECOM; artifacts not kept) also downloaded weights: 58 s total, 1.4 GB RSS.

### 2.1 `cell_matching` True vs False
Identical on single clean tables (source, ELECOM: 74/74, 56/56). On the three-table slide `True` returns text (59/63 tokens, tables flattened),
`False` returns a structurally plausible grid with **empty cells** → our runner marks it `failed`. `False` was ≈24–36 % faster warm (7.1–8.7 s vs 9.9–13.5 s).
Raw `DoclingDocument` JSON + Markdown per run are in `runs/docling_*/…/docling_document.json|docling_tables.md`.

### 2.2 OCR label fidelity (Docling + RapidOCR vs text layer, row-order alignment; `runs/ocr_rapid_rapid/*`)
| doc | labels | exact | typical error |
|---|---|---|---|
| source raster | 43 | 34 | `流動資産→流動資產`, `固定資産→固定資產` (産→產) |
| elecom raster | 34 | 22 | same, plus `売掛金→壳掛金` |
| daiwabo raster | 21 (text layer) | 12 (rest lost in the flattened grid) | – |
Digits: 0 substitutions in all three pages; 2 of 74 `－` placeholders dropped on the original (rows 建設仮勘定 / 長期貸付金, prior period) and reported as `absent_text_cell`, not as 0.

## 3. What each failure looks like (visually checked crops in `docs/evidence/`)
| id | file | what it shows |
|---|---|---|
| F1 | `F1_native_v2_daiwabo_false_assurance.png` | frozen v2 draws boxes only on the right table's first two columns; left table, deltas and the lower table silently absent; run `status=ok`, issues only `missing_period_header`/`unit_not_detected` |
| F2 | `F2_docling_cmtrue_daiwabo_merged.png` | one table box over the whole slide (3 tables → 1 grid); lower-table columns shifted, `→ 12,410` fused, explanation text spilled into numeric columns |
| F3 | `F3_docling_cmfalse_daiwabo_empty.png` | table box present, zero cell boxes (no text) |
| F4 | `F4_ocr_source_raster_missing_dash.png` (+`.json`) | OCR boxes everywhere except the two `－` cells (建設仮勘定, 長期貸付金) |
| S1 | `S1_native_grid_daiwabo.png` | success: 3 tables, 63 amount boxes, `△`/`+` preserved, deltas typed `change_amount` |
| S2 | `S2_native_grid_elecom.png` | success: 56 amount boxes, `△4` negative kept, unit 百万円 detected |
| S3 | `S3_native_grid_elecom_p13_equity_statement.png` | out-of-template stress page: 5-col + 8-col tables, wrapped labels merged, all `－`/`△` kept. **Known defects:** header words leak into one `section` row (`価差額金整累計額額合計`) and centred spanning headers (株主資本, その他の包括利益累計額) get single-column spans |

Other recorded defects: v2 reports `unit_not_detected` on ELECOM and Daiwabo and two false `financial_reconciliation_failure` warnings on ELECOM (its gross/net grouping misreads net-only accounts); `native_grid` finds no unit for Daiwabo tables 2–3 (unit printed only above table 1 → left `null` with an issue, not inherited).

## 4. Router and validator (measured behaviour, not accuracy)
* Digital, clean → `native_accept` (45–88 ms). Daiwabo additionally logs `native_v2 disagrees with native_grid (9 mismatches, 1 vs 3 tables); v2 labels contain amounts (false assurance)`.
* `--verify` Docling cross-check on Daiwabo: Docling lacked 4 native tokens and invented none; every Docling token is in the text layer → native kept, `checker_differs_native_glyphs_kept` info issue. A Docling token that is in the text layer but absent from the native table would force `needs_visual_review` (rule implemented, **no natural example occurred**; not exercised beyond unit logic).
* Raster → OCR path → status always `needs_visual_review`/`partial`, never `ok` (no second source; arithmetic checks need hierarchy that Docling/OCR output lacks).
* Validator (never edits cells): Daiwabo 14 `pass` + 5 `within_rounding`, 0 violations (delta = current − previous, assets total = liabilities+net assets total); ELECOM 8 `within_rounding`; original 5 `within_rounding`, 1 skipped (gross/depreciation/net group). Frozen-sample perturbations: removing a `△` raises an `arithmetic_violation`; removing a cell yields `absent_text_cell` + `partial_data_row`.

## 5. Page sweep (native_grid claims, no gold; `runs/native_grid_page_sweep.json`)
ELECOM (21 pages): tables claimed on 12 pages [0,4,6,8–15,19]; Daiwabo (56 pages): 7 pages [4,7,8,9,10,19,25]. These are counts of *claims*, not checked; only p9/p10 (ELECOM p9 = index 8, Daiwabo p10 = index 9) and ELECOM index 12 were looked at.

## 6. Threats to validity (read before quoting any number)
1. **In-sample design for `native_grid`.** I viewed the original, ELECOM idx 8 and Daiwabo idx 9 renders while building it and tuned header/column/segmentation rules on them (plus ELECOM idx 12 for wrapped labels). Its 100 % token recall on these pages is *not* an out-of-template estimate. Docling was run with defaults, untuned → the comparison favours native_grid.
2. **No human-verified gold.** Recall/precision use the PDF text layer (exact strings only). Labels, hierarchy, roles, periods are unscored here; the Codex harness owns holdout gold. Original-page "dev-gold" is AI-drafted.
3. **Same-source rasterisation.** OCR results come from clean 200-dpi renders of the same three pages (no noise, skew, JPEG, scanner contrast). They are not scan-quality estimates and not independent templates.
4. n = 3 pages, 1 environment; latency from 3 in-process repeats (cold = 1 sample). Memory/disk contention on the laptop adds variance (one 85 s outlier).
5. OMRON (the hardest holdout: grouped headers, composition %, delta, multiline) **is absent**: no result exists. `%`-column and grouped-header handling is implemented and unit-tested only on parse-level semantics, **not measured on a real page**.

## 7. Attempted but blocked
| item | what happened |
|---|---|
| OMRON holdout download | `omron.com` returned an Akamai "Access Denied" HTML page for a plain request and for one retry with a browser-like User-Agent; stopped. Stored as `data/pdfs/omron.ACCESS_DENIED.html` (not a PDF). Needs a manual download by the applicant. |
| PaddleOCR-VL-1.6 full pipeline | **Not installed or run — preflight only** (`scripts/preflight_paddleocr_vl.py` → `docs/logs/paddleocr_vl_preflight.json`): HF repo `PaddlePaddle/PaddleOCR-VL-1.6` weights 1.92 GB + layout `PP-DocLayoutV3` 0.13 GB + `paddlepaddle` 3.3.1 wheel 195 MB ≈ 2.26 GB minimum vs **1.86 GB free disk at that moment (now 1.3 GB)**; installing would have filled the disk of a shared desktop. Also no usable GPU and ≈2.4 GB available RAM for a 0.9 B model. Verdict: BLOCKED on disk (then RAM, GPU). Substitute used: Docling + RapidOCR (PaddleOCR-family PP-OCR) Japanese path. **No claim about PaddleOCR-VL accuracy or fit.** |
| Tesseract `jpn` | binary/traineddata not installed; installing needs system packages (not attempted). |
| GPU inference | driver unreachable; not debugged, per instructions. |

## 8. Proposed, not run
Selective crop re-run (OCR/VLM only on cells where native and checker disagree); calibrated confidence; PP-StructureV3 and PaddleOCR-VL on a machine with ≥8 GB free disk/RAM or a working GPU; real scans / noisy rasterisation; OMRON and a second independent issuer; ruling-line detection for merged header spans; hierarchy inference for OCR/Docling output (would enable the arithmetic check as second evidence); `%`/composition and delta validation on a real page.

## 9. Reproduce
```bash
python -m unittest discover -s baseline_v2/tests -p 'test_*.py' -q   # 25 frozen tests
python -m unittest discover -s tests -q                              # 25 track-B tests
python scripts/run_matrix.py                                         # ≈25 min on this laptop; needs .venv-docling
python scripts/run_matrix.py --rescore                               # recompute metrics from stored predictions
python scripts/make_failure_crops.py && python scripts/page_sweep.py
```
Run manifests record `git_commit` of HEAD at run time with `+dirty` when the tree had uncommitted edits (the matrix ran on `a76d46c+dirty`; the reference-token footer rule in `compare.py` was refined afterwards and applied with `--rescore`, no model re-run).
