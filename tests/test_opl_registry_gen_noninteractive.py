# SPDX-License-Identifier: OPL-1.4
"""Tests for opl_registry_gen.py — non-interactive generation, in-process for coverage."""
from __future__ import annotations

import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path

# Import the module under test (no import-time side effects).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import opl_registry_gen as rg


def _run_main(argv: list[str]) -> tuple[int, str]:
    """Invoke main() in-process with patched sys.argv; returns (exit_code, stdout)."""
    old_argv = sys.argv
    sys.argv = ["opl_registry_gen.py", *argv]
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            rg.main()
        return 0, buf.getvalue()
    except SystemExit as e:
        return int(e.code or 0), buf.getvalue()
    finally:
        sys.argv = old_argv


class TestRegistryGen:
    def test_non_interactive_generates_valid_json(self, tmp_path):
        out = tmp_path / "REGISTRY.json"
        rc, _ = _run_main([
            "--non-interactive",
            "--maintainer", "Acme <a@acme.com>",
            "--jurisdiction", "United States",
            "--terms-url", "https://acme.com/terms",
            "--output", str(out),
        ])
        assert rc == 0
        assert out.exists()
        data = json.loads(out.read_text())
        assert data["license"] == "OPL-1.4"
        assert data["maintainer"] == "Acme <a@acme.com>"
        assert data["jurisdiction"] == "United States"
        assert data["standard_terms_url"] == "https://acme.com/terms"
        assert data["schema_version"] == "1.0"

    def test_default_output_filename(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rc, _ = _run_main([
            "--non-interactive",
            "--maintainer", "B <b@b.com>",
            "--jurisdiction", "Germany",
            "--terms-url", "https://b.com/t",
        ])
        assert rc == 0
        assert (tmp_path / "REGISTRY.json").exists()

    def test_missing_maintainer_still_writes_defaults(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rc, _ = _run_main(["--non-interactive", "--terms-url", "https://x.com/t"])
        assert rc == 0
        data = json.loads((tmp_path / "REGISTRY.json").read_text())
        assert data["license"] == "OPL-1.4"
        assert "maintainer" in data

    def test_version_flag(self):
        rc, out = _run_main(["--version"])
        assert rc == 0
        assert "OPL Adoption Tools 1.4" in out
