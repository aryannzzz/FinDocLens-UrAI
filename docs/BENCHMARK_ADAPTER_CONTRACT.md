# Extraction/evaluation handoff (benchmark-1.0)

This implements the representation in `EVAL_PROTOCOL.md`; this document is the runnable handoff for the extraction owner. No extraction or model adapter is implemented here. Frozen v2 is consumed through the loss-disclosing `benchmark.compat.from_v2` evaluation projection, with unchanged native JSON stored separately.

Two integration routes:

```bash
# Score an already produced canonical result (works without model dependencies).
.venv/bin/python -m benchmark.evaluate \
  --gold benchmark/gold/elecom_p9.json --prediction path/to/prediction.json --out path/to/metrics.json

# The callable is imported once per document process and called cold + 3 times warm.
.venv/bin/python -m benchmark.run --backend BACKEND_NAME \
  --entrypoint adapters.YOUR_MODULE:extract --run-id YOUR_UNIQUE_RUN_ID
```

`extract(input_path: str, *, context: dict) -> dict` receives only the selected PDF and provenance context, **never gold**. Context contains `document_id`, `source_sha256` (full original filing), `input_sha256` (selected input PDF), `source_page_index` (0-based original page), and coordinate convention. The callable must return those identities explicitly. Loading may occur on import or first call; lazy loading must be disclosed. Reuse cached model state for warm calls. Optional module `BENCHMARK_METADATA` must state actual `device`, `backend_version`, `model_revision`, and `checkpoint_id`; nulls need a reason for native/no-model backends. The harness independently measures CPU RSS; GPU allocator peaks remain unmeasured unless a separate backend record supplies actual measurements. Do not call a declared GPU peak a harness measurement.

Canonical result fields:

| Level | Required fields / interpretation |
|---|---|
| document | `schema_version`, `document_id`, `source_sha256`, `input_sha256`, `backend`, `model_revision`, `page_bbox`, `status`, `issues[]`, `tables[]` |
| table | `table_id` (local arbitrary ID), `page` (1-based selected PDF), `bbox`, `reading_order`, `headers[]`, `rows[]`, `issues[]` |
| header | `header_id`, `kind` (`leaf`/`group`), `column_index`, exact `text`, `period`, `role` for leaves, `bbox`, `colspan`, `rowspan`, optional `parent_id` |
| row | `row_id`, `row_index` (0-based within table), `label`, exact `raw_label`, `parent_path[]` (excluding self), `bbox`, `type`, `cells[]` |
| cell | `column_index` (0-based physical financial column), `header_id`, `period`, `role`, exact `raw`, typed `value`, explicit `status`, `bbox`, `backend`, `evidence_kind` |

PDF coordinates are points, top-left origin in **unrotated** page space. Preserve `page_rotation_degrees` when relevant. `page_bbox` is the unrotated crop extent. Do not combine side-by-side tables. Section rows can have zero cells; other rows include every expected column slot, even when absent. Numeric-column count is not fixed. Group nodes carry actual spans and parent relationships, not an invented flat repeated string. A missing box/span/header is null **with a capability/status explanation**, not fabricated geometry. Bbox-less tables cannot be localized by the current matcher and are explicitly counted as unlocalizable. Full raw JSON/native/OCR text must remain separately accessible. Returned canonical output is also saved verbatim as `original_result.json`; models with additional raw output should return its path and hash in provenance.

Roles: `amount`, `composition_pct`, `change_amount`, `other`. Percent values are displayed percentage points (`10.25` means 10.25%, not 0.1025). Numeric decimals may be JSON numbers or exact decimal strings. `other` text cells retain their string value. Statuses: `observed`, `negative_zero`, `not_reported`, `absent_text_cell`, `unreadable`, `uncertain`, `unparseable`. Preserve `△0`, `－`, plus signs, comma/decimal glyphs and labels in raw fields. A dash maps to null/not_reported, never zero. No accounting-based repair is permitted.

Run statuses: `success`, `partial`, `abstained`, `error`, `oom`, `timeout`, `unavailable`. The worker converts empty row extraction into an explicit abstention. Exceptions/OOM/timeouts become empty failed predictions scored with full gold denominators. Raw outputs are never repaired in place by the evaluator. Canonical JSON below `runs/<backend>/<doc_id>/<run_id>/<cold|warm_N>/` is immutable per run; choose a new run ID for a changed implementation.

Alignment does not require matching table/row IDs. Tables use one-to-one page/IoU >= .1; rows use equal labels after Unicode whitespace removal, geometry/context/order for ties, never fuzzy edits or amounts. Cells use physical `column_index`; header periods/roles are evaluated separately. An unsupported percentage/change column must remain missing rather than be relabeled as an amount.

The evaluator reports table/row P/R/F1; miss/spurious counts; exact raw tokens over all gold cells, matched predicted slots, and all predicted cells; typed value/status fidelity; numeric-only metrics; exact raw labels; row order; period+role headers; group text/spans and group-parent accuracy; hierarchy edges with full paths; abstention and correct injected-missing abstention; omissions and false assurance. It removes only Unicode whitespace for raw token comparisons and never normalizes signs/punctuation. Null denominators are `rate:null`, not a perfect score. `other` text cells are separate from numeric-only denominators. TEDS/GriTS/CER are not implemented or claimed.

The extraction owner should treat the independent pages as evaluation-only. Their references are all `ai_draft`, with `human_checked_cells=0`. `--require-human` refuses those references. Preserve source families in one split. No holdout-specific override, label rewrite or post-hoc table splitting may be added to the evaluation projection.
