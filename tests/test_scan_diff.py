# SPDX-License-Identifier: OPL-1.4
import sys
import json
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))


def _mkrepo() -> Path:
    d = Path(__file__).parent / "_tmp_scanrepo"
    if d.exists():
        import shutil
        shutil.rmtree(d)
    (d / "src").mkdir(parents=True)
    (d / "src" / "a.py").write_text("x=1\n")
    return d


def test_scan_diff_proposes_without_writing():
    repo = _mkrepo()
    out = subprocess.run(
        [sys.executable, "opl_adapters.py", "--run", "scan", "--json",
         "--repo", str(repo), "--mode", "diff",
         "--maintainer", "Acme <ops@acme.com>", "--terms-url", "https://acme.com/terms"],
        cwd=str(Path(__file__).resolve().parent.parent / "tools"),
        capture_output=True, text=True)
    assert out.returncode in (0, 1), out.stderr  # 1 == repo non-compliant, still returns a diff
    d = json.loads(out.stdout)
    assert "diff" in d["outputs"]
    diff = json.loads(d["outputs"]["diff"])
    assert "NOTICE" in diff["proposed"]
    # read-only: nothing written to the repo
    assert (repo / "NOTICE").exists() is False
    assert (repo / "src" / "a.py").read_text() == "x=1\n"
