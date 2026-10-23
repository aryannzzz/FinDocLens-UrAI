# V3 declaration recording and reproducibility evidence

Implementation commit: `d4d750b`. The following evidence tests that committed code. It does not perform human verification; the human source-review basis is the project author's explicit declaration in `review/human_signoff/declaration_v3.json`.

- `reproducibility.json`: exact commands, exit codes, 165-test result (including the check that runs the 25 frozen baseline tests), package/device metadata, changed-file list, source-export and reference locks. No inference/downloads. CPU/GPU inference memory is not claimed.
- `tests_full.log`: 165 passed in 11.663s.
- `checks.log`: v3 check/replay/report/asset validation, historical v2 replay, original frozen/AI-reference/split validation, empty diffs for protected history and parser outputs/code, whitespace check. All nine commands exited zero.
- `final_browser_http.json`, `final_browser_file.json`: final committed-code Chrome smoke tests. Each verifies all three actual source images and their dimensions, source zoom/highlight, Japanese row/dash inspection, 197/197 accepted restoration, JSON download with all 197 accepted cells and declaration binding, absence of invented per-cell inspection times, preservation of the earlier draft namespace, and persistence of a later draft edit. HTTP additionally blocks an image and checks a visible error/disabled decisions. Actual PNG screenshots are local and ignored by Git; tests can regenerate them without models or downloads.
- `browser_http.json`, `browser_file.json`: preliminary passing checks during implementation. Their `git_commit` is the then-parent revision, not a claim that the unfinished worktree was committed there. Use the `final_` reports, which additionally pin tested-file hashes, as evidence for the finished code.
- `SHA256.json`: evidence file hashes. Declaration/reference/result locks are separate.

Sources loaded: original PDF page 1 (`original_page.png`, 1654×2339), ELECOM PDF page 9 (`elecom_p9_page.png`, 1654×2339), Daiwabo PDF page 10 (`daiwabo_p10_page.png`, 2667×1500), all at 200 dpi. The author declaration covers 74+56+67=197 existing contents. UI automation inspected display/asset functionality only and created no source-review certification.

The review server was tested using `.venv/bin/python -m benchmark.review --serve --port 8765`, at `http://127.0.0.1:8765/benchmark/review/index.html`. Start it from the repository root whenever reopening. Cached source PDFs are required; a checkout does not include ignored source images. Existing images are reused/checked and generated only as needed from those cached PDFs.

No previous predictions, measurements, original AI gold, v1/v2 snapshots, exported decisions, old ledgers, `findoclens/`, `adapters/` or frozen baseline were modified. Full-table structure, inferred periods and blind generalization remain unverified. Remaining applicant/research requirements are in `docs/SUBMISSION_STATUS.md`.
