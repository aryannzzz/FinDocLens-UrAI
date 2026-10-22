"""Auditable PDF-text-layer balance sheet parser. No OCR or model calls."""
from __future__ import annotations
import argparse, csv, json, re
from collections import defaultdict
from pathlib import Path
import fitz

NUM = re.compile(r'^[△▲−\-]?[\d,]+$|^[－—–-]$')

def parse_amount(s):
    s = s.replace(' ', '').replace('，', ',')
    if s in {'－','—','–','-'}: return None, 'dash_not_reported'
    if not NUM.fullmatch(s): raise ValueError(f'Invalid monetary token: {s!r}')
    neg = s[:1] in '△▲−-'
    n = int(s.lstrip('△▲−-').replace(',',''))
    return -n if neg else n, ('negative_zero' if neg and n == 0 else 'observed')

def get_lines(page):
    groups=defaultdict(list)
    for b in page.get_text('dict')['blocks']:
        for line in b.get('lines',[]):
            for span in line['spans']:
                token=span['text'].strip()
                if token: groups[round(span['bbox'][1],1)].append((span['bbox'][0],token,span['bbox']))
    # Group by same baseline; handles PDF spans split into distinct blocks.
    ys=sorted(groups)
    merged=[]
    for y in ys:
        if merged and abs(merged[-1][0]-y)<2.0: merged[-1][1].extend(groups[y])
        else: merged.append([y,list(groups[y])])
    return [(y, sorted(items,key=lambda x:x[0])) for y,items in merged]

def parse_page(page, page_number):
    lines=get_lines(page)
    records=[]; issues=[]; headers={}
    hierarchy=[]
    last_gross=None
    for y,items in lines:
        tokens=[(x,t,b) for x,t,b in items if t.strip()]
        full=' '.join(t for _,t,_ in tokens)
        if '単位' in full: headers['unit']='thousand_JPY'
        if '2025' in full: headers['period_previous']='2025-03-31'
        if '2026' in full: headers['period_current']='2026-03-31'
        if y<145 or y>800: continue
        left=[z for z in tokens if z[0]<290]
        old_raw=''.join(z[1] for z in tokens if 290<=z[0]<422)
        new_raw=''.join(z[1] for z in tokens if z[0]>=422)
        old=[(290,old_raw,None)] if NUM.fullmatch(old_raw) else []
        new=[(422,new_raw,None)] if NUM.fullmatch(new_raw) else []
        label=''.join(t for _,t,_ in left).strip()
        if not label:continue
        x=min(z[0] for z in left)
        if not (old or new):
            last_gross=None
            # New section starts at an indentation smaller than the last section.
            while hierarchy and hierarchy[-1]['x'] >= x-2:hierarchy.pop()
            hierarchy.append({'label':label,'x':x})
            records.append(dict(page=page_number,type='section',label=label,path=[h['label'] for h in hierarchy],indent_x=round(x,1),period_previous=None,period_current=None,raw_previous=None,raw_current=None,notes=[]))
            continue
        if len(old)!=1 or len(new)!=1:
            issues.append({'kind':'ambiguous_cells','label':label,'y':y,'old':[z[1] for z in old],'new':[z[1] for z in new]})
            continue
        oldval,oldflag=parse_amount(old[0][1]); newval,newflag=parse_amount(new[0][1])
        # Totals belong to their parent; full asset total has root path.
        is_total=label.endswith('合計')
        path=[h['label'] for h in hierarchy]
        # Explicit local gross/depreciation/net triple within tangible fixed assets.
        # Avoid treating identically named depreciation rows as interchangeable.
        if label=='減価償却累計額' and last_gross and x>last_gross['x']+4:
            path=path+[last_gross['label']]
        elif label.endswith('（純額）'):
            last_gross=None
        elif label not in {'土地','建設仮勘定'} and not is_total and ('有形固定資産' in path) and x<110:
            last_gross={'label':label,'x':x}
        if label=='資産合計':path=['資産の部']
        elif is_total and path and (label.startswith(path[-1]) or label==path[-1]+'合計'):
            path=path[:-1]
        flags=[f'{k}:{f}' for k,f in [('previous',oldflag),('current',newflag)] if f!='observed']
        records.append(dict(page=page_number,type='total' if is_total else 'item',label=label,path=path+[label],indent_x=round(x,1),period_previous=oldval,period_current=newval,raw_previous=old[0][1],raw_current=new[0][1],notes=flags))
    return records,issues,headers

def run(path):
    doc=fitz.open(path); rows=[]; issues=[]; page_meta=[]
    for n,p in enumerate(doc,1):
        rec,err,metadata=parse_page(p,n); rows.extend(rec);issues.extend(err);page_meta.append(metadata)
    monetary=[r for r in rows if r['type']!='section']
    if not monetary:issues.append({'kind':'no_monetary_rows','message':'May be image-only or unsupported layout; OCR/VLM is NOT implemented.'})
    totals={r['label']:r for r in monetary if r['type']=='total'}
    # Compare independent declared subtotals; discrepancy can be rounding in reported thousand-yen amounts.
    checks=[]
    for parent,parts in [('資産合計',['流動資産合計','固定資産合計']),('固定資産合計',['有形固定資産合計','無形固定資産合計','投資その他の資産合計'])]:
        for year in ('period_previous','period_current'):
            if parent in totals and all(v in totals for v in parts):
                actual=totals[parent][year]; calculated=sum(totals[x][year] for x in parts)
                checks.append({'check':parent,'period':year,'reported':actual,'sum_of_components':calculated,'difference':actual-calculated,'within_rounding_tolerance_2':abs(actual-calculated)<=2})
    return {'schema_version':'1.0','source':str(path),'pages':len(doc),'page_metadata':page_meta,'rows':rows,'issues':issues,'checks':checks,'stats':{'rows_total':len(rows),'monetary_rows':len(monetary),'two_value_rows':sum(r['period_previous'] is not None and r['period_current'] is not None for r in monetary)}}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('pdf');ap.add_argument('--out',default='output');a=ap.parse_args()
    output=Path(a.out);output.mkdir(parents=True,exist_ok=True)
    result=run(a.pdf)
    (output/'table.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    with (output/'table.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.writer(f);w.writerow(['page','type','hierarchical_path','label_ja','2025-03-31_thousand_JPY','2026-03-31_thousand_JPY','raw_2025','raw_2026','notes'])
        for r in result['rows']:w.writerow([r['page'],r['type'],' / '.join(r['path']),r['label'],r['period_previous'],r['period_current'],r['raw_previous'],r['raw_current'],'; '.join(r['notes'])])
    print(json.dumps({'stats':result['stats'],'issues':result['issues'],'checks':result['checks']},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
