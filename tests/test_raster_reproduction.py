"""Critical clean-checkout regression: rebuild pinned inputs without editing gold."""
from pathlib import Path
import json
import shutil
import tempfile
import unittest
from unittest.mock import patch

from benchmark.common import ROOT, read_json, sha256
from benchmark import raster_variants


class RasterReproduction(unittest.TestCase):
    def test_missing_rasters_rebuild_and_existing_corruption_is_retained(self):
        parent_manifest = ROOT/'benchmark/manifest.jsonl'
        parents = {e['document_id']: e for e in map(json.loads, parent_manifest.read_text().splitlines())}
        if any(not (ROOT/parents[name]['input_path']).exists() for name in raster_variants.PARENTS):
            self.skipTest('source pages unavailable; run benchmark.dataset first')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = ['benchmark/manifest.jsonl', 'benchmark/raster_manifest.jsonl', 'benchmark/gold/raster/SHA256.json']
            locks = read_json(ROOT/'benchmark/gold/raster/SHA256.json')
            paths += list(locks)
            paths += [parents[name]['input_path'] for name in raster_variants.PARENTS]
            for name in paths:
                (root/name).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT/name, root/name)
            before = {name: sha256(root/name) for name in paths}
            with patch.object(raster_variants, 'ROOT', root), patch.object(raster_variants, 'MANIFEST', root/'benchmark/raster_manifest.jsonl'):
                raster_variants.materialize()
                entries = list(map(json.loads, (root/'benchmark/raster_manifest.jsonl').read_text().splitlines()))
                for entry in entries:
                    self.assertEqual(sha256(root/entry['input_path']), entry['input_sha256'])
                raster_variants.materialize()  # idempotent with cached PDFs
                self.assertEqual(before, {name: sha256(root/name) for name in paths})
                corrupt = root/entries[0]['input_path']
                corrupt.write_bytes(b'deliberately corrupted input')
                with self.assertRaisesRegex(ValueError, 'Existing raster hash mismatch'):
                    raster_variants.materialize()
                self.assertEqual(corrupt.read_bytes(), b'deliberately corrupted input')
