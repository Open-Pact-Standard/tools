# SPDX-License-Identifier: OPL-1.4
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import opl_adapters as adapters


def test_six_capabilities_registered():
    ids = [c["id"] for c in adapters.catalogue()]
    assert ids == ["adopt", "custom-opl", "scan", "kit", "migrate", "research", "adopt-full"]


def test_migrate_runs_dry_run():
    d = Path(tempfile.mkdtemp())
    (d / "LICENSE").write_text("MIT License\nCopyright (c) 2024 Acme\n")
    (d / "a.py").write_text("x=1\n")
    out = subprocess.run(
        [sys.executable, "opl_adapters.py", "--run", "migrate", "--json",
         "--repo", str(d), "--from_license", "MIT", "--dry_run", "true"],
        cwd=str(Path(__file__).resolve().parent.parent / "tools"),
        capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert "migration_report" in json.loads(out.stdout)["outputs"]
