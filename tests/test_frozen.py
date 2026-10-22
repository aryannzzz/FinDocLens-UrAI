"""Run all original tests in a temporary copy: their generators must not mutate v2."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from benchmark.common import ROOT, frozen_check


class FrozenRegressionTests(unittest.TestCase):
    def test_original_25_tests_in_unchanged_copy(self):
        with tempfile.TemporaryDirectory(prefix='findoclens-v2-') as tmp:
            target = Path(tmp)/'baseline_v2'
            shutil.copytree(ROOT/'baseline_v2', target)
            p = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'],
                               cwd=target, capture_output=True, text=True, timeout=60,
                               env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
            self.assertEqual(p.returncode, 0, p.stdout+p.stderr)
            self.assertIn('Ran 25 tests', p.stderr)
        self.assertEqual(frozen_check(), [])
