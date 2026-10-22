"""Source-only annotation bootstrap with issuer-specific, declared draft regions.

Never reads holdout model predictions. Draft files are create-only. Coordinates
are PDF points on the selected page, top-left origin, page numbering starts at 1.
"""
import argparse
import csv
from decimal import Decimal
import re
import unicodedata

import fitz

from benchmark.common import ROOT, read_json, sha256, utc, write_json
from benchmark.compat import union


def numeric(raw):
    if raw is None:
        return None, 'absent_text_cell'
    if raw.strip() in {'－', '—', '–', '-'}:
        return None, 'not_reported'
    s = unicodedata.normalize('NFKC', re.sub(r'\s+', '', raw)).replace(',', '')
    sign = -1 if s.startswith(('△', '▲', '−', '-')) else 1
    s = s.lstrip('△▲−-+')
    if not re.fullmatch(r'\d+(?:\.\d+)?%?', s):
        return None, 'unparseable'
    value = Decimal(s.rstrip('%')) * sign
    return (int(value) if value == value.to_integral() else str(value)), 'negative_zero' if value == 0 and sign == -1 else 'observed'


def source_lines(page, box, tolerance=3):
    spans = [dict(text=s['text'], bbox=list(s['bbox']))
             for b in page.get_text('dict', flags=fitz.TEXTFLAGS_DICT & ~fitz.TEXT_PRESERVE_IMAGES)['blocks']
             for l in b.get('lines', []) for s in l['spans'] if s['text'].strip()
             and box[0] <= (s['bbox'][0]+s['bbox'][2])/2 < box[2]
             and box[1] <= (s['bbox'][1]+s['bbox'][3])/2 < box[3]]
    spans.sort(key=lambda s: (s['bbox'][1]+s['bbox'][3])/2)
    groups = []
    for span in spans:
        cy = (span['bbox'][1]+span['bbox'][3])/2
        if groups and abs(cy-groups[-1][0]) < tolerance:
            groups[-1][1].append(span)
        else:
            groups.append((cy, [span]))
    return [sorted(spans, key=lambda s: s['bbox'][0]) for _, spans in groups]


def header(index, period, role, text, bbox, **extra):
    return dict(header_id=f'c{index}', column_index=index, period=period, role=role, text=text,
                bbox=bbox, kind='leaf', colspan=1, rowspan=1, annotation_status='ai_draft', **extra)


def table_rows(page, table, bands):
    rows = []
    for spans in source_lines(page, table['body_bbox'], tolerance=4):
        label_spans = [s for s in spans if s['bbox'][0] < bands[0][0]]
        label = ''.join(s['text'] for s in label_spans)
        if not label:
            raise ValueError('Unlabeled source row in annotation region')
        cells = []
        for column, (lo, hi) in enumerate(bands):
            pieces = [s for s in spans if lo <= (s['bbox'][0]+s['bbox'][2])/2 < hi]
            if not pieces:
                continue  # section rows have zero numeric cells; inspect/review explicitly
            raw = ''.join(s['text'] for s in pieces)
            h = table['headers'][column]
            value, status = (raw, 'observed') if h['role'] == 'other' else numeric(raw)
            if status == 'unparseable':
                raise ValueError(f'Unparseable source token in draft: {label}: {raw}')
            cells.append(dict(column_index=column, header_id=h['header_id'], period=h['period'], role=h['role'],
                              raw=raw, value=value, status=status, bbox=union([s['bbox'] for s in pieces]),
                              backend='annotation_native_bootstrap', evidence_kind='native_pdf', annotation_status='ai_draft'))
        rows.append(dict(row_id=f"{table['table_id']}_r{len(rows)+1:03d}", row_index=len(rows),
                         raw_label=label, label=label, label_bbox=union([s['bbox'] for s in label_spans]),
                         bbox=union([s['bbox'] for s in spans]), parent_path=[],
                         type='item' if cells else 'section', cells=cells, annotation_status='ai_draft'))
    return rows


def elecom(page):
    table = dict(table_id='assets', page=1, bbox=[54.5, 101, 522.7, 543.5],
                 body_bbox=[54.5, 128, 522.7, 543.5], reading_order=0,
                 headers=[header(0, '2025-03-31', 'amount', '前連結会計年度(2025年３月31日)', [300, 105, 396, 126]),
                          header(1, '2026-03-31', 'amount', '当連結会計年度(2026年３月31日)', [424, 105, 521, 126])], issues=[])
    table['rows'] = table_rows(page, table, [(280, 430), (430, 540)])
    sections = []
    for row in table['rows']:
        label = row['label']
        if row['type'] == 'section':
            x = row['label_bbox'][0]
            while sections and sections[-1][1] >= x-1:
                sections.pop()
            row['parent_path'] = [s[0] for s in sections]
            sections.append((label, x))
        elif label.endswith('合計'):
            row['type'] = 'total'
            name = label[:-2]
            base = next((i for i, (s, _) in enumerate(sections) if s == name), None)
            row['parent_path'] = [s[0] for s in sections[:base]] if base is not None else ['資産の部']
            if label == '資産合計':
                row['parent_path'] = ['資産の部']
        else:
            row['parent_path'] = [s[0] for s in sections]
    return [table]


def daiwabo(page):
    tables = []
    for table_id, box, body, bands, header_boxes in [
        ('assets', [50, 67, 467, 416], [50, 101, 467, 413], [(195, 280), (280, 380), (380, 467)], [[205, 73, 273, 98], [291, 73, 372, 98], [389, 73, 460, 98]]),
        ('liabilities_equity', [480, 67, 912, 416], [480, 101, 912, 413], [(625, 712), (712, 824), (824, 912)], [[635, 73, 703, 98], [735, 73, 816, 98], [831, 73, 904, 98]]),
        ('explanation', [58, 417, 930, 522], [58, 417, 930, 522], [(295, 380), (420, 510), (520, 610), (615, 930)], [None]*4),
    ]:
        table = dict(table_id=table_id, page=1, bbox=box, body_bbox=body, reading_order=len(tables),
                     headers=[header(0, '2025-03-31', 'amount', '2025/3' if table_id != 'explanation' else None, header_boxes[0]),
                              header(1, '2025-12-31', 'amount', '2025/12' if table_id != 'explanation' else None, header_boxes[1]),
                              header(2, '2025-12-31_vs_2025-03-31', 'change_amount', '増減' if table_id != 'explanation' else None, header_boxes[2])], issues=[])
        if table_id == 'explanation':
            table['headers'].append(header(3, None, 'other', None, None, status='implicit_unprinted'))
            for h in table['headers']:
                h['status'] = 'implicit_unprinted; period association AI-drafted from upper tables'
        table['rows'] = table_rows(page, table, bands)
        # Arrows are a relation marker, not a fourth financial numeric column.
        if table_id == 'assets':
            for r in table['rows'][1:4]:
                r['parent_path'] = ['流動資産']
        elif table_id == 'liabilities_equity':
            for r in table['rows'][1:3]:
                r['parent_path'] = ['流動負債']
            table['rows'][4]['parent_path'] = ['固定負債']
            table['rows'][7]['parent_path'] = ['純資産合計']
        for r in table['rows']:
            if r['label'].endswith('合計'):
                r['type'] = 'total'
        tables.append(table)
    return tables


def original(page):
    table = dict(table_id='assets', page=1, bbox=[60, 120, 529, 680], body_bbox=[60, 146, 540, 680], reading_order=0,
                 headers=[header(0, '2025-03-31', 'amount', '(2025 年３月31 日)', [297, 121, 398, 142]),
                          header(1, '2026-03-31', 'amount', '(2026 年３月31 日)', [422, 121, 523, 142])], issues=[])
    # Original row reference is the frozen AI-authored TSV, not independent human gold.
    source = table_rows(page, table, [(275, 410), (410, 540)])
    with (ROOT/'baseline_v2/tests/gold_rows.tsv').open() as handle:
        reference = list(csv.DictReader(handle, delimiter='\t'))
    used = set()
    rows = []
    for ref in reference:
        path = ref['path'].split('/')
        candidates = [(i, r) for i, r in enumerate(source) if i not in used and r['label'] == path[-1]]
        if not candidates:
            raise ValueError(f'Original TSV label absent in source region: {path}')
        i, row = candidates[0]
        used.add(i)
        row.update(row_index=len(rows), type=ref['type'], parent_path=path[:-1])
        if ref['type'] != 'section':
            assert [c['raw'] for c in row['cells']] == [ref['raw_2025'], ref['raw_2026']]
        rows.append(row)
    table['rows'] = rows
    table['bbox'] = union([r['bbox'] for r in rows] + [[275, 112, 529, 120]])
    return [table]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--document', choices=['original', 'elecom_p9', 'daiwabo_p10'], required=True)
    args = parser.parse_args()
    import json
    entry = next(json.loads(s) for s in (ROOT/'benchmark/manifest.jsonl').read_text().splitlines()
                 if json.loads(s)['document_id'] == args.document)
    target = ROOT/'benchmark/gold'/f'{args.document}.json'
    if target.exists():
        parser.error('Draft exists. No overwrite: use a documented correction record with source evidence.')
    with fitz.open(ROOT/entry['input_path']) as doc:
        tables = {'original': original, 'elecom_p9': elecom, 'daiwabo_p10': daiwabo}[args.document](doc[0])
        result = dict(schema_version='benchmark-1.0', document_id=args.document, source_sha256=entry['source_sha256'],
                      input_sha256=entry['input_sha256'], source_page_index=entry['source_page_index'],
                      page=1, page_bbox=list(doc[0].rect), annotation_status='ai_draft', human_checked_cells=0,
                      annotation_method='AI-selected regions and hierarchy; source-native token bootstrap; AI visual inspection; no holdout predictions read',
                      created_at=utc(), verification=dict(reviewer=None, date=None, evidence=None),
                      scope=dict(tables_complete=True, rows_complete=True, cells_complete=True,
                                 note='Selected page only. Completeness and hierarchy are AI draft assertions pending human verification.'),
                      unit='million_JPY' if args.document != 'original' else 'thousand_JPY', tables=tables)
    write_json(target, result)
    print(args.document, 'ai_draft', len(tables), 'tables', sum(len(t['rows']) for t in tables), 'rows',
          sum(len(r['cells']) for t in tables for r in t['rows']), 'cells', sha256(target))


if __name__ == '__main__':
    main()
