# Project rules for all coding agents

Goal: Ur AI internship take-home. Build an auditable, reusable financial PDF table parser and small controlled benchmark, not a fake leaderboard.

Read `00_START_HERE.md`, `docs/EVAL_PROTOCOL.md`, and the existing README before edits. Treat `baseline_v2` as an immutable benchmark snapshot; introduce new code under `findoclens/`, `adapters/`, `benchmark/`, `review/` or a clearly documented structure. If migrating source, retain original files and results.

Invariants:
- Preserve exact original Japanese labels and monetary glyphs (`△`, `－`, `△0`, plus and decimals) in `raw` alongside typed `value` / `status`. `－` is not automatically zero.
- Preserve page, table, row, column coordinates and method provenance. Keep original source text/image predictions separate. Do not silently repair accounting inconsistencies or replace visual evidence with a guess.
- Handle low-confidence, missing or unparseable cells explicitly. Never let an empty extraction count as a successful parse.
- A table may have 0, 1, 2 or more financial subcolumns; grouped headers and multiple tables must not be silently flattened or merged. Use `null` only with an explicit status explaining why.
- Run frozen original tests and new holdouts before making success claims. Do not tune on holdout gold; label all examples with same-issuer/independent-issuer and synthetic/source.
- Record elapsed time, device, peak GPU allocation or `nvidia-smi` observed memory, package and model versions, checkpoint IDs, and errors. Distinguish cold-load from warmed inference. Never fabricate benchmark results.
- Dependencies belong in virtualenv / optional extras. Do not alter system CUDA, display/NVIDIA drivers, global Python, or reboot without applicant approval.
- Keep independent agent branches and small commits; write artifacts to `runs/<backend>/<doc_id>` with metadata. No secrets in repo or prompts.
- Include Git commit, commands run, tests with pass/fail, changes made and outstanding risks in final agent response.

Review gates: **independent gold**, **negative-sign/dash fidelity**, **no silent omission**, **readable source evidence**, **out-of-template behavior**.
