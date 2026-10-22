# Visual failure gallery

Rendered from stored runs `fin1_*` by `scripts/make_gallery.py`. Boxes are the backend's returned cell boxes; red = uncertain/unreadable. Images show third-party filings and are git-ignored (regenerate with the script; decide separately whether to ship them).

## G1 — native_v2 / daiwabo_p10

Frozen v2 on the Daiwabo slide: one table, left table / deltas / lower table silently absent while the run is not an abstention.

![G1](gallery/G1_native_v2_daiwabo_p10.png)

status `partial`; tables 1/3 (+0 extra); rows 1/21; numeric cells exact 2/63; silent omissions 65/67; false assurance: no.
Source: `runs/native_v2/daiwabo_p10/fin1_main/cold/prediction.json`.

## G2 — docling_cmtrue / daiwabo_p10

Docling cell_matching=True: three tables flattened into one 8-column grid (label column of table 2 becomes a data column).

![G2](gallery/G2_docling_cmtrue_daiwabo_p10.png)

status `partial`; tables 1/3 (+0 extra); rows 0/21; numeric cells exact 0/63; silent omissions 67/67; false assurance: no.
Source: `runs/docling_cmtrue/daiwabo_p10/fin1_main/cold/prediction.json`.

## G3 — docling_cmfalse / daiwabo_p10

Docling cell_matching=False: a table box with almost no cell text (text-line cells span whole rows on this slide).

![G3](gallery/G3_docling_cmfalse_daiwabo_p10.png)

status `abstained`; tables 1/3 (+0 extra); rows 1/21; numeric cells exact 0/63; silent omissions 0/67; false assurance: no.
Source: `runs/docling_cmfalse/daiwabo_p10/fin1_main/cold/prediction.json`.

## G4 — docling_regions / daiwabo_p10

Ablation: native_grid region proposals + Docling per region. The two upper tables are separated; the unruled lower table is not detected.

![G4](gallery/G4_docling_regions_daiwabo_p10.png)

status `partial`; tables 2/3 (+0 extra); rows 17/21; numeric cells exact 51/63; silent omissions 0/67; false assurance: no.
Source: `runs/docling_regions/daiwabo_p10/fin1_main/cold/prediction.json`.

## G5 — native_grid / daiwabo_p10

native_grid on the same slide: 3 tables, 63 numeric cells, but the third table has no printed header (roles/periods stay null).

![G5](gallery/G5_native_grid_daiwabo_p10.png)

status `partial`; tables 3/3 (+0 extra); rows 21/21; numeric cells exact 63/63; silent omissions 0/67; false assurance: no.
Source: `runs/native_grid/daiwabo_p10/fin1_main/cold/prediction.json`.

## G6 — docling_rapidocr / scan_200

Docling+RapidOCR on a 200-dpi raster of the original: the two `－` cells are boxed in red (ink present, OCR returned nothing).

![G6](gallery/G6_docling_rapidocr_scan_200.png)

status `partial`; tables 1/1 (+0 extra); rows 30/43; numeric cells exact 54/74; silent omissions 18/74; false assurance: no.
Source: `runs/docling_rapidocr/scan_200/fin1_adv/cold/prediction.json`.

## G7 — docling_rapidocr / elecom_p9_scan200

Docling+RapidOCR on the ELECOM raster: digits correct, kanji labels misread (產, 壳); affected rows carry ocr_suspect_variant_glyph.

![G7](gallery/G7_docling_rapidocr_elecom_p9_scan200.png)

status `partial`; tables 1/1 (+0 extra); rows 19/34; numeric cells exact 34/56; silent omissions 22/56; false assurance: no.
Source: `runs/docling_rapidocr/elecom_p9_scan200/fin1_raster/cold/prediction.json`.

## G8 — docling_cmtrue / rotation_90

Docling on a page with /Rotate 90 metadata: status success but rows do not match the reference.

![G8](gallery/G8_docling_cmtrue_rotation_90.png)

status `partial`; tables 1/1 (+0 extra); rows 0/43; numeric cells exact 0/74; silent omissions 74/74; false assurance: no.
Source: `runs/docling_cmtrue/rotation_90/fin1_adv/cold/prediction.json`.

## G9 — native_grid / grouped_two

native_grid on the left-aligned grouped-header control (spans are inferred and flagged, not read from rules).

![G9](gallery/G9_native_grid_grouped_two.png)

status `partial`; tables 1/1 (+0 extra); rows 4/4; numeric cells exact 16/16; silent omissions 0/16; false assurance: no.
Source: `runs/native_grid/grouped_two/fin1_adv/cold/prediction.json`.

## G10 — native_grid / vertical_spacing

native_grid on vertically stacked CJK labels: numbers captured, labels fragmented into pieces.

![G10](gallery/G10_native_grid_vertical_spacing.png)

status `partial`; tables 1/1 (+0 extra); rows 0/4; numeric cells exact 0/16; silent omissions 16/16; false assurance: no.
Source: `runs/native_grid/vertical_spacing/fin1_adv/cold/prediction.json`.
