# RESULTS — FinDocLens integrated evaluation (22 Oct 2026)

> **Read first.** The historical `fin1` tables below use immutable AI-drafted references (`ai_draft`, **0 human-verified cells at measurement time**). Their scores remain agreement with those drafts.
> **Provenance correction, 23 Oct:** only **51 cells (31 original, 20 ELECOM, 0 Daiwabo)** were individually reviewed against source images. All eight backends match 51/51 raw/value-status cells on that restricted sample. The other **146** are bulk user-approved AI drafts with a prior AI visual cross-check. The unchanged **197-cell comparison is approved-reference agreement, not fully human-verified ground truth**. Current v2 scores and exact cell lists: [`docs/HUMAN_REVIEW_RESULTS.md`](docs/HUMAN_REVIEW_RESULTS.md), `benchmark/human_gold/v2/`, `results/human_v2/`. The earlier 98-label attestation is preserved, but no individual per-label decisions were exported. Structure and the 12 inferred Daiwabo lower-table periods remain unreviewed. These pages are **development-exposed, not blind tests**. Original export/ledger, v1 snapshots, predictions, measurements and historical tables below are unchanged.
> CPU only; **no GPU measurement exists**. OMRON could not be downloaded and is absent. No model was trained; no VLM / PaddleOCR-VL was run.
> **P0 pass (after the independent review).** The tables below are the pre-fix `fin1` development record and are unchanged. Four review findings were addressed afterwards
> (silent loss of year-like amounts and one-column tables, evaluator blind spots, merged-cell mapping; finding 3, independent validation, remains open): see
> [`docs/P0_FIXES.md`](docs/P0_FIXES.md) and `docs/P0_BEFORE_AFTER.md`. A complete re-run (`p0fix2`) changed no status and no value/alignment score on the 18 reference pages; the new structure
> axes (cell period/role/header link) show Daiwabo `native_grid` at 51/63 periods (34/63 before an adapter fix), the rest being a reference-convention question (B1/B9). The "holdout" pages are
> design-exposed, not blind tests (`benchmark/exposure.json`).
> `native_grid` was developed and again modified during integration while looking at these pages, so its scores on them are **in-sample** (§5).

Code under test: commit `afcfb56` (branch `integration-v1`); all `fin1_*` runs were produced from it (`provenance.code` in every prediction; the only
"dirty" entry is the untracked, unused `adapters/auto.py` for the Docling runs started after it was created). Raw model output, canonical
predictions, per-trial metrics and measurements are immutable under `runs/<backend>/<doc>/fin1_<set>/` and indexed in `results/results.json|csv`.

## 1. What was run
* **Backends** (all through the same harness, `adapters/<name>.py`, projected to `benchmark-1.0`): `v2` (Codex's projection of the frozen parser), `native_v2` (findoclens projection
  of the same parser), `native_grid`, `docling_cmtrue`, `docling_cmfalse`, `docling_rapidocr`, plus the router `auto` and two ablations (`docling_regions`, `docling_rapidocr_medium`).
* **Pages with a reference (18)**: original (development), ELECOM p9 and Daiwabo p10 (independent issuers; manifest split `holdout`, but design-exposed, not blind tests), 3 raster controls of the original (150/200 dpi, text layer deleted),
  5 digital perturbations of the original, 5 synthetic layouts (development), and — added in this stage — 200-dpi raster derivatives of ELECOM p9 and Daiwabo p10
  (`benchmark/raster_variants.py`, own lock file; same split/family as the parent). OMRON p13: unavailable.
* **Trials**: cold (fresh process) + 3 warm on the main and raster sets; cold + 1 warm on the adversarial set for Docling backends (3 warm for native ones).
* **Integration check** (`scripts/contract_report.py fin1`, gold-free): all 450 stored predictions (cold + warm trials, 9 backends) pass the structural contract check
  (`adapters/contract.py`: required fields, vocabularies, slot uniqueness, parent links, null-status cells carry no value, empty extraction never a success), and for every page the canonical output of the cold and warm trials is identical (0 pages differ). This shows the outputs are *comparable and schema-compliant*; it says nothing about correctness.

## 2. Headline, scoped to what was measured
1. **Digital text-layer pages, simple layouts**: every text-layer path reproduces every numeric token of the original page (74/74) and ELECOM p9 (56/56), glyphs exactly (`△`, `△0`, `－` kept), with no extra tokens. The text-layer parsers take 0.17 s cold / 17–54 ms warm / ≈80 MB;
   Docling takes 11–15 s cold (≈70× slower) / 6–8 s warm / 1.3–1.5 GB (≈15–18× the RAM) on CPU for the same result. On these two pages **TableFormer added no accuracy**, and no hierarchy (0/42, 0/33 edges), while the parsers that read indentation got it.
2. **A multi-table slide separates the approaches** (Daiwabo p10, 63 numeric cells in 3 tables): frozen v2 aligns **2/63** cells (it finds 18/63 tokens, one table of three) and still returns `partial`, not an abstention;
   Docling with cell matching **flattens the three tables into one grid** (55/63 tokens present, 0/63 correctly aligned; the only warning is `repeated_header_text_possible_side_by_side_tables`); Docling without cell matching **abstains** (no cell text, cause in §4);
   `native_grid` aligns 63/63 (in-sample). TableFormer itself is not the culprit: given the two upper table regions it gets both right (`docling_regions`: 2/3 tables, 51/63 cells, 0 silent omissions); the page-level layout step merges the regions and misses the unruled lower table.
3. **Raster pages need OCR, and native backends fail closed**: on all 5 raster pages every backend that reads the text layer (`v2`, `native_v2`, `native_grid`, and Docling without OCR, with or without regions) returns `abstained` (Docling: `table_without_numeric_cells`) with 0 silent omissions. Docling + RapidOCR recovers the digits (label-free token recall 72/74, 56/56 and 56/63; no digit is misread — the 7 missing Daiwabo tokens are fused with `→` or replaced by explanation text) but misreads kanji labels
   (産→產, 売→壳: 9/35 and 11/28 paired rows) and cannot see lone `－`; under strict label matching this costs 27–39 % of numeric cells on the single-table pages (§3 table B) and everything on the Daiwabo slide.
4. **Routing avoids model calls on clear pages**: `auto` accepted native output without any model on 12 of the 13 digital pages (0.2–0.3 s) and called a model (15–20 s, ≈2 GB child process) on the 5 raster pages and on the one digital page that raised an arithmetic alarm (`sign_erasure`); on digital pages its tables equal `native_grid`'s, on raster pages `docling_rapidocr`'s.
5. **Where the model path actively harmed**: Docling under `/Rotate 90` metadata returns a one-row garbage table with status `partial` (74/74 cells silently lost, bboxes in rotated space); text-layer parsers are unaffected.
   These statements hold for these pages and this machine; they are not a leaderboard and not an out-of-template estimate.

## 3. Measured tables (AI-drafted references; denominators are reference cells/rows/tables; failures count as zero)
Columns: *numeric cells exact* = raw string equal after removing whitespace only, matched by label-matched row and physical column; *typed* = value+status; *silent omissions* = reference cells with no predicted cell and no omission warning
(rule of `benchmark/evaluate.py`: abstention, `partial_data_row`, `omitted_table`… count as warned); *false assurance* = status `success` although errors exist. Status `partial` is assigned when any warning exists **or the backend declares `hierarchy_not_inferred`**
(all Docling variants), so no Docling row can be a "false assurance" by that definition — read the silent-omission column instead.

#### A. Digital pages: original (development), ELECOM p9, Daiwabo p10 (AI-drafted references, 0 human-verified cells)

| doc | backend | status | tables (matched/gold, extra) | row F1 (P/R) | numeric cells exact (raw) | typed value+status | leaf headers | groups | hierarchy edges | silent omissions | false assurance | cold | warm median | peak RSS MB |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| original | v2 | success | 1/1, +0 | 1.00 (1.00/1.00) | 74/74 (100%) | 74/74 (100%) | 2/2 (100%) | n/a | 42/42 | 0/74 (0%) | no | 165 ms | 31 ms | 79 |
| original | native_v2 | success | 1/1, +0 | 1.00 (1.00/1.00) | 74/74 (100%) | 74/74 (100%) | 2/2 (100%) | n/a | 42/42 | 0/74 (0%) | no | 163 ms | 27 ms | 79 |
| original | native_grid | success | 1/1, +0 | 1.00 (1.00/1.00) | 74/74 (100%) | 74/74 (100%) | 2/2 (100%) | n/a | 42/42 | 0/74 (0%) | no | 173 ms | 34 ms | 79 |
| original | docling_cmtrue | partial | 1/1, +0 | 1.00 (1.00/1.00) | 74/74 (100%) | 74/74 (100%) | 2/2 (100%) | n/a | 0/42 | 0/74 (0%) | no | 13.3 s | 7.7 s | 1427 |
| original | docling_cmfalse | partial | 1/1, +0 | 1.00 (1.00/1.00) | 74/74 (100%) | 74/74 (100%) | 2/2 (100%) | n/a | 0/42 | 0/74 (0%) | no | 13.6 s | 8.0 s | 1422 |
| original | docling_rapidocr | partial | 1/1, +0 | 1.00 (1.00/1.00) | 74/74 (100%) | 74/74 (100%) | 2/2 (100%) | n/a | 0/42 | 0/74 (0%) | no | 19.3 s | 13.3 s | 2080 |
| original | docling_regions | partial | 1/1, +0 | 1.00 (1.00/1.00) | 74/74 (100%) | 74/74 (100%) | 2/2 (100%) | n/a | 0/42 | 0/74 (0%) | no | 14.1 s | 8.4 s | 1269 |
| original | auto | success | 1/1, +0 | 1.00 (1.00/1.00) | 74/74 (100%) | 74/74 (100%) | 2/2 (100%) | n/a | 42/42 | 0/74 (0%) | no | 292 ms | 69 ms | 79 |
| elecom_p9 | v2 | partial | 1/1, +0 | 1.00 (1.00/1.00) | 56/56 (100%) | 56/56 (100%) | 2/2 (100%) | n/a | 32/33 | 0/56 (0%) | no | 137 ms | 20 ms | 79 |
| elecom_p9 | native_v2 | partial | 1/1, +0 | 1.00 (1.00/1.00) | 56/56 (100%) | 56/56 (100%) | 2/2 (100%) | n/a | 32/33 | 0/56 (0%) | no | 182 ms | 17 ms | 80 |
| elecom_p9 | native_grid | success | 1/1, +0 | 1.00 (1.00/1.00) | 56/56 (100%) | 56/56 (100%) | 2/2 (100%) | n/a | 33/33 | 0/56 (0%) | no | 167 ms | 19 ms | 80 |
| elecom_p9 | docling_cmtrue | partial | 1/1, +0 | 1.00 (1.00/1.00) | 56/56 (100%) | 56/56 (100%) | 2/2 (100%) | n/a | 0/33 | 0/56 (0%) | no | 11.7 s | 7.5 s | 1335 |
| elecom_p9 | docling_cmfalse | partial | 1/1, +0 | 1.00 (1.00/1.00) | 56/56 (100%) | 56/56 (100%) | 2/2 (100%) | n/a | 0/33 | 0/56 (0%) | no | 11.9 s | 6.6 s | 1257 |
| elecom_p9 | docling_rapidocr | partial | 1/1, +0 | 1.00 (1.00/1.00) | 56/56 (100%) | 56/56 (100%) | 2/2 (100%) | n/a | 0/33 | 0/56 (0%) | no | 17.2 s | 10.3 s | 1855 |
| elecom_p9 | docling_regions | partial | 1/1, +0 | 1.00 (1.00/1.00) | 56/56 (100%) | 56/56 (100%) | 2/2 (100%) | n/a | 0/33 | 0/56 (0%) | no | 12.0 s | 6.8 s | 1227 |
| elecom_p9 | auto | success | 1/1, +0 | 1.00 (1.00/1.00) | 56/56 (100%) | 56/56 (100%) | 2/2 (100%) | n/a | 33/33 | 0/56 (0%) | no | 208 ms | 40 ms | 80 |
| daiwabo_p10 | v2 | partial | 1/3, +0 | 0.07 (0.11/0.05) | 2/63 (3%) | 2/63 (3%) | 0/10 (0%) | n/a | 0/7 | 65/67 (97%) | no | 160 ms | 44 ms | 84 |
| daiwabo_p10 | native_v2 | partial | 1/3, +0 | 0.07 (0.11/0.05) | 2/63 (3%) | 2/63 (3%) | 0/10 (0%) | n/a | 0/7 | 65/67 (97%) | no | 183 ms | 43 ms | 85 |
| daiwabo_p10 | native_grid | partial | 3/3, +0 | 1.00 (1.00/1.00) | 63/63 (100%) | 63/63 (100%) | 6/10 (60%) | n/a | 0/7 | 0/67 (0%) | no | 208 ms | 53 ms | 85 |
| daiwabo_p10 | docling_cmtrue | partial | 1/3, +0 | 0.00 (0.00/0.00) | 0/63 (0%) | 0/63 (0%) | 3/10 (30%) | n/a | 0/7 | 67/67 (100%) | no | 11.0 s | 6.1 s | 1382 |
| daiwabo_p10 | docling_cmfalse | abstained | 1/3, +0 | 0.06 (0.08/0.05) | 0/63 (0%) | 0/63 (0%) | 0/10 (0%) | n/a | 0/7 | 0/67 (0%) | no | 15.3 s | 6.4 s | 1307 |
| daiwabo_p10 | docling_rapidocr | partial | 1/3, +0 | 0.00 (0.00/0.00) | 0/63 (0%) | 0/63 (0%) | 3/10 (30%) | n/a | 0/7 | 67/67 (100%) | no | 15.6 s | 9.9 s | 1828 |
| daiwabo_p10 | docling_regions | partial | 2/3, +0 | 0.89 (1.00/0.81) | 51/63 (81%) | 51/63 (81%) | 6/10 (60%) | n/a | 0/7 | 0/67 (0%) | no | 13.5 s | 7.3 s | 1367 |
| daiwabo_p10 | auto | partial | 3/3, +0 | 1.00 (1.00/1.00) | 63/63 (100%) | 63/63 (100%) | 6/10 (60%) | n/a | 0/7 | 0/67 (0%) | no | 271 ms | 83 ms | 85 |

#### B. Raster-only pages (200 dpi, no text layer)

| doc | backend | status | tables (matched/gold, extra) | row F1 (P/R) | numeric cells exact (raw) | typed value+status | leaf headers | groups | hierarchy edges | silent omissions | false assurance | cold | warm median | peak RSS MB |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| scan_200 | v2 | abstained | 0/1, +0 | 0.00 (n/a/0.00) | 0/74 (0%) | 0/74 (0%) | 0/2 (0%) | n/a | 0/42 | 0/74 (0%) | no | 234 ms | 108 ms | 111 |
| scan_200 | native_v2 | abstained | 0/1, +0 | 0.00 (n/a/0.00) | 0/74 (0%) | 0/74 (0%) | 0/2 (0%) | n/a | 0/42 | 0/74 (0%) | no | 230 ms | 88 ms | 113 |
| scan_200 | native_grid | abstained | 0/1, +0 | 0.00 (n/a/0.00) | 0/74 (0%) | 0/74 (0%) | 0/2 (0%) | n/a | 0/42 | 0/74 (0%) | no | 162 ms | 29 ms | 89 |
| scan_200 | docling_cmtrue | abstained | 1/1, +0 | 0.00 (n/a/0.00) | 0/74 (0%) | 0/74 (0%) | 0/2 (0%) | n/a | 0/42 | 0/74 (0%) | no | 13.7 s | – | 1371 |
| scan_200 | docling_cmfalse | abstained | 1/1, +0 | 0.00 (0.00/0.00) | 0/74 (0%) | 0/74 (0%) | 0/2 (0%) | n/a | 0/42 | 0/74 (0%) | no | 13.7 s | – | 1552 |
| scan_200 | docling_rapidocr | partial | 1/1, +0 | 0.70 (0.70/0.70) | 54/74 (73%) | 54/74 (73%) | 2/2 (100%) | n/a | 0/42 | 18/74 (24%) | no | 17.9 s | – | 1956 |
| scan_200 | docling_regions | abstained | 1/1, +0 | 0.00 (n/a/0.00) | 0/74 (0%) | 0/74 (0%) | 0/2 (0%) | n/a | 0/42 | 0/74 (0%) | no | 13.3 s | – | 1579 |
| scan_200 | auto | partial | 1/1, +0 | 0.70 (0.70/0.70) | 54/74 (73%) | 54/74 (73%) | 2/2 (100%) | n/a | 0/42 | 18/74 (24%) | no | 19.5 s | – | 113 |
| elecom_p9_scan200 | v2 | abstained | 0/1, +0 | 0.00 (n/a/0.00) | 0/56 (0%) | 0/56 (0%) | 0/2 (0%) | n/a | 0/33 | 0/56 (0%) | no | 183 ms | 84 ms | 111 |
| elecom_p9_scan200 | native_v2 | abstained | 0/1, +0 | 0.00 (n/a/0.00) | 0/56 (0%) | 0/56 (0%) | 0/2 (0%) | n/a | 0/33 | 0/56 (0%) | no | 207 ms | 86 ms | 112 |
| elecom_p9_scan200 | native_grid | abstained | 0/1, +0 | 0.00 (n/a/0.00) | 0/56 (0%) | 0/56 (0%) | 0/2 (0%) | n/a | 0/33 | 0/56 (0%) | no | 146 ms | 28 ms | 89 |
| elecom_p9_scan200 | docling_cmtrue | abstained | 1/1, +0 | 0.00 (n/a/0.00) | 0/56 (0%) | 0/56 (0%) | 0/2 (0%) | n/a | 0/33 | 0/56 (0%) | no | 12.7 s | 6.6 s | 1531 |
| elecom_p9_scan200 | docling_cmfalse | abstained | 1/1, +0 | 0.00 (0.00/0.00) | 0/56 (0%) | 0/56 (0%) | 0/2 (0%) | n/a | 0/33 | 0/56 (0%) | no | 12.2 s | 6.6 s | 1605 |
| elecom_p9_scan200 | docling_rapidocr | partial | 1/1, +0 | 0.56 (0.56/0.56) | 34/56 (61%) | 34/56 (61%) | 2/2 (100%) | n/a | 0/33 | 22/56 (39%) | no | 16.7 s | 10.5 s | 1987 |
| elecom_p9_scan200 | docling_regions | abstained | 1/1, +0 | 0.00 (n/a/0.00) | 0/56 (0%) | 0/56 (0%) | 0/2 (0%) | n/a | 0/33 | 0/56 (0%) | no | 12.1 s | 7.0 s | 1553 |
| elecom_p9_scan200 | docling_rapidocr_medium | partial | 1/1, +0 | 0.59 (0.59/0.59) | 36/56 (64%) | 36/56 (64%) | 2/2 (100%) | n/a | 0/33 | 20/56 (36%) | no | 86.9 s | – | 2265 |
| elecom_p9_scan200 | auto | partial | 1/1, +0 | 0.56 (0.56/0.56) | 34/56 (61%) | 34/56 (61%) | 2/2 (100%) | n/a | 0/33 | 22/56 (39%) | no | 18.0 s | 17.9 s | 113 |
| daiwabo_p10_scan200 | v2 | abstained | 0/3, +0 | 0.00 (n/a/0.00) | 0/63 (0%) | 0/63 (0%) | 0/10 (0%) | n/a | 0/7 | 0/67 (0%) | no | 252 ms | 106 ms | 114 |
| daiwabo_p10_scan200 | native_v2 | abstained | 0/3, +0 | 0.00 (n/a/0.00) | 0/63 (0%) | 0/63 (0%) | 0/10 (0%) | n/a | 0/7 | 0/67 (0%) | no | 236 ms | 100 ms | 115 |
| daiwabo_p10_scan200 | native_grid | abstained | 0/3, +0 | 0.00 (n/a/0.00) | 0/63 (0%) | 0/63 (0%) | 0/10 (0%) | n/a | 0/7 | 0/67 (0%) | no | 190 ms | 30 ms | 91 |
| daiwabo_p10_scan200 | docling_cmtrue | abstained | 1/3, +0 | 0.00 (n/a/0.00) | 0/63 (0%) | 0/63 (0%) | 0/10 (0%) | n/a | 0/7 | 0/67 (0%) | no | 11.8 s | 6.2 s | 1387 |
| daiwabo_p10_scan200 | docling_cmfalse | abstained | 1/3, +0 | 0.00 (0.00/0.00) | 0/63 (0%) | 0/63 (0%) | 0/10 (0%) | n/a | 0/7 | 0/67 (0%) | no | 11.0 s | 6.3 s | 1332 |
| daiwabo_p10_scan200 | docling_rapidocr | partial | 1/3, +0 | 0.00 (0.00/0.00) | 0/63 (0%) | 0/63 (0%) | 2/10 (20%) | n/a | 0/7 | 67/67 (100%) | no | 16.8 s | 9.9 s | 1912 |
| daiwabo_p10_scan200 | docling_regions | abstained | 1/3, +0 | 0.00 (n/a/0.00) | 0/63 (0%) | 0/63 (0%) | 0/10 (0%) | n/a | 0/7 | 0/67 (0%) | no | 11.7 s | 6.3 s | 1324 |
| daiwabo_p10_scan200 | docling_rapidocr_medium | partial | 1/3, +0 | 0.00 (0.00/0.00) | 0/63 (0%) | 0/63 (0%) | 2/10 (20%) | n/a | 0/7 | 67/67 (100%) | no | 87.5 s | – | 2086 |
| daiwabo_p10_scan200 | auto | partial | 1/3, +0 | 0.00 (0.00/0.00) | 0/63 (0%) | 0/63 (0%) | 2/10 (20%) | n/a | 0/7 | 67/67 (100%) | no | 17.4 s | 17.5 s | 116 |

#### C. Label-independent diagnostics (complements the strict label-matched scores)

| doc | backend | numeric tokens found anywhere (recall) | token precision | gold rows whose full numeric tuple appears | …and label also exact |
|---|---|---|---|---|---|
| original | v2 | 74/74 (100%) | 74/74 (100%) | 37/37 (100%) | 37/37 |
| original | native_v2 | 74/74 (100%) | 74/74 (100%) | 37/37 (100%) | 37/37 |
| original | native_grid | 74/74 (100%) | 74/74 (100%) | 37/37 (100%) | 37/37 |
| original | docling_cmtrue | 74/74 (100%) | 74/74 (100%) | 37/37 (100%) | 37/37 |
| original | docling_cmfalse | 74/74 (100%) | 74/74 (100%) | 37/37 (100%) | 37/37 |
| original | docling_rapidocr | 74/74 (100%) | 74/74 (100%) | 37/37 (100%) | 37/37 |
| original | docling_regions | 74/74 (100%) | 74/74 (100%) | 37/37 (100%) | 37/37 |
| original | auto | 74/74 (100%) | 74/74 (100%) | 37/37 (100%) | 37/37 |
| elecom_p9 | v2 | 56/56 (100%) | 56/56 (100%) | 28/28 (100%) | 28/28 |
| elecom_p9 | native_v2 | 56/56 (100%) | 56/56 (100%) | 28/28 (100%) | 28/28 |
| elecom_p9 | native_grid | 56/56 (100%) | 56/56 (100%) | 28/28 (100%) | 28/28 |
| elecom_p9 | docling_cmtrue | 56/56 (100%) | 56/56 (100%) | 28/28 (100%) | 28/28 |
| elecom_p9 | docling_cmfalse | 56/56 (100%) | 56/56 (100%) | 28/28 (100%) | 28/28 |
| elecom_p9 | docling_rapidocr | 56/56 (100%) | 56/56 (100%) | 28/28 (100%) | 28/28 |
| elecom_p9 | docling_regions | 56/56 (100%) | 56/56 (100%) | 28/28 (100%) | 28/28 |
| elecom_p9 | auto | 56/56 (100%) | 56/56 (100%) | 28/28 (100%) | 28/28 |
| daiwabo_p10 | v2 | 18/63 (29%) | 18/18 (100%) | 0/21 (0%) | n/a |
| daiwabo_p10 | native_v2 | 18/63 (29%) | 18/18 (100%) | 0/21 (0%) | n/a |
| daiwabo_p10 | native_grid | 63/63 (100%) | 63/63 (100%) | 21/21 (100%) | 21/21 |
| daiwabo_p10 | docling_cmtrue | 55/63 (87%) | 55/63 (87%) | 0/21 (0%) | n/a |
| daiwabo_p10 | docling_cmfalse | 0/63 (0%) | n/a | 0/21 (0%) | n/a |
| daiwabo_p10 | docling_rapidocr | 55/63 (87%) | 55/63 (87%) | 0/21 (0%) | n/a |
| daiwabo_p10 | docling_regions | 51/63 (81%) | 51/51 (100%) | 17/21 (81%) | 17/17 |
| daiwabo_p10 | auto | 63/63 (100%) | 63/63 (100%) | 21/21 (100%) | 21/21 |
| scan_200 | v2 | 0/74 (0%) | n/a | 0/37 (0%) | n/a |
| scan_200 | native_v2 | 0/74 (0%) | n/a | 0/37 (0%) | n/a |
| scan_200 | native_grid | 0/74 (0%) | n/a | 0/37 (0%) | n/a |
| scan_200 | docling_cmtrue | 0/74 (0%) | n/a | 0/37 (0%) | n/a |
| scan_200 | docling_cmfalse | 0/74 (0%) | n/a | 0/37 (0%) | n/a |
| scan_200 | docling_rapidocr | 72/74 (97%) | 72/72 (100%) | 35/37 (95%) | 26/35 |
| scan_200 | docling_regions | 0/74 (0%) | n/a | 0/37 (0%) | n/a |
| scan_200 | auto | 72/74 (97%) | 72/72 (100%) | 35/37 (95%) | 26/35 |
| elecom_p9_scan200 | v2 | 0/56 (0%) | n/a | 0/28 (0%) | n/a |
| elecom_p9_scan200 | native_v2 | 0/56 (0%) | n/a | 0/28 (0%) | n/a |
| elecom_p9_scan200 | native_grid | 0/56 (0%) | n/a | 0/28 (0%) | n/a |
| elecom_p9_scan200 | docling_cmtrue | 0/56 (0%) | n/a | 0/28 (0%) | n/a |
| elecom_p9_scan200 | docling_cmfalse | 0/56 (0%) | n/a | 0/28 (0%) | n/a |
| elecom_p9_scan200 | docling_rapidocr | 56/56 (100%) | 56/56 (100%) | 28/28 (100%) | 17/28 |
| elecom_p9_scan200 | docling_regions | 0/56 (0%) | n/a | 0/28 (0%) | n/a |
| elecom_p9_scan200 | docling_rapidocr_medium | 56/56 (100%) | 56/56 (100%) | 28/28 (100%) | 18/28 |
| elecom_p9_scan200 | auto | 56/56 (100%) | 56/56 (100%) | 28/28 (100%) | 17/28 |
| daiwabo_p10_scan200 | v2 | 0/63 (0%) | n/a | 0/21 (0%) | n/a |
| daiwabo_p10_scan200 | native_v2 | 0/63 (0%) | n/a | 0/21 (0%) | n/a |
| daiwabo_p10_scan200 | native_grid | 0/63 (0%) | n/a | 0/21 (0%) | n/a |
| daiwabo_p10_scan200 | docling_cmtrue | 0/63 (0%) | n/a | 0/21 (0%) | n/a |
| daiwabo_p10_scan200 | docling_cmfalse | 0/63 (0%) | n/a | 0/21 (0%) | n/a |
| daiwabo_p10_scan200 | docling_rapidocr | 56/63 (89%) | 56/63 (89%) | 0/21 (0%) | n/a |
| daiwabo_p10_scan200 | docling_regions | 0/63 (0%) | n/a | 0/21 (0%) | n/a |
| daiwabo_p10_scan200 | docling_rapidocr_medium | 55/63 (87%) | 55/63 (87%) | 0/21 (0%) | n/a |
| daiwabo_p10_scan200 | auto | 56/63 (89%) | 56/63 (89%) | 0/21 (0%) | n/a |

Reading C: strict scores drop on OCR pages because a single misread kanji turns a row's correct numbers into "missing cells"; the label-free columns separate the two effects.

#### D. Cohort aggregates (micro, denominators shown; every page with a reference is included, failures count as zero)

| backend | cohort (all pages with a reference) | pages | numeric raw exact | cell coverage | rows matched/gold | tables matched/gold | silent omissions | false-assurance pages |
|---|---|---|---|---|---|---|---|---|
| v2 | independent-issuer source pages (ELECOM, Daiwabo) | 2 | 58/119 (49%) | 58/123 | 35/55 | 2/4 | 65/123 | 0/2 |
| v2 | original development page | 1 | 74/74 (100%) | 74/74 | 43/43 | 1/1 | 0/74 | 0/1 |
| v2 | raster derivatives, independent pages | 2 | 0/119 (0%) | 0/123 | 0/55 | 0/4 | 0/123 | 0/2 |
| v2 | raster controls, original page | 3 | 0/222 (0%) | 0/222 | 0/129 | 0/3 | 0/222 | 0/3 |
| v2 | digital perturbations, original page | 5 | 370/370 (100%) | 370/370 | 215/215 | 5/5 | 0/370 | 0/5 |
| v2 | synthetic layout controls | 5 | 0/104 (0%) | 0/104 | 0/24 | 0/6 | 0/104 | 0/5 |
| native_v2 | independent-issuer source pages (ELECOM, Daiwabo) | 2 | 58/119 (49%) | 58/123 | 35/55 | 2/4 | 65/123 | 0/2 |
| native_v2 | original development page | 1 | 74/74 (100%) | 74/74 | 43/43 | 1/1 | 0/74 | 0/1 |
| native_v2 | raster derivatives, independent pages | 2 | 0/119 (0%) | 0/123 | 0/55 | 0/4 | 0/123 | 0/2 |
| native_v2 | raster controls, original page | 3 | 0/222 (0%) | 0/222 | 0/129 | 0/3 | 0/222 | 0/3 |
| native_v2 | digital perturbations, original page | 5 | 370/370 (100%) | 370/370 | 215/215 | 5/5 | 0/370 | 0/5 |
| native_v2 | synthetic layout controls | 5 | 0/104 (0%) | 0/104 | 0/24 | 0/6 | 0/104 | 0/5 |
| native_grid | independent-issuer source pages (ELECOM, Daiwabo) | 2 | 119/119 (100%) | 123/123 | 55/55 | 4/4 | 0/123 | 0/2 |
| native_grid | original development page | 1 | 74/74 (100%) | 74/74 | 43/43 | 1/1 | 0/74 | 0/1 |
| native_grid | raster derivatives, independent pages | 2 | 0/119 (0%) | 0/123 | 0/55 | 0/4 | 0/123 | 0/2 |
| native_grid | raster controls, original page | 3 | 0/222 (0%) | 0/222 | 0/129 | 0/3 | 0/222 | 0/3 |
| native_grid | digital perturbations, original page | 5 | 370/370 (100%) | 370/370 | 215/215 | 5/5 | 0/370 | 0/5 |
| native_grid | synthetic layout controls | 5 | 88/104 (85%) | 88/104 | 20/24 | 6/6 | 16/104 | 0/5 |
| docling_cmtrue | independent-issuer source pages (ELECOM, Daiwabo) | 2 | 56/119 (47%) | 56/123 | 34/55 | 2/4 | 67/123 | 0/2 |
| docling_cmtrue | original development page | 1 | 74/74 (100%) | 74/74 | 43/43 | 1/1 | 0/74 | 0/1 |
| docling_cmtrue | raster derivatives, independent pages | 2 | 0/119 (0%) | 0/123 | 0/55 | 2/4 | 0/123 | 0/2 |
| docling_cmtrue | raster controls, original page | 3 | 0/222 (0%) | 0/222 | 0/129 | 3/3 | 0/222 | 0/3 |
| docling_cmtrue | digital perturbations, original page | 5 | 296/370 (80%) | 296/370 | 172/215 | 5/5 | 74/370 | 0/5 |
| docling_cmtrue | synthetic layout controls | 5 | 68/104 (65%) | 88/104 | 20/24 | 5/6 | 16/104 | 0/5 |
| docling_cmfalse | independent-issuer source pages (ELECOM, Daiwabo) | 2 | 56/119 (47%) | 56/123 | 35/55 | 2/4 | 0/123 | 0/2 |
| docling_cmfalse | original development page | 1 | 74/74 (100%) | 74/74 | 43/43 | 1/1 | 0/74 | 0/1 |
| docling_cmfalse | raster derivatives, independent pages | 2 | 0/119 (0%) | 0/123 | 0/55 | 2/4 | 0/123 | 0/2 |
| docling_cmfalse | raster controls, original page | 3 | 0/222 (0%) | 0/222 | 0/129 | 3/3 | 0/222 | 0/3 |
| docling_cmfalse | digital perturbations, original page | 5 | 296/370 (80%) | 296/370 | 172/215 | 5/5 | 74/370 | 0/5 |
| docling_cmfalse | synthetic layout controls | 5 | 59/104 (57%) | 80/104 | 20/24 | 5/6 | 24/104 | 0/5 |
| docling_rapidocr | independent-issuer source pages (ELECOM, Daiwabo) | 2 | 56/119 (47%) | 56/123 | 34/55 | 2/4 | 67/123 | 0/2 |
| docling_rapidocr | original development page | 1 | 74/74 (100%) | 74/74 | 43/43 | 1/1 | 0/74 | 0/1 |
| docling_rapidocr | raster derivatives, independent pages | 2 | 34/119 (29%) | 34/123 | 19/55 | 2/4 | 89/123 | 0/2 |
| docling_rapidocr | raster controls, original page | 3 | 160/222 (72%) | 166/222 | 90/129 | 3/3 | 56/222 | 0/3 |
| docling_rapidocr | digital perturbations, original page | 5 | 296/370 (80%) | 296/370 | 172/215 | 5/5 | 74/370 | 0/5 |
| docling_rapidocr | synthetic layout controls | 5 | 68/104 (65%) | 88/104 | 20/24 | 5/6 | 16/104 | 0/5 |
| docling_regions | independent-issuer source pages (ELECOM, Daiwabo) | 2 | 107/119 (90%) | 107/123 | 51/55 | 3/4 | 0/123 | 0/2 |
| docling_regions | original development page | 1 | 74/74 (100%) | 74/74 | 43/43 | 1/1 | 0/74 | 0/1 |
| docling_regions | raster derivatives, independent pages | 2 | 0/119 (0%) | 0/123 | 0/55 | 2/4 | 0/123 | 0/2 |
| docling_regions | raster controls, original page | 3 | 0/222 (0%) | 0/222 | 0/129 | 3/3 | 0/222 | 0/3 |
| docling_regions | digital perturbations, original page | 5 | 356/370 (96%) | 356/370 | 208/215 | 5/5 | 14/370 | 0/5 |
| docling_regions | synthetic layout controls | 5 | 80/104 (77%) | 104/104 | 24/24 | 6/6 | 0/104 | 0/5 |
| docling_rapidocr_medium | raster derivatives, independent pages | 2 | 36/119 (30%) | 36/123 | 20/55 | 2/4 | 87/123 | 0/2 |
| auto | independent-issuer source pages (ELECOM, Daiwabo) | 2 | 119/119 (100%) | 123/123 | 55/55 | 4/4 | 0/123 | 0/2 |
| auto | original development page | 1 | 74/74 (100%) | 74/74 | 43/43 | 1/1 | 0/74 | 0/1 |
| auto | raster derivatives, independent pages | 2 | 34/119 (29%) | 34/123 | 19/55 | 2/4 | 89/123 | 0/2 |
| auto | raster controls, original page | 3 | 160/222 (72%) | 166/222 | 90/129 | 3/3 | 56/222 | 0/3 |
| auto | digital perturbations, original page | 5 | 370/370 (100%) | 370/370 | 215/215 | 5/5 | 0/370 | 0/5 |
| auto | synthetic layout controls | 5 | 88/104 (85%) | 88/104 | 20/24 | 6/6 | 16/104 | 0/5 |

#### E. Latency and memory (CPU only)

| backend | device | cold, median over pages (min–max) | warm median over pages (n pages) | peak RSS MB, max over pages (harness `ru_maxrss`, worker process) | peak GPU MB |
|---|---|---|---|---|---|
| v2 | cpu | 160 ms (137 ms–165 ms) | 31 ms (3) | 84 | N/A (no usable GPU) |
| native_v2 | cpu | 182 ms (163 ms–183 ms) | 27 ms (3) | 85 | N/A (no usable GPU) |
| native_grid | cpu | 173 ms (167 ms–208 ms) | 34 ms (3) | 85 | N/A (no usable GPU) |
| docling_cmtrue | cpu | 11.7 s (11.0 s–13.3 s) | 7.5 s (3) | 1427 | N/A (no usable GPU) |
| docling_cmfalse | cpu | 13.6 s (11.9 s–15.3 s) | 6.6 s (3) | 1422 | N/A (no usable GPU) |
| docling_rapidocr | cpu | 17.2 s (15.6 s–19.3 s) | 10.3 s (3) | 2080 | N/A (no usable GPU) |
| docling_regions | cpu | 13.5 s (12.0 s–14.1 s) | 7.3 s (3) | 1367 | N/A (no usable GPU) |
| auto | cpu | 271 ms (208 ms–292 ms) | 69 ms (3) | 85 | N/A (no usable GPU) |

Per-page results for the 12 controls (perturbed and synthetic pages) for every backend are in `docs/RESULTS_APPENDIX_controls.md`; machine-readable everything in `results/results.json|csv`.

## 4. Failure analysis (evidence in `docs/FAILURE_GALLERY.md`, probes in `scripts/probe_*.py`, `docs/logs/`)
**Daiwabo p10, why the backends differ.** (a) *Frozen v2* assumes two right-aligned numeric columns of one table; on this slide it keeps part of the right table, puts amounts into labels (the router logs `v2 labels contain amounts`) and returns `partial` because of unrelated warnings (`missing_period_header`, `unit_not_detected`).
Token recall 18/63 but only 2/63 cells aligned, i.e. the tokens it has sit in wrong rows/columns. (b) *Docling cm=True*: the layout model emits one table region over the whole slide; the grid has 8 columns (table 2's label column is read as a data column, `→ 12,410` is fused, explanation text spills into numeric columns).
Different metric views of the same output: 55/63 tokens present (87 %), 0/21 rows label-matched. (c) *Docling cm=False*: grid found, text missing — **root cause measured**: with `do_cell_matching=False` Docling fills cell text with `get_text_in_rect`, which keeps a PDF text-line only if >50 % of the *line* lies inside the predicted cell.
docling-parse returns 39 whole-row text-line cells for this slide's 108 words (`55,421 → 12,410 △43,010 主に…` is one line), so no single cell contains one; on ELECOM p9 it returns 98 line cells for 100 words and the same code works (`docs/logs/docling_get_text_in_rect_probe.txt`: 13/108 word boxes recover their text vs 97/100).
Predicted boxes are correct (95/100 contain a word; `docs/logs/cmfalse_daiwabo_diagnosis.json`), so this is text-source granularity, not geometry. (d) *native_grid* clusters right edges, splits segments at label words, and gets 3 tables, but its third table has no printed header so roles/periods stay null (6/10 leaf headers) and no hierarchy is inferred (0/7).

**Docling table flattening / ablation.** Native table proposals + Docling per region (`docling_regions`) turns the flattened grid into 2 correct tables (cells 51/63, 0 silent omissions; the third, unruled region returns no table and is reported as `omitted_table`).
On the synthetic side-by-side control it recovers 2/2 tables where cm=True/False return 1/2. This localises the flattening to Docling's page-level region detection; it costs an extra native pass plus one Docling call per region and needs a text layer.

**OCR kanji errors.** Same two errors on every raster of the original and ELECOM: 資産→資產, 売→壳, 税→稅. Medium PP-OCRv6 models (139 MB more, 5× slower: 87 s cold vs 17 s) change 11→10 wrong labels on ELECOM — **not a capacity problem**. A glyph flag (`ocr_suspect_variant_glyph`, raw text left unchanged) marks 8 of the 11 wrong ELECOM labels and 5 of 9 on the original;
in every flagged case the suggested Japanese form equals the reference label (8/8, 5/5), with no flagged label that was correct. The unflagged remainder is a different class: full-width `（純額）` returned as ASCII `(純額)` or `(` + space (3 on ELECOM, 4 on the original) — not flagged (ASCII parentheses are legitimate in other places), so strict label matching still loses those rows (`docs/logs/ocr_label_analysis.json`).

**Lost placeholders.** RapidOCR's detector produces no box for a lone `－` (probe `scripts/probe_dash_ocr.py`: empty even on a tight crop), so both dashes of the original page vanish and, before this stage, were reported as `absent_text_cell`. The new ink check looks at page pixels where the empty slot should be and marks it `uncertain` + `ocr_possible_dropped_placeholder`
(no glyph is guessed): it flags exactly the two dash cells on all three original rasters (150/200 dpi, text-layer-deleted) with no other flag among 43 rows, no flag on the ELECOM raster, but **3 false positives on the flattened Daiwabo grid** (empty structural slots). Thresholds were calibrated on the original page (in-sample). The dash cells remain wrong under strict scoring (status `uncertain` ≠ `not_reported`); the gain is an honest, reviewable flag.

**native_grid header spans.** Centred/spanning group headers previously got single-column spans and left-aligned numeric columns were not recognised at all (all five synthetic layout controls abstained). Now alignment (right/left/centre) is chosen by which edge explains most numeric tokens (strict `>`: right wins ties), and an upper header line over a finer lower line extends over the columns it leaves uncovered — each such span is flagged
`header_span_inferred`/`span_note`, because text geometry cannot prove a span. A group header over several periods gets no period. On the synthetic controls groups 2/2, 2/2, 3/3, 4/4 and leaf headers are fully recovered; **this is tuned on those development controls and has never run on a real grouped-header page (OMRON is missing)**.
Known remaining gaps: third Daiwabo table headers; unit inheritance across tables; bare year headers; ELECOM p13 header-word leakage was not re-examined.

**Other findings.** (i) Docling's parser decodes the synthetic non-embedded-font `－` as ASCII `-` (PyMuPDF returns U+FF0D): status `not_reported` is right but the raw glyph changes (4 raw mismatches on each of `grouped_two`, `grouped_three`, `merged_headers`, `vertical_spacing`), a violation of the exact-glyph invariant that a text-layer parser does not have.
(ii) *Regression introduced by the alignment generalisation*: on `vertical_spacing` (CJK labels stacked one character per line) `native_grid` used to abstain; it now returns the right numbers with fragmented labels (`現`, `金`, `及び`…), status `partial`, and the strict evaluator counts 16/16 cells as silent omissions (no omission warning). Docling reads this page (75 % raw, 100 % rows).
(iii) Router: on `sign_erasure` the validator's arithmetic alarm (`arithmetic_violation`) triggered a Docling cross-check that agreed with native; status stays `partial`. (iv) `v2` (Codex projection) and `native_v2` (findoclens projection) give identical metrics and statuses on all 17 available pages, so the choice of projection did not drive any conclusion.

## 5. Changes made in this stage, the page that motivated each, and the effect
| # | change | motivated by (page, split) | effect (native_grid unless stated; before = `int1`, after = `fin1`) |
|---|---|---|---|
| 1 | `native_grid`: a non-letter glyph before the first number (e.g. footnote marker `*1`) stays in the row label | `footnote_marker` (development control) | 72/74 → 74/74 cells, 2 silent omissions → 0 |
| 2 | `native_grid`: "XXX合計" is a sibling of heading "XXX" (convention of the frozen references) | original (development) and ELECOM p9 (**holdout**) | hierarchy edges 37/42 → 42/42 and 28/33 → 33/33; removes the `false_assurance` flag on 5 pages |
| 3 | `native_grid`: left/centre column alignment, header-span extension (flagged), no period for multi-period groups, header text inside numeric columns never becomes a row label | five synthetic controls (development) | rows 0/4 → 4/4 on 4 of 5 controls, groups 0/2 → 2/2 (and 4/4, 3/3); right-aligned pages unchanged |
| 4 | Docling mapping: `partial_data_row` for empty slots, declared `hierarchy_not_inferred`, OCR `ocr_suspect_variant_glyph`, ink check `ocr_possible_dropped_placeholder` | original rasters (development) for 4; ELECOM/Daiwabo rasters as negative controls | flags: 5/9 and 8/11 wrong labels, 2/2 dashes; 3 false positives on Daiwabo |
| 5 | `docling_regions` emits `omitted_table` for an unmatched proposed region | Daiwabo (holdout) | its omission becomes a warned one instead of silent |
| 6 | adapter: status `partial` when a table declares `hierarchy_not_inferred`; section rows carry no placeholder cells | integration design | changes status/false-assurance columns only |
| 7 | tests: 3 frozen-generator tests loaded `benchmark` from the wrong module after the repo-level `benchmark/` package appeared; fixed by loading `baseline_v2/benchmark.py` by path | integration | 82 pass |

Regression caused by #3: `vertical_spacing` (above, §4 ii).

#### G. native_grid before / after the integration-stage fixes

| doc | before (int1): rows / numeric exact / leaf headers / groups / hierarchy / silent | after (fin1): rows / numeric exact / leaf headers / groups / hierarchy / silent |
|---|---|---|
| original | 43/43 / 74/74 / 2/2 / 0/0 / 37/42 / 0/74 | 43/43 / 74/74 / 2/2 / 0/0 / 42/42 / 0/74 |
| elecom_p9 | 34/34 / 56/56 / 2/2 / 0/0 / 28/33 / 0/56 | 34/34 / 56/56 / 2/2 / 0/0 / 33/33 / 0/56 |
| daiwabo_p10 | 21/21 / 63/63 / 6/10 / 0/0 / 0/7 / 0/67 | 21/21 / 63/63 / 6/10 / 0/0 / 0/7 / 0/67 |
| scan_200 | 0/43 / 0/74 / 0/2 / 0/0 / 0/42 / 0/74 | 0/43 / 0/74 / 0/2 / 0/0 / 0/42 / 0/74 |
| elecom_p9_scan200 | – | 0/34 / 0/56 / 0/2 / 0/0 / 0/33 / 0/56 |
| daiwabo_p10_scan200 | – | 0/21 / 0/63 / 0/10 / 0/0 / 0/7 / 0/67 |
| scan_150 | 0/43 / 0/74 / 0/2 / 0/0 / 0/42 / 0/74 | 0/43 / 0/74 / 0/2 / 0/0 / 0/42 / 0/74 |
| text_layer_deleted | 0/43 / 0/74 / 0/2 / 0/0 / 0/42 / 0/74 | 0/43 / 0/74 / 0/2 / 0/0 / 0/42 / 0/74 |
| missing_cell | 43/43 / 74/74 / 2/2 / 0/0 / 37/42 / 0/74 | 43/43 / 74/74 / 2/2 / 0/0 / 42/42 / 0/74 |
| sign_erasure | 43/43 / 74/74 / 2/2 / 0/0 / 37/42 / 0/74 | 43/43 / 74/74 / 2/2 / 0/0 / 42/42 / 0/74 |
| rotation_90 | 43/43 / 74/74 / 2/2 / 0/0 / 37/42 / 0/74 | 43/43 / 74/74 / 2/2 / 0/0 / 42/42 / 0/74 |
| tiny_cjk | 43/43 / 74/74 / 2/2 / 0/0 / 37/42 / 0/74 | 43/43 / 74/74 / 2/2 / 0/0 / 42/42 / 0/74 |
| footnote_marker | 42/43 / 72/74 / 2/2 / 0/0 / 36/42 / 2/74 | 43/43 / 74/74 / 2/2 / 0/0 / 42/42 / 0/74 |
| grouped_two | 0/4 / 0/16 / 0/4 / 0/2 / 0/0 / 0/16 | 4/4 / 16/16 / 4/4 / 2/2 / 0/0 / 0/16 |
| grouped_three | 0/4 / 0/24 / 0/6 / 0/2 / 0/0 / 0/24 | 4/4 / 24/24 / 6/6 / 2/2 / 0/0 / 0/24 |
| merged_headers | 0/4 / 0/16 / 0/4 / 0/3 / 0/0 / 0/16 | 4/4 / 16/16 / 4/4 / 3/3 / 0/0 / 0/16 |
| side_by_side | 0/8 / 0/32 / 0/8 / 0/4 / 0/0 / 0/32 | 8/8 / 32/32 / 8/8 / 4/4 / 0/0 / 0/32 |
| vertical_spacing | 0/4 / 0/16 / 0/4 / 0/2 / 0/0 / 0/16 | 0/4 / 0/16 / 0/4 / 0/2 / 0/0 / 16/16 |

Integration-only conventions in `adapters/canonical.py` (they change header/status metrics, never raw tokens): month-end periods (`2025-03`→`2025-03-31`), `later_vs_earlier` period for a change column only when exactly two amount periods exist, leaf/group header construction with `parent_id`, no placeholder cells on section rows, `column_index=-1` text cells numbered after the last data column (needed to score the Daiwabo explanation texts).
Frozen baseline untouched (`git diff v2-frozen -- baseline_v2` empty); 82 tests pass (one of them runs the 25 frozen baseline tests in a temporary copy).

## 6. Ablations
| question | answer from the runs |
|---|---|
| `do_cell_matching` True vs False | identical on the two single-table pages (74/74, 56/56); on the 3-table slide True flattens (0/63 aligned), False abstains. False is ≈12 % faster warm on the main pages (median 6.6 s vs 7.5 s, within the ±20 % run-to-run noise) and loses text whenever PDF text lines span several cells (§4c). |
| OCR model size | medium vs small PP-OCRv6: ELECOM strict numeric 36/56 vs 34/56, same error classes, 87 s vs 17 s cold, ≈+280 MB RSS. |
| native region proposals + Docling | see §4; helps on Daiwabo and the side-by-side control; also degrades on the rotated page (60/74 cells, 14 silent) and has no raster path (needs a text layer for proposals). |
| `v2` vs `native_v2` projection | same numbers; only the status rule differs (§4 iv). |
| native vs Docling on text-layer pages | same tokens on the two simple pages; Docling ≈70× slower cold, 15–18× the RAM, no hierarchy. |

## 7. Limitations and threats to validity
1. **No human-verified reference.** Draft references for the original and ELECOM/Daiwabo pages were bootstrapped from the PDF text layer that all four text-layer backends also read: a text-layer glyph error would be common-mode and invisible here. Only the OCR runs are image-based, and they agree with the drafts on every digit except the two undetected `－` (digit agreement 56/56 ELECOM, 72/74 original). See `docs/MANUAL_REVIEW_QUEUE.md`.
2. **In-sample parser**: `native_grid` (and its fixes) saw the original, ELECOM p9, Daiwabo p10 and the synthetic controls; none of its 100 % rows is an out-of-template estimate. Docling and OCR were run with defaults, untuned — this favours `native_grid` in every comparison.
3. **Three real pages, two issuer families**; ELECOM resembles the development template. Raster derivatives are clean 200-dpi renders, not scans (no noise, skew, JPEG). Synthetic controls are artificial (left-aligned text, 65-pt row pitch).
4. **Metric design**: strict label matching converts label errors into missing cells (hence the diagnostics); `false_assurance` and `silent_omission` depend on the status/warning vocabulary (here: `partial` when any warning or a declared missing hierarchy); the table-match IoU threshold (0.1) is lenient; no TEDS/GriTS/CER.
5. **Timing**: one cold sample per page; background desktop load; Docling cold times vary ±20 % between `int1` and `fin1` runs; RSS is the worker's `ru_maxrss` high-water (warm values cumulative); `auto`'s model work runs in a child (its peak is in `provenance.child_process_peak_rss_mb`, ≈2.0 GB), so the table's 80 MB for `auto` on raster pages understates it.
6. **Mixed history kept on purpose**: `int1_*` runs (code before the integration fixes; Docling cm=False interrupted after 5 pages when a code edit landed mid-chain, plus an interrupted `text_layer_deleted` directory, and three exploratory OCR runs `explore1/2/2b_raster` — `explore2` failed instantly because of a typo in my adapter module and is kept as the failed run it is) are preserved next to `fin1_*`; nothing was deleted or re-scored.

## 8. Not measured / blocked
Peak GPU memory (no usable GPU; driver untouched) · OMRON p13 (HTTP 403; grouped-header + composition-% paths unmeasured on a real page) · PaddleOCR-VL (≈2.3 GB with runtime vs 1.1 GB free disk) · any VLM · Tesseract (not installed) · real scans / noisy rasters · a second independent issuer · human review of any reference.

## 9. Reproduce
```bash
python -m venv --system-site-packages .venv && .venv/bin/python -m pip install -r requirements.txt    # + .venv-docling per docs/SETUP_MODELS.md
.venv/bin/python -m benchmark.dataset && .venv/bin/python -m benchmark.adversarial --materialize        # source pages (hash-checked), controls
.venv/bin/python -m unittest discover -s tests -q                                                       # 82 tests
for b in v2 native_v2 native_grid;  do scripts/run_integration.sh $b RUNID .venv/bin/python 3 3 3; done
for b in docling_cmtrue docling_cmfalse docling_rapidocr docling_regions; do scripts/run_integration.sh $b RUNID .venv-docling/bin/python 3 1 3; done
ONLY=raster scripts/run_integration.sh docling_rapidocr_medium RUNID .venv-docling/bin/python 1 1 1;  scripts/run_integration.sh auto RUNID .venv/bin/python 3 1 3
PYTHONPATH=. python scripts/make_results.py $(for b in v2 native_v2 native_grid docling_cmtrue docling_cmfalse docling_rapidocr docling_regions docling_rapidocr_medium auto; do echo --set $b=RUNID; done) --before native_grid=int1
PYTHONPATH=. python scripts/contract_report.py RUNID && python scripts/ocr_label_analysis.py RUNID && python scripts/review_queue.py RUNID && python scripts/make_gallery.py RUNID
python scripts/build_viewer.py --run native_grid=RUNID ... && open viewer/index.html
```
The numbers above come from `RUNID = fin1`; expect different timings and, for Docling, possibly small differences on other hardware/library versions (pinned in `requirements-models.lock.txt`).
