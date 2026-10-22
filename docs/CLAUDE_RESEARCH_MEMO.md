# Research memo — when does a model beat the text layer for Japanese financial tables? (track B)

**Question.** Is native PDF text fastest and most faithful on digital financial tables, failing only on raster pages or complex structure, so that
conditional model-backed structure/OCR can raise coverage without hurting source fidelity?

**What was built and run (CPU only, no GPU available).** Frozen v2 wrapped as a backend; a generalised text-layer parser (`native_grid`: N columns, several tables
per page, grouped headers by text extent, amount/%/delta roles, units, wrapped labels); Docling 2.141 TableFormer ACCURATE with `do_cell_matching` True/False;
Docling + RapidOCR (Japanese) for image-only pages; a rule-based router; a conservative validator; a common schema with evidence boxes per cell.
Pages: the original sample, ELECOM p9, Daiwabo p10 (digital) and 200-dpi image-only copies of each. OMRON could not be downloaded; PaddleOCR-VL-1.6 was not run
(preflight: ≥2.26 GB of downloads vs 1.86 GB free disk, no GPU). Metric: exact numeric strings versus the PDF text layer, so it is valid for digital pages and their rasterisations
and says nothing about labels or structure. Full tables: `CLAUDE_RESULTS.md`.

**Findings (all measured).**
1. *Speed and footprint.* Native: 13–48 ms warm, ≈100 MB. Docling CPU: 7–14 s warm, ≈1.4 GB. Docling + OCR: 14–16 s warm, ≈2.2 GB. Model cost is 2–3 orders of magnitude higher, so a router that only calls a model on demand is the sensible default.
2. *Fidelity on clean digital tables.* Native and Docling both reproduced all 74 and 56 numeric tokens (original, ELECOM) including `△`, and the one `△4`/`－` cases; `auto` took the native result without a model in 45–88 ms.
3. *Complex layout favoured the text layer here, not the model.* On the Daiwabo slide (three tables, `+`/`△` deltas, arrows, notes) frozen v2 returned `ok` with 18/63 tokens (silent partial extraction); Docling flattened three tables into one grid and lost 4/63 tokens, and with `cell_matching=False` returned a table with no text. The generalised native parser found 3 tables / 63 tokens. The router detected v2's failure (labels containing amounts, table-count mismatch) and treated Docling's differences as explained by the text layer.
4. *Raster pages.* All native backends failed closed (0 cells, explicit status). Docling without OCR found a table but no text (marked `failed`). Docling + RapidOCR recovered 72/74, 56/56, 59/63 numeric tokens with **no wrong digit**, but mis-read ≈20–35 % of kanji labels (産→產) and dropped 2 `－` placeholders; the router therefore returns `needs_visual_review`, never `ok`, for OCR-only output.
5. *Validator.* Delta, subtotal and assets = liabilities+equity checks passed or sat within the named rounding policy on all three pages; removing one `△` triggered an alarm; no value was ever modified.

**Verdict.** *Supported:* native text is fastest and exact on good digital tables; fails closed on raster; OCR adds coverage at 10³× latency with label-level errors a human must review.
*Not supported (on these pages):* that complex structure alone needs a model — the parser that models geometry explicitly beat Docling on the hardest page, though Docling remains the only candidate for pages whose text layer is absent or whose structure is not right-aligned numerics.
*Disagreement handling is the useful research direction:* the cheap disagreement signal (native vs checker vs text layer) correctly separated "checker is wrong" from "native may have omitted something", and that is where a selective crop re-run would pay off.

**Caveats that bound these claims.** (a) `native_grid` was designed while viewing these very pages: its holdout numbers are in-sample for design; Docling was untuned. (b) No human-verified gold: results are token-level against the text layer. (c) Three pages, one machine, same-source clean rasterisations (not scans). (d) OMRON (grouped headers, composition %, multi-line labels) is untested; `%`/composition logic exists but is unmeasured on a real page. (e) PaddleOCR-VL and any GPU result are absent, not negative.

**Next experiments (proposed, unrun).** OMRON and a second independent issuer scored by the Codex gold; noisy/skewed/JPEG scans; selective crop re-run triggered by disagreement; hierarchy inference for OCR output so that arithmetic checks can serve as second evidence; PP-StructureV3 / PaddleOCR-VL on hardware with ≥8 GB disk/RAM or a working GPU.
