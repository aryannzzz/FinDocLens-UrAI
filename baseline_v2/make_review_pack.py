"""Prepare targeted visual VLM/human review inputs; does NOT call any model."""
import json,argparse,re
from pathlib import Path
import fitz
from parser_v2 import run

REVIEW_INSTRUCTIONS="""You are reviewing a Japanese financial-table extraction. Use ONLY the supplied page crop as evidence.
Return JSON containing {\"transcription\": [{\"label\":...,\"previous_raw\":...,\"current_raw\":...}], \"uncertain\":true|false,\"reason\":...}.
Preserve △ (negative), △0, － (not reported), column associations and thousands-of-yen units verbatim.
If any glyph is invisible/ambiguous, mark uncertain. Do not recompute or edit numbers to force totals.
A human must confirm proposed changes against the PDF image; these proposals are never automatically merged.
"""

def make_pack(pdf,output):
    parsed=run(pdf);output=Path(output);output.mkdir(parents=True,exist_ok=True)
    doc=fitz.open(pdf)
    tasks=[]
    for page_data in parsed['pages']:
        issues=page_data['issues']
        if not issues:continue
        page=doc[page_data['page']-1]
        for index,issue in enumerate(issues,1):
            target=next((r for r in page_data['rows'] if issue.get('label')==r['label']),None)
            # Reconciliation violations need a page-level crop because the offending cell is unknown.
            region=page.rect
            if target and issue['code']=='partial_data_row':
                r=fitz.Rect(target['bbox']);region=fitz.Rect(max(0,r.x0-18),max(0,r.y0-15),min(page.rect.x1,r.x1+12),min(page.rect.y1,r.y1+15))
            image=page.get_pixmap(matrix=fitz.Matrix(2,2),clip=region,alpha=False)
            filename=f"review_page_{page_data['page']}_issue_{index}.png";image.save(output/filename)
            tasks.append({'page':page_data['page'],'issue':issue,'image':filename,'region_pdf_pts':[round(float(v),2) for v in region], 'prompt':'review_prompt.txt'})
    (output/'review_prompt.txt').write_text(REVIEW_INSTRUCTIONS)
    (output/'review_tasks.json').write_text(json.dumps({'model_executed':False,'automatic_merge_allowed':False,'tasks':tasks},ensure_ascii=False,indent=2))
    return tasks

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('pdf');p.add_argument('--out',default='output/review');args=p.parse_args()
    print(f'{len(make_pack(args.pdf,args.out))} review tasks prepared; no model called')
