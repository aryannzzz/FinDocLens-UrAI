# Official research links and why to read them (verified October 22, 2026)

- Docling table pipelines / TableFormer mode and cell matching: https://github.com/docling-project/docling/blob/main/docs/usage/advanced_options.md ; official serializer and merged-cell spans: https://docling-project.github.io/docling/concepts/serialization/
- PaddleOCR-VL full pipeline: https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/pipeline_usage/PaddleOCR-VL.en.md — read before choosing engine/install. `PaddleOCRVL` includes layout + element recognition; 0.9B base component alone is not the same end-to-end pipeline. CPU/Transformers/Paddle engines documented, 6GB compatibility not guaranteed.
- PP-StructureV3/OCR and Japanese models: https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/pipeline_usage/PP-StructureV3.en.md
- Microsoft Table Transformer, plus why OCR still needed: https://github.com/microsoft/table-transformer ; GriTS and PubTables-1M.
- OmniDocBench dataset / TEDS / diverse document conditions (CVPR 2025, updated 2026): https://github.com/opendatalab/OmniDocBench ; scores and methods use their own dataset, not comparable to our single-page number.
- Japanese chart/table evaluation (HakushoBench, 2026): https://arxiv.org/abs/2606.01132 — valuable motivation for non-English layouts but it is VQA, not a drop-in cell-extraction benchmark.
- Japanese visual document QA (JDocQA): https://arxiv.org/abs/2403.19454 — QA benchmark, not direct PDF-table cell gold.
- Official Codex project instructions: https://developers.openai.com/codex/agent-configuration/agents-md and worktrees: https://developers.openai.com/codex/environments/git-worktrees
- Official Claude Code isolated worktree sessions: https://code.claude.com/docs/en/common-workflows
- Japanese OCR CPU fallback: https://tesseract-ocr.github.io/tessdoc/Data-Files ; use `jpn` traineddata.

Do not treat advertised model OmniDocBench leaderboard scores as Japanese balance-sheet accuracy. Report this project's own metrics separately.
