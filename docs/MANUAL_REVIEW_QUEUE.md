# Manual review queue for the AI-drafted references

> **Current v3:** Aryan Jain explicitly declares that he personally compared all **197 annotated cell contents** (74 original, 56 ELECOM, 67 Daiwabo) with the original PDF images. Decisions are **bulk recorded from that declaration**, without invented dropdown clicks or per-cell inspection times. Structure, header links, merged spans and inferred periods remain unreviewed. The earlier 51/146 v2 history is preserved; these pages remain development-exposed, not blind holdouts. All 37 listed sign/dash/plus/negative-zero cases are covered by the new declaration. `remaining_sign_review_v2.csv` is a historical queue, not a current remaining-cell list.

The original `benchmark/gold/` remains `ai_draft` with zero human counts; verified contents are separately versioned in `benchmark/human_gold/v3/`. The generated queue below preserves the original scope and candidates. The remaining review work is structural; see [current report](HUMAN_REVIEW_RESULTS.md) and [submission status](SUBMISSION_STATUS.md).

## A. Must check: signs, dashes, plus signs, negative zero (project gate: negative-sign/dash fidelity)

A native text layer can carry a wrong glyph or lose a thin mark without any tool noticing, and all four extractors read the same layer. These cells are where a silent error costs the most. Compare the crop with `raw` character by character.

| doc | row id | label | col | draft raw | draft status |
|---|---|---|---|---|---|
| original | `assets_r012` | 貸倒引当金 | 0 | `△2,979` | observed |
| original | `assets_r012` | 貸倒引当金 | 1 | `△0` | negative_zero |
| original | `assets_r017` | 減価償却累計額 | 0 | `△1,923,585` | observed |
| original | `assets_r017` | 減価償却累計額 | 1 | `△1,640,253` | observed |
| original | `assets_r020` | 減価償却累計額 | 0 | `△3,634,165` | observed |
| original | `assets_r020` | 減価償却累計額 | 1 | `△1,914,091` | observed |
| original | `assets_r024` | 減価償却累計額 | 0 | `△147,599` | observed |
| original | `assets_r024` | 減価償却累計額 | 1 | `△172,066` | observed |
| original | `assets_r026` | 建設仮勘定 | 0 | `－` | not_reported |
| original | `assets_r028` | 減価償却累計額 | 0 | `△840,375` | observed |
| original | `assets_r028` | 減価償却累計額 | 1 | `△421,883` | observed |
| original | `assets_r038` | 長期貸付金 | 0 | `－` | not_reported |
| elecom_p9 | `assets_r031` | 貸倒引当金 | 0 | `△4` | observed |
| elecom_p9 | `assets_r031` | 貸倒引当金 | 1 | `△4` | observed |
| daiwabo_p10 | `assets_r001` | 流動資産 | 2 | `+17,426` | observed |
| daiwabo_p10 | `assets_r002` | 現金及び預金 | 2 | `△43,010` | observed |
| daiwabo_p10 | `assets_r003` | 受取手形及び売掛金 | 2 | `+31,130` | observed |
| daiwabo_p10 | `assets_r004` | 商品及び製品 | 2 | `+22,808` | observed |
| daiwabo_p10 | `assets_r005` | 有形固定資産 | 2 | `+1,280` | observed |
| daiwabo_p10 | `assets_r006` | 無形固定資産 | 2 | `+1,554` | observed |
| daiwabo_p10 | `assets_r007` | 投資その他の資産 | 2 | `△1,106` | observed |
| daiwabo_p10 | `assets_r008` | 資産合計 | 2 | `+19,155` | observed |
| daiwabo_p10 | `liabilities_equity_r001` | 流動負債 | 2 | `+15,124` | observed |
| daiwabo_p10 | `liabilities_equity_r002` | 支払手形及び買掛金 | 2 | `△14,827` | observed |
| daiwabo_p10 | `liabilities_equity_r003` | 短期借入金 | 2 | `+33,800` | observed |
| daiwabo_p10 | `liabilities_equity_r004` | 固定負債 | 2 | `△4,379` | observed |
| daiwabo_p10 | `liabilities_equity_r005` | 長期借入金 | 2 | `△3,567` | observed |
| daiwabo_p10 | `liabilities_equity_r006` | 負債合計 | 2 | `+10,745` | observed |
| daiwabo_p10 | `liabilities_equity_r007` | 純資産合計 | 2 | `+8,409` | observed |
| daiwabo_p10 | `liabilities_equity_r008` | 自己株式 | 0 | `△15,088` | observed |
| daiwabo_p10 | `liabilities_equity_r008` | 自己株式 | 1 | `△2,667` | observed |
| daiwabo_p10 | `liabilities_equity_r008` | 自己株式 | 2 | `+12,420` | observed |
| daiwabo_p10 | `liabilities_equity_r009` | 負債純資産合計 | 2 | `+19,155` | observed |
| daiwabo_p10 | `explanation_r001` | 現金及び預金 | 2 | `△43,010` | observed |
| daiwabo_p10 | `explanation_r002` | 受取手形及び売掛金 | 2 | `+31,130` | observed |
| daiwabo_p10 | `explanation_r003` | 商品及び製品 | 2 | `+22,808` | observed |
| daiwabo_p10 | `explanation_r004` | 借入金 | 2 | `+30,233` | observed |

Counts: original 12, elecom_p9 2, daiwabo_p10 23 (total 37). Plain digits are in section D.

## B. Structural assertions in the drafts that no extractor can confirm

| # | doc | assertion in the draft | why it is uncertain | evidence |
|---|---|---|---|---|
| B1 | daiwabo_p10 | The lower table has headers `c0..c3` with the periods/roles of the two upper tables (2025-03-31, 2025-12-31, change, text). | The slide prints no header over this table; the draft copied the periods from the tables above. Every backend that reads only what is printed leaves these columns without a header. | `benchmark/gold/daiwabo_p10.json` table `explanation`; native_grid header score 6/10 is exactly these 4 leaves |
| B2 | daiwabo_p10 | The four explanation texts are cells without the leading arrow: `主に商品在庫の増加に伴う減少`; `DISの売上債権の増加`; `主にGIGAスクール向け商品増加`; `運転資本として`. | The PDF text layer prints `→` before each text and the extractors keep it (`→主に…`). Whether the arrow belongs to the cell text decides 4 cells (`raw_cell_exact`). | cell mismatches in `runs/native_grid/daiwabo_p10/fin1_main/cold/metrics.json` |
| B3 | daiwabo_p10 | The page has exactly 3 tables (assets, liabilities+equity, explanation) and the draft's table/row boxes are right. | The explanation block has no ruling or header; a different annotator may call it a note or two tables. Table matching uses bbox IoU ≥ 0.1 so box choices matter. | review sheet, section `daiwabo_p10` |
| B4 | daiwabo_p10 | 7 hierarchy edges (e.g. `現金及び預金` under `流動資産`). | The slide has no section-heading rows; the parent assignment was inferred from indentation by the drafter. Every backend scores 0/7. | `parent_path` in the reference |
| B5 | daiwabo_p10 | Change column `増減` has period `2025-12-31_vs_2025-03-31` (current minus previous). | Convention chosen by the drafter; the validator's 17 delta checks on tables 1–2 (12 exact, 5 within rounding, 0 violations) support current−previous, but the header text only says 増減 and table 3 has no check. | `findoclens` validator checks, `docs/CLAUDE_RESULTS.md` §4 |
| B6 | daiwabo_p10 | Unit `million_JPY` for all three tables. | Printed once (`（百万円）`, above table 1 only). Tables 2–3 inherit it in the draft. | page crop |
| B7 | elecom_p9 | `その他（純額）` is a child of `有形固定資産`, not of `建設仮勘定`. | Frozen v2 (a text-geometry parser) attaches it elsewhere; the draft follows the source layout. Only the indentation in the crop can settle it (1 hierarchy edge). | `benchmark/reports/measured.md` |
| B8 | original | `建設仮勘定` and `長期貸付金` have a `－` in the prior-period column (status `not_reported`, value null); `貸倒引当金` has `△0` (negative zero). | These are the three cells where a human must confirm that the page really prints a dash / a triangle-zero (an OCR engine cannot see the dash at all, see `docs/FAILURE_GALLERY.md` G6). | section A |
| B9 | daiwabo_p10 | (added in the P0 pass) Whether the lower explanation table should carry the periods/roles of the tables above (`c0..c3`: 2025-03-31, 2025-12-31, change, text). | Under evaluator v2 this decides 12 of the 63 Daiwabo cell-period scores: the slide prints no header there, `native_grid` leaves period null, the draft inherited them. Neither side is repaired; it needs a human decision. | `docs/P0_FIXES.md` §5 |

## C. Where an image-based reader disagrees with the draft (label-independent)

Docling+RapidOCR reads pixels, not the text layer, so it is the only reader that is not common-mode with the draft's native-text bootstrap. Gold numeric tokens that the OCR run did not return anywhere on the page (multiset comparison; location- and label-free):

* **scan_200**: gold 74 tokens; OCR returned 72; absent from OCR: `－`×2; produced by OCR but not in the draft: none.
* **elecom_p9_scan200**: gold 56 tokens; OCR returned 56; absent from OCR: none; produced by OCR but not in the draft: none.
* **daiwabo_p10_scan200**: gold 63 tokens; OCR returned 63; absent from OCR: `12,410`×1, `△43,010`×1, `+31,130`×1, `68,303`×1, `+22,808`×1, `50,936`×1, `+30,233`×1; produced by OCR but not in the draft: `→12,410`×1, `主に商品在庫の増加に伴う減少`×1, `DISの売上債権の増加`×1, `→68,303`×1, `主にGIGAスクール向け商品増加`×1, `→50,936`×1, `運転資本として`×1.

A token in the first list is either an OCR miss (expected for lone `－`, see the dash probe) or a draft error. A token in the second list is an OCR misread or a draft omission. Check each against the crop before concluding either way. In the stored run the Daiwabo entries are explained by structure, not by digits: OCR fuses the printed arrow with the number (`→12,410`) and returns the four explanation texts, which the draft stores as text cells; the digits themselves agree. ELECOM and the original page show no digit disagreement except the two lone `－`.

## D. Everything else

Project minimum (`AGENTS.md`, `benchmark/README.md`): all table boundaries, all headers/units, exact Japanese labels, all signs/dashes (section A), and at least 20 numeric cells per independent page; preferably the complete references.

| doc | rows | cells | suggested scope |
|---|---|---|---|
| original | 43 | 74 | all 43 labels + all 74 tokens (this is the page the baseline was tuned on) |
| elecom_p9 | 34 | 56 | all 34 labels; ≥ 20 tokens incl. both `△`; table box and unit |
| daiwabo_p10 | 21 | 67 | 3 table boxes; all 21 labels; ≥ 20 tokens across the three tables; items B1–B6 |

Raster derivatives and synthetic/perturbed controls inherit their parent's reference or are generated with known truth; reviewing the parent pages covers them (the derived references are listed in `benchmark/gold/raster/SHA256.json`).
