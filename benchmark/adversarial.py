"""Deterministic source-family perturbations and from-scratch synthetic layouts.

Expected references are transformed copies, never edits to the source reference.
Generation must run before inspecting predictions. All references remain AI draft.
"""
from copy import deepcopy
import argparse
import json
from pathlib import Path

import fitz

from benchmark.annotate import header, numeric
from benchmark.common import ROOT, read_json, sha256, utc, write_json

MATERIALIZE = False


def map_boxes(value, scale, dx=0, dy=0):
    if isinstance(value, dict):
        for k, v in value.items():
            if (k.endswith('bbox') or k == 'bbox') and isinstance(v, list) and len(v) == 4:
                value[k] = [v[0]*scale+dx, v[1]*scale+dy, v[2]*scale+dx, v[3]*scale+dy]
            else:
                map_boxes(v, scale, dx, dy)
    elif isinstance(value, list):
        for v in value:
            map_boxes(v, scale, dx, dy)


def entry_for(doc_id, path, gold, operation, truth, family, reference_path):
    gold.update(document_id=doc_id, input_sha256=sha256(path), source_sha256=sha256(path),
                annotation_status='ai_draft', human_checked_cells=0, synthetic=True,
                transformation=dict(operation=operation, visual_truth=truth, source_family=family))
    if reference_path.exists():
        if not MATERIALIZE:
            raise ValueError('Reference exists; use --materialize to regenerate inputs without changing gold')
        frozen = read_json(reference_path)
        if frozen['input_sha256'] != sha256(path) or frozen['tables'] != gold['tables']:
            raise ValueError(f'Generated input/reference differs from frozen draft: {doc_id}. Check pinned package versions; do not change gold.')
    else:
        if MATERIALIZE:
            raise ValueError('Materialize mode requires an existing reference')
        write_json(reference_path, gold)
    return dict(document_id=doc_id, company='Synthetic control', source_url=None, source_page_index=0,
                page=1, source_sha256=sha256(path), input_sha256=sha256(path),
                input_path=str(path.relative_to(ROOT)), gold_path=str(reference_path.relative_to(ROOT)),
                source_kind='synthetic', source_family=family, issuer_relation='same_issuer' if family == 'ur_ai_original' else 'not_applicable_synthetic',
                split='development', domain='synthetic_financial_table', status='available',
                human_audit_status='ai_draft', human_checked_cells=0,
                difficulty=operation, visual_truth=truth,
                license_note='Local synthetic derivative; source-family rights apply')


def transformed(name, operation):
    original = ROOT/'baseline_v2/source.pdf'
    reference = ROOT/'benchmark/gold/original.json'
    gold = deepcopy(read_json(reference))
    folder = ROOT/'benchmark/data/adversarial'/name
    folder.mkdir(parents=True, exist_ok=True)
    path = folder/'page.pdf'
    source = fitz.open(original)
    output = fitz.open()
    truth = 'preserved content; rendering may change'
    if name.startswith('scan_') or name == 'text_layer_deleted':
        dpi = int(name.split('_')[1]) if name.startswith('scan_') else 300
        pix = source[0].get_pixmap(dpi=dpi, alpha=False)
        page = output.new_page(width=source[0].rect.width, height=source[0].rect.height)
        page.insert_image(page.rect, stream=pix.tobytes('png'))
        truth = f'visible glyph content retained through {dpi}dpi rasterization; all native text removed; not pixel-identical to vector original'
    elif name == 'tiny_cjk':
        page = output.new_page(width=source[0].rect.width, height=source[0].rect.height)
        page.show_pdf_page(fitz.Rect(20, 20, 20+source[0].rect.width*.5, 20+source[0].rect.height*.5), source, 0)
        map_boxes(gold, .5, 20, 20)
        gold['page_bbox'] = list(page.rect)
        truth = 'content preserved; CJK font size halved, bboxes transformed'
    else:
        output.insert_pdf(source)
        page = output[0]
        if name == 'rotation_90':
            page.set_rotation(90)
            gold['page_rotation_degrees'] = 90
            truth = 'content preserved; PDF page rotation 90 degrees; coordinates stay in unrotated PDF space'
        elif name in {'missing_cell', 'sign_erasure'}:
            row = next(r for r in gold['tables'][0]['rows'] if r['label'] == ('売掛金' if name == 'missing_cell' else '貸倒引当金'))
            cell = row['cells'][0]
            box = fitz.Rect(cell['bbox'])
            if name == 'sign_erasure':
                chars = [c for b in page.get_text('rawdict')['blocks'] for l in b.get('lines', [])
                         for s in l['spans'] for c in s['chars'] if c['c'] == '△' and box.contains(fitz.Rect(c['bbox']))]
                if len(chars) != 1:
                    raise ValueError('Sign erasure needs one source glyph')
                box = fitz.Rect(chars[0]['bbox'])
                box.x1 -= .05
                cell['raw'] = cell['raw'].removeprefix('△')
                cell['value'], cell['status'] = numeric(cell['raw'])
                truth = 'changed: only negative marker erased; derived reference expects positive printed number'
            else:
                cell.update(raw=None, value=None, status='absent_text_cell')
                truth = 'changed: one entire visible cell erased; derived reference expects explicit absent_text_cell'
            page.add_redact_annot(box, fill=(1, 1, 1))
            page.apply_redactions()
        elif name == 'footnote_marker':
            row = next(r for r in gold['tables'][0]['rows'] if r['label'] == '売掛金')
            box = row['label_bbox']
            page.insert_text((box[2]+1, box[3]-3), '*1', fontsize=5)
            row['raw_label'] += '*1'
            row['label'] += '*1'
            row['label_bbox'][2] += 7
            truth = 'changed: printed *1 added to exact row label; numbers unchanged'
    output.save(path, deflate=True, no_new_id=True)
    output.close()
    source.close()
    gold['derived_from'] = dict(gold_path=str(reference.relative_to(ROOT)), gold_sha256=sha256(reference),
                                source_sha256=sha256(original))
    return entry_for(name, path, gold, operation, truth, 'ur_ai_original', ROOT/'benchmark/gold/adversarial'/f'{name}.json')


def synthetic(name, subcolumns=2, side_by_side=False, vertical=False):
    folder = ROOT/'benchmark/data/adversarial'/name
    folder.mkdir(parents=True, exist_ok=True)
    path = folder/'page.pdf'
    doc = fitz.open()
    page = doc.new_page(width=1000 if side_by_side else 800, height=430)
    font = fitz.Font('japan')

    def text(x, y, value, size=10):
        page.insert_text((x, y), value, fontname='japan', fontsize=size)
        return [x, y-size*font.ascender, x+font.text_length(value, fontsize=size), y-size*font.descender]

    tables = []
    for table_number in range(2 if side_by_side else 1):
        x0 = 20+table_number*490
        width = 460 if side_by_side else 760
        label_width, n = (150 if side_by_side else 210), subcolumns*2
        step = (width-label_width)/n
        table = dict(table_id=f't{table_number}', page=1, bbox=[x0, 40, x0+width, 370], reading_order=table_number,
                     headers=[], rows=[], issues=[])
        for group, period in enumerate(('2025-03-31', '2026-03-31')):
            gx = x0+label_width+group*subcolumns*step
            label = '2025年3月期' if group == 0 else '2026年3月期'
            box = text(gx+4, 65, label, 10)
            table['headers'].append(dict(header_id=f'g{group}', kind='group', text=label, period=period,
                                          column_index=group*subcolumns, colspan=subcolumns, rowspan=1, bbox=box))
        # Groups are distinct from leaves; parent_id carries the structural edge.
        roles = ['amount', 'composition_pct', 'change_amount'][:subcolumns]
        for column in range(n):
            role = roles[column % subcolumns]
            raw = {'amount': '金額', 'composition_pct': '構成比', 'change_amount': '増減'}[role]
            x = x0+label_width+column*step
            box = text(x+3, 91, raw, 9)
            table['headers'].append(header(column, ('2025-03-31', '2026-03-31')[column//subcolumns], role, raw, box,
                                           parent_id=f'g{column//subcolumns}'))
        if name == 'merged_headers':
            # A single outer group spans both period groups (three header levels).
            box = text(x0+label_width+4, 35, '連結貸借対照表', 10)
            table['headers'].append(dict(header_id='outer', kind='group', text='連結貸借対照表', period=None,
                                          column_index=0, colspan=n, rowspan=1, bbox=box))
            table['bbox'][1] = 20
            for h in table['headers']:
                if h.get('header_id') in {'g0', 'g1'}:
                    h['parent_id'] = 'outer'
        values = [('現金及び預金', '1,234', '+2.5', '△0'),
                  ('貸倒引当金', '△0', '－', '+0.5'),
                  ('その他', '－', '10.25', '△2.5'),
                  ('資産合計', '+1,234', '100.0', '+0')]
        for index, (label, amount, pct, delta) in enumerate(values):
            y = 135+index*65
            label_box = text(x0+5, y, label, 10) if not vertical else None
            if vertical:
                boxes = [text(x0+5, y-20+k*7, c, 6) for k, c in enumerate(label)]
                label_box = [min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)]
            row = dict(row_id=f't{table_number}_r{index}', row_index=index, label=label, raw_label=label,
                       parent_path=[], type='total' if index == 3 else 'item', label_bbox=label_box,
                       bbox=[x0, y-30, x0+width, y+20], cells=[])
            for column in range(n):
                role = roles[column % subcolumns]
                raw = {'amount': amount, 'composition_pct': pct, 'change_amount': delta}[role]
                box = text(x0+label_width+column*step+3, y, raw, 9)
                value, status = numeric(raw)
                row['cells'].append(dict(column_index=column, header_id=f'c{column}',
                                         period=('2025-03-31', '2026-03-31')[column//subcolumns], role=role,
                                         raw=raw, value=value, status=status, bbox=box,
                                         backend='synthetic_generator', evidence_kind='native_pdf', annotation_status='ai_draft'))
            table['rows'].append(row)
        for y in [40, 73, 103, 153, 218, 283, 370]:
            page.draw_line((x0, y), (x0+width, y), width=.4)
        tables.append(table)
    doc.save(path, no_new_id=True)
    doc.close()
    gold = dict(schema_version='benchmark-1.0', document_id=name, tables=tables, page=1, source_page_index=0,
                page_bbox=[0, 0, 1000 if side_by_side else 800, 430], created_at=utc(),
                annotation_method='AI-authored synthetic fixture; deterministic values, no independent source evidence',
                verification=dict(reviewer=None), scope=dict(tables_complete=True, rows_complete=True, cells_complete=True), unit='synthetic')
    return entry_for(name, path, gold, name, 'new synthetic visual truth; no company generalization claim',
                     'synthetic_layout_controls', ROOT/'benchmark/gold/adversarial'/f'{name}.json')


def main():
    global MATERIALIZE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--materialize', action='store_true', help='Regenerate missing local PDFs against existing hashes; never overwrite references/manifest')
    MATERIALIZE = parser.parse_args().materialize
    if (ROOT/'benchmark/adversarial_manifest.jsonl').exists() and not MATERIALIZE:
        raise SystemExit('Adversarial manifest already exists; references are create-only')
    entries = [transformed(name, operation) for name, operation in [
        ('missing_cell', 'visible digital cell redaction'), ('sign_erasure', 'visible negative sign erasure'),
        ('text_layer_deleted', 'rasterized page with no native text; visible content preserved'),
        ('rotation_90', '90-degree page rotation'), ('scan_150', '150dpi raster scan'),
        ('scan_200', '200dpi raster scan'), ('tiny_cjk', '50% scale and translated page'),
        ('footnote_marker', 'superscript marker inserted in row label'),
    ]]
    entries += [synthetic('grouped_two', 2), synthetic('grouped_three', 3),
                synthetic('merged_headers', 2), synthetic('side_by_side', 2, side_by_side=True),
                synthetic('vertical_spacing', 2, vertical=True)]
    if not MATERIALIZE:
        (ROOT/'benchmark/adversarial_manifest.jsonl').write_text(''.join(json.dumps(e, ensure_ascii=False)+'\n' for e in entries), encoding='utf-8')
    print('Materialized' if MATERIALIZE else 'Created', len(entries), 'synthetic cases; none are independent issuer holdouts')


if __name__ == '__main__':
    main()
