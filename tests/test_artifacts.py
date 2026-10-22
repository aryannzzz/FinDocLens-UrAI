from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from benchmark.common import ROOT, frozen_check, read_json, sha256, write_json
from benchmark.validate import validate_reference
from benchmark.run import run_one
from tests.test_benchmark import fixture


class ArtifactTests(unittest.TestCase):
    def test_frozen_source_outputs_unchanged(self):
        self.assertEqual(frozen_check(), [])

    def test_draft_hashes_and_reference_completeness(self):
        for path, digest in read_json(ROOT/'benchmark/gold/SHA256.json').items():
            self.assertEqual(sha256(ROOT/path), digest)
            self.assertEqual(validate_reference(read_json(ROOT/path)), [], path)

    def test_source_families_have_no_split_leakage(self):
        splits = {}
        for file in ['manifest.jsonl', 'adversarial_manifest.jsonl']:
            for line in (ROOT/'benchmark'/file).read_text().splitlines():
                e = json.loads(line)
                splits.setdefault(e['source_family'], set()).add(e['split'])
        self.assertTrue(all(len(s) == 1 for s in splits.values()))

    def test_derived_missing_cell_and_sign_have_new_truth(self):
        missing = read_json(ROOT/'benchmark/gold/adversarial/missing_cell.json')
        r = next(r for r in missing['tables'][0]['rows'] if r['label'] == '売掛金')
        self.assertEqual(r['cells'][0]['status'], 'absent_text_cell')
        sign = read_json(ROOT/'benchmark/gold/adversarial/sign_erasure.json')
        r = next(r for r in sign['tables'][0]['rows'] if r['label'] == '貸倒引当金')
        self.assertEqual((r['cells'][0]['raw'], r['cells'][0]['value']), ('2,979', 2979))
        original = read_json(ROOT/'benchmark/gold/original.json')
        self.assertEqual(next(r for r in original['tables'][0]['rows'] if r['label'] == '貸倒引当金')['cells'][0]['raw'], '△2,979')

    def test_worker_records_backend_exception(self):
        with tempfile.TemporaryDirectory() as tmp:
            command = [sys.executable, '-m', 'benchmark.worker', '--input', str(ROOT/'baseline_v2/source.pdf'),
                       '--document-id', 'original', '--source-sha256', sha256(ROOT/'baseline_v2/source.pdf'),
                       '--out', tmp, '--warm', '0', '--entrypoint', 'tests.worker_backends:crash']
            response = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=15)
            self.assertEqual(response.returncode, 0, response.stderr)
            m = read_json(Path(tmp)/'cold/measurement.json')
            self.assertEqual(m['status'], 'error')
            self.assertIn('deliberate harness error', m['error'])
            self.assertGreater(m['peak_memory_mb'], 0)
            self.assertEqual(read_json(Path(tmp)/'cold/prediction.json')['tables'], [])

    def test_worker_does_not_accept_empty_table_as_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            command = [sys.executable, '-m', 'benchmark.worker', '--input', str(ROOT/'baseline_v2/source.pdf'),
                       '--document-id', 'original', '--source-sha256', sha256(ROOT/'baseline_v2/source.pdf'),
                       '--out', tmp, '--warm', '0', '--entrypoint', 'tests.worker_backends:empty']
            response = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=15)
            self.assertEqual(response.returncode, 0, response.stderr)
            self.assertEqual(read_json(Path(tmp)/'cold/measurement.json')['status'], 'abstained')
            self.assertEqual(read_json(Path(tmp)/'cold/original_result.json')['status'], 'success')

    def test_worker_records_oom(self):
        with tempfile.TemporaryDirectory() as tmp:
            command = [sys.executable, '-m', 'benchmark.worker', '--input', str(ROOT/'baseline_v2/source.pdf'),
                       '--document-id', 'original', '--source-sha256', sha256(ROOT/'baseline_v2/source.pdf'),
                       '--out', tmp, '--warm', '0', '--entrypoint', 'tests.worker_backends:oom']
            response = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=15)
            self.assertEqual(response.returncode, 0, response.stderr)
            self.assertEqual(read_json(Path(tmp)/'cold/measurement.json')['status'], 'oom')

    def test_timeout_stays_in_gold_denominator(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'benchmark').mkdir()
            input_path = ROOT/'baseline_v2/source.pdf'
            gold, _ = fixture()
            write_json(root/'gold.json', gold)
            entry = dict(document_id='test', status='available', input_path=str(input_path),
                         input_sha256=sha256(input_path), source_sha256='source', gold_path='gold.json')
            timeout = subprocess.TimeoutExpired(['fixture'], .01)
            with patch('benchmark.run.ROOT', root), patch('benchmark.run.commit', return_value='fixture'), \
                 patch('benchmark.run.subprocess.check_output', return_value=''), \
                 patch('benchmark.run.subprocess.run', side_effect=timeout):
                meta, reports = run_one(entry, 'timeout-fixture', 'tests.worker_backends:crash', 0, .01, 'test', {})
            self.assertEqual(meta['status'], 'timeout')
            self.assertEqual(reports[0]['metrics']['raw_cell_exact']['total'], 3)
            self.assertEqual(reports[0]['metrics']['raw_cell_exact']['correct'], 0)

    def test_human_status_requires_reviewer(self):
        gold = read_json(ROOT/'benchmark/gold/original.json')
        gold['annotation_status'] = 'human_verified'
        self.assertIn('Human verification needs named reviewer', validate_reference(gold))
