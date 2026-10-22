"""Isolated backend worker; gold annotations are never read in this process."""
import argparse
from copy import deepcopy
import importlib
import importlib.util
import resource
import sys
import time
import traceback

from benchmark.common import ROOT, read_json, sha256, write_json
from benchmark.compat import from_v2


def main():
    sys.dont_write_bytecode = True  # Frozen parser directory must stay byte-for-byte untouched.
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--document-id', required=True)
    parser.add_argument('--source-sha256', required=True)
    parser.add_argument('--source-page-index', type=int, default=0)
    parser.add_argument('--out', required=True)
    parser.add_argument('--warm', type=int, default=3)
    parser.add_argument('--entrypoint')
    args = parser.parse_args()
    from pathlib import Path
    out = Path(args.out)
    load_start = time.perf_counter()
    load_error = None
    try:
        import fitz
        if args.entrypoint:
            module_name, function = args.entrypoint.split(':')
            module = importlib.import_module(module_name)
            backend = getattr(module, function)
        else:
            spec = importlib.util.spec_from_file_location('frozen_parser_v2', ROOT / 'baseline_v2/parser_v2.py')
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            backend = module.run
    except Exception:
        load_error = traceback.format_exc()
    load_ms = (time.perf_counter()-load_start)*1000
    input_hash = sha256(args.input)
    for index in range(args.warm+1):
        folder = out / ('cold' if index == 0 else f'warm_{index}')
        start = time.perf_counter()
        stages = dict(load_ms=load_ms if index == 0 else 0.)
        result = dict(mode='cold_process' if index == 0 else 'warm_same_process', iteration=index,
                      status='error', error=None, device='cpu' if not args.entrypoint else 'unspecified',
                      model_revision=None, checkpoint_id=None,
                      model_metadata=getattr(module, 'BENCHMARK_METADATA', {}) if not load_error else {})
        for field in ('device', 'model_revision', 'checkpoint_id', 'backend_version'):
            if field in result['model_metadata']:
                result[field] = result['model_metadata'][field]
        try:
            if load_error:
                raise RuntimeError(load_error)
            # Repeated rendering is included as evidence preprocessing; no PDF download or gold work is timed.
            render_start = time.perf_counter()
            page_metadata = []
            with fitz.open(args.input) as pdf:
                for page in pdf:
                    page_metadata.append(dict(page=page.number+1, page_bbox=list(page.cropbox),
                                              page_rotation_degrees=page.rotation))
                    pixmap = page.get_pixmap(dpi=200, alpha=False)
                    if index == 0:
                        folder.mkdir(parents=True, exist_ok=True)
                        pixmap.save(folder / f'evidence_page_{page.number+1}.png')
            stages['render_ms'] = (time.perf_counter()-render_start)*1000
            infer_start = time.perf_counter()
            context = dict(document_id=args.document_id, source_sha256=args.source_sha256, input_sha256=input_hash,
                           source_page_index=args.source_page_index, page_numbering='1-based selected PDF; unrotated PDF coordinates')
            raw = backend(args.input, context=context) if args.entrypoint else backend(args.input)
            stages['inference_ms'] = (time.perf_counter()-infer_start)*1000
            normalize_start = time.perf_counter()
            prediction = deepcopy(raw) if args.entrypoint else from_v2(raw, args.document_id, args.source_sha256, input_hash)
            if not args.entrypoint:
                prediction['pages'] = page_metadata
                prediction['page_bbox'] = page_metadata[0]['page_bbox'] if len(page_metadata) == 1 else None
                prediction['page_bbox_status'] = 'observed_selected_pdf_cropbox' if len(page_metadata) == 1 else 'multipage_see_pages'
                prediction['source_page_index'] = args.source_page_index
            stages['normalization_ms'] = (time.perf_counter()-normalize_start)*1000
            # The callable must provide its own identity/provenance; do not silently fill missing fields.
            if prediction.get('document_id') != args.document_id or prediction.get('source_sha256') != args.source_sha256:
                raise ValueError('Backend prediction identity does not match invocation')
            if not any(t.get('rows') for t in prediction.get('tables', [])):
                prediction['status'] = 'abstained'
                prediction.setdefault('issues', []).append(dict(code='empty_extraction', severity='error'))
            write_start = time.perf_counter()
            write_json(folder / 'original_result.json', raw)
            write_json(folder / 'prediction.json', prediction)
            stages['serialize_ms'] = (time.perf_counter()-write_start)*1000
            result['status'] = prediction.get('status', 'unspecified')
        except Exception as exc:
            result['error'] = traceback.format_exc()
            result['status'] = 'oom' if isinstance(exc, MemoryError) or 'out of memory' in str(exc).lower() else 'error'
            write_json(folder / 'prediction.json', dict(document_id=args.document_id,
                       source_sha256=args.source_sha256, input_sha256=input_hash,
                       status=result['status'], tables=[], issues=[dict(code='backend_exception', message=str(exc))]))
        result.update(stages=stages, time_ms=(time.perf_counter()-start)*1000 + (load_ms if index == 0 else 0),
                      cold_image_export_included=index == 0,
                      peak_memory_mb=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
                      memory_method='Linux ru_maxrss: process lifetime high-water RSS; warm peaks are cumulative, not deltas',
                      peak_gpu_allocation_mb=None,
                      gpu_memory_status='unmeasured: worker does not import or reset framework GPU allocator')
        write_json(folder / 'measurement.json', result)


if __name__ == '__main__':
    main()
