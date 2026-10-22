"""Gold-free integration check over stored runs: contract compliance (adapters/contract.py), warm-vs-cold determinism and raw-artifact hashes.

    python scripts/contract_report.py RUN_PREFIX [RUN_PREFIX ...]      -> results/contract_check.json + stdout table
"""
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

from adapters.contract import check_prediction

ROOT = Path(__file__).resolve().parents[1]


def core(p):
    """Everything that must be identical between trials: the canonical tables and statuses (provenance/timing excluded)."""
    q = {k: v for k, v in p.items() if k not in ("provenance",)}
    return hashlib.sha256(json.dumps(q, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def main(prefixes):
    report = defaultdict(lambda: dict(predictions=0, compliant=0, violations={}, nondeterministic=[], raw_missing=[], failed_runs=[]))
    for runs in sorted((ROOT / "runs").iterdir()):
        if not runs.is_dir() or runs.name in ("auto_verify", "_test"):
            continue
        for doc in sorted(runs.iterdir()):
            if not doc.is_dir():
                continue
            for run in sorted(doc.iterdir()):
                if not any(run.name.startswith(p + "_") for p in prefixes) or not (run / "metadata.json").exists():
                    continue
                r = report[runs.name]
                meta = json.loads((run / "metadata.json").read_text())
                if meta.get("status") in ("error", "oom", "timeout"):
                    r["failed_runs"].append(f"{doc.name}/{run.name}: {meta.get('status')}")
                trials = [t for t in sorted(run.iterdir()) if t.is_dir() and t.name != "raw" and (t / "prediction.json").exists()]
                hashes = set()
                for t in trials:
                    p = json.loads((t / "prediction.json").read_text())
                    if meta.get("status") == "unavailable":
                        continue
                    r["predictions"] += 1
                    v = check_prediction(p) if p.get("schema_version") == "benchmark-1.0" else ["not benchmark-1.0 (failure placeholder)"]
                    if not v:
                        r["compliant"] += 1
                    for x in v:
                        key = x.split(": ", 1)[-1] if ": " in x else x
                        key = " ".join(w for w in key.split() if not w.isdigit())[:80]
                        r["violations"][key] = r["violations"].get(key, 0) + 1
                    if p.get("status") in ("success", "partial", "abstained"):
                        hashes.add(core(p))
                if len(hashes) > 1:
                    r["nondeterministic"].append(f"{doc.name}/{run.name}")
                if "native" not in runs.name and runs.name != "v2" and (run / "raw/cold").exists() and not any((run / "raw/cold").iterdir()):
                    r["raw_missing"].append(f"{doc.name}/{run.name}")
    out = ROOT / "results"
    out.mkdir(exist_ok=True)
    (out / "contract_check.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"{'backend':26} {'predictions':>11} {'compliant':>9}  nondeterministic  failed runs")
    for b, r in sorted(report.items()):
        print(f"{b:26} {r['predictions']:11d} {r['compliant']:9d}  {len(r['nondeterministic']):16d}  {len(r['failed_runs'])}")
        for k, n in r["violations"].items():
            print(f"      violation x{n}: {k}")


if __name__ == "__main__":
    main(sys.argv[1:] or ["int1"])
