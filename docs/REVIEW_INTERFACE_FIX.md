# Source review interface repair — 23 October 2026

**Open the working interface:** http://127.0.0.1:8765/benchmark/review/

From the repository root, start or restart it with:

```bash
cd /home/aryannzzz/ur_ai_RnD_agent_starter
.venv/bin/python -m benchmark.review --serve --port 8765
```

Keep that terminal running. If port 8765 is already serving this interface, use the existing URL. Ctrl+C stops the server. For a direct local file, first build with `.venv/bin/python -m benchmark.review`, then open `benchmark/review/index.html`.

**Exact root cause**

The integrated worktree at `bc9df9a` had the tracked `benchmark/review/index.html` and `audit_template.json`, but no `benchmark/review/assets/` directory. The old HTML referenced 103 embedded table/row images and three linked full pages, all absent here. `.gitignore` deliberately excludes those generated assets. They existed under `/home/aryannzzz/findoclens-codex/benchmark/review/assets/`, a separate Git worktree; ignored/generated files do not transfer with commits or worktree checkouts. Relative image paths were correct. Browser testing reproduced all 103 broken embedded images in the old tracked page with its absent assets; this was not caused by a `file://` restriction.

The old generator could render the missing files, but opening tracked HTML did not invoke it. There was no integrity gate, visible recovery message, or reliable documented startup path for a checkout with absent assets. The original full-page view was also only a link; annotations and source were difficult to compare.

**Modified files**

| Files | Change |
|---|---|
| `benchmark/review.py` | Build/check/serve CLI, localhost binding, preserved optional failure-sheet generation |
| `benchmark/review_site.py` (new) | Validate PDF/reference identity; generate/reuse only three source images; detect absent/corrupt/stale images, broken URLs, and altered embedded annotations |
| `benchmark/review_ui.html` (new) | Offline UI template: source beside annotations, row/cell/header highlights, zoom, decision fields, draft persistence, JSON download, explicit image errors |
| `benchmark/review/index.html` | Regenerated working interface with the original reference data embedded verbatim |
| `benchmark/review/audit_template.json` | Regenerated unreviewed scaffold with original values and source/reference/bbox identity; not a human review record |
| `benchmark/review/asset_manifest.json` (new) | Image/PDF/reference hashes and source page indexes for integrity checks |
| `tests/test_review_site.py` (new) | Six lightweight regressions for source identity, exact unchanged references, missing/corrupt images, wrong cached renderings, broken URLs and edited embedded values |
| `scripts/check_review_browser.py` (new) | Optional installed-Chrome smoke test using a disposable profile; no browser/model download |
| `README.md`, `benchmark/README.md`, `benchmark/review/README.md` | Correct launch command, URL, review workflow and asset lifecycle |
| This report and `runs/review_ui/source_review/20261023/` | Diagnosis, source identity proof, test logs, browser checks and run metadata |

The local images regenerated/verified are `benchmark/review/assets/{original,elecom_p9,daiwabo_p10}_page.png`. They remain ignored, as before, pending source redistribution review. Together they occupy **867,605 bytes** (about 860 KB filesystem usage). Disk space was checked before generation: **1.7 GB free on a 97 GB filesystem, 99% used**. It remained 1.7 GB free afterward. No PDFs or models were downloaded. Existing ELECOM/Daiwabo renderings were reused after comparison with freshly rendered selected-PDF bytes; original was rendered from its existing PDF. Row/cell crops now use a browser canvas instead of duplicating hundreds of images on disk.

**Source images actually verified**

| Document | Original source PDF page (one-based) | Local selected PDF page | Image dimensions |
|---|---:|---:|---:|
| Original | 1 | 1 | 1654 × 2339 |
| ELECOM | 9 (original index 8) | 1 | 1654 × 2339 |
| Daiwabo | 10 (original index 9) | 1 | 2667 × 1500 |

All three selected PDFs and full-source PDFs match the existing manifest hashes. At 200dpi, each generated image's RGB pixels equal the corresponding page in the full original PDF, and the selected PDF renders the same pixels. This independently checks page selection, not just HTML URLs or matching image dimensions. Reference tables embedded in the interface exactly equal the existing reference JSON. Evidence: `runs/review_ui/source_review/20261023/source_identity.json` and `benchmark/review/asset_manifest.json`.

**End-to-end checks**

- `.venv/bin/python -m unittest discover -s tests -v`: **133 tests passed**, including the subprocess run of all 25 frozen baseline tests; six new review regressions are included.
- `.venv/bin/python -m benchmark.validate`: **PASS**. Frozen source/reference hashes, completeness checks and source-family checks pass.
- `.venv/bin/python -m benchmark.review --check`: **PASS**. Missing images can also be reproduced and detected by the regression tests, without touching the real assets.
- Chrome 150 headless, HTTP: all three source images loaded with nonzero natural dimensions, selected cells contained visible source ink, source/detail zoom and region highlights worked, and a Japanese row label plus dash placeholder were inspected in screenshots.
- Chrome 150 headless, `file://`: all three images, zoom/highlight controls, draft restoration and JSON download also passed. There are no remote JS/CSS dependencies or `fetch()` calls.
- With an image deliberately blocked in the isolated test browser, the interface displayed a recovery message, cleared stale detail evidence, and disabled decisions for the unavailable source.
- JSON export downloaded `human_review_decisions.json` containing **197 cell entries**, all source/reference hashes and evidence coordinates, exact Japanese/monetary raw strings, and the selected decisions/notes. All three decision types were tested. The unreviewed dash retained `raw='－'`, `value=null`, `status='not_reported'`.

The browser test's three dummy decisions were explicitly named `AUTOMATED_UI_TEST_NOT_HUMAN`, stored only in a temporary browser profile, and deleted with the temporary download. They do not populate the user's browser or any human review record. The real generated scaffold still contains **197 unreviewed decisions**. No reference values, human verification counts, frozen baseline files, parser/evaluator code or existing benchmark results were changed. The pre-existing untracked `ur_ai_visual_audit/` directory was left untouched.

Detailed final browser evidence: `runs/review_ui/source_review/20261023/browser_http_complete.json` and `browser_file_complete.json`. Corresponding screenshots are local-only PNGs beside those reports. The old broken interface is captured as `browser_before.json` and `browser_before_broken.png`. `metadata.json` records commands, code hashes, package/browser versions, disk usage and the absence of model/GPU work.

**Remaining practical limits**

Images remain generated local assets, so a different checkout must run the launcher and have the cached PDFs available. Browser draft storage is specific to its profile and origin; export JSON before changing browsers, ports or machines. The interface never applies corrections or certifies the reference automatically. Human review and any later versioned correction process remain the applicant's responsibility.
