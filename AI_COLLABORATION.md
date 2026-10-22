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
* **No human has verified any reference annotation.** Every reference is `ai_draft` with `human_checked_cells = 0`; the boxes in
  `docs/USER_SIGNOFF.md` are unticked. All accuracy-like numbers are agreement with unverified drafts.
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

## Not visible from this session
The chat transcripts of the ChatGPT session that wrote `baseline_v2`, of the Codex session and of the earlier Claude Code session
are not available here. Whatever they did that is not reflected in git history or in the files cannot be reported.
