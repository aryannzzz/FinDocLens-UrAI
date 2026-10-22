| config | doc | variant | status | tables | rows | numeric_cells | token_recall | token_precision | dev_gold_cells_correct | cold_ms | warm_ms_median | peak_rss_mb |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| native_v2 | source | digital | ok | 1 | 37 | 74 | 1.0 | 1.0 | 74/74 | 44.8 | 19.1 | 57.7 |
| native_v2 | source | raster200 | failed | 0 | 0 | 0 | 0.0 | 0.0 | 0/74 | 150.0 | 128.1 | 143.8 |
| native_v2 | elecom | digital | ok | 1 | 28 | 56 | 1.0 | 1.0 |  | 59.4 | 18.6 | 92.5 |
| native_v2 | elecom | raster200 | failed | 0 | 0 | 0 | 0.0 | 0.0 |  | 143.0 | 183.7 | 143.1 |
| native_v2 | daiwabo | digital | ok | 1 | 9 | 18 | 0.2857 | 1.0 |  | 68.2 | 45.6 | 92.6 |
| native_v2 | daiwabo | raster200 | failed | 0 | 0 | 0 | 0.0 | 0.0 |  | 161.2 | 139.3 | 146.5 |
| native_grid | source | digital | ok | 1 | 37 | 74 | 1.0 | 1.0 | 74/74 | 25.5 | 35.0 | 97.3 |
| native_grid | source | raster200 | failed | 0 | 0 | 0 | 0.0 | 0.0 | 0/74 | 39.0 | 27.4 | 97.3 |
| native_grid | elecom | digital | ok | 1 | 28 | 56 | 1.0 | 1.0 |  | 49.6 | 12.7 | 97.3 |
| native_grid | elecom | raster200 | failed | 0 | 0 | 0 | 0.0 | 0.0 |  | 36.1 | 28.3 | 97.3 |
| native_grid | daiwabo | digital | ok | 3 | 21 | 63 | 1.0 | 1.0 |  | 52.7 | 47.9 | 97.3 |
| native_grid | daiwabo | raster200 | failed | 0 | 0 | 0 | 0.0 | 0.0 |  | 33.8 | 33.1 | 100.8 |
| docling_cmtrue | source | digital | ok | 1 | 37 | 74 | 1.0 | 1.0 | 74/74 | 22633.3 | 13483.9 | 1465.5 |
| docling_cmtrue | source | raster200 | failed | 1 | 0 | 0 | 0.0 | 0.0 | 0/74 | 22859.3 | 12378.8 | 1533.5 |
| docling_cmtrue | elecom | digital | ok | 1 | 28 | 56 | 1.0 | 1.0 |  | 17469.2 | 11051.3 | 1341.1 |
| docling_cmtrue | elecom | raster200 | failed | 1 | 0 | 0 | 0.0 | 0.0 |  | 17363.3 | 13918.1 | 1600.4 |
| docling_cmtrue | daiwabo | digital | ok | 1 | 13 | 59 | 0.9365 | 1.0 |  | 17474.7 | 9854.3 | 1485.6 |
| docling_cmtrue | daiwabo | raster200 | failed | 1 | 0 | 0 | 0.0 | 0.0 |  | 16952.6 | 11123.1 | 1599.8 |
| docling_cmfalse | source | digital | ok | 1 | 37 | 74 | 1.0 | 1.0 | 74/74 | 85369.3 | 8686.5 | 1387.5 |
| docling_cmfalse | elecom | digital | ok | 1 | 28 | 56 | 1.0 | 1.0 |  | 12654.3 | 7115.4 | 1343.9 |
| docling_cmfalse | daiwabo | digital | failed | 1 | 0 | 0 | 0.0 | 0.0 |  | 12118.5 | 7532.0 | 1381.8 |
| docling_ocr_rapid | source | raster200 | ok | 1 | 37 | 72 | 0.973 | 1.0 | 62/74 | 24808.7 | 15780.4 | 2248.4 |
| docling_ocr_rapid | elecom | raster200 | ok | 1 | 28 | 56 | 1.0 | 1.0 |  | 21786.2 | 14743.2 | 2187.8 |
| docling_ocr_rapid | daiwabo | raster200 | ok | 1 | 13 | 59 | 0.9365 | 1.0 |  | 22234.6 | 13752.5 | 2129.7 |
| auto | source | digital | ok | 1 | 37 | 74 | 1.0 | 1.0 | 74/74 | 45.1 |  |  |
| auto | source | raster200 | needs_visual_review | 1 | 37 | 72 | 0.973 | 1.0 | 62/74 | 25893.2 |  |  |
| auto | elecom | digital | ok | 1 | 28 | 56 | 1.0 | 1.0 |  | 69.7 |  |  |
| auto | elecom | raster200 | needs_visual_review | 1 | 28 | 56 | 1.0 | 1.0 |  | 24811.2 |  |  |
| auto | daiwabo | digital | ok | 3 | 21 | 63 | 1.0 | 1.0 |  | 87.7 |  |  |
| auto | daiwabo | raster200 | needs_visual_review | 1 | 13 | 59 | 0.9365 | 1.0 |  | 23851.0 |  |  |
| auto_verify | source | digital | ok | 1 | 37 | 74 | 1.0 | 1.0 | 74/74 | 20703.5 |  |  |
| auto_verify | elecom | digital | ok | 1 | 28 | 56 | 1.0 | 1.0 |  | 18698.7 |  |  |
| auto_verify | daiwabo | digital | ok | 3 | 21 | 63 | 1.0 | 1.0 |  | 17530.8 |  |  |
