"""Reproduce the test audit with exact command, commit, code hashes and logs."""
import subprocess
import sys
import time

from benchmark.common import ROOT, commit, sha256, utc, write_json


def main():
    command = [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v']
    start = time.perf_counter()
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    transcript = result.stdout+result.stderr
    (ROOT/'benchmark/reports/tests.txt').write_text(transcript)
    write_json(ROOT/'benchmark/reports/tests.json', dict(command=command, git_commit=commit(), timestamp=utc(),
               elapsed_ms=(time.perf_counter()-start)*1000, returncode=result.returncode,
               status='pass' if result.returncode == 0 else 'fail',
               test_files={str(p.relative_to(ROOT)): sha256(p) for p in (ROOT/'tests').glob('*.py')},
               note='Root suite includes original 25 tests executed in isolated temporary copy.'))
    print(transcript)
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
