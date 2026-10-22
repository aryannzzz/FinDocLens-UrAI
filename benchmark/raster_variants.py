"""200dpi raster (no text layer) derivatives of the independent-issuer pages, for OCR-path evaluation.

Integration-stage addition (the original adversarial set rasterizes only the Ur AI original page). Each derivative has the
parent page's AI-draft reference copied verbatim except identity fields: rasterization preserves the visible content and the
page extent, so boxes are unchanged. The derivative stays in the parent's split (holdout) and source family; it is NOT an
independent template. References remain `ai_draft`; nothing is edited in response to model output.
"""
from copy import deepcopy
import argparse
import json
import tempfile
from pathlib import Path

import fitz

from benchmark import adversarial
from benchmark.common import ROOT, read_json, sha256

PARENTS = ['elecom_p9', 'daiwabo_p10']
MANIFEST = ROOT/'benchmark/raster_manifest.jsonl'


def render_raster(source_path, target):
    with fitz.open(source_path) as source, fitz.open() as out:
        page = out.new_page(width=source[0].rect.width, height=source[0].rect.height)
        page.insert_image(page.rect, stream=source[0].get_pixmap(dpi=200, alpha=False).tobytes('png'))
        out.save(target, deflate=True, no_new_id=True)


def materialize():
    """Rebuild ignored inputs against pinned hashes; never write gold or manifests."""
    parents = {e['document_id']: e for e in map(json.loads, (ROOT/'benchmark/manifest.jsonl').read_text().splitlines())}
    locks = read_json(ROOT/'benchmark/gold/raster/SHA256.json')
    entries = list(map(json.loads, MANIFEST.read_text().splitlines()))
    for e in entries:
        gold_path = ROOT/e['gold_path']
        if locks.get(e['gold_path']) != sha256(gold_path):
            raise ValueError(f"Reference hash mismatch: {e['document_id']}")
        gold = read_json(gold_path)
        if any(gold[k] != e[k] for k in ('document_id', 'input_sha256', 'source_sha256')):
            raise ValueError(f"Reference/manifest identity mismatch: {e['document_id']}")
        target = ROOT/e['input_path']
        if target.exists():
            if sha256(target) != e['input_sha256']:
                raise ValueError(f"Existing raster hash mismatch (retained): {e['document_id']}")
            continue
        parent = parents[e['derived_from_document']]
        source_path = ROOT/parent['input_path']
        if sha256(source_path) != parent['input_sha256']:
            raise ValueError(f"Parent input hash mismatch: {e['document_id']}")
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='raster-build-', dir=target.parent) as tmp:
            staged = Path(tmp)/'page.pdf'
            render_raster(source_path, staged)
            if sha256(staged) != e['input_sha256']:
                raise ValueError(f"Rebuilt raster hash mismatch: {e['document_id']}; use the pinned PyMuPDF version")
            staged.replace(target)
    print('Materialized/verified', len(entries), 'raster inputs; references and manifests unchanged')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--materialize', action='store_true', help='Rebuild missing PDFs against frozen hashes without writing annotations')
    args = parser.parse_args()
    if MANIFEST.exists():
        # The manifest and reference files are tracked, whereas their PDFs are ignored.
        # A normal checkout must be able to reconstruct the missing local inputs.
        materialize()
        return
    if args.materialize:
        raise SystemExit('Materialization needs an existing pinned raster manifest')
    manifest = {e['document_id']: e for e in map(json.loads, (ROOT/'benchmark/manifest.jsonl').read_text().splitlines())}
    entries = []
    for parent in PARENTS:
        entry = manifest[parent]
        gold = deepcopy(read_json(ROOT/f'benchmark/gold/{parent}.json'))
        name = f'{parent}_scan200'
        folder = ROOT/'benchmark/data/raster'/name
        folder.mkdir(parents=True, exist_ok=True)
        path = folder/'page.pdf'
        render_raster(ROOT/entry['input_path'], path)
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
