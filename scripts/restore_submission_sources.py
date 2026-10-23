"""Restore ignored issuer pages without changing frozen manifests or annotations.

Default: use an existing cache only. --fetch explicitly downloads source PDFs,
never models. Full PDFs and selected pages must match the frozen source hashes.
"""
import argparse
from pathlib import Path
import tempfile
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from benchmark.common import read_json, sha256
import json


def install(entry, cache=None, fetch=False):
    import fitz
    target = ROOT/entry['input_path']
    if target.exists():
        if sha256(target) != entry['input_sha256']:
            raise ValueError(f'Existing selected PDF is corrupt; retained: {entry["document_id"]}')
        return 'already verified'
    did = entry['document_id']
    cached = Path(cache)/did if cache else target.parent
    selected = cached/'page.pdf'
    if selected.is_file():
        if sha256(selected) != entry['input_sha256']:
            raise ValueError(f'Cached selected PDF hash mismatch: {did}')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(selected.read_bytes())
        return 'copied verified selected page'
    original = cached/'original.pdf'
    # Temporary outputs prevent an unsuccessful download/render from replacing
    # a cached input or being mistaken for a valid selected source.
    with tempfile.TemporaryDirectory(prefix='findoclens-source-') as tmp:
        if not original.is_file():
            if not fetch:
                raise FileNotFoundError(f'{did}: restore {entry["input_path"]} or provide --cache DIR; --fetch explicitly opts into source download')
            original = Path(tmp)/'original.pdf'
            req = urllib.request.Request(entry['source_url'], headers={'User-Agent':'FinDocLens-submission/1.0'})
            with urllib.request.urlopen(req, timeout=45) as response:
                data = response.read(30_000_001)
            if len(data) > 30_000_000 or not data.startswith(b'%PDF-'):
                raise ValueError(f'Expected source PDF under 30 MB: {did}')
            original.write_bytes(data)
        if sha256(original) != entry['source_sha256']:
            raise ValueError(f'Full source PDF hash mismatch: {did}; frozen sources/manifest retained')
        candidate = Path(tmp)/'page.pdf'
        with fitz.open(original) as source, fitz.open() as selected_pdf:
            i = entry['source_page_index']
            selected_pdf.insert_pdf(source, from_page=i, to_page=i)
            selected_pdf.save(candidate, garbage=4, deflate=True, no_new_id=True)
        if sha256(candidate) != entry['input_sha256']:
            raise ValueError(f'Selected PDF bytes differ: {did}; use pinned PyMuPDF environment or an exact selected-page cache')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(candidate.read_bytes())
        return 'restored verified selected page'


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--cache', type=Path, help='Directory containing elecom_p9/ and daiwabo_p10/, with page.pdf or original.pdf')
    ap.add_argument('--fetch', action='store_true', help='Explicitly allow downloading only the two available issuer source PDFs')
    args = ap.parse_args()
    entries = [json.loads(s) for s in (ROOT/'benchmark/manifest.jsonl').read_text().splitlines() if s.strip()]
    for e in entries:
        if e['status'] != 'available':
            print(e['document_id']+': excluded (historically unavailable)')
        elif e['document_id'] == 'original':
            if sha256(ROOT/e['input_path']) != e['input_sha256']:
                raise ValueError('Supplied original input changed')
            print('original: supplied assignment page verified')
        else:
            print(e['document_id']+': '+install(e, args.cache, args.fetch))
    print('PASS: source inputs verified; manifests, annotations and stored predictions unchanged')


if __name__ == '__main__':
    main()
