"""Run manifest helpers: system info, git commit, package versions, peak memory (all measured, never guessed)."""
from __future__ import annotations
import datetime
import importlib.metadata as md
import json
import os
import platform
import resource
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def git_commit():
    try:
        out = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=10)
        dirty = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain"], capture_output=True, text=True, timeout=10)
        return out.stdout.strip() + ("+dirty" if dirty.stdout.strip() else "")
    except Exception:
        return None


def pkg_versions(names):
    v = {}
    for n in names:
        try:
            v[n] = md.version(n)
        except md.PackageNotFoundError:
            v[n] = None
    return v


def hardware():
    mem = {}
    try:
        for line in Path("/proc/meminfo").read_text().splitlines()[:3]:
            k, val = line.split(":")
            mem[k] = round(int(val.split()[0]) / 1024)
    except Exception:
        pass
    cpu = None
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                cpu = line.split(":", 1)[1].strip()
                break
    except Exception:
        pass
    gpu = {"nvidia_smi": None}
    try:
        r = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,memory.used", "--format=csv,noheader"],
                           capture_output=True, text=True, timeout=15)
        gpu["nvidia_smi"] = r.stdout.strip() if r.returncode == 0 else f"unavailable (exit {r.returncode}): {(r.stdout + r.stderr).strip()[:160]}"
    except FileNotFoundError:
        gpu["nvidia_smi"] = "nvidia-smi not found"
    except Exception as e:
        gpu["nvidia_smi"] = f"error: {e!r}"
    return {"cpu": cpu, "cpu_threads": os.cpu_count(), "mem_MB": mem, "gpu": gpu, "platform": platform.platform(),
            "python": platform.python_version()}


def peak_rss_mb():
    """Process peak resident set (ru_maxrss, KiB on Linux)."""
    return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)


def load_source_manifest():
    p = ROOT / "data" / "manifest.json"
    return json.loads(p.read_text()) if p.exists() else {}


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
