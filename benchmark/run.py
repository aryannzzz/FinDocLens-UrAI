"""Run frozen v2 or an external callable, then score in a separate process boundary."""
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import time

from benchmark.common import ROOT, commit, frozen_check, read_json, sha256, utc, write_json
from benchmark.evaluate import aggregate, evaluate


def hardware():
    data = dict(platform=platform.platform(), python=sys.version, python_executable=sys.executable,
                cpu=platform.processor(), logical_cpus=os.cpu_count(), packages={})
    try:
        data['ram_mb'] = os.sysconf('SC_PAGE_SIZE')*os.sysconf('SC_PHYS_PAGES')/1024**2
        cpu_lines = Path('/proc/cpuinfo').read_text().splitlines()
        data['cpu'] = next((s.split(':', 1)[1].strip() for s in cpu_lines if s.startswith('model name')), data['cpu'])
    except (OSError, ValueError):
        data['ram_mb'] = None
    for package in ('PyMuPDF', 'pdfplumber', 'numpy', 'Pillow', 'torch', 'docling', 'transformers'):
        try:
            data['packages'][package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            data['packages'][package] = None
    try:
        response = subprocess.run(['nvidia-smi', '--query-gpu=name,uuid,driver_version,memory.total', '--format=csv,noheader'],
                                  capture_output=True, text=True, timeout=5)
        data['gpu_probe'] = dict(command=response.args, returncode=response.returncode,
                                 stdout=response.stdout, stderr=response.stderr)
    except (OSError, subprocess.TimeoutExpired) as exc:
        data['gpu_probe'] = dict(status='unavailable', error=str(exc))
    return data


def run_one(entry, backend, entrypoint, warm, timeout, run_id, environment, resume=False):
    folder = ROOT / 'runs' / backend / entry['document_id'] / run_id
    if resume and (folder/'metadata.json').exists():
        metadata = read_json(folder/'metadata.json')
        scores = read_json(ROOT/metadata['metrics_path']) if metadata.get('metrics_path') else None
        return metadata, [scores] if scores else []
    folder.mkdir(parents=True, exist_ok=False)
    metadata = dict(run_id=run_id, timestamp=utc(), git_commit=commit(),
                    worktree_dirty=bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True)),
                    code_sha256={str(p.relative_to(ROOT)): sha256(p) for p in sorted((ROOT/'benchmark').glob('*.py'))},
                    source=entry, backend=backend, backend_version='frozen-v2' if not entrypoint else 'external_callable',
                    model_revision=None, checkpoint_id=None, environment=environment, warm_requested=warm,
                    backend_source_sha256=sha256(ROOT/'baseline_v2/parser_v2.py') if not entrypoint else None,
                    model_kind='native_rules_no_checkpoint' if not entrypoint else 'specified_by_external_backend',
                    timeout_seconds=timeout, human_audit_status=entry.get('human_audit_status', 'ai_draft'))
    reports = []
    if entry.get('status') != 'available':
        metadata.update(status='unavailable', error=entry.get('error'), time_ms=None, peak_memory_mb=None)
        write_json(folder/'metadata.json', metadata)
        return metadata, reports
    source_path = ROOT / entry['input_path']
    if sha256(source_path) != entry['input_sha256']:
        raise ValueError('Input bytes do not match manifest')
    command = [sys.executable, '-m', 'benchmark.worker', '--input', str(source_path),
               '--document-id', entry['document_id'], '--source-sha256', entry['source_sha256'],
               '--source-page-index', str(entry.get('source_page_index', 0)),
               '--out', str(folder), '--warm', str(warm)]
    if entrypoint:
        command.extend(['--entrypoint', entrypoint])
    metadata['command'] = command
    start = time.perf_counter()
    try:
        process = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=timeout,
                                 env={**os.environ, 'BENCHMARK_RUN_DIR': str(folder)})
        metadata.update(returncode=process.returncode, worker_status='completed' if process.returncode == 0 else 'error')
        (folder/'stdout.txt').write_text(process.stdout)
        (folder/'stderr.txt').write_text(process.stderr)
    except subprocess.TimeoutExpired as exc:
        metadata.update(returncode=None, worker_status='timeout', error=f'Timeout after {timeout}s')
        (folder/'stderr.txt').write_bytes(exc.stderr or b'')
    metadata['process_wall_ms'] = (time.perf_counter()-start)*1000
    gold_path = ROOT / entry.get('gold_path', f"benchmark/gold/{entry['document_id']}.json")
    gold = read_json(gold_path) if gold_path.exists() else None
    measurements = []
    for index in range(warm+1):
        trial = folder / ('cold' if index == 0 else f'warm_{index}')
        if not (trial/'measurement.json').exists():
            write_json(trial/'measurement.json', dict(mode='cold_process' if index == 0 else 'warm_same_process',
                       status=metadata['worker_status'], error=metadata.get('error', 'Worker ended without an outcome'),
                       time_ms=None, peak_memory_mb=None))
            write_json(trial/'prediction.json', dict(document_id=entry['document_id'], source_sha256=entry['source_sha256'],
                       input_sha256=entry['input_sha256'], status=metadata['worker_status'], tables=[],
                       issues=[dict(code='worker_failure', severity='error')]))
        measurement = read_json(trial/'measurement.json')
        measurements.append(measurement)
        if gold:
            try:
                report = evaluate(gold, read_json(trial/'prediction.json'))
                report.update(gold_sha256=sha256(gold_path), prediction_sha256=sha256(trial/'prediction.json'),
                              prediction_path=str((trial/'prediction.json').relative_to(ROOT)), source=entry,
                              measurement=measurement)
                write_json(trial/'metrics.json', report)
                if index == 0:
                    reports.append(report)
            except ValueError as exc:
                # Bad identity/schema is a failed evaluation, never a skipped successful page.
                measurement.update(status='invalid_prediction', error=str(exc))
                write_json(trial/'measurement.json', measurement)
                empty = dict(document_id=entry['document_id'], source_sha256=entry['source_sha256'],
                             input_sha256=entry['input_sha256'], status='error', tables=[], issues=[str(exc)])
                report = evaluate(gold, empty)
                report.update(evaluation_error=str(exc), source=entry, measurement=measurement)
                write_json(trial/'metrics.json', report)
                if index == 0:
                    reports.append(report)
    successful_warm = [m['time_ms'] for m in measurements[1:] if m['status'] in {'success', 'partial', 'abstained'} and m['time_ms'] is not None]
    metadata.update(measurements=measurements, status=measurements[0]['status'],
                    cold_time_ms=measurements[0]['time_ms'],
                    warm_median_ms=statistics.median(successful_warm) if len(successful_warm) >= 3 else None,
                    warm_completed=len(successful_warm),
                    metrics_path=str((folder/'cold/metrics.json').relative_to(ROOT)) if gold else None,
                    reference_status=gold.get('annotation_status') if gold else 'unannotated',
                    timing_scope='200dpi evidence render (cold also saves PNG) + backend load/inference + evaluation projection + JSON serialization. Acquisition and scoring excluded; process_wall_ms also includes interpreter startup.',
                    warm_definition='same interpreter and loaded backend; PDF reopened/rendered each repetition')
    write_json(folder/'metadata.json', metadata)
    return metadata, reports


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', default='benchmark/manifest.jsonl')
    parser.add_argument('--backend', default='v2')
    parser.add_argument('--entrypoint', help='module:function accepting a PDF path, returning the canonical schema')
    parser.add_argument('--warm', type=int, default=3)
    parser.add_argument('--timeout', type=float, default=120)
    parser.add_argument('--run-id', default=utc().replace(':', '').replace('+', '_'))
    parser.add_argument('--documents', nargs='*')
    parser.add_argument('--resume', action='store_true', help='Rebuild summary from completed, immutable run artifacts')
    args = parser.parse_args()
    if args.warm < 0 or args.timeout <= 0 or not all(c.isalnum() or c in '-_.' for c in args.backend+args.run_id):
        parser.error('Invalid repetition count, timeout or output name')
    if bool(args.entrypoint) != (args.backend != 'v2'):
        parser.error('External backends need --entrypoint; v2 always uses frozen parser')
    if frozen_check():
        parser.error('Frozen v2 hash mismatch: '+str(frozen_check()))
    entries = [json.loads(line) for line in Path(args.manifest).read_text().splitlines() if line.strip()]
    if args.documents:
        unknown = set(args.documents)-{e['document_id'] for e in entries}
        if unknown:
            parser.error('Unknown documents: '+str(sorted(unknown)))
        entries = [e for e in entries if e['document_id'] in args.documents]
    if not entries:
        parser.error('No manifest entries selected')
    environment = hardware()
    metadata, reports = [], []
    for entry in entries:
        result, scores = run_one(entry, args.backend, args.entrypoint, args.warm, args.timeout, args.run_id, environment, args.resume)
        metadata.append(result)
        reports.extend(scores)
        print(entry['document_id'], result['status'], result.get('cold_time_ms'), result.get('warm_median_ms'))
    cohorts = {}
    for report in reports:
        entry = report['source']
        key = '/'.join([entry['split'], entry['issuer_relation'], entry['source_kind'], report['reference_status']])
        cohorts.setdefault(key, []).append(report)
    summary = dict(run_id=args.run_id, git_commit=commit(), backend=args.backend,
                   documents=metadata, cohorts={key: aggregate(group) for key, group in cohorts.items()},
                   unavailable=[e['source']['document_id'] for e in metadata if e['status'] == 'unavailable'],
                   note='AI-drafted references are provisional. Failure/abstention outcomes remain in scored gold denominators; unavailable and unannotated inputs listed explicitly.')
    write_json(ROOT/'benchmark/reports'/f'{args.backend}_{args.run_id}.json', summary)


if __name__ == '__main__':
    main()
