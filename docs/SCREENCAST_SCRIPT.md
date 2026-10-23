# 2-minute screencast script (not recorded)

No screencast was made in the session that wrote this file. This is a script for the applicant to record, if they choose to; every
claim in it is backed by a file named in brackets, and every number must be re-read from `RESULTS.md` right before recording.

| time | on screen | say |
|---|---|---|
| 0:00 | terminal: `bash run_demo.sh` finishing (tests green) | "Japanese financial-statement tables from PDF pages. Pretrained extraction paths behind one schema. The author personally verified all 197 cell contents against source images; the decisions were bulk recorded from his declaration. Structure remains unreviewed." |
| 0:15 | `docs/HUMAN_REVIEW_RESULTS.md` | "Native_grid matches all 193 financial cells but 193 of 197 total contents, including 63 of 67 on Daiwabo. These are development-exposed results; full table structure is not human-certified." |
| 0:40 | viewer: pick `daiwabo_p10`, backend `native_v2` | "The frozen baseline returns status partial but silently drops two of three tables: 2 of 63 numeric cells. Click a box: exact glyphs, typed value, evidence kind." [viewer/index.html] |
| 1:00 | switch backend to `docling_cmtrue`, then `native_grid` | "One merged grid versus three tables." |
| 1:15 | viewer: `scan_200`, backend `docling_rapidocr`, tab "Review warnings" | "On a raster page only OCR works. Digits survive; kanji are misread (産→產) and the lone `－` placeholders are not detected. Both are flagged for review instead of being repaired." [docs/FAILURE_GALLERY.md G6/G7] |
| 1:40 | `docs/MANUAL_REVIEW_QUEUE.md` | "Only 6 of the 37 high-risk sign and placeholder cases are individually reviewed. The remaining 31 and structural assumptions still need human sign-off." |
| 1:55 | RESULTS.md limitations | "CPU only, three real pages, two added issuer families. Every measured source was exposed during development; there is no blind generalization result." |
