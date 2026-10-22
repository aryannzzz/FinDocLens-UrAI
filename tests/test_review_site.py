"""Offline source review: missing evidence must fail, without changing references."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from benchmark.common import ROOT, read_json, sha256
from benchmark import review_site


class SourceReviewAssets(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for name in ('baseline_v2/source.pdf', 'benchmark/gold/original.json', 'benchmark/review_ui.html'):
            dest = self.root/name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT/name, dest)
        self.entry = json.loads((ROOT/'benchmark/manifest.jsonl').read_text().splitlines()[0])
        self.folder = self.root/'benchmark/review'
        self.patcher = patch.object(review_site, 'ROOT', self.root)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def build(self):
        return review_site.build([self.entry])

    def test_real_source_and_exact_annotations_with_unreviewed_decisions(self):
        gold_path = self.root/'benchmark/gold/original.json'
        before = sha256(gold_path)
        data = self.build()
        self.assertEqual(sha256(gold_path), before)
        self.assertEqual(data['documents'][0]['tables'], read_json(gold_path)['tables'])
        self.assertEqual(data['documents'][0]['human_checked_cells'], 0)
        self.assertEqual(len(data['decisions']), 74)
        self.assertTrue(all(d['decision'] == 'unreviewed' for d in data['decisions']))
        self.assertIn('△0', {d['expected_raw'] for d in data['decisions']})
        self.assertIn('－', {d['expected_raw'] for d in data['decisions']})
        self.assertEqual(review_site.check(), [])

    def test_missing_image_fails_integrity_check_and_rebuild_repairs_it(self):
        self.build()
        image = self.folder/'assets/original_page.png'
        digest = sha256(image)
        image.unlink()
        self.assertTrue(any('missing' in e for e in review_site.check()))
        self.build()
        self.assertEqual(sha256(image), digest)
        self.assertEqual(review_site.check(), [])

    def test_corrupt_image_is_detected_and_unrelated_rendering_is_not_reused(self):
        # An existing file with this name is not evidence that it is the right page.
        from PIL import Image
        Image.new('RGB', (10, 10), 'red').save(self.root/'baseline_v2/page_200dpi.png')
        self.build()
        image = self.folder/'assets/original_page.png'
        with Image.open(image) as im:
            self.assertGreater(im.width, 1000)
        image.write_bytes(b'not an image')
        self.assertTrue(review_site.check())

    def test_wrong_pdf_identity_is_rejected_before_annotations_are_presented(self):
        self.entry['input_sha256'] = '0'*64
        with self.assertRaisesRegex(ValueError, 'Source input hash mismatch'):
            self.build()
        self.assertFalse((self.folder/'index.html').exists())

    def test_changed_reference_and_broken_embedded_image_url_are_detected(self):
        self.build()
        html_path = self.folder/'index.html'
        html_path.write_text(html_path.read_text().replace('assets/original_page.png', 'assets/missing.png'))
        self.assertTrue(any('broken source URL' in e for e in review_site.check()))
        self.build()
        path = self.root/'benchmark/gold/original.json'
        path.write_text(path.read_text()+'\n')
        self.assertTrue(any('changed gold_path' in e for e in review_site.check()))

    def test_edited_embedded_values_cannot_keep_a_valid_reference_identity(self):
        self.build()
        path = self.folder/'index.html'
        html = path.read_text()
        path.write_text(html.replace('2,002,429', '2,002,430'))
        self.assertTrue(any('embedded annotations differ' in e for e in review_site.check()))


if __name__ == '__main__':
    unittest.main()
