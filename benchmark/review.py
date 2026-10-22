"""Render source-only HTML check sheets and real measured failure contact sheets."""
import argparse
from html import escape
import json
from pathlib import Path

import fitz
from PIL import Image, ImageDraw

from benchmark.common import ROOT, read_json, sha256, write_json


def crop(page, box, target, padding=3):
    rect = fitz.Rect(box) + (-padding, -padding, padding, padding)
    # PyMuPDF text boxes are always unrotated; rendering clip follows page rotation.
    if page.rotation:
        rect = rect * page.rotation_matrix
    rect = rect & page.rect
    page.get_pixmap(dpi=200, clip=rect, alpha=False).save(target)


def sheet(entries, failures=None):
    folder = ROOT/'benchmark/review'
    assets = folder/'assets'
    assets.mkdir(parents=True, exist_ok=True)
    rows, decisions = [], []
    for entry in entries:
        gold_path = ROOT/entry.get('gold_path', f"benchmark/gold/{entry['document_id']}.json")
        if entry['status'] != 'available' or not gold_path.exists():
            rows.append(f"<h2>{escape(entry['document_id'])}: unavailable / unannotated</h2><p>{escape(entry.get('error', ''))}</p>")
            continue
        gold = read_json(gold_path)
        digest = sha256(gold_path)
        rows.append(f"<h2>{escape(entry['document_id'])} — AI DRAFT, human_checked_cells=0</h2><p>Original page index {entry['source_page_index']}; source SHA {entry['source_sha256']}; reference SHA {digest}</p>")
        with fitz.open(ROOT/entry['input_path']) as doc:
            page = doc[0]
            page_name = f"{entry['document_id']}_page.png"
            page.get_pixmap(dpi=200, alpha=False).save(assets/page_name)
            rows.append(f'<a href="assets/{page_name}">Open full 200dpi source page</a>')
            for table in gold['tables']:
                name = f"{entry['document_id']}_{table['table_id']}_table.png"
                crop(page, table['bbox'], assets/name)
                rows.append(f"<h3>{escape(table['table_id'])}</h3><p>Verify table count, extent, row order, hierarchy, headers and printed units.</p><img class='table' src='assets/{name}'><pre>{escape(json.dumps(table['headers'], ensure_ascii=False, indent=2))}</pre>")
                for row in table['rows']:
                    name = f"{entry['document_id']}_{row['row_id']}.png"
                    crop(page, row['bbox'], assets/name)
                    rows.append(f"<div class='row'><h4>{escape(row['row_id'])}: {escape(row['raw_label'])}</h4><p>Parent: {escape('/'.join(row['parent_path']))}</p><img src='assets/{name}'><table><tr><th>Column</th><th>Period / role</th><th>Raw (exact)</th><th>Typed / status</th><th>Human decision</th><th>Correction / note</th></tr>")
                    for cell in row['cells']:
                        key = f"{entry['document_id']}:{row['row_id']}:{cell['column_index']}"
                        decisions.append(dict(key=key, document_id=entry['document_id'], gold_sha256=digest,
                                              source_sha256=entry['source_sha256'], row_id=row['row_id'],
                                              column_index=cell['column_index'], evidence=f'assets/{name}',
                                              decision='unreviewed', correction=None))
                        rows.append(f"<tr data-key='{escape(key)}'><td>{cell['column_index']}</td><td>{escape(str(cell['period']))} / {escape(cell['role'])}</td><td><code>{escape(str(cell['raw']))}</code></td><td>{escape(str(cell['value']))} / {cell['status']}</td><td><select><option>unreviewed</option><option>accepted</option><option>correction_needed</option><option>unreadable</option></select></td><td><input aria-label='Correction note'></td></tr>")
                    rows.append('</table></div>')
    script = """<script>
const base = DECISIONS;
function save(){
  const reviewer=document.getElementById('reviewer').value.trim();
  if(!reviewer){alert('Enter the human reviewer name.');return;}
  const out={reviewer,reviewed_at:new Date().toISOString(),type:'human_review_decisions',scope_note:document.getElementById('scope').value,decisions:base.map(d=>{
    const row=[...document.querySelectorAll('tr[data-key]')].find(r=>r.dataset.key===d.key);
    return {...d,decision:row.querySelector('select').value,correction:row.querySelector('input').value||null};
  })};
  const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(out,null,2)],{type:'application/json'}));a.download='human_review_decisions.json';a.click();
}
</script>""".replace('DECISIONS', json.dumps(decisions, ensure_ascii=False).replace('<', '\\u003c'))
    html = """<!doctype html><html lang='en'><meta charset='utf-8'><title>FinDocLens source reference review</title>
<style>body{font:16px sans-serif;margin:28px;max-width:1500px}img{max-width:100%;image-rendering:auto}img.table{max-height:650px}table{border-collapse:collapse}td,th{border:1px solid #aaa;padding:6px}code{font-size:19px}.row{margin:24px 0;padding:12px;border:1px solid #bbb}pre{white-space:pre-wrap}input{min-width:160px}</style>
<h1>Source reference review — all annotations AI-drafted</h1><p>Inspect the source images independently. These draft tokens are not model predictions and have not been human certified. At least 20 numeric cells per holdout, signs/dashes, all headers, table boundaries and omissions need review; full verification is preferable. An AI image inspection does not constitute human verification.</p>
<p>Reviewer: <input id='reviewer'> Scope / table-header-label checks: <input id='scope' style='width:60%'></p><button onclick='save()'>Export review decisions</button>
<p>Export does not modify gold or certify unreviewed cells. Preserve corrections as a new version with source crop, reason, old/new token and reference hash.</p>
""" + '\n'.join(rows) + script + '</html>'
    (folder/'index.html').write_text(html, encoding='utf-8')
    write_json(folder/'audit_template.json', dict(reviewer=None, decisions=decisions,
                                                 note='Unreviewed template; never a human verification record'))
    if failures:
        failure_sheet(entries, failures, folder, assets)
    print('Review sheet:', folder/'index.html', len(decisions), 'cell decisions; all unreviewed')


def failure_sheet(entries, summary_path, folder, assets):
    summary = read_json(summary_path)
    entry_map = {e['document_id']: e for e in entries}
    selected = []
    for meta in summary['documents']:
        if not meta.get('metrics_path'):
            continue
        report = read_json(ROOT/meta['metrics_path'])
        candidates = report.get('errors', [])
        # Preserve variety across rows and documents rather than eight cells of one row.
        used = set()
        for event in candidates:
            if event['row_id'] in used or not event.get('bbox'):
                continue
            used.add(event['row_id'])
            selected.append((meta['source'], event, meta['metrics_path']))
            if len(used) >= 4:
                break
        if len(selected) >= 8:
            break
    canvas = Image.new('RGB', (1300, max(1, len(selected))*180), 'white')
    draw = ImageDraw.Draw(canvas)
    evidence = []
    for index, (entry, event, metrics_path) in enumerate(selected[:8]):
        gold_path = ROOT/entry.get('gold_path', f"benchmark/gold/{entry['document_id']}.json")
        gold = read_json(gold_path)
        row = next(r for t in gold['tables'] for r in t['rows'] if r['row_id'] == event['row_id'])
        name = f'failure_{index+1:02d}.png'
        with fitz.open(ROOT/entry['input_path']) as doc:
            crop(doc[0], row['bbox'], assets/name, padding=5)
        with Image.open(assets/name) as image:
            image.thumbnail((1260, 130))
            canvas.paste(image, (20, index*180+30))
        draw.text((20, index*180+5), f"{index+1}. {entry['document_id']} {event['row_id']} col={event['column_index']} {event['kind']} (see JSON for exact glyphs)", fill='black')
        evidence.append(dict(event, document_id=entry['document_id'], crop=f'assets/{name}', metrics_path=metrics_path,
                             source_sha256=entry['source_sha256'], reference_status='ai_draft'))
    canvas.save(folder/'failure_contact_sheet.png')
    write_json(folder/'failure_contact_sheet.json', evidence)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', default='benchmark/manifest.jsonl')
    parser.add_argument('--failures', help='A measured benchmark summary JSON')
    args = parser.parse_args()
    entries = [json.loads(s) for s in Path(args.manifest).read_text().splitlines() if s.strip()]
    sheet(entries, args.failures)
