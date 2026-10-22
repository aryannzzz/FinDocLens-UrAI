"""Layout-adaptive, evidence-linked parser for PDF-native Japanese financial tables.

No OCR/VLM runs. Uses unsupervised right-edge clustering and PDF geometry.
Fails closed on missing/ambiguous cells; original glyphs are never changed.
"""
from __future__ import annotations
import argparse, csv, json, math, re, statistics, unicodedata
from collections import Counter
from pathlib import Path
import fitz

AMOUNT = re.compile(r'^[△▲−-]?(?:\d{1,3}(?:,\d{3})+|\d+)$|^[－—–-]$')
AMOUNT_FRAGMENT = re.compile(r'^[△▲−－—–\d,\-]+$')
JP = re.compile(r'[\u3040-\u30ff\u3400-\u9fff]')


def normalize_amount(raw):
    s = unicodedata.normalize('NFKC', raw.strip()).replace(' ', '').replace('，', ',')
    if raw.strip() in {'－', '—', '–', '-'}: return None, 'not_reported'
    if not AMOUNT.fullmatch(s) and not AMOUNT.fullmatch(raw.strip()):
        raise ValueError(f'Invalid monetary token: {raw!r}')
    negative = s.startswith(('△', '▲', '−', '-'))
    n = int(s.lstrip('△▲−-').replace(',', ''))
    return -n if negative else n, 'negative_zero' if negative and n == 0 else 'observed'


def bbox_union(boxes):
    return [round(min(v[i] for v in boxes), 2) if i < 2 else round(max(v[i] for v in boxes), 2) for i in range(4)] if boxes else None


def read_lines(page):
    """Merge spans belonging to one physical row even across PDF text blocks."""
    spans=[]
    for block in page.get_text('dict', sort=False)['blocks']:
        for line in block.get('lines', []):
            for span in line.get('spans', []):
                s=span['text'].strip()
                if not s: continue
                box=tuple(span['bbox'])
                spans.append({'text':s,'bbox':box,'x':box[0], 'cy':(box[1]+box[3])/2, 'height':box[3]-box[1]})
    spans.sort(key=lambda z:z['cy'])
    rows=[]
    for s in spans:
        if rows and abs(s['cy']-rows[-1]['cy'])<=max(1.5, min(s['height'],rows[-1]['median_height'])*0.33):
            rr=rows[-1];rr['spans'].append(s)
            rr['cy']=statistics.median(t['cy'] for t in rr['spans'])
            rr['median_height']=statistics.median(t['height'] for t in rr['spans'])
        else:
            rows.append({'cy':s['cy'],'median_height':s['height'],'spans':[s]})
    for r in rows:
        r['spans'].sort(key=lambda s:s['x'])
        r['amounts']=[]
        current=[]
        def flush():
            if current:
                raw=''.join(s['text'] for s in current)
                if AMOUNT.fullmatch(raw):
                    r['amounts'].append({'raw':raw,'bbox':bbox_union([s['bbox'] for s in current]), 'spans':current.copy()})
                current.clear()
        for s in r['spans']:
            if AMOUNT_FRAGMENT.fullmatch(s['text']):
                if current and s['bbox'][0]-current[-1]['bbox'][2] > max(2.2,s['height']*0.40): flush()
                current.append(s)
            else: flush()
        flush()
        r['text']=''.join(s['text'] for s in r['spans'])
    return rows


def cluster_endpoints(values, tol):
    groups=[]
    for end in sorted(values):
        match=next((g for g in groups if abs(end-statistics.median(g))<tol),None)
        if match is None:groups.append([end])
        else:match.append(end)
    return sorted([(len(g),statistics.median(g)) for g in groups],reverse=True)


def infer_anchors(lines,page_width):
    """Infer monetary columns from repeated right-aligned endpoints, without x cutoffs."""
    eligible=[]
    for r in lines:
        if len(r['amounts'])<2:continue
        if not JP.search(r['text']):continue
        numeric=[a for a in r['amounts'] if a['bbox'][0]>page_width*.15]
        if len(numeric)<2:continue
        last=sorted(numeric,key=lambda a:a['bbox'][2])[-2:]
        if last[1]['bbox'][2]-last[0]['bbox'][2] < page_width*.09:continue
        eligible.append((r,last))
    if len(eligible)<3:return None,{'reason':'insufficient_tabular_evidence','candidate_rows':len(eligible)}
    clusters=cluster_endpoints([a['bbox'][2] for _,last in eligible for a in last], max(2, page_width*.008))
    winners=[]
    for count,end in clusters:
        if all(abs(end-e)>=page_width*.09 for e in winners):winners.append(end)
        if len(winners)==2:break
    if len(winners)!=2 or min(sum(abs(a['bbox'][2]-x)<page_width*.008 for _,last in eligible for a in last) for x in winners)<3:
        return None,{'reason':'unstable_column_anchors','endpoint_clusters':clusters[:6]}
    return sorted(winners),{'candidate_rows':len(eligible),'endpoint_clusters':[(n,round(v,2)) for n,v in clusters[:6]]}


def parse_dates(lines,anchors):
    """Find all Japanese fiscal dates in reading order (often one shared PDF row)."""
    dates=[]
    for r in lines:
        normalized=unicodedata.normalize('NFKC',r['text']).replace(' ','')
        for m in re.finditer(r'(20\d{2})年(\d{1,2})月(\d{1,2})日',normalized):
            month, day=int(m[2]),int(m[3])
            if 1<=month<=12 and 1<=day<=31:
                dates.append(f'{int(m[1]):04d}-{month:02d}-{day:02d}')
        if len(dates)>=len(anchors):break
    return dates[:len(anchors)] if len(dates)>=len(anchors) and len(set(dates[:len(anchors)]))==len(anchors) else [None]*len(anchors)


def section_path(sections,label,indent):
    if label.endswith('合計'):
        prefix=label[:-2]
        for k in range(len(sections)-1,-1,-1):
            if sections[k]['label']==prefix:
                return [s['label'] for s in sections[:k]]+[label]
        if label=='資産合計' and sections:return [sections[0]['label'],label]
    return [s['label'] for s in sections if s['x'] < indent+2]+[label]


def parse_page(page,page_number):
    rows=read_lines(page)
    anchors,detail=infer_anchors(rows,page.rect.width)
    result={'page':page_number,'page_size':[round(page.rect.width,2),round(page.rect.height,2)],'source':'pymupdf_pdf_text', 'column_anchors':anchors,'anchor_diagnostics':detail,'periods':[],'unit':None,'rows':[],'issues':[],'checks':[]}
    if anchors is None:
        result['issues'].append({'severity':'error','code':'needs_visual_fallback','message':'No stable native text columns: OCR/VLM is required and not run.'})
        return result
    result['periods']=parse_dates(rows,anchors)
    if None in result['periods']:result['issues'].append({'severity':'warning','code':'missing_period_header'})
    if any('単位' in r['text'] and '千円' in r['text'] for r in rows):result['unit']='thousand_JPY'
    else:result['issues'].append({'severity':'warning','code':'unit_not_detected'})
    tol=max(3,page.rect.width*.008)
    candidates=[]
    for r in rows:
        assigned=[];extra=[]
        for amount in r['amounts']:
            ds=[abs(amount['bbox'][2]-anchor) for anchor in anchors]
            j=min(range(len(anchors)),key=ds.__getitem__)
            if ds[j]<=tol:assigned.append((j,amount,ds[j]))
            else:extra.append(amount)
        bycol={}
        for col,amt,offset in assigned:bycol.setdefault(col,[]).append((amt,offset))
        # Take only rows with evidence for *both* value columns, avoiding lone numeric footer/header noise.
        if len(bycol)!=len(anchors):continue
        if any(len(v)!=1 for v in bycol.values()):
            result['issues'].append({'severity':'error','code':'duplicate_amount_column','y':round(r['cy'],2)})
            continue
        first_x=min(a['bbox'][0] for v in bycol.values() for a,_ in v)
        label_spans=[s for s in r['spans'] if s['bbox'][2]<=first_x-tol and not AMOUNT.fullmatch(s['text'])]
        label=''.join(s['text'] for s in label_spans).strip()
        if not label or not JP.search(label):continue
        candidates.append((r,bycol,label,label_spans,extra))
    if not candidates:
        result['issues'].append({'severity':'error','code':'no_verified_data_rows'})
        return result
    heights=[c[0]['cy'] for c in candidates]
    spacings=[b-a for a,b in zip(heights,heights[1:]) if 2<b-a<page.rect.height*.05]
    pitch=statistics.median(spacings) if spacings else page.rect.height*.016
    lo=min(heights)-2.3*pitch;hi=max(heights)+pitch*1.7
    candidate_y={id(c[0]):c for c in candidates}
    # Explicitly retain partial rows. Missing cells must not disappear without warning.
    for row in rows:
        if id(row) in candidate_y or not(lo<=row['cy']<=hi):continue
        assigned={}
        for amount in row['amounts']:
            errors=[abs(amount['bbox'][2]-anchor) for anchor in anchors]
            col=min(range(len(anchors)),key=errors.__getitem__)
            if errors[col]<=tol:assigned.setdefault(col,[]).append((amount,errors[col]))
        if len(assigned)!=1 or any(len(v)!=1 for v in assigned.values()):continue
        start=min(t[0]['bbox'][0] for v in assigned.values() for t in v)
        label_spans=[t for t in row['spans'] if t['bbox'][2]<=start-tol and not AMOUNT.fullmatch(t['text'])]
        label=''.join(t['text'] for t in label_spans).strip()
        if JP.search(label) and label_spans:
            candidate_y[id(row)]=(row,assigned,label,label_spans,[])
            result['issues'].append({'severity':'warning','code':'partial_data_row','label':label,'y':round(row['cy'],2),'present_columns':sorted(assigned)})
    sections=[];gross=None
    for row in rows:
        if not (lo<=row['cy']<=hi):continue
        c=candidate_y.get(id(row))
        if c:
            _,bycol,label,label_spans,extra=c
            x=min(s['bbox'][0] for s in label_spans)
            is_total=label.endswith('合計')
            path=section_path(sections,label,x) if is_total else [s['label'] for s in sections]+[label]
            association=None
            if not is_total and label=='減価償却累計額' and gross and x>gross['x']+2:
                association=gross['label'];path=[s['label'] for s in sections]+[gross['label'],label]
            elif not is_total and label.endswith('（純額）') and gross:
                association=gross['label'];path=[s['label'] for s in sections]+[gross['label'],label]
                gross=None
            elif not is_total and ('有形固定資産' in [s['label'] for s in sections]) and (not label.endswith('（純額）')):
                parent_indent=sections[-1]['x'] if sections else x
                if x>parent_indent+2 and x<parent_indent+max(25,page.rect.width*.06) and label!='減価償却累計額':
                    gross={'label':label,'x':x}
            vals=[]
            for idx in range(len(anchors)):
                if idx not in bycol:
                    vals.append({'column':idx,'period':result['periods'][idx],'raw':None,'value':None,'status':'absent_text_cell','bbox':None,'anchor_residual_pt':None,'evidence':'missing'})
                else:
                    amt,dist=bycol[idx][0]
                    value,status=normalize_amount(amt['raw'])
                    vals.append({'column':idx,'period':result['periods'][idx], 'raw':amt['raw'], 'value':value,'status':status,'bbox':amt['bbox'],'anchor_residual_pt':round(dist,3),'evidence':'embedded_pdf_text'})
            record={'page':page_number,'row':len(result['rows'])+1,'type':'total' if is_total else 'item','label':label,'path':path, 'association':association, 'indent_x':round(x,2),'bbox':bbox_union([s['bbox'] for s in row['spans']]),'label_bbox':bbox_union([s['bbox'] for s in label_spans]),'cells':vals,'review':[]}
            if any(v['status']=='absent_text_cell' for v in vals): record['review'].append('missing_displayed_cell')
            if extra and any(a['bbox'][0]>min(anchors)-page.rect.width*.1 for a in extra):
                record['review'].append('extra_numeric_tokens')
            result['rows'].append(record)
        else:
            # A real section row has Japanese text on the left, and no cells on the right.
            if not JP.search(row['text']):continue
            left=[s for s in row['spans'] if s['bbox'][2]<anchors[0]-page.rect.width*.12]
            right=[s for s in row['spans'] if s not in left]
            if not left or right:continue
            label=''.join(s['text'] for s in left).strip()
            if not label or any(ch in label for ch in ['単位','会計年度']):continue
            x=min(s['bbox'][0] for s in left)
            while sections and x<=sections[-1]['x']+2: sections.pop()
            sections.append({'label':label,'x':x})
            gross=None
            result['rows'].append({'page':page_number,'row':len(result['rows'])+1,'type':'section','label':label,'path':[s['label'] for s in sections], 'indent_x':round(x,2),'bbox':bbox_union([s['bbox'] for s in left]), 'label_bbox':bbox_union([s['bbox'] for s in left]), 'cells':[], 'review':[]})
    result['checks']=check_finances(result['rows'])
    for check in result['checks']:
        if not check['plausibly_rounded']:
            result['issues'].append({'severity':'warning','code':'financial_reconciliation_failure',
               'check':check['name'],'period':check['period'],'difference':check['difference']})
    return result


def check_finances(rows):
    """Diagnostic checks. Respect displayed rounding and never repair values."""
    totals={tuple(r['path']):r for r in rows if r['type']=='total'}
    items=[r for r in rows if r['type']=='item']
    checks=[]
    def add(label,parents,children,year):
        expected=totals.get(tuple(parents))
        if expected is None or any(child is None for child in children):return
        a=expected['cells'][year]['value'];v=[child['cells'][year]['value'] for child in children]
        if a is None:return
        if any(t is None for t in v):return
        delta=a-sum(v)
        checks.append({'name':label,'period':expected['cells'][year]['period'],'column':year,'reported':a,'calculated':sum(v),'difference':delta,'plausibly_rounded':abs(delta)<=max(1,len(v)),'kind':'subtotal'})
    # Group by hierarchical sections, keeping only net rows when gross-depreciation-net groups exist.
    for target in rows:
        if target['type']!='total':continue
        name=target['label'][:-2]
        section=next((s for s in rows if s['type']=='section' and s['label']==name and s['path'][:-1]==target['path'][:-1]),None)
        if section is None:continue
        section_prefix=section['path']
        direct=[r for r in items if r['path'][:len(section_prefix)]==section_prefix and (
            len(r['path'])==len(section_prefix)+1 or (len(r['path'])==len(section_prefix)+2 and r['label'].endswith('（純額）')))]
        # Eliminate gross rows when the same account has a corresponding net row.
        gross_with_net={r['path'][len(section_prefix)] for r in direct if len(r['path'])==len(section_prefix)+2 and r['label'].endswith('（純額）')}
        direct=[r for r in direct if not (len(r['path'])==len(section_prefix)+1 and r['label'] in gross_with_net)]
        if direct:
            for y in range(2):add(name+' subtotal',target['path'],direct,y)
    # Section totals may themselves be nested into a parent subtotal (e.g. tangible/intangible/investment).
    for target in rows:
        if target['type']!='total':continue
        prefix=target['label'][:-2]
        section=next((r for r in rows if r['type']=='section' and r['label']==prefix and r['path'][:-1]==target['path'][:-1]),None)
        if section is None:continue
        children=[r for r in rows if r['type']=='total' and r is not target and r['path'][:-1]==section['path']]
        if children:
            for y in range(2):add(prefix+' child totals',target['path'],children,y)
    # Example has outermost 資産合計 with one subtotal for 流動 and one 固定; section-level detection above handles it.
    for net in items:
        if not (net.get('association') and net['label'].endswith('（純額）')):continue
        gross=next((a for a in items if a['label']==net['association'] and a['path']==net['path'][:-2]+[net['association']]),None)
        dep=next((a for a in items if a['label']=='減価償却累計額' and a['path']==net['path'][:-1]+['減価償却累計額']),None)
        if not gross or not dep:continue
        for y in range(2):
            vals=[r['cells'][y]['value'] for r in (gross,dep,net)]
            if any(v is None for v in vals):continue
            checks.append({'name':'gross + depreciation = net: '+gross['label'],'period':net['cells'][y]['period'],'column':y,'reported':vals[2], 'calculated':vals[0]+vals[1],'difference':vals[2]-vals[0]-vals[1], 'plausibly_rounded':abs(vals[2]-vals[0]-vals[1])<=1,'kind':'net_asset'})
    # Add top-level assets sum; financial statement could use varied labels, so constrain to an explicit pair.
    curr=next((r for r in rows if r['label']=='流動資産合計'),None)
    fixed=next((r for r in rows if r['label']=='固定資産合計'),None)
    total=next((r for r in rows if r['label']=='資産合計'),None)
    if curr and fixed and total:
        for y in range(2):
            vals=[r['cells'][y]['value'] for r in (curr,fixed,total)]
            delta=vals[2]-vals[0]-vals[1]
            checks.append({'name':'total assets','period':total['cells'][y]['period'],'column':y,'reported':vals[2],'calculated':vals[0]+vals[1], 'difference':delta, 'plausibly_rounded':abs(delta)<=2,'kind':'subtotal'})
    return checks


def run(path):
    doc=fitz.open(path);pages=[parse_page(p,i) for i,p in enumerate(doc,1)]
    rows=[r for p in pages for r in p['rows']]
    issues=[dict(page=p['page'],**x) for p in pages for x in p['issues']]
    checks=[dict(page=p['page'],**x) for p in pages for x in p['checks']]
    stats={'pages':len(pages),'sections':sum(r['type']=='section' for r in rows),'monetary_rows':sum(r['type']!='section' for r in rows),'complete_rows':sum(r['type']!='section' and len(r['cells'])==2 and all(c['status']!='absent_text_cell' for c in r['cells']) for r in rows),'reported_cell_count':sum(sum(c['status']!='absent_text_cell' for c in r['cells']) for r in rows),'issues':len(issues),'nonzero_reconciliation_differences':sum(x['difference']!=0 for x in checks)}
    return {'schema_version':'2.0','source_file':str(path),'method':'adaptive_pdf_native_no_ocr_or_vlm', 'pages':pages,'rows':rows,'issues':issues,'checks':checks,'stats':stats}


def write_outputs(data, out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    (out/'table.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    with (out/'table.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['page','type','hierarchy','Japanese_account','first_period','second_period','raw_first','raw_second','first_cell_bbox','second_cell_bbox','review'])
        for r in data['rows']:
            c=r['cells'];w.writerow([r['page'],r['type'],' / '.join(r['path']),r['label'],*(c[i]['value'] if len(c)>i else '' for i in (0,1)),*(c[i]['raw'] if len(c)>i else '' for i in (0,1)),*(c[i]['bbox'] if len(c)>i else '' for i in (0,1)), '; '.join(r['review'])])
    (out/'validation.json').write_text(json.dumps({'stats':data['stats'],'checks':data['checks'],'issues':data['issues']},ensure_ascii=False,indent=2),encoding='utf-8')


def draw_evidence(pdf,out,parsed):
    doc=fitz.open(pdf)
    for n,page in enumerate(doc):
        overlay=page.new_shape()
        for r in parsed['pages'][n]['rows']:
            box=r['label_bbox']
            if box:overlay.draw_rect(fitz.Rect(box));overlay.finish(color=(0.1,0.2,0.8),width=.5)
            for cell in r['cells']:
                if cell['bbox']:
                    overlay.draw_rect(fitz.Rect(cell['bbox']));overlay.finish(color=(0.1,.55,.2),width=.6)
        overlay.commit()
        pix=page.get_pixmap(matrix=fitz.Matrix(1.65,1.65),alpha=False)
        pix.save(str(Path(out)/f'evidence_page_{n+1}.png'))


def main():
    ap=argparse.ArgumentParser();ap.add_argument('pdf');ap.add_argument('--out',default='output');ap.add_argument('--visualize',action='store_true');args=ap.parse_args()
    data=run(args.pdf);write_outputs(data,args.out)
    if args.visualize:draw_evidence(args.pdf,args.out,data)
    print(json.dumps({'stats':data['stats'],'issues':data['issues'],'anchors':[p['column_anchors'] for p in data['pages']]},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
