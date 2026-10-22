"""Reproducible controlled transformations of ONE PDF; not an unseen-doc benchmark."""
import json,statistics,time
from pathlib import Path
import fitz
from parser_v2 import run
from evaluate import measure,read_gold

ROOT=Path(__file__).resolve().parent
SRC=ROOT/'source.pdf'
VARIANTS=ROOT/'tests'/'generated'
VARIANTS.mkdir(parents=True,exist_ok=True)


def make_variant(name,scale=1.0,offset=(40,25),with_noise=False):
    src=fitz.open(SRC);rect=src[0].rect
    out=fitz.open();page=out.new_page(width=rect.width*1.65,height=rect.height*1.50)
    x,y=offset
    page.show_pdf_page(fitz.Rect(x,y,x+rect.width*scale,y+rect.height*scale),src,0)
    if with_noise:
        page.insert_text((rect.width*.4,rect.height*1.38),'Footnote: 2025 2026 123 456 789',fontsize=10)
    target=VARIANTS/(name+'.pdf');out.save(target);out.close();src.close();return target


def raster_only():
    src=fitz.open(SRC); pix=src[0].get_pixmap(matrix=fitz.Matrix(1.6,1.6),alpha=False)
    out=fitz.open();page=out.new_page(width=src[0].rect.width,height=src[0].rect.height)
    page.insert_image(page.rect,stream=pix.tobytes('png'))
    target=VARIANTS/'raster_only.pdf';out.save(target);out.close();src.close();return target


def remove_one_cell():
    src=fitz.open(SRC);ref=run(SRC)
    value=next(r for r in ref['rows'] if r['label']=='売掛金')['cells'][0]
    src[0].add_redact_annot(fitz.Rect(value['bbox']),fill=(1,1,1));src[0].apply_redactions()
    target=VARIANTS/'missing_value.pdf';src.save(target);src.close();return target


def remove_negative_marker():
    src=fitz.open(SRC);from parser_v2 import read_lines
    targetline=next(r for r in read_lines(src[0]) if '△2,979' in r['text'])
    marker=next(s for s in targetline['spans'] if s['text']=='△')
    # redact only the negative sign glyph, not the neighboring digits
    box=fitz.Rect(marker['bbox']);box.x1-=.05
    src[0].add_redact_annot(box,fill=(1,1,1));src[0].apply_redactions()
    target=VARIANTS/'lost_negative_sign.pdf';src.save(target);src.close();return target


def make_two_page():
    source=fitz.open(SRC);out=fitz.open();out.insert_pdf(source);out.insert_pdf(source)
    target=VARIANTS/'two_pages.pdf';out.save(target);out.close();source.close();return target


def evaluate_one(name,file,gold):
    t=time.perf_counter();parsed=run(file);elapsed=time.perf_counter()-t
    first=parsed['pages'][0]['rows']
    scores=measure(first,gold) if first else None
    return {'variant':name,'runtime_ms':round(elapsed*1000,1), 'pages':parsed['stats']['pages'],'monetary_rows':parsed['stats']['monetary_rows'],'reported_cells':parsed['stats']['reported_cell_count'],'section_rows':parsed['stats']['sections'],'raw_cell_accuracy_first_page':scores['raw_cell_accuracy'] if scores else None,'hierarchy_exact_first_page':scores['path_accuracy'] if scores else None,'dates_first_page':parsed['pages'][0]['periods'],'issues':[x['code'] for x in parsed['issues']],'unexpected_financial_check_failures':sum(not c['plausibly_rounded'] for c in parsed['checks'])}


def main():
    gold=read_gold(ROOT/'tests'/'gold_rows.tsv')
    tasks=[('original',SRC),('scaled_79',make_variant('scaled_79',scale=.79,offset=(100,45))),('scaled_123',make_variant('scaled_123',scale=1.23,offset=(34,60))),('translated',make_variant('translated',scale=1,offset=(180,15))),('distractor_footer',make_variant('distractor_footer',scale=.91,offset=(90,33),with_noise=True)),('two_pages',make_two_page()),('missing_value',remove_one_cell()),('lost_negative_sign',remove_negative_marker()),('raster_only',raster_only())]
    results=[evaluate_one(name,file,gold) for name,file in tasks]
    (ROOT/'output'/'robustness.json').write_text(json.dumps({'description':'Single-source transformations; NOT independent company/template generalization','results':results},indent=2,ensure_ascii=False),encoding='utf-8')
    for r in results: print(f"{r['variant']:<21} rows={r['monetary_rows']:>2} cells={r['reported_cells']:>3} acc={str(r['raw_cell_accuracy_first_page']):>4} issues={r['issues']} runtime={r['runtime_ms']}ms")
if __name__=='__main__':main()
