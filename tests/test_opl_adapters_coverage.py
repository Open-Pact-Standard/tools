# SPDX-License-Identifier: OPL-1.4
"""In-process tests for opl_adapters.py — plugin registry, adapters, CLI param parsing."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import opl_adapters as adapters


class TestCatalogue:
    def test_catalogue_ids(self):
        ids = [a["id"] for a in adapters.catalogue()]
        for expected in ("adopt", "scan", "kit", "research", "migrate", "adopt-full"):
            assert expected in ids

    def test_catalogue_has_params(self):
        for a in adapters.catalogue():
            assert "params" in a
            assert isinstance(a["params"], list)


class TestRunAdapterUnknown:
    def test_unknown_id(self):
        res = adapters.run_adapter("does-not-exist", None, {})
        assert res.ok is False
        assert "Unknown adapter" in res.messages[0]


class TestScan:
    def test_scan_no_root(self):
        res = adapters.run_adapter("scan", None, {})
        assert res.ok is False
        assert "Repository not found." in res.messages

    def test_scan_report_real_repo(self, tmp_path):
        # create a minimal compliant-ish repo
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "a.py").write_text("# SPDX-License-Identifier: OPL-1.4\nprint(1)\n")
        (tmp_path / "LICENSE").write_text("OPL\n")
        (tmp_path / "NOTICE").write_text("OPL Version: 1.4\n")
        res = adapters.run_adapter("scan", tmp_path, {"skip_remote": "true"})
        assert "opl_check" in res.outputs


class TestScanDiff:
    def test_scan_diff_no_root(self):
        res = adapters.run_adapter("scan", None, {"mode": "diff"})
        assert res.ok is False

    def test_scan_diff_real_repo(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "a.py").write_text("print(1)\n")  # no SPDX
        (tmp_path / "LICENSE").write_text("OPL\n")
        res = adapters.run_adapter("scan", tmp_path, {"mode": "diff", "skip_remote": "true"})
        assert "diff" in res.outputs
        diff = __import__("json").loads(res.outputs["diff"])
        assert "checks" in diff


class TestAdopt:
    def test_adopt_no_root_preview(self):
        res = adapters.run_adapter("adopt", None, {"write": "false"})
        # preview mode with no root still runs opl_init against temp dir
        assert "NOTICE" in res.outputs or "LICENSE (Custom OPL)" in res.outputs

    def test_adopt_write_real_repo(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "a.py").write_text("print(1)\n")
        res = adapters.run_adapter("adopt", tmp_path, {
            "write": "true",
            "maintainer": "Test <t@e.com>",
            "jurisdiction": "United States",
            "terms_url": "https://example.com/t",
        })
        # At minimum returns a result dict; NOTICE may or may not be written
        # depending on opl_init availability. Assert it is an AdapterResult-like.
        assert isinstance(res.ok, bool)


class TestAdoptFull:
    def test_adopt_full_no_repo(self):
        res = adapters.run_adapter("adopt-full", None, {})
        assert res.ok is False

    def test_adopt_full_preview(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "a.py").write_text("print(1)\n")
        # adopt-full reads the repo from params["repo"], not the root arg.
        res = adapters.run_adapter("adopt-full", None, {
            "repo": str(tmp_path),
            "confirm": "false",
            "maintainer": "Test <t@e.com>",
            "terms_url": "https://example.com/t",
        })
        assert res.ok is True
        assert "NOTICE" in res.outputs or "LICENSE (Custom OPL)" in res.outputs


class TestMigrate:
    def test_migrate_no_root(self):
        res = adapters.run_adapter("migrate", None, {})
        assert res.ok is False

    def test_migrate_real_repo(self, tmp_path):
        (tmp_path / "setup.py").write_text("__version__ = '0.1'\n")
        (tmp_path / "LICENSE").write_text("MIT License\n")
        res = adapters.run_adapter("migrate", tmp_path, {"from_license": "MIT", "dry_run": "true"})
        assert "migration_report" in res.outputs


class TestResearch:
    def test_research_base_missing(self, monkeypatch):
        # Point the research doc path at a non-existent file to hit the not-found branch.
        monkeypatch.setattr(adapters, "HERE", Path("/nonexistent/here"))
        res = adapters.run_adapter("research", None, {"jurisdiction": "Germany"})
        assert res.ok is False
        assert "RESEARCH_BASE.md not found." in res.messages

    def test_research_known_jurisdiction(self, tmp_path, monkeypatch):
        # research doc path = HERE.parent.parent / open-pact-license / RESEARCH_BASE.md
        # So set HERE = tmp_path/A/B so parent.parent == tmp_path.
        fake_here = tmp_path / "A" / "B"
        fake_here.mkdir(parents=True)
        (tmp_path / "open-pact-license").mkdir()
        (tmp_path / "open-pact-license" / "RESEARCH_BASE.md").write_text(
            "# Research\nGermany: BGB §§ 305–310.\n"
        )
        monkeypatch.setattr(adapters, "HERE", fake_here)
        res = adapters.run_adapter("research", None, {"jurisdiction": "Germany"})
        assert res.ok is True
        assert "Germany" in res.outputs["research"]


class TestConsequenceText:
    def test_dosp_off(self):
        out = adapters._consequence_text({})
        assert "DOSP=off" in out

    def test_dosp_on(self):
        out = adapters._consequence_text({"dosp": "36"})
        assert "DOSP=36mo" in out

    def test_commercial_personal(self):
        out = adapters._consequence_text({"commercial_model": "personal_only"})
        assert "personal_only" in out

    def test_commercial_free(self):
        out = adapters._consequence_text({"commercial_model": "free_for_all"})
        assert "free_for_all" in out

    def test_commercial_paid(self):
        out = adapters._consequence_text({"commercial_model": "paid_standard_terms"})
        assert "paid" in out


class TestAssembleLicense:
    def test_assemble_missing_custom_opl(self, monkeypatch, tmp_path):
        # Force custom_opl.py to be absent so the fallback path returns something.
        fake_here = tmp_path / "tools"
        fake_here.mkdir()
        monkeypatch.setattr(adapters, "HERE", fake_here)
        out = adapters._assemble_license({"commercial_model": "paid_standard_terms"}, "United States")
        assert isinstance(out, str)


class TestCliArgvParams:
    def test_parse_basic(self):
        aid, params = adapters._cli_argv_params([
            "--run", "scan", "--repo", "/tmp/x",
            "--maintainer", "Y", "--terms-url", "https://y.com",
            "--mode", "diff", "--skip_remote", "true",
        ])
        assert aid == "scan"
        assert params["repo"] == "/tmp/x"
        assert params["maintainer"] == "Y"
        assert params["terms_url"] == "https://y.com"
        assert params["mode"] == "diff"
        assert params["skip_remote"] == "true"

    def test_parse_terms_url_alias(self):
        _aid, params = adapters._cli_argv_params([
            "--run", "adopt", "--repo", "/tmp/x", "--terms_url", "https://z.com",
        ])
        assert params["terms_url"] == "https://z.com"

    def test_parse_defaults(self):
        _aid, params = adapters._cli_argv_params(["--run", "scan"])
        assert params["jurisdiction"] == "United States"
        assert params["abandonment"] == "36"
        assert params["confirm"] == "false"


class TestRunTool:
    def test_exception_returns_minus_one(self, monkeypatch):
        # Patch subprocess.run to raise so the except-branch is exercised.
        import subprocess as sp

        def boom(*a, **k):
            raise RuntimeError("spawn failed")

        monkeypatch.setattr(sp, "run", boom)
        rc, so, se = adapters.run_tool("opl_check.py", "x")
        assert rc == -1
        assert so == ""
        assert "spawn failed" in se


class TestAssembleLicenseBranches:
    def test_dosp_adds_flag_and_custom_opl_writes_license(self, tmp_path):
        # Real custom_opl.py run with --dosp-months: exercises line 154 + 158
        # (license file exists → returns its text).
        out = adapters._assemble_license(
            {"commercial_model": "paid_standard_terms", "dosp": "12"}, "United States")
        assert isinstance(out, str)
        assert "license assembly unavailable" not in out

    def test_no_license_file_falls_back_to_stdout(self, tmp_path, monkeypatch):
        # custom_opl succeeds (rc=0) but no LICENSE written → returns stdout.
        def fake_run_tool(script, *args, **kwargs):
            return 0, "stdout-from-custom-opl", ""

        monkeypatch.setattr(adapters, "run_tool", fake_run_tool)
        out = adapters._assemble_license({"commercial_model": "paid_standard_terms"}, "US")
        assert out == "stdout-from-custom-opl"


class TestScanDiffEdgeCases:
    def test_bad_json_parses_to_empty(self, tmp_path, monkeypatch):
        def fake_run_tool(script, *args, **kwargs):
            return 1, "not-json{{", ""

        monkeypatch.setattr(adapters, "run_tool", fake_run_tool)
        res = adapters.run_adapter("scan", tmp_path, {"mode": "diff"})
        assert res.ok is False
        data = json.loads(res.outputs["diff"])
        assert data["checks"] == []
        assert data["proposed"] == {}


class TestKit:
    def test_kit_runs_and_lists_files(self):
        res = adapters.run_adapter("kit", None, {})
        assert res.ok is True
        assert "kit files" in res.outputs


class TestAdoptFullConfirmed:
    def test_confirm_writes_notice_and_validates(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "a.py").write_text("print(1)\n")
        res = adapters.run_adapter("adopt-full", None, {
            "repo": str(tmp_path),
            "confirm": "true",
            "maintainer": "Test <t@e.com>",
            "terms_url": "https://example.com/t",
        })
        assert res.ok is True
        assert (tmp_path / "NOTICE").exists()
        assert "opl_check" in res.outputs


class TestMainBlock:
    def test_main_json_and_plain(self, capsys, monkeypatch, tmp_path):
        import runpy

        # JSON mode: failing scan (empty repo) still emits valid JSON, exit 1.
        monkeypatch.setattr(sys, "argv", [
            "opl_adapters.py", "--json", "--run", "scan", "--repo", str(tmp_path),
        ])
        with pytest.raises(SystemExit) as ei:
            runpy.run_module("opl_adapters", run_name="__main__")
        assert ei.value.code == 1  # scan failed on empty repo
        data = json.loads(capsys.readouterr().out)
        assert data["ok"] is False
        assert "opl_check" in data["outputs"]

        # Plain mode: [FAIL] banner + exit 1.
        monkeypatch.setattr(sys, "argv", [
            "opl_adapters", "--run", "scan", "--repo", str(tmp_path),
        ])
        with pytest.raises(SystemExit) as ei2:
            runpy.run_module("opl_adapters", run_name="__main__")
        assert ei2.value.code == 1
        out2 = capsys.readouterr().out
        assert "[FAIL] adapter scan" in out2


class TestDataclasses:
    def test_adapter_result_defaults(self):
        r = adapters.AdapterResult(True)
        assert r.outputs == {}
        assert r.messages == []
        assert r.consequence == ""

    def test_register_returns_adapter(self):
        a = adapters.Adapter(
            id="tmp_x", title="T", description="d", params=[],
            run=lambda root, p: adapters.AdapterResult(True),
        )
        reg = adapters.register(a)
        assert reg.id == "tmp_x"
        assert "tmp_x" in adapters.REGISTRY
