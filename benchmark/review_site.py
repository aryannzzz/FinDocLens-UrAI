"""Offline review assets and integrity checks. Never writes references or decisions."""
from html.parser import HTMLParser
from copy import deepcopy
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit
import os

import fitz

from benchmark.common import ROOT, read_json, sha256, write_json


def restored_review(documents, decisions):
    """Restore an explicit current declaration; never infer review from AI gold."""
    current = ROOT/'benchmark/human_gold/CURRENT.json'
    if not current.exists() or read_json(current).get('current_version') != 'v3':
        return None
    pointer = read_json(current)
    manifest_path = current.parent/pointer['manifest']
    if sha256(manifest_path) != pointer['manifest_sha256']:
        raise ValueError('Current human reference manifest changed')
    from benchmark.human_declaration import check as check_v3
    docs, _ = check_v3(manifest_path.parent)
    manifest = read_json(manifest_path)
    seed = read_json(manifest_path.parent/manifest['review_decisions'])
    by_key = {d['key']: d for d in seed['decisions']}
    if set(by_key) != {d['key'] for d in decisions}:
        raise ValueError('Declared review does not cover exactly these review cells')
    for decision in decisions:
        accepted = by_key[decision['key']]
        if any(accepted[k] != decision[k] for k in decision if k not in {'decision', 'correction'}):
            raise ValueError(f'Declared review identity/content mismatch: {decision["key"]}')
        decision.update(accepted)
    for doc in documents:
        doc['human_verified_cell_contents'] = docs[doc['id']]['human_checked_cells']
    return dict(**{k: v for k, v in seed.items() if k != 'decisions'},
                reference_lock_sha256=sha256(manifest_path.parent/'SHA256.json'),
                details=read_json(ROOT/manifest['declaration']['path']))


def build(entries, folder=None):
    folder = Path(folder) if folder else ROOT/'benchmark/review'
    assets = folder/'assets'
    assets.mkdir(parents=True, exist_ok=True)
    documents, unavailable, decisions = [], [], []
    records = []
    for entry in entries:
        did = entry['document_id']
        gold_path = ROOT/entry.get('gold_path', f'benchmark/gold/{did}.json')
        if entry['status'] != 'available' or not gold_path.exists():
            unavailable.append(dict(id=did, reason=entry.get('error') or 'No reference available'))
            continue
        source = ROOT/entry['input_path']
        if not source.exists():
            raise ValueError(f'Missing cached source PDF: {source}; restore it before building the review')
        if sha256(source) != entry['input_sha256']:
            raise ValueError(f'Source input hash mismatch: {did}')
        gold = read_json(gold_path)
        for key in ('document_id', 'source_sha256', 'input_sha256'):
            if gold.get(key) != entry[key]:
                raise ValueError(f'Reference/source {key} mismatch: {did}')
        digest = sha256(gold_path)
        # Selected PDFs contain the source page at index 0. Do not use source_page_index
        # (8 or 9) against these one-page PDFs.
        with fitz.open(source) as pdf:
            if len(pdf) != 1:
                raise ValueError(f'Review expects a one-page selected PDF: {did}')
            page = pdf[0]
            page_bbox = list(page.rect)
            rotation = page.rotation
            pix = page.get_pixmap(dpi=200, alpha=False)
            rendered = pix.tobytes('png')
            target = assets/f'{did}_page.png'
            if not target.exists() or target.read_bytes() != rendered:
                cached = source.parent/'page_200dpi.png'
                # Reuse existing renderings only after matching the actual selected PDF.
                content = cached.read_bytes() if cached.exists() else None
                target.write_bytes(content if content == rendered else rendered)
        image_url = target.relative_to(folder).as_posix()
        pdf_url = Path(os.path.relpath(source, folder)).as_posix()
        item = dict(id=did, company=entry.get('company', did), source_page_index=entry['source_page_index'],
                    selected_page_index=0, source_sha256=entry['source_sha256'], input_sha256=entry['input_sha256'],
                    gold_sha256=digest, image=image_url, pdf=pdf_url, page_bbox=page_bbox,
                    image_width=pix.width, image_height=pix.height, rotation=rotation,
                    annotation_status=gold.get('annotation_status'), human_checked_cells=gold.get('human_checked_cells', 0),
                    unit=gold.get('unit'), tables=gold['tables'])
        documents.append(item)
        records.append(dict(document_id=did, image=image_url, image_sha256=sha256(target),
                            input_path=entry['input_path'], input_sha256=entry['input_sha256'],
                            gold_path=str(gold_path.relative_to(ROOT)), gold_sha256=digest,
                            source_sha256=entry['source_sha256'], source_page_index=entry['source_page_index'],
                            selected_page_index=0, dpi=200, image_width=pix.width, image_height=pix.height))
        for table in gold['tables']:
            for row in table['rows']:
                for cell in row['cells']:
                    decisions.append(dict(key=f"{did}:{row['row_id']}:{cell['column_index']}", document_id=did,
                                          source_sha256=entry['source_sha256'], input_sha256=entry['input_sha256'],
                                          gold_sha256=digest, source_page_index=entry['source_page_index'], selected_page_index=0,
                                          table_id=table['table_id'], row_id=row['row_id'], column_index=cell['column_index'],
                                          bbox=cell.get('bbox'), evidence=image_url,
                                          expected_raw=cell['raw'], expected_value=cell['value'], expected_status=cell['status'],
                                          decision='unreviewed', correction=None))
    if not documents:
        raise ValueError('No available source PDFs with matching references')
    # Preserve the unreviewed template; declared acceptances are a separate record.
    write_json(folder/'audit_template.json', dict(reviewer=None, decisions=decisions,
                                                note='Unreviewed template; never a human verification record'))
    declaration = restored_review(documents, decisions)
    data = dict(documents=documents, unavailable=unavailable, decisions=decisions)
    if declaration:
        data['review_declaration'] = declaration
    template = (ROOT/'benchmark/review_ui.html').read_text(encoding='utf-8')
    embedded = json.dumps(data, ensure_ascii=False).replace('<', '\\u003c')
    (folder/'index.html').write_text(template.replace('<!-- REVIEW_DATA -->', embedded), encoding='utf-8')
    write_json(folder/'asset_manifest.json', dict(version=1, documents=records))
    problems = check(folder)
    if problems:
        raise ValueError('\n'.join(problems))
    print(f'Review ready: {len(documents)} source pages, {len(decisions)} cells; declared acceptances={len(decisions) if declaration else 0}; assets verified')
    return data


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if (tag in ('script', 'img') and key == 'src') or (tag == 'link' and key == 'href'):
                self.urls.append(value)


def check(folder=None):
    """Fail on missing/corrupt images, stale references, wrong inputs, or broken UI assets."""
    folder = Path(folder) if folder else ROOT/'benchmark/review'
    if not (folder/'asset_manifest.json').exists():
        return ['Missing review asset manifest. Run: .venv/bin/python -m benchmark.review --serve']
    errors = []
    try:
        manifest = read_json(folder/'asset_manifest.json')
        html = (folder/'index.html').read_text(encoding='utf-8')
        # Validate the embedded data too: a valid manifest alone cannot certify stale HTML.
        marker = '<script id="review-data" type="application/json">'
        embedded = json.loads(html.split(marker, 1)[1].split('</script>', 1)[0])
        embedded_docs = {d['id']: d for d in embedded['documents']}
        for record in manifest['documents']:
            did = record['document_id']
            for field, digest in [('image', 'image_sha256'), ('input_path', 'input_sha256'), ('gold_path', 'gold_sha256')]:
                path = (folder if field == 'image' else ROOT)/record[field]
                if not path.is_file():
                    errors.append(f'{did}: missing {path}')
                elif sha256(path) != record[digest]:
                    errors.append(f'{did}: changed {field}: {path}')
            image_path = folder/record['image']
            if image_path.exists():
                from PIL import Image
                with Image.open(image_path) as im:
                    if im.size != (record['image_width'], record['image_height']):
                        errors.append(f'{did}: image size mismatch')
                    im.verify()
            doc = embedded_docs.pop(did, None)
            if not doc or any(doc.get(k) != record.get(k) for k in ('gold_sha256', 'input_sha256', 'source_sha256', 'source_page_index', 'selected_page_index')):
                errors.append(f'{did}: stale embedded source/reference identity')
            elif doc['image'] != record['image'] or not (folder/unquote(doc['pdf'])).is_file():
                errors.append(f'{did}: broken source URL')
            elif doc.get('tables') != read_json(ROOT/record['gold_path'])['tables']:
                errors.append(f'{did}: embedded annotations differ from the reference')
        if embedded_docs:
            errors.append('Embedded source pages are missing from the asset manifest')
        # Reconstruct default decisions from the original AI annotations, then
        # validate their declaration binding as well as the displayed contents.
        originals = []
        for doc in embedded['documents']:
            for table in doc['tables']:
                for row in table['rows']:
                    for cell in row['cells']:
                        originals.append(dict(key=f"{doc['id']}:{row['row_id']}:{cell['column_index']}",
                            document_id=doc['id'], source_sha256=doc['source_sha256'], input_sha256=doc['input_sha256'],
                            gold_sha256=doc['gold_sha256'], source_page_index=doc['source_page_index'], selected_page_index=0,
                            table_id=table['table_id'], row_id=row['row_id'], column_index=cell['column_index'],
                            bbox=cell.get('bbox'), evidence=doc['image'], expected_raw=cell['raw'],
                            expected_value=cell['value'], expected_status=cell['status'], decision='unreviewed', correction=None))
        expected_documents = deepcopy(embedded['documents'])
        declaration = restored_review(expected_documents, originals)
        if declaration != embedded.get('review_declaration') or originals != embedded['decisions']:
            errors.append('Embedded decisions/declaration differ from the current review record')
        if expected_documents != embedded['documents']:
            errors.append('Embedded human content counts differ from the current review record')
        links = Links()
        links.feed(html)
        for url in links.urls:
            parsed = urlsplit(url)
            if parsed.scheme or parsed.netloc:
                errors.append(f'Review must be offline: external asset {url}')
            elif not (folder/unquote(parsed.path)).is_file():
                errors.append(f'Missing UI asset: {url}')
    except (OSError, ValueError, KeyError, IndexError) as exc:
        errors.append(f'Invalid review assets: {exc}')
    return errors
