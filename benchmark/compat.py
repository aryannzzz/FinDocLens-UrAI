"""Loss-disclosing, evaluation-only view of immutable v2 predictions.

No extraction logic. Original model/native result must be saved separately.
V2 has no table detector: a page's row union becomes one hypothesized table.
"""
from copy import deepcopy


def union(boxes):
    boxes = [b for b in boxes if b]
    return [min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes)] if boxes else None


def from_v2(data, document_id, source_sha256, input_sha256=None):
    tables = []
    for page in data.get('pages', []):
        rows = []
        for row in page['rows']:
            cells = [dict(deepcopy(cell), column_index=cell['column'],
                          header_id=f"c{cell['column']}", role='amount',
                          backend='v2', evidence_kind='native_pdf') for cell in row['cells']]
            rows.append(dict(row_id=f"r{row['row']}", row_index=row['row']-1, label=row['label'],
                             raw_label=row['label'], parent_path=row['path'][:-1], bbox=row['bbox'],
                             type=row['type'], cells=cells, issues=row.get('review', [])))
        if rows:
            tables.append(dict(table_id=f"v2_page_{page['page']}", page=page['page'],
                               bbox=union([r['bbox'] for r in rows]), reading_order=0,
                               detection_method='page row union; no independent table detection',
                               headers=[dict(header_id=f'c{i}', column_index=i, period=p, role='amount',
                                             text=None, bbox=None, kind='leaf', colspan=None, rowspan=None,
                                             capability_status='period from v2; role from monetary parser; source header spans unavailable')
                                        for i, p in enumerate(page['periods'])],
                               rows=rows, issues=page['issues']))
    issues = deepcopy(data.get('issues', []))
    return dict(schema_version='benchmark-1.0', document_id=document_id, source_sha256=source_sha256,
                input_sha256=input_sha256 or source_sha256, backend='v2', model_revision=None,
                page_bbox=None, page_bbox_status='source PDF metadata required; v2 does not expose page rotation',
                status='abstained' if not tables else 'partial' if issues else 'success',
                tables=tables, issues=issues,
                capabilities=dict(table_detection=False, grouped_headers=False, grid_spans=False),
                provenance='Evaluation-only projection; original_result.json retains unchanged v2 output')
