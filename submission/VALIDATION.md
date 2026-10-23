# Final delivery validation

Implementation/V3 freeze: `9a6ebcb`. This document distinguishes local source-backed verification from a rights-conscious archive without added issuer PDF assets.

- Frozen workspace: **170 tests passed** (165 existing + 5 delivery guards), including the subprocess that runs all 25 original baseline tests. No parser/backend/evaluator or frozen snapshot changed.
- Documented offline subset: **90 tests passed**, including the frozen subprocess, benchmark/evaluator cases, adapters and P0 regression cases. No model dependency or added issuer PDF is needed.
- Native CLI: supplied original, one table / 43 rows / 74 financial contents, JSON + Markdown + evidence PNG. Auto with `--no-models` also completes and logs native routing. Exact glyph/status checks are part of verification; smoke runs are separate from benchmark results.
- Offline V3 replay: all original/V1/V2/V3 locks, original export/declaration and 48 stored prediction/report/aggregate comparisons pass. Financial/text denominator is 193+4=197 per backend/selection.
- Source restoration: cache-only verification passes against existing selected PDFs; missing/corrupt cache tests reject rather than download or overwrite. The optional explicit `--fetch` path was not invoked for delivery.
- Report: a two-page PDF and standalone HTML accompany the Markdown; first-page rendering and PDF text were inspected. No third-party renderer/model installation was required.

Preview ZIP validation from a fresh directory outside the repository:

- Read-only offline package integrity/V3 replay and CLI output passed; the CLI's original-page contents matched 74/74, with the expected Markdown glyphs and nonempty evidence PNG.
- Chrome loaded every image and all **35 backend views** across five portable pages, tested evidence clicks/zoom, Markdown, JSON, warnings and explicitly labeled historical metrics, with no JavaScript exceptions.
- After local-cache restoration of selected issuer pages, source hashes, 13 original/synthetic controls, two issuer rasters, full V3 import/scoring replay, report reproduction and source-review assets passed without downloads/inference.
- The clean extraction ran **170 tests: 163 passed, 7 optional legacy full-filing tests skipped** because those tests use full `data/pdfs/` filings rather than the restored one-page inputs. The workspace has the full filings and passed **170/170**. This asset distinction is documented in `START_HERE.md`.
- The 90-test offline subset passes without skips after the documented original-control materialization step.

Final archive checks are repeated from its committed build. The final external receipt records the ZIP checksum, exact commands/counts and build commit; `submission/BUILD.json` and `PACKAGE_MANIFEST.json` inside the ZIP identify its source commit and payload hashes. Full transcripts remain mandatory separate attachments, not claimed as present.

No inference, source/weight downloads, new experiments or parser changes were performed for final delivery. Historical CPU measurements are retained; no new GPU or performance claim is made.

The optional source-review Chrome checker initially failed without a Git checkout. Delivery changes are limited to that checker: it now reads `submission/BUILD.json` for revision provenance when `.git` is absent, covered by a dedicated regression. Core parser/adapters/evaluator remain unchanged. The CLI Markdown samples retain their exact generated trailing blank warning text; `.gitattributes` scopes whitespace checking for these raw samples rather than editing parser output.

After supplying the exact cached full PDFs by temporary local hardlinks (not inside the archive), the clean preview extraction also passes **170/170 tests with no skips**. The Git-less source-review browser checker passes with all three images, **197/197 accepted restoration**, JSON export, zoom, preserved earlier draft namespace and later draft-edit persistence. No archive member was replaced by a downloaded filing.
