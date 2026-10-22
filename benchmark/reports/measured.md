# Measured benchmark (AI-drafted references)

All cell and structure scores below are provisional agreement with AI-drafted references. Human-verified cells: **0**. No OCR/VLM backend was run in this workstream.

| Run / document | Outcome | Tables matched/gold | Rows matched/gold | Numeric raw exact/gold | Header roles/gold | Cold process ms | Warm median ms (3) | Cold peak RSS MiB |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| independent_final-v1 / original | success | 1/1 | 43/43 | 74/74 | 2/2 | 183.80 | 31.48 | 79.16 |
| independent_final-v1 / elecom_p9 | partial | 1/1 | 34/34 | 56/56 | 2/2 | 190.16 | 22.22 | 79.62 |
| independent_final-v1 / omron_p13 | unavailable | — | — | — | — | — | — | — |
| independent_final-v1 / daiwabo_p10 | partial | 1/3 | 1/21 | 2/63 | 0/10 | 184.42 | 40.99 | 84.07 |
| adversarial_final-v1 / missing_cell | partial | 1/1 | 43/43 | 74/74 | 2/2 | 166.69 | 34.21 | 78.86 |
| adversarial_final-v1 / sign_erasure | partial | 1/1 | 43/43 | 74/74 | 2/2 | 183.48 | 34.07 | 79.20 |
| adversarial_final-v1 / text_layer_deleted | abstained | 0/1 | 0/43 | 0/74 | 0/2 | 435.40 | 266.27 | 168.12 |
| adversarial_final-v1 / rotation_90 | success | 1/1 | 43/43 | 74/74 | 2/2 | 193.75 | 40.48 | 79.23 |
| adversarial_final-v1 / scan_150 | abstained | 0/1 | 0/43 | 0/74 | 0/2 | 255.19 | 112.36 | 92.26 |
| adversarial_final-v1 / scan_200 | abstained | 0/1 | 0/43 | 0/74 | 0/2 | 231.59 | 112.30 | 112.09 |
| adversarial_final-v1 / tiny_cjk | success | 1/1 | 43/43 | 74/74 | 2/2 | 143.92 | 28.02 | 78.40 |
| adversarial_final-v1 / footnote_marker | success | 1/1 | 43/43 | 74/74 | 2/2 | 182.67 | 32.53 | 79.25 |
| adversarial_final-v1 / grouped_two | abstained | 0/1 | 0/4 | 0/16 | 0/4 | 117.81 | 5.82 | 73.68 |
| adversarial_final-v1 / grouped_three | abstained | 0/1 | 0/4 | 0/24 | 0/6 | 121.67 | 5.16 | 73.99 |
| adversarial_final-v1 / merged_headers | abstained | 0/1 | 0/4 | 0/16 | 0/4 | 106.88 | 5.41 | 73.91 |
| adversarial_final-v1 / side_by_side | abstained | 0/2 | 0/8 | 0/32 | 0/8 | 127.51 | 8.79 | 77.10 |
| adversarial_final-v1 / vertical_spacing | abstained | 0/1 | 0/4 | 0/16 | 0/4 | 125.29 | 5.13 | 73.65 |

The cold total covers backend import/load, 200dpi render plus cold PNG export, extraction, evaluation projection and JSON serialization. Warm trials keep the same interpreter/backend but reopen and render the PDF; they do not export another PNG. `process_wall_ms` additionally captures interpreter startup. These are process-cold measurements, with no claim of a cleared OS disk cache. Acquisition, annotation and scoring are excluded.

RSS is Linux process-lifetime `ru_maxrss`, including rendering. Warm high-water marks are cumulative and cannot be interpreted as incremental memory. All v2 extraction used the CPU. The recorded `nvidia-smi` probe failed to communicate with the driver; GPU memory is null/unmeasured. No driver or system package changes were attempted.

ELECOM is a genuinely different issuer, but its layout is similar to the development page. Its 56/56 tokens therefore do not establish heterogeneous-layout reliability. The hierarchy disagreement is `その他（純額）`: v2 attaches it under `建設仮勘定`, while the source-based draft places it directly under `有形固定資産`. Human review is still required.

Daiwabo exposes the layout failure: 1/3 table regions matched, 1/21 rows matched, 8 spurious rows, and 65/67 cell slots omitted without a specific omission warning. Only 2/63 numeric tokens match the draft. The lower table contains four additional explanatory text cells, which are included in all-cell metrics and excluded from numeric-only metrics. A generic unit/header/financial warning does not excuse a silent omission.

OMRON was attempted twice and returned HTTP 403. It remains an unavailable candidate, with no fabricated source hash, gold denominator, latency or score. There are two available independent source pages out of three requested candidates. This availability denominator is distinct from the known-cell accuracy denominator.

The missing-cell control expects an explicit missing status and achieves 1/1 correct abstention. Sign erasure changes the visible source: the derived reference expects positive `2,979`; the original reference stays `△2,979`. Rotation is PDF rotation metadata with unchanged native coordinates, so success does not establish recognition of physically rotated raster text. Scan/text-layer controls retain their full gold denominators and score zero after explicit abstention.

Synthetic grouped columns, nested merged headers, side-by-side tables, decimals/plus/dash/negative-zero tokens, and vertical CJK spacing are development controls. They are not independent-company evidence. The five synthetic layouts abstained; no TEDS, GriTS, CER, statistical significance or model leaderboard is claimed.

Review gate status: independent issuer sourcing **met for two pages**; independent human gold **pending**; original sign/dash regression **met**; heterogeneous numeric/grouped-header extraction **fails**; no silent omission **fails on Daiwabo**; readable source crops **generated and AI-inspected, human review pending**.

Next steps: review every row and header plus at least 20 numeric cells per independent page in `benchmark/review/index.html`; export named human decisions; version any correction with old/new token, reason, crop and frozen reference hash. Obtain the OMRON source through an authorized local download. Plug the separately owned backends into `docs/BENCHMARK_ADAPTER_CONTRACT.md`, preserving raw results and reporting failures against these same references.
