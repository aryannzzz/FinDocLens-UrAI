"""Read-only offline integrity and stored V3 content replay. No PDF/model fetch.

This verifies locked snapshot bytes and recomputes content scores. Full
source-PDF-backed import/review checks remain separate after source restoration.
"""
import argparse
from collections import defaultdict
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from benchmark.common import read_json, sha256, frozen_check
from benchmark.declared_scoring import score_scope, AXES
from benchmark.evaluate import ratio


def check():
    frozen = frozen_check()
    if frozen:
        raise ValueError(f'Frozen baseline changed: {frozen}')
    locks = [('benchmark/gold/SHA256.json', ROOT), ('benchmark/gold/raster/SHA256.json', ROOT)]
    locks += [(f'benchmark/human_gold/v{v}/SHA256.json', ROOT/f'benchmark/human_gold/v{v}') for v in (1,2,3)]
    locks += [(f'results/human_v{v}/SHA256.json', ROOT/f'results/human_v{v}') for v in (1,2,3)]
    for name, parent in locks:
        for file, digest in read_json(ROOT/name).items():
            if sha256(parent/file) != digest:
                raise ValueError(f'Locked artifact changed: {name}: {file}')
    pointer = read_json(ROOT/'benchmark/human_gold/CURRENT.json')
    ref = ROOT/'benchmark/human_gold'
    if pointer['current_version'] != 'v3' or sha256(ref/pointer['manifest']) != pointer['manifest_sha256']:
        raise ValueError('Current reference pointer changed')
    manifest = read_json(ref/pointer['manifest'])
    declaration = read_json(ROOT/manifest['declaration']['path'])
    if sha256(ROOT/manifest['declaration']['path']) != manifest['declaration']['sha256']:
        raise ValueError('Reviewer declaration changed')
    if sha256(ROOT/declaration['original_export']) != declaration['original_export_sha256']:
        raise ValueError('Original export changed')
    docs = {did: read_json(ref/'v3'/item['path']) for did,item in manifest['documents'].items()}
    if sum(d['human_checked_cells'] for d in docs.values()) != 197 or manifest['structural_annotations_human_verified']:
        raise ValueError('Human content/structure scope changed')
    config = read_json(ROOT/'review/human_signoff/evaluation_v3.json')
    summary = read_json(ROOT/'results/human_v3/summary.json')
    if config['reference_declaration_sha256'] != manifest['declaration']['sha256']:
        raise ValueError('Score selection declaration mismatch')
    if (summary['reference_lock_sha256'] != sha256(ref/'v3/SHA256.json') or
            summary['selection_sha256'] != sha256(ROOT/'review/human_signoff/evaluation_v3.json')):
        raise ValueError('Summary lock/selection mismatch')
    comparisons = 0
    for selection in config['sets']:
        grouped = defaultdict(list)
        seen = set()
        expected = {(b,d) for b in selection['backends'] for d in docs}
        for item in selection['predictions']:
            pair = item['backend'], item['document_id']
            if pair not in expected or pair in seen:
                raise ValueError('Duplicate/unexpected stored prediction')
            seen.add(pair)
            if sha256(ROOT/item['path']) != item['sha256']:
                raise ValueError(f'Prediction changed: {item["path"]}')
            pred = read_json(ROOT/item['path'])
            result = score_scope(docs[item['document_id']], pred, 'human_verified_content_accuracy')
            report = read_json(ROOT/'results/human_v3/reports'/selection['name']/item['backend']/(item['document_id']+'.json'))
            if report['scopes']['human_verified_content_accuracy'] != result:
                raise ValueError('Stored page report does not reproduce')
            grouped[item['backend']].append(result)
            comparisons += 1
        if seen != expected:
            raise ValueError('Missing predictions; denominator cannot shrink')
        scores = {b: {axis: ratio(sum(r['metrics'][axis]['correct'] for r in rs),
                                 sum(r['metrics'][axis]['total'] for r in rs)) for axis in AXES}
                  for b,rs in grouped.items()}
        if scores != summary['scores'][selection['name']]['human_verified_content_accuracy']:
            raise ValueError('Stored V3 aggregate does not reproduce')
    package_manifest = ROOT/'submission/PACKAGE_MANIFEST.json'
    if package_manifest.exists():
        for name, info in read_json(package_manifest)['files'].items():
            if sha256(ROOT/name) != info['sha256']:
                raise ValueError(f'Package member changed: {name}')
    print(f'PASS: frozen baseline; original and V1/V2/V3 locks; declaration; {comparisons} stored V3 comparisons (197 cells each backend/set); package hashes if present')
    print('No inference/download. PDF-backed import/asset validation requires optional issuer source restoration.')


if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    check()
