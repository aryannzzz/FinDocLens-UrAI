"""Non-destructive feasibility preflight for PaddleOCR-VL (no install, no download of weights).

Records: HF repo file sizes, PyPI wheel size, free disk, available RAM, GPU status. Output: docs/logs/paddleocr_vl_preflight.json
"""
import json
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from findoclens.runinfo import hardware, utc_now


def get(u):
    with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "findoclens-preflight"}), timeout=30) as r:
        return json.load(r)


out = {"timestamp_utc": utc_now(), "hardware": hardware(), "repos": {}, "pypi": {}}
total_dl = 0
for repo in ("PaddlePaddle/PaddleOCR-VL-1.6", "PaddlePaddle/PP-DocLayoutV3", "PaddlePaddle/PP-DocLayoutV2"):
    try:
        d = get(f"https://huggingface.co/api/models/{repo}?blobs=true")
        fs = {s["rfilename"]: s.get("size") for s in d.get("siblings", [])}
        out["repos"][repo] = {"files": len(fs), "total_bytes": sum(v or 0 for v in fs.values()), "largest": sorted(fs.items(), key=lambda x: -(x[1] or 0))[:2],
                              "lastModified": d.get("lastModified")}
    except Exception as e:
        out["repos"][repo] = {"error": repr(e)}
for pkg in ("paddlepaddle", "paddleocr"):
    try:
        d = get(f"https://pypi.org/pypi/{pkg}/json")
        v = d["info"]["version"]
        fl = [f for f in d["releases"][v] if f["filename"].endswith(".whl") and ("cp312" in f["filename"] and "manylinux" in f["filename"] or pkg == "paddleocr")]
        out["pypi"][pkg] = {"version": v, "wheels": [(f["filename"], f["size"]) for f in fl[:2]]}
    except Exception as e:
        out["pypi"][pkg] = {"error": repr(e)}
du = shutil.disk_usage(ROOT)
r = out["repos"]
need = (r.get("PaddlePaddle/PaddleOCR-VL-1.6", {}).get("total_bytes", 0) + r.get("PaddlePaddle/PP-DocLayoutV3", {}).get("total_bytes", 0)
        + sum(w[1] for w in out["pypi"].get("paddlepaddle", {}).get("wheels", [])[:1]))
out["disk"] = {"free_bytes": du.free, "needed_lower_bound_bytes": need, "fits_on_disk": du.free > need * 1.5}
out["verdict"] = ("BLOCKED: install+weights would not fit on disk with a safe margin" if not out["disk"]["fits_on_disk"]
                  else "disk OK; RAM/GPU still to be checked")
(ROOT / "docs/logs").mkdir(parents=True, exist_ok=True)
(ROOT / "docs/logs/paddleocr_vl_preflight.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
print(json.dumps({"disk": out["disk"], "verdict": out["verdict"]}, indent=1))
