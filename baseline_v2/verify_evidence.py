"""Second PDF text extractor cross-check: NOT independent visual truth / OCR."""
import json,argparse,unicodedata
from pathlib import Path
import pdfplumber
from parser_v2 import run

def check(pdf,parsed=None):
    parsed=parsed or run(pdf)
    detail=[]
    with pdfplumber.open(pdf) as doc:
        by_page={i+1:page.chars for i,page in enumerate(doc.pages)}
        for row in parsed['rows']:
            for cell in row['cells']:
                if cell['bbox'] is None:continue
                x0,y0,x1,y1=cell['bbox']
                chars=[c for c in by_page[row['page']] if x0-.4<=(c['x0']+c['x1'])/2<=x1+.4 and y0-1.5<=(c['top']+c['bottom'])/2<=y1+1.5]
                found=''.join(c['text'] for c in sorted(chars,key=lambda c:c['x0']))
                match=unicodedata.normalize('NFKC',found)==unicodedata.normalize('NFKC',cell['raw'])
                detail.append({'page':row['page'],'row':row['row'],'label':row['label'],'column':cell['column'],'pymupdf':cell['raw'],'pdfplumber':found,'match':match})
    return {'verification':'independent_pdf_native_engine_not_visual_ground_truth','compared':len(detail),'agreed':sum(x['match'] for x in detail),'mismatched':[x for x in detail if not x['match']]}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('pdf');p.add_argument('--out',default='output/cross_engine.json');a=p.parse_args()
    report=check(a.pdf)
    Path(a.out).parent.mkdir(exist_ok=True,parents=True)
    Path(a.out).write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps({'compared':report['compared'],'agreed':report['agreed'],'mismatches':len(report['mismatched'])},indent=2))
