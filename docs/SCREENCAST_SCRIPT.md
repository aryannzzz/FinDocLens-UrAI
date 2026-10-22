# 2-minute screencast script (not recorded)

No screencast was made in the session that wrote this file. This is a script for the applicant to record, if they choose to; every
claim in it is backed by a file named in brackets, and every number must be re-read from `RESULTS.md` right before recording.

| time | on screen | say |
|---|---|---|
| 0:00 | terminal: `bash run_demo.sh` finishing (tests green) | "Japanese financial-statement tables from PDF pages. Five extraction paths behind one schema, one evaluator, references that are AI drafts, not human-verified." |
| 0:15 | `RESULTS.md` headline table | "Digital pages: the text-layer parser reads every numeric token on the original and ELECOM pages and 63 of 63 on the Daiwabo slide, in about 20–50 ms. Docling TableFormer takes seconds and flattens the three Daiwabo tables into one." [RESULTS.md §A] |
| 0:40 | viewer: pick `daiwabo_p10`, backend `native_v2` | "The frozen baseline returns status partial but silently drops two of three tables: 2 of 63 numeric cells. Click a box: exact glyphs, typed value, evidence kind." [viewer/index.html] |
| 1:00 | switch backend to `docling_cmtrue`, then `native_grid` | "One merged grid versus three tables." |
| 1:15 | viewer: `scan_200`, backend `docling_rapidocr`, tab "Review warnings" | "On a raster page only OCR works. Digits survive; kanji are misread (産→產) and the lone `－` placeholders are not detected. Both are flagged for review instead of being repaired." [docs/FAILURE_GALLERY.md G6/G7] |
| 1:40 | `docs/MANUAL_REVIEW_QUEUE.md` | "Nothing here is human-verified. This is the list of what a person must check, starting with every sign and dash." |
| 1:55 | RESULTS.md limitations | "CPU only, three real pages, one independent issuer family each. A narrow result, not a leaderboard." |
