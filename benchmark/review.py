"""Render source-only HTML check sheets and real measured failure contact sheets."""
import argparse
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
    from benchmark.review_site import build
    build(entries)
    if failures:
        folder = ROOT/'benchmark/review'
        failure_sheet(entries, failures, folder, folder/'assets')


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


def main():
    from functools import partial
    from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
    from benchmark.review_site import check

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', default='benchmark/manifest.jsonl')
    parser.add_argument('--failures', help='A measured benchmark summary JSON')
    parser.add_argument('--check', action='store_true', help='Check generated images, source hashes and UI assets without writing')
    parser.add_argument('--serve', action='store_true', help='Build/check the review and serve it offline on localhost')
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    if args.check:
        problems = check()
        if problems:
            parser.exit(1, '\n'.join(problems)+'\nRun .venv/bin/python -m benchmark.review --serve to rebuild.\n')
        print('PASS: review images, source/reference hashes and offline UI assets')
    else:
        manifest = Path(args.manifest)
        if not manifest.is_absolute():
            manifest = ROOT/manifest
        entries = [json.loads(s) for s in manifest.read_text().splitlines() if s.strip()]
        sheet(entries, args.failures)
    if args.serve:
        handler = partial(SimpleHTTPRequestHandler, directory=str(ROOT))
        with ThreadingHTTPServer(('127.0.0.1', args.port), handler) as server:
            print(f'Review URL: http://127.0.0.1:{server.server_port}/benchmark/review/', flush=True)
            print('Local files only; Ctrl+C stops the server. Reference files are never edited.', flush=True)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass


if __name__ == '__main__':
    main()
