"""Download exact public sources, hash bytes, extract and render selected pages.

Full PDFs and derived images are local-only pending redistribution review.
Network failures are manifest entries, never successful examples.
"""
import argparse
import json
import time
import urllib.request
from pathlib import Path

import fitz

from benchmark.common import ROOT, sha256, utc, write_json

CANDIDATES = [
    ('elecom_p9', 'ELECOM', 'https://www2.jpx.co.jp/disc/67500/140120260331594026.pdf', 8,
     'native balance sheet; two periods; million JPY', 'financial_statement'),
    ('omron_p13', 'OMRON', 'https://www.omron.com/jp/ja/ir/irlib/pdfs/20260513_tanshin.pdf', 12,
     'grouped period/amount/composition headers; five financial columns; multiline labels', 'financial_statement'),
    ('daiwabo_p10', 'Daiwabo Holdings', 'https://www2.jpx.co.jp/disc/31070/140120260206550180.pdf', 9,
     'side-by-side tables and lower explanatory table; three numeric columns', 'financial_slide'),
]


def acquire(refresh=False, offline=False):
    entries = []
    for doc_id, company, url, index, difficulty, domain in CANDIDATES:
        folder = ROOT / 'benchmark/data' / doc_id
        folder.mkdir(parents=True, exist_ok=True)
        pdf = folder / 'original.pdf'
        entry = dict(document_id=doc_id, company=company, source_url=url, source_page_index=index,
                     page=1, split='holdout', issuer_relation='independent_issuer', source_kind='source',
                     source_family=company, domain=domain, difficulty=difficulty,
                     license_note='Public access; redistribution permission unreviewed. Full PDF and derived images local only.',
                     human_audit_status='ai_draft', human_checked_cells=0)
        metadata_path = folder / 'download.json'
        start = time.perf_counter()
        try:
            if refresh or not pdf.exists():
                if offline:
                    failure = folder / 'access_failure.json'
                    raise RuntimeError(json.loads(failure.read_text())['error'] if failure.exists() else 'No cached PDF; offline acquisition')
                request = urllib.request.Request(url, headers={'User-Agent': 'FinDocLens-research/1.0'})
                with urllib.request.urlopen(request, timeout=45) as response:
                    data = response.read(30_000_001)
                    if len(data) > 30_000_000 or not data.startswith(b'%PDF-'):
                        raise ValueError('Expected PDF under 30MB')
                    metadata = dict(requested_url=url, final_url=response.url, http_status=response.status,
                                    headers=dict(response.headers), downloaded_at=utc(), byte_count=len(data))
                if pdf.exists() and pdf.read_bytes() != data:
                    raise ValueError('Remote bytes changed; pinned source retained. Use a new document ID for a revised filing.')
                pdf.write_bytes(data)
                metadata['source_sha256'] = sha256(pdf)
                write_json(metadata_path, metadata)
            metadata = json.loads(metadata_path.read_text())
            if sha256(pdf) != metadata['source_sha256']:
                raise ValueError('Cached bytes differ from original download hash')
            write_json(ROOT/'benchmark/sources'/f'{doc_id}.json', metadata)
            with fitz.open(pdf) as source:
                if index >= len(source):
                    raise ValueError(f'Page {index} unavailable in {len(source)}-page file')
                page_pdf = folder / 'page.pdf'
                with fitz.open() as selected:
                    selected.insert_pdf(source, from_page=index, to_page=index)
                    selected.save(page_pdf, garbage=4, deflate=True, no_new_id=True)
                page = source[index]
                page.get_pixmap(dpi=200, alpha=False).save(folder / 'page_200dpi.png')
                write_json(folder / 'native_text.json', page.get_text('dict', flags=fitz.TEXTFLAGS_DICT & ~fitz.TEXT_PRESERVE_IMAGES))
                (folder / 'native_text.txt').write_text(page.get_text(sort=True), encoding='utf-8')
                entry.update(source_sha256=sha256(pdf), input_sha256=sha256(page_pdf),
                             input_path=str(page_pdf.relative_to(ROOT)), page_bbox=list(page.rect),
                             original_page_count=len(source), status='available', error=None,
                             download_metadata=f'benchmark/sources/{doc_id}.json',
                             acquisition_warnings=fitz.TOOLS.mupdf_warnings())
        except Exception as exc:
            entry.update(status='unavailable', error=f'{type(exc).__name__}: {exc}', attempted_at=utc(),
                         source_sha256=None, input_path=None)
            write_json(ROOT/'benchmark/sources'/f'{doc_id}_failure.json', entry)
        entry['acquisition_elapsed_ms'] = round((time.perf_counter() - start) * 1000, 3)
        entries.append(entry)
        print(doc_id, entry['status'], entry.get('error'))
    original = ROOT / 'baseline_v2/source.pdf'
    entries.insert(0, dict(document_id='original', company='Ur AI supplied issuer (development)',
                          source_url=None, source_page_index=0, page=1, source_sha256=sha256(original),
                          input_sha256=sha256(original), input_path='baseline_v2/source.pdf',
                          source_family='ur_ai_original', split='development', issuer_relation='same_issuer',
                          source_kind='source', domain='financial_statement', difficulty='in-template native two-column',
                          license_note='Supplied take-home attachment; redistribution rights unreviewed',
                          status='available', human_audit_status='ai_draft', human_checked_cells=0))
    (ROOT / 'benchmark/manifest.jsonl').write_text(''.join(json.dumps(x, ensure_ascii=False) + '\n' for x in entries), encoding='utf-8')
    return entries


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh', action='store_true')
    parser.add_argument('--offline', action='store_true', help='Use cached sources; retain unavailable records without network')
    args = parser.parse_args()
    acquire(args.refresh, args.offline)
