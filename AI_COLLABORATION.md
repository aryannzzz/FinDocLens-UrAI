# AI collaboration disclosure (integration stage)

This file says who/what produced which part of the repository. **It is not the AI chat log and does not summarise all chat
activity.** Ur AI asked for the complete AI chat transcript(s); the applicant must export and attach them separately. Several
agents worked in separate sessions that this file cannot see (see "Not visible from this session").

## Who did what (as far as this session can establish from git history and the files themselves)
| part | produced by | evidence |
|---|---|---|
| `baseline_v2/` (v1/v2 native parser, 25 tests, gold TSV) | ChatGPT GPT-6 (per `baseline_v2/AI_COLLABORATION.md`) | tag `v2-frozen`, `benchmark/frozen_sha256.json`; unchanged here (`git diff v2-frozen -- baseline_v2` is empty) |
| `benchmark/` (evaluator, worker/harness, dataset download, AI-draft references, adversarial controls, review sheet), `docs/BENCHMARK_ADAPTER_CONTRACT.md` | Codex agent, branch `codex-benchmark` | commits `7369ec3`, `36088e5` |
| `findoclens/` backends (native_v2 wrapper, native_grid, Docling, Docling+RapidOCR, router, validator), `scripts/`, first round of `docs/CLAUDE_*.md` | Claude Code agent, branch `claude-backends` | commits `741b4c0` … `f53dd9a` |
| Integration, adapters, fixes, raster derivatives, diagnostics, viewer, final runs, `RESULTS.md` and the other documents in this stage | Claude Code (model: Sonnet 5.5), branch `integration-v1`, one session on 22 Oct 2026 | the commits after `a36e867` |

## What no AI did, and what is still missing
* **Current v3:** Aryan Jain explicitly declares that he personally compared all **197 annotated cell contents** (74 original, 56 ELECOM, 67 Daiwabo) with the original PDF images. Decisions are **bulk recorded from that declaration**, without invented dropdown clicks or per-cell inspection times. Structure, header links, merged spans and inferred periods remain unreviewed. The earlier 51/146 v2 history is preserved; these pages remain development-exposed, not blind holdouts. Original AI gold, original export, v1/v2 snapshots and old ledgers remain unchanged. AI recorded the declaration and replayed stored predictions; it did not perform the human inspection or create per-cell click events. See `docs/HUMAN_REVIEW_RESULTS.md` and `docs/USER_SIGNOFF.md`.
* **No model was trained.** No VLM (including PaddleOCR-VL) was run. The only learned models executed are Docling's layout and
  TableFormer checkpoints and RapidOCR's PP-OCRv6 detector/recognizer, all pre-trained and unmodified.
* No GPU was usable; all model numbers are CPU. No GPU memory was measured.
* OMRON p13 could not be downloaded (HTTP 403) and was never evaluated.

## Where AI judgement shaped results (read before trusting a number)
* `native_grid` was developed by looking at the original, ELECOM p9 and Daiwabo p10 pages and their failures; during integration it
  was changed again after observing mismatches against the AI-draft references on the original (development), ELECOM p9 and Daiwabo
  p10 (independent) and on the synthetic controls (development). Scores on those pages are in-sample for it. The
  integration-stage fixes are listed in `RESULTS.md` §6 with the page that motivated each.
* The adapter layer (`adapters/canonical.py`) applies documented conventions (month-end periods, status mapping, leaf/group header
  construction, section rows without placeholder cells). They affect header/status metrics, not raw cell tokens. See the module docstring.
* References were not edited in response to model output. Disagreements are listed in `docs/MANUAL_REVIEW_QUEUE.md` for a human.
* Codex implemented the later independent review, offline source-review repair, versioned approval import and this provenance correction; the applicant supplied the human export and subsequent clarifications. The pre-existing second visual pass archived under `review/second_ai_visual_audit/` is AI-only, not blind, and has no recorded model/version. It is not substituted for human annotation. No parser output or original AI reference changed during provenance correction, and no inference was rerun.

## Not visible from this session
The chat transcripts of the ChatGPT session that wrote `baseline_v2`, of the Codex session and of the earlier Claude Code session
are not available here. Whatever they did that is not reflected in git history or in the files cannot be reported.
