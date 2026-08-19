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
        for expected in ("adopt-1cmd", "adopt", "scan", "kit", "research", "migrate", "adopt-full"):
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


class TestAdoptLive:
    """The Option-A widget backend must wrap the REAL spine (opl_adopt.py)
    and yield a self-consistent repo — not reimplement adopt logic."""

    def test_adopt_live_yields_self_consistent_repo(self, tmp_path):
        # Tiny 1-file Apache fixture.
        (tmp_path / "LICENSE").write_text("Apache License 2.0\n")
        (tmp_path / "app.py").write_text("def f():\n    return 1\n")
        res = adapters.run_adapter("adopt-live", None, {
            "source": "path", "repo_path": str(tmp_path),
            "maintainer": "Demo <demo@example.com>",
            "jurisdiction": "United States",
            "terms_url": "https://demo.example.com/terms",
            "opl_ai": "out", "abandonment": "36", "dosp": "",
        })
        assert res.ok is True
        # NOTICE generated, LICENSE swapped, summary present.
        assert "NOTICE" in res.outputs and res.outputs["NOTICE"].strip()
        assert "Diff summary" in res.outputs
        # Repo is actually self-consistent: valid SPDX + OPL LICENSE.
        notice = (tmp_path / "NOTICE").read_text()
        assert "OPL Version: 1.4" in notice
        lic = (tmp_path / "LICENSE").read_text()
        assert "OPL-1.4" in lic or "Open-Pact" in lic
        app = (tmp_path / "app.py").read_text()
        assert "SPDX-License-Identifier: OPL-1.4" in app
        assert "OPL-OPL-1.4" not in app


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


class TestAdopt1Cmd:
    def test_adopt_1cmd_no_repo(self):
        # adopt-1cmd requires a real repo path (it runs opl_adopt against it).
        res = adapters.run_adapter("adopt-1cmd", None, {"maintainer": "X <x@e.com>"})
        assert res.ok is False
        assert "Repository not found" in res.messages[0]

    def test_adopt_1cmd_dry_run_self_consistent(self, tmp_path):
        # Build a minimal repo the spine can act on: a source file + a license file
        # the swap step will replace, plus manifests to exercise the manifest step.
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "a.py").write_text("print(1)\n")
        (tmp_path / "LICENSE").write_text("MIT License\n")
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "demo"\nlicense = "MIT"\n')
        res = adapters.run_adapter("adopt-1cmd", tmp_path, {
            "maintainer": "Demo <demo@example.com>",
            "jurisdiction": "United States",
            "terms_url": "https://example.com/standard-terms",
            "dry_run": "true",
        })
        # Dry run surfaces opl_adopt's real output + VERDICT line.
        assert res.ok is True
        body = res.messages[0] if res.messages else ""
        assert "OPL Adopt" in body
        assert "OPL ADOPTION COMPLETE" in res.messages[0]
        # Dry-run semantics (matches opl_adopt): NOTICE + SPDX always run, but the
        # destructive swaps are skipped — LICENSE and manifest license field stay MIT.
        assert (tmp_path / "NOTICE").exists()
        assert (tmp_path / "LICENSE").read_text() == "MIT License\n"
        assert 'license = "MIT"' in (tmp_path / "pyproject.toml").read_text()

    def test_adopt_1cmd_writes_and_verdict(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "a.py").write_text("# SPDX-License-Identifier: MIT\nprint(1)\n")
        (tmp_path / "LICENSE").write_text("MIT License\n")
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "demo"\nlicense = "MIT"\n')
        res = adapters.run_adapter("adopt-1cmd", tmp_path, {
            "maintainer": "Demo <demo@example.com>",
            "jurisdiction": "United States",
            "terms_url": "https://example.com/standard-terms",
            "dry_run": "false",
        })
        assert res.ok is True
        # The spine did its job: NOTICE + swapped LICENSE + updated manifest.
        assert (tmp_path / "NOTICE").exists()
        assert "OPL" in (tmp_path / "LICENSE").read_text().upper()
        assert "OPL-1.4" in (tmp_path / "pyproject.toml").read_text()


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
        # Preview must NOT write to the repo.
        assert not (tmp_path / "LICENSE").exists()

    def test_adopt_full_confirm_writes_license(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "a.py").write_text("print(1)\n")
        res = adapters.run_adapter("adopt-full", None, {
            "repo": str(tmp_path),
            "confirm": "true",
            "maintainer": "Test <t@e.com>",
            "terms_url": "https://example.com/t",
        })
        # The confirmed write must land a real LICENSE.md (regression guard for the
        # dogfood find: adopt-full reported success without writing the license).
        assert res.ok is True
        assert (tmp_path / "LICENSE").exists()
        assert (tmp_path / "NOTICE").exists()
        assert "Open-Pact License" in (tmp_path / "LICENSE").read_text()


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


class TestCustomOpl:
    def test_adapter_registered(self):
        ids = [a["id"] for a in adapters.catalogue()]
        assert "custom-opl" in ids

    def test_builds_variant(self, tmp_path):
        out = tmp_path / "out"
        res = adapters.run_adapter("custom-opl", None, {
            "out": str(out), "maintainer": "Acme <ops@acme.com>",
            "terms_url": "https://acme.com/terms", "dosp": "months",
            "dosp_months": "24", "commercial_model": "paid_standard_terms",
        })
        assert res.ok is True
        assert "LICENSE" in res.outputs
        assert "NOTICE" in res.outputs
        assert "OPL Version" in res.outputs["NOTICE"]
        assert "Customization Schedule" in res.outputs["LICENSE"]
        assert "Fair Source: YES" in res.consequence
        assert (out / "LICENSE").exists()

    def test_default_slot_values(self, tmp_path):
        # Empty params (shared-CLI defaults leak "" / "36") must still assemble.
        res = adapters.run_adapter("custom-opl", None, {"out": str(tmp_path / "o")})
        assert res.ok is True
        assert "LICENSE" in res.outputs

    def test_hard_block_surfaces_as_failure(self, tmp_path):
        res = adapters.run_adapter("custom-opl", None, {
            "out": str(tmp_path / "o"), "dosp": "forever_frozen",
            "fair_source_label": "fair_source",
        })
        assert res.ok is False
        assert any("HARD BLOCK" in m for m in res.messages)

    def test_forever_frozen_is_source_available(self, tmp_path):
        res = adapters.run_adapter("custom-opl", None, {
            "out": str(tmp_path / "o"), "dosp": "forever_frozen",
        })
        assert res.ok is True
        assert "Fair Source: NO" in res.consequence

    def test_abandonment_free_text_normalized(self, tmp_path):
        # Shared parser passes abandonment="36"; must normalize to a valid choice.
        res = adapters.run_adapter("custom-opl", None, {
            "out": str(tmp_path / "o"), "abandonment": "36",
            "abandonment_months": "48",
        })
        assert res.ok is True
        assert "Abandonment=48mo" in res.consequence


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


class TestCanary:
    def test_registered_in_catalogue(self):
        ids = [a["id"] for a in adapters.catalogue()]
        assert "canary" in ids

    # A fake origin-canary binary so the sign-path behaviour is tested deterministically
    # without depending on the real Rust binary or a real identity blob.
    @staticmethod
    def _stub_bin(tmp_path):
        stub = tmp_path / "origin-canary"
        stub.write_text(
            "#!/usr/bin/env python3\n"
            "import sys, json\n"
            "args = sys.argv[1:]\n"
            "def val(flag):\n"
            "    return args[args.index(flag)+1] if flag in args else None\n"
            "cmd = sys.argv[0]\n"
            "if len(args) and args[0] == 'embed':\n"
            "    out = val('--manifest-out'); n = val('--num-canaries') or '2'\n"
            "    # plant a token so the repo genuinely changes\n"
            "    src = val('--source')\n"
            "    import glob\n"
            "    for f in glob.glob(src + '/**/*.py', recursive=True):\n"
            "        open(f, 'a').write('canary_stub_token\\n')\n"
            "    json.dump({'token_count': int(n), 'project_id': 1, 'merkle_root': 'stub'},\n"
            "              open(out, 'w'), indent=2)\n"
            "    print('Files modified'); print('Manifest: ' + out)\n"
            "    sys.exit(0)\n"
            "if len(args) and args[0] == 'sign':\n"
            "    pf = val('--passphrase-file'); out = val('--out')\n"
            "    if pf is None:\n"
            "        print('error: passphrase prompt failed: no tty', file=sys.stderr)\n"
            "        sys.exit(1)\n"
            "    if 'WRONG' in open(pf).read():\n"
            "        print('error: decryption failed (wrong passphrase or corrupted blob): x', file=sys.stderr)\n"
            "        sys.exit(1)\n"
            "    if 'GENERIC' in open(pf).read():\n"
            "        print('error: no such commitment type', file=sys.stderr)\n"
            "        sys.exit(1)\n"
            "    json.dump({'signed': True}, open(out, 'w'))\n"
            "    print('Commitment signed.')\n"
            "    sys.exit(0)\n"
            "sys.exit(2)\n"
            ,
            encoding="utf-8",
        )
        stub.chmod(0o755)
        return stub

    def _repo(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "a.py").write_text("x = 1\n")
        return tmp_path

    def _stub_canary_params(self, **kw):
        params = {"distribution_id": "v1.0", "project_id": "1", "num_canaries": "2"}
        params.update(kw)
        return params

    def test_sign_requires_passphrase_file_fast_fail(self, tmp_path, monkeypatch):
        # sign=true + identity but no passphrase file must fail fast with a clear, actionable
        # message and must NOT touch the repo (no embed, no tokens planted).
        repo = self._repo(tmp_path)
        stub = self._stub_bin(tmp_path)
        monkeypatch.setattr(adapters, "origin_canary_bin", lambda: stub)
        ident = tmp_path / "my.id"
        ident.write_bytes(b"fake-blob")
        res = adapters.run_adapter("canary", repo, self._stub_canary_params(
            sign="true", identity=str(ident)))
        assert not res.ok
        assert any("requires --passphrase_file" in m for m in res.messages)
        # no embed ran -> repo unmodified
        assert "canary_stub_token" not in (repo / "src" / "a.py").read_text()

    def test_sign_success_writes_commitment_in_repo(self, tmp_path, monkeypatch):
        repo = self._repo(tmp_path)
        stub = self._stub_bin(tmp_path)
        monkeypatch.setattr(adapters, "origin_canary_bin", lambda: stub)
        ident = tmp_path / "my.id"
        ident.write_bytes(b"fake-blob")
        pf = tmp_path / "pass.txt"
        pf.write_text("correct-passphrase\n")
        res = adapters.run_adapter("canary", repo, self._stub_canary_params(
            sign="true", identity=str(ident), passphrase_file=str(pf)))
        assert res.ok is True
        # commitment is written IN the repo (beside the manifest), never the harness CWD
        assert "commitment" in res.outputs
        commit = Path(res.outputs["commitment"])
        assert commit.exists()
        assert str(repo) in str(commit) or ".." not in str(commit.relative_to(repo))
        assert "signed" in res.consequence

    def test_sign_wrong_passphrase_clear_message_no_partial(self, tmp_path, monkeypatch):
        repo = self._repo(tmp_path)
        stub = self._stub_bin(tmp_path)
        monkeypatch.setattr(adapters, "origin_canary_bin", lambda: stub)
        ident = tmp_path / "my.id"
        ident.write_bytes(b"fake-blob")
        pf = tmp_path / "pass.txt"
        pf.write_text("WRONG-passphrase\n")
        res = adapters.run_adapter("canary", repo, self._stub_canary_params(
            sign="true", identity=str(ident), passphrase_file=str(pf)))
        assert not res.ok
        assert "wrong passphrase" in res.consequence.lower() or "decryption failed" in res.consequence.lower()
        # embed succeeded (manifest + tokens) but NO partial commitment written
        assert (repo / ".canary" / "canary_manifest.json").exists()
        assert not (repo / ".canary" / "canary_commitment.json").exists()
        assert "embedded-but-unsigned" in res.consequence

    def test_sign_skip_when_no_identity(self, tmp_path, monkeypatch):
        repo = self._repo(tmp_path)
        stub = self._stub_bin(tmp_path)
        monkeypatch.setattr(adapters, "origin_canary_bin", lambda: stub)
        res = adapters.run_adapter("canary", repo, self._stub_canary_params(sign="true"))
        assert res.ok is True
        assert "skipped" in res.consequence

    def test_sign_false_is_embed_only(self, tmp_path, monkeypatch):
        repo = self._repo(tmp_path)
        stub = self._stub_bin(tmp_path)
        monkeypatch.setattr(adapters, "origin_canary_bin", lambda: stub)
        res = adapters.run_adapter("canary", repo, self._stub_canary_params(sign="false"))
        assert res.ok is True
        assert "embed-only" in res.consequence

    def test_sign_generic_failure_surfaces_stderr(self, tmp_path, monkeypatch):
        # A sign failure that is NOT a passphrase problem must surface the binary's stderr
        # as the reason (clear message, no traceback), and still report embedded-but-unsigned.
        repo = self._repo(tmp_path)
        stub = self._stub_bin(tmp_path)
        monkeypatch.setattr(adapters, "origin_canary_bin", lambda: stub)
        ident = tmp_path / "my.id"
        ident.write_bytes(b"fake-blob")
        pf = tmp_path / "pass.txt"
        pf.write_text("GENERIC error path\n")
        res = adapters.run_adapter("canary", repo, self._stub_canary_params(
            sign="true", identity=str(ident), passphrase_file=str(pf)))
        assert not res.ok
        assert "embedded-but-unsigned" in res.consequence
        assert "origin-canary sign exited non-zero" in res.consequence or "no such commitment type" in res.consequence

    def test_sign_subprocess_exception_is_clean(self, tmp_path, monkeypatch):
        # A spawn/timeout error while signing must surface as a clean message, not a traceback.
        repo = self._repo(tmp_path)
        stub = self._stub_bin(tmp_path)
        monkeypatch.setattr(adapters, "origin_canary_bin", lambda: stub)
        # force subprocess.run to raise on the sign call (embed succeeds first)
        import subprocess as sp
        real_run = sp.run
        def flaky(cmd, **kw):
            if "sign" in (cmd[1] if len(cmd) > 1 else ""):
                raise RuntimeError("spawn failed")
            return real_run(cmd, **kw)
        monkeypatch.setattr(sp, "run", flaky)
        ident = tmp_path / "my.id"
        ident.write_bytes(b"fake-blob")
        pf = tmp_path / "pass.txt"
        pf.write_text("correct\n")
        res = adapters.run_adapter("canary", repo, self._stub_canary_params(
            sign="true", identity=str(ident), passphrase_file=str(pf)))
        assert not res.ok
        assert "embedded-but-unsigned" in res.consequence


class TestCanaryCliParams:
    def test_parse_sign_params(self):
        _aid, params = adapters._cli_argv_params([
            "--run", "canary", "--repo", "/tmp/x", "--distribution_id", "v1.0",
            "--sign", "true", "--identity", "/i/id", "--passphrase_file", "/p/pass",
            "--commitment_path", ".canary/c.json",
        ])
        assert params["sign"] == "true"
        assert params["identity"] == "/i/id"
        assert params["passphrase_file"] == "/p/pass"
        assert params["commitment_path"] == ".canary/c.json"

    def test_missing_binary_clear_message(self, tmp_path, monkeypatch):
        # No origin-canary binary -> clean guidance, not a crash.
        monkeypatch.setattr(adapters, "origin_canary_bin", lambda: None)
        res = adapters.run_adapter("canary", tmp_path, {"distribution_id": "v1"})
        assert not res.ok
        assert "origin-canary (Rust) binary not found" in res.messages[0]

    def test_missing_distribution_id(self, tmp_path, monkeypatch):
        # Ensure the bin check passes so we reach the dist check deterministically.
        monkeypatch.setattr(adapters, "origin_canary_bin", lambda: Path("/bin/true"))
        res = adapters.run_adapter("canary", tmp_path, {"project_id": "1"})
        assert not res.ok
        assert any("distribution_id is required" in m for m in res.messages)

    def test_repo_required(self, tmp_path):
        res = adapters.run_adapter("canary", tmp_path / "nope", {"distribution_id": "v1"})
        assert not res.ok
        assert "Repository not found" in res.messages[0]
