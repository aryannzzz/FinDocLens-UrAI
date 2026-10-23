# Offline source annotation review

From `/home/aryannzzz/ur_ai_RnD_agent_starter`:

```bash
.venv/bin/python -m benchmark.review --serve --port 8765
```

Open **http://127.0.0.1:8765/benchmark/review/**. Keep the terminal running; Ctrl+C stops the server. It binds only to 127.0.0.1 and uses Python's standard HTTP server. No models, network downloads, or additional frontend dependencies are required. If the port is occupied, use `--port 8766` and the matching URL.

The launcher validates the selected PDF hashes against the manifest/reference identities, builds only three 200dpi page PNGs (about 860 KB total), then validates the generated interface and image hashes. Existing renderings are reused when they exactly match the selected PDF's rendering. Row and cell crops are drawn in the browser from those same source images; hundreds of duplicate crop files are unnecessary. Selected PDFs contain one page at index 0, corresponding to original page 1, ELECOM page 9, and Daiwabo page 10.

1. Select a document. Its source page, original page number, reference status, source/reference hashes and annotations are available in the interface.
2. Click a row label, raw value, table extent, or header. The left panel highlights the corresponding source region and shows a magnified detail. Use either zoom slider and scroll the source/detail panes. “Fit page width” returns to the top of the source; “Open image” and “Open selected PDF” provide independent full-size views.
3. The v3 author declaration restores all 197 accepted decisions and the reviewer name. Its banner distinguishes personally verified contents from unreviewed structure, with bulk recording and no invented per-cell clicks/times. For any later changes, select `accepted`, `correction_needed`, or `unreadable` per cell; review edits do not silently change the frozen v3 snapshot. Use the correction/reason field for proposed changes and scope notes for labels, hierarchy, headers, units and table boundaries. Reference values are read-only.
4. Export `human_review_decisions.json`. The export includes every cell's decision, exact original raw/value/status, source and reference hashes, original page index, table/row/column identity, and evidence bbox. Export records decisions only; it never edits gold or applies human verification counts. Browser drafts are keyed by reference/input hashes plus the v3 declaration hash (older drafts remain separately stored) and normally survive reload; the JSON download is your portable copy. No decisions are sent to the server.

To build without a server or check without writing:

```bash
.venv/bin/python -m benchmark.review
.venv/bin/python -m benchmark.review --check
```

After building, `/home/aryannzzz/ur_ai_RnD_agent_starter/benchmark/review/index.html` can also be opened directly. Scripts/data are embedded and images/PDF links are relative, so there is no `fetch()` or remote dependency that requires HTTP. Chrome was tested both ways; the localhost URL is recommended for consistent browser storage behavior.

**Why images previously disappeared:** the HTML and decision template were tracked, while `benchmark/review/assets/` was ignored. The integrated worktree contained no assets; the source worktree had them. A worktree switch or checkout copies tracked HTML, not ignored images. Relative paths were correct; the actual PNG files were absent. The old page had 103 broken embedded images and no asset-integrity guard. The new launcher repairs this from cached PDFs, `--check` fails on missing/stale evidence, and the browser shows a visible image error and disables decisions for unavailable evidence.

Tests:

```bash
.venv/bin/python -m unittest tests.test_review_site -v
# Optional actual-browser smoke test: installed Chrome + websocket-client; no browser download.
.venv/bin/python scripts/check_review_browser.py \
  --expect-declaration --out /tmp/source-review-browser-check.json
```

The browser test uses an isolated temporary profile and explicitly marked dummy decisions. It verifies all three images, region highlights, zoom, draft restoration, JSON download and missing-image handling; its test decisions are deleted. It does not perform human verification. Use a new output filename when repeating it.

Rendered source images remain local and ignored because source redistribution rights are unreviewed. Restore the cached PDFs before using the launcher on a machine without them; it does not redownload documents.
