# SPDX-License-Identifier: OPL-1.4
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))


def _mkrepo(tmp_path: Path) -> Path:
    d = tmp_path / "repo"
    d.mkdir()
    (d / "src").mkdir()
    (d / "src" / "a.py").write_text("x=1\n")
    return d


def test_scan_diff_proposes_without_writing(tmp_path):
    repo = _mkrepo(tmp_path)
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
