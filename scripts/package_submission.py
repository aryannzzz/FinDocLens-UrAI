"""Create a deterministic compact ZIP from the clean committed delivery tree.

No source/model downloads or inference. The original repo/experiments are never
edited. Extra files are generated inventory/audit metadata inside the archive.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from benchmark.common import sha256

FREEZE = '9a6ebcb5c24ed80caaed59092ebb6f1608547016'
CORE = ['baseline_v2', 'findoclens', 'adapters', 'benchmark']
PORTABLE_DOCS = {'original', 'scan_200', 'grouped_two', 'side_by_side', 'vertical_spacing'}
SECRETS = {
    'private_key': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    'openai_key': re.compile(r'\bsk-(?:proj-|svcacct-)[A-Za-z0-9_-]{25,}'),
    'anthropic_key': re.compile(r'\bsk-ant-[A-Za-z0-9_-]{25,}'),
    'aws_access_key': re.compile(r'\bAKIA[A-Z0-9]{16}\b'),
    'github_key': re.compile(r'\b(?:ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})'),
    'google_key': re.compile(r'\bAIza[A-Za-z0-9_-]{30,}'),
    'hf_key': re.compile(r'\bhf_[A-Za-z0-9]{30,}'),
    'oauth_bearer': re.compile(r'\bya29\.[A-Za-z0-9_-]{30,}'),
}
MACHINE_PATH = re.compile(r'(?:'+re.escape('/'+'home/')+r'[^\s"\'<>),;]+|'+re.escape('/'+'Users/')+r'[^\s"\'<>),;]+|[A-Z]:\\Users\\[^\s"\'<>),;]+)')


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n').encode()


def select(name):
    """Return archive path/reason; do not include untracked files implicitly."""
    p = PurePosixPath(name)
    if p.is_absolute() or '..' in p.parts:
        raise ValueError(f'Unsafe input path: {name}')
    if name.startswith(('dist/', 'submission/delivery_validation/')) or name == 'submission/DELIVERY_RECEIPT.json':
        return None, 'delivery outputs/receipts are external to avoid self-reference'
    if name.startswith('submission/viewer_assets/'):
        suffix = name.removeprefix('submission/viewer_assets/')
        if suffix == 'data.js' or (suffix.startswith('pages/') and Path(suffix).stem in PORTABLE_DOCS):
            return 'viewer/'+suffix, None
        return None, 'nonportable viewer assets'
    if name.startswith('docs/evidence/') or name.startswith('docs/gallery/'):
        return None, 'filing imagery excluded pending redistribution review'
    if name.startswith('runs/'):
        parts = p.parts
        if parts[1] in {'human_review', 'review_provenance', 'human_declaration'}:
            return (name, None) if p.suffix in {'.json','.csv','.log','.md'} else (None, 'human-review images/local outputs omitted')
        if len(parts)>4 and parts[2].startswith('review_') and parts[3]=='independent_review_20261022':
            return (name, None) if p.suffix in {'.json','.pdf','.md'} else (None, 'synthetic probe duplicate output')
        if len(parts)>4 and parts[3] in {'fin1_main','fin1_adv','fin1_raster','p0fix2_main','p0fix2_adv','p0fix2_raster','p0fix3_main'}:
            if parts[4]=='metadata.json' or parts[4]=='cold':
                return (name, None) if p.suffix in {'.json','.md','.csv','.txt'} else (None, 'duplicated page imagery')
            return None, 'warm predictions duplicated; warm measurements retained in metadata'
        return None, 'exploratory/aborted/duplicate runs retained in repository, omitted from compact ZIP'
    if p.suffix.lower() in {'.png','.jpg','.jpeg','.webp','.pdf'} and not name.startswith('baseline_v2/') and not name.startswith('submission/sample_outputs/') and not name.startswith('FINAL_REPORT.'):
        return None, 'non-assignment binary source/evidence omitted'
    if any(x in p.parts for x in ('.git', '__pycache__', 'node_modules', '.cache')) or any(x.startswith('.venv') for x in p.parts):
        return None, 'cache/environment'
    if p.name in {'.env','credentials.json','token.json'} or p.suffix in {'.pem','.key','.safetensors','.onnx','.pt','.pth'}:
        raise ValueError(f'Credential/model filename must not be shipped: {name}')
    return name, None


def audit(files):
    secret_hits, absolute_paths = [], []
    for name, data in files.items():
        try:
            value = data.decode('utf-8')
        except UnicodeDecodeError:
            continue
        for line_no, line in enumerate(value.splitlines(),1):
            for rule, pattern in SECRETS.items():
                if pattern.search(line):
                    secret_hits.append(dict(file=name,line=line_no,rule=rule))
            if MACHINE_PATH.search(line):
                absolute_paths.append(dict(file=name,line=line_no,
                    classification='historical/inert metadata or documentation; not an archive member path'))
    runtime_hits=[x for x in absolute_paths if Path(x['file']).suffix in {'.py','.sh'}]
    if secret_hits or runtime_hits:
        raise ValueError(f'Package audit failed (values suppressed): secrets={secret_hits}; runtime machine paths={runtime_hits}')
    return dict(secret_pattern_hits=secret_hits, runtime_machine_path_hits=runtime_hits,
                historical_machine_path_locations=absolute_paths,
                scope='Known credential formats plus archive-path and runtime home-path checks; not a proof that arbitrary secrets are impossible.',
                historical_paths_note='Original metadata/report paths are inert and preserved byte-for-byte for hashes. All new runnable entrypoints use relative/repository-derived paths.')


def build(out, allow_dirty=False):
    out = Path(out)
    if out.exists():
        raise FileExistsError(f'Create-only delivery ZIP: {out}')
    dirty = subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=ROOT,text=True)
    if dirty and not allow_dirty:
        raise ValueError('Commit tracked packaging changes before building the final ZIP')
    core_diff = subprocess.check_output(['git','diff',FREEZE,'--name-only','--',*CORE],cwd=ROOT,text=True)
    if core_diff:
        raise ValueError('Implementation freeze changed: '+core_diff)
    files, sources, omissions = {}, {}, {}
    tracked = subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')[:-1]
    for name in tracked:
        destination, reason = select(name)
        if destination is None:
            omissions[name] = reason
            continue
        path = ROOT/name
        if path.is_symlink() or not path.is_file():
            raise ValueError('Missing/symlinked tracked member: '+name)
        if destination in files:
            raise ValueError('Duplicate archive destination: '+destination)
        files[destination] = path.read_bytes()
        sources[destination] = name
    required = ['START_HERE.md','FINAL_REPORT.md','FINAL_REPORT.html','FINAL_REPORT.pdf',
                'viewer/index.html','viewer/data.js','baseline_v2/source.pdf',
                'submission/VALIDATION.md','submission/TRANSCRIPT_CHECKLIST.md',
                'requirements.txt','requirements-models.lock.txt','benchmark/human_gold/v3/manifest.json']
    if any(n not in files for n in required):
        raise ValueError('Missing required delivery files: '+str([n for n in required if n not in files]))
    # Every hash-pinned prediction used by V1/V2/V3 must survive compaction.
    for v in (1,2,3):
        config = json.loads(files[f'review/human_signoff/evaluation_v{v}.json'])
        for selection in config['sets']:
            for item in selection['predictions']:
                if item['path'] not in files or hashlib.sha256(files[item['path']]).hexdigest()!=item['sha256']:
                    raise ValueError('Missing/changed required prediction: '+item['path'])
    payload_audit = audit(files)
    build_info = dict(source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                      implementation_freeze=FREEZE, v3_content_cells=197,
                      working_tree_dirty=bool(dirty), model_inference_run=False, downloads=False,
                      complete_chat_transcripts_included=False)
    files['submission/BUILD.json'] = encode(build_info)
    files['submission/PACKAGE_AUDIT.json'] = encode(payload_audit)
    inventory = dict(schema_version='submission-package-1',build=build_info,
                     files={name:dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),source_path=sources.get(name,'generated packaging metadata')) for name,data in sorted(files.items())},
                     omitted_tracked_files=omissions, omitted_reason_counts=dict(Counter(omissions.values())),
                     local_ignored_assets='Virtualenvs, caches, models, downloaded issuer PDFs and filing renders are excluded; only explicitly tracked original/synthetic viewer assets are mapped into viewer/.',
                     integrity_note='Inventory hashes cover all payload members except this self-describing manifest. External ZIP checksum covers the entire archive.')
    files['submission/PACKAGE_MANIFEST.json'] = encode(inventory)
    out.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(out,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,data in sorted(files.items()):
            info = zipfile.ZipInfo('ur_ai_submission/'+name,date_time=(2026,10,23,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=(0o100755 if name.endswith('.sh') else 0o100644)<<16
            z.writestr(info,data,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    with zipfile.ZipFile(out) as z:
        if z.testzip():
            raise ValueError('ZIP CRC test failed')
        if any(PurePosixPath(n).is_absolute() or '..' in PurePosixPath(n).parts for n in z.namelist()):
            raise ValueError('Unsafe ZIP member')
    digest=sha256(out)
    out.with_suffix(out.suffix+'.sha256').write_text(digest+'  '+out.name+'\n')
    print(json.dumps(dict(path=str(out),bytes=out.stat().st_size,sha256=digest,members=len(files),
                          secret_pattern_hits=0,runtime_machine_path_hits=0,
                          historical_path_locations=len(payload_audit['historical_machine_path_locations']),
                          source_commit=build_info['source_commit']),indent=2))
    return out


if __name__ == '__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--allow-dirty',action='store_true',help='Preview only; final archives must be built from committed tracked files')
    args=ap.parse_args()
    build(args.out,args.allow_dirty)
