# FinDocLens — Ur AI Take-Home Agent Sprint (22–23 Oct 2026)

## Objective
Upgrade the supplied `baseline_v2` single-page native-text parser into a small **evidence-grounded hybrid financial-table extraction prototype**. Deliver a runnable repo, machine-readable JSON/Markdown, at least one independent-document evaluation, a model-backed comparison if feasible, and transparent limitations. Never claim a trained model or outside-the-template performance without actual measurements.

## Existing evidence (reproduced 22 Oct)
- `baseline_v2/parser_v2.py`: reads PDF text geometry and infers two numeric columns; Japanese financial hierarchy and arithmetic checks. It cannot parse raster-only source or heterogeneous multi-table/5-subcolumn layouts.
- Reproduces 43/43 manually AI-transcribed original rows, 74/74 monetary glyph strings, with 25 tests. This gold is NOT an independently human-certified benchmark.
- Synthetic scale/translation tests validate invariance on the same source only; they do not test cross-issuer generalization.

## The three most valuable new holdouts
1. ELECOM, **PDF page 9 (zero-based 8)**: https://www2.jpx.co.jp/disc/67500/140120260331594026.pdf — independent balance sheet, units million JPY, 2 periods.
2. OMRON, **PDF page 13 (zero-based 12)**: https://www.omron.com/jp/ja/ir/irlib/pdfs/20260513_tanshin.pdf — grouped 2025/26 headers, amount + composition-percent for each period, plus delta column, multiline and spaced Japanese.
3. Daiwabo, **PDF page 10 (zero-based 9)**: https://www2.jpx.co.jp/disc/31070/140120260206550180.pdf — separate assets and liabilities tables with 2025/3, 2025/12 and change, and lower explanatory table on the same slide.
These are public links, but review redistribution rights before bundling their complete PDFs. Manifest should store URLs, SHA-256, and page indexes; do not assert that downloads or model runs succeeded if they did not.

## Workflow
1. Unzip; copy `baseline_v2` into a Git repository; make an initial commit and keep a frozen `v2` baseline tag. Add `AGENTS.md` and `CLAUDE.md` to repo root. Confirm `python -m unittest discover -s tests -q` passes.
2. Run **Codex task 01** (dataset, golden annotations protocol, benchmark and evaluator) and **Claude Code task 02** (backends, router, schema). Use separate branches/worktrees; do not edit identical files in parallel.
3. Run **task 03** (integration, adversarial audit, demo and report). Accept only changes with evidence and complete logs.
4. The applicant should manually verify a meaningful sample of gold cells against rendered pages, preferably every original row and at least 20 numeric cells per holdout. AI auto-annotation must be clearly marked unverified until checked.
5. Keep time for a reliable submission and export the **complete AI chat transcript** as explicitly requested in the email.

## Non-negotiable scope
Prioritize balance-sheet PDFs, not PPT/chart support, training, a SaaS platform, or advanced GPU serving. A real Docling comparison and an independently scored holdout beat three unverified VLM claims. If memory/time blocks a VLM, fall back to native+Docling+Japanese OCR and report the blocker precisely.

## Definition of done
- `python -m unittest discover -s tests -v` green; reproducible `run_demo.sh` or equivalent.
- Original-source regression green, without loosening gold or using source-specific hardcoded overrides.
- Per-backend output, source evidence boxes, consistent schema, model/run metadata, and explicit failure statuses.
- Per-document and aggregate accuracy/coverage/error analysis; warm/cold latency and memory if measurable.
- Evidence screenshot (visually checked), 4–8 real failure crops, model comparison table, 1–2 page research memo, CLI/review UI.
- Honest separation of **measured**, **attempted but blocked**, and **proposed** experiments.
