# Full AI collaboration disclosure (in addition to required chat log)

On October 22, 2026, ChatGPT GPT-6 assisted in a two-stage Ur AI take-home response:

1. Initial PDF-native parser (`v1`), extracting one Japanese balance-sheet page using hand-calibrated coordinates. This code is preserved as `tests/baseline_parser.py` in this package.
2. Research and redesigned parser (`v2`), using automatic numeric-column right-edge discovery, physical-line/numeric-span joining, hierarchical accounting structure, provenance bounding boxes, financial checks, missing-cell retention, full source-coordinate visual evidence, a second PDF text extraction engine check, manually specified reference labels/values, controlled geometric perturbations, and tests.

ChatGPT conducted web research into Docling TableFormer, Microsoft Table Transformer/PubTables, PaddleOCR-VL, MinerU, and Marker; it wrote the code, documentation, reference data and evaluation design, and ran all local tests. The applicant should review the results and claims, and personally verify the reference values and source page before submitting.

**No pretrained VLM was downloaded or executed, and no model was trained.** The example VLM review packet is generated but not sent to a model. The same public sample PDF was used throughout, with artificial variants. Scores do not indicate accuracy across independent templates or companies.

**Ur AI requested the full AI chat log. This disclosure is not the complete chat log. The applicant must attach/export the entire relevant ChatGPT conversation as required, including all prompts and answers, corrections, failures, and improvements.**
