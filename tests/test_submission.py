"""Delivery guards: immutable cached sources and no credential/runtime path leaks."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from benchmark.common import ROOT, sha256
from scripts import package_submission as package
from scripts import restore_submission_sources as restore


class DeliveryGuards(unittest.TestCase):
    def test_source_review_checker_reads_revision_from_gitless_package(self):
        from scripts import check_review_browser
        import json
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'submission').mkdir()
            (root/'submission/BUILD.json').write_text(json.dumps(dict(source_commit='packaging-commit')))
            with patch.object(check_review_browser, 'ROOT', root), patch.object(
                    check_review_browser.subprocess, 'run', return_value=SimpleNamespace(returncode=128, stdout='')):
                self.assertEqual(check_review_browser.revision_info(), dict(
                    git_commit='packaging-commit', revision_basis='packaged_build_manifest'))

    def test_compact_selection_preserves_required_predictions_and_excludes_filing_images(self):
        self.assertEqual(package.select('runs/native_grid/daiwabo_p10/p0fix2_main/cold/prediction.json')[0],
                         'runs/native_grid/daiwabo_p10/p0fix2_main/cold/prediction.json')
        self.assertIsNone(package.select('runs/native_grid/daiwabo_p10/fin1_main/warm_1/prediction.json')[0])
        self.assertIsNone(package.select('docs/evidence/F2_docling_cmtrue_daiwabo_merged.png')[0])
        self.assertIsNone(package.select('benchmark/data/elecom_p9/page.pdf')[0])
        self.assertEqual(package.select('submission/viewer_assets/pages/original.jpg')[0], 'viewer/pages/original.jpg')
        self.assertIsNone(package.select('submission/viewer_assets/pages/daiwabo_p10.jpg')[0])
        with self.assertRaises(ValueError):
            package.select('../unsafe.txt')

    def test_secret_and_runtime_path_guards_distinguish_inert_history(self):
        with self.assertRaises(ValueError):
            package.audit({'sample.json': ('sk-'+'proj-'+'x'*32).encode()})
        with self.assertRaises(ValueError):
            package.audit({'bad.py': ('source="'+'/ho'+'me/example/input.pdf"').encode()})
        result = package.audit({'history.json': ('{"old_source":"'+'/ho'+'me/example/input.pdf"}').encode()})
        self.assertEqual(result['secret_pattern_hits'], [])
        self.assertEqual(package.audit({'package_submission.py':Path(package.__file__).read_bytes()})['runtime_machine_path_hits'], [])
        self.assertEqual(len(result['historical_machine_path_locations']),1)

    def test_cache_restore_checks_bytes_and_retains_existing_corruption(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cache = root/'cache/example'
            cache.mkdir(parents=True)
            source = cache/'page.pdf'
            source.write_bytes((ROOT/'baseline_v2/source.pdf').read_bytes())
            entry = dict(document_id='example',input_path='benchmark/data/example/page.pdf',input_sha256=sha256(source))
            target = root/entry['input_path']
            with patch.object(restore,'ROOT',root):
                self.assertIn('copied',restore.install(entry,root/'cache'))
                self.assertEqual(sha256(target),entry['input_sha256'])
                self.assertEqual(restore.install(entry,root/'cache'),'already verified')
                target.write_bytes(b'corrupt cache; retain me')
                with self.assertRaisesRegex(ValueError,'corrupt; retained'):
                    restore.install(entry,root/'cache')
                self.assertEqual(target.read_bytes(),b'corrupt cache; retain me')
                target.unlink()
                source.write_bytes(b'wrong cache')
                with self.assertRaisesRegex(ValueError,'hash mismatch'):
                    restore.install(entry,root/'cache')
                self.assertFalse(target.exists())

    def test_cache_only_never_downloads_missing_sources(self):
        entry=dict(document_id='missing',input_path='benchmark/data/missing/page.pdf')
        with tempfile.TemporaryDirectory() as tmp, patch.object(restore,'ROOT',Path(tmp)), \
             patch.object(restore.urllib.request,'urlopen',side_effect=AssertionError('network must not run')):
            with self.assertRaises(FileNotFoundError):
                restore.install(entry)


if __name__ == '__main__':
    unittest.main()
