"""200dpi raster (no text layer) derivatives of the independent-issuer pages, for OCR-path evaluation.

Integration-stage addition (the original adversarial set rasterizes only the Ur AI original page). Each derivative has the
parent page's AI-draft reference copied verbatim except identity fields: rasterization preserves the visible content and the
page extent, so boxes are unchanged. The derivative stays in the parent's split (holdout) and source family; it is NOT an
independent template. References remain `ai_draft`; nothing is edited in response to model output.
"""
from copy import deepcopy
import json

import fitz

from benchmark import adversarial
from benchmark.common import ROOT, read_json, sha256

PARENTS = ['elecom_p9', 'daiwabo_p10']
MANIFEST = ROOT/'benchmark/raster_manifest.jsonl'


def main():
    if MANIFEST.exists():
        raise SystemExit('Raster manifest already exists; references are create-only')
    manifest = {e['document_id']: e for e in map(json.loads, (ROOT/'benchmark/manifest.jsonl').read_text().splitlines())}
    entries = []
    for parent in PARENTS:
        entry = manifest[parent]
        source = fitz.open(ROOT/entry['input_path'])
        gold = deepcopy(read_json(ROOT/f'benchmark/gold/{parent}.json'))
        name = f'{parent}_scan200'
        folder = ROOT/'benchmark/data/raster'/name
        folder.mkdir(parents=True, exist_ok=True)
        path = folder/'page.pdf'
        out = fitz.open()
        page = out.new_page(width=source[0].rect.width, height=source[0].rect.height)
        page.insert_image(page.rect, stream=source[0].get_pixmap(dpi=200, alpha=False).tobytes('png'))
        out.save(path, deflate=True, no_new_id=True)
        gold['derived_from'] = dict(gold_path=f'benchmark/gold/{parent}.json', gold_sha256=sha256(ROOT/f'benchmark/gold/{parent}.json'),
                                    source_sha256=entry['source_sha256'])
        e = adversarial.entry_for(name, path, gold, '200dpi raster scan of an independent-issuer page',
                                  'visible content retained through 200dpi rasterization; all native text removed; not pixel-identical',
                                  entry['source_family'], ROOT/f'benchmark/gold/raster/{name}.json')
        e.update(source_kind='source_derivative', split='holdout', issuer_relation='independent_issuer',
                 company=entry['company'], domain=entry['domain'], derived_from_document=parent, source_page_index=0)
        entries.append(e)
    MANIFEST.write_text(''.join(json.dumps(e, ensure_ascii=False)+'\n' for e in entries), encoding='utf-8')
    print('Created', len(entries), 'raster derivatives')


if __name__ == '__main__':
    (ROOT/'benchmark/gold/raster').mkdir(parents=True, exist_ok=True)
    main()
