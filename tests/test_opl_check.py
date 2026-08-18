"""Tests for opl_check.py"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from opl_check import CheckResult, check_license, check_notice, check_opl_ai, check_spdx_headers


class TestCheckResult:
    def test_passed_result(self):
        r = CheckResult("test", True, "all good")
        assert r.name == "test"
        assert r.passed is True
        assert r.message == "all good"
        assert r.severity == "error"

    def test_failed_result(self):
        r = CheckResult("test", False, "bad", "warning")
        assert r.severity == "warning"

    def test_to_dict(self):
        r = CheckResult("license", True, "found", "info")
        d = r.to_dict()
        assert d == {"check": "license", "passed": True, "message": "found", "severity": "info"}


class TestCheckLicense:
    def test_no_license_file(self, tmp_path):
        r = check_license(tmp_path)
        assert r.passed is False
        assert "No LICENSE" in r.message

    def test_mit_license(self, tmp_path):
        (tmp_path / "LICENSE").write_text("MIT License\nPermission is hereby granted...\n")
        r = check_license(tmp_path)
        assert r.passed is False
        assert "does not reference OPL" in r.message
        assert r.severity == "warning"

    def test_opl_license(self, tmp_path):
        (tmp_path / "LICENSE.md").write_text("# Open-Pact License v1.4\n...\n")
        r = check_license(tmp_path)
        assert r.passed is True
        assert "OPL reference" in r.message

    def test_opl_in_license(self, tmp_path):
        (tmp_path / "LICENSE").write_text("This is the OPL license.\n")
        r = check_license(tmp_path)
        assert r.passed is True

    def test_licence_variant(self, tmp_path):
        (tmp_path / "LICENCE.md").write_text("Open-Pact License\n")
        r = check_license(tmp_path)
        assert r.passed is True


class TestCheckNotice:
    def test_no_notice(self, tmp_path):
        r = check_notice(tmp_path)
        assert r.passed is False
        assert "No NOTICE" in r.message

    def test_complete_notice(self, tmp_path):
        notice = """Maintainer: Jane Doe
Standard Terms: https://example.com/terms
Jurisdiction: California, United States
OPL Version: 1.4
"""
        (tmp_path / "NOTICE").write_text(notice)
        r = check_notice(tmp_path)
        assert r.passed is True
        assert "all required fields" in r.message

    def test_incomplete_notice_missing_jurisdiction(self, tmp_path):
        notice = """Maintainer: Jane Doe
Standard Terms: https://example.com/terms
"""
        (tmp_path / "NOTICE").write_text(notice)
        r = check_notice(tmp_path)
        assert r.passed is False
        assert "jurisdiction" in r.message

    def test_incomplete_notice_missing_url(self, tmp_path):
        notice = """Maintainer: Jane Doe
Jurisdiction: California
OPL: 1.4
"""
        (tmp_path / "NOTICE").write_text(notice)
        r = check_notice(tmp_path)
        assert r.passed is False
        assert "standard terms URL" in r.message

    def test_notice_md_variant(self, tmp_path):
        notice = """# NOTICE
Maintainer: Acme Corp
Standard-Terms URL: https://acme.com/terms
Governing Jurisdiction: Delaware
OPL v1.4
"""
        (tmp_path / "NOTICE.md").write_text(notice)
        r = check_notice(tmp_path)
        assert r.passed is True


class TestCheckSpdxHeaders:
    def test_no_source_files(self, tmp_path):
        r = check_spdx_headers(tmp_path, [])
        assert r.passed is True
        assert "No source files" in r.message or "info" in r.severity

    def test_all_have_spdx(self, tmp_path):
        (tmp_path / "main.py").write_text("# SPDX-License-Identifier: OPL-1.4\nprint('hi')\n")
        r = check_spdx_headers(tmp_path, [])
        assert r.passed is True
        assert "All" in r.message

    def test_some_missing_spdx(self, tmp_path):
        (tmp_path / "main.py").write_text("# SPDX-License-Identifier: OPL-1.4\nprint('hi')\n")
        (tmp_path / "utils.py").write_text("def foo(): pass\n")
        r = check_spdx_headers(tmp_path, [])
        assert r.passed is False
        assert "1 files missing" in r.message


class TestCheckOplAi:
    def test_no_notice(self, tmp_path):
        r = check_opl_ai(tmp_path)
        assert r.passed is False
        assert "no NOTICE" in r.message

    def test_ai_opt_out(self, tmp_path):
        (tmp_path / "NOTICE").write_text("Maintainer: Test\nOPL-AI: opted out.\n")
        r = check_opl_ai(tmp_path)
        assert r.passed is True
        assert "OPL-AI" in r.message

    def test_ai_opt_in(self, tmp_path):
        (tmp_path / "NOTICE").write_text("Maintainer: Test\nOPL-AI: opted in.\n")
        r = check_opl_ai(tmp_path)
        assert r.passed is True

    def test_no_ai_config(self, tmp_path):
        (tmp_path / "NOTICE").write_text("Maintainer: Test\nVersion: 1.4\n")
        r = check_opl_ai(tmp_path)
        assert r.passed is False
        assert "optional" in r.severity or "No OPL-AI" in r.message


class TestCLI:
    def test_help(self):
        tool = str(Path(__file__).resolve().parent.parent / "tools" / "opl_check.py")
        result = subprocess.run([sys.executable, tool, "--help"], capture_output=True, text=True)
        assert result.returncode == 0
        assert "--json" in result.stdout
        assert "--strict" in result.stdout
        assert "--skip-remote" in result.stdout

    def test_json_output(self, tmp_path):
        tool = str(Path(__file__).resolve().parent.parent / "tools" / "opl_check.py")
        result = subprocess.run(
            [sys.executable, tool, str(tmp_path), "--json", "--skip-remote"],
            capture_output=True, text=True)
        assert result.returncode == 1  # no LICENSE or NOTICE
        data = json.loads(result.stdout)
        assert isinstance(data, list)
        assert len(data) == 5
        names = [d["check"] for d in data]
        assert "license" in names
        assert "notice" in names
        assert "spdx-headers" in names

    def test_fully_compliant_repo(self, tmp_path):
        (tmp_path / "LICENSE.md").write_text("Open-Pact License v1.4\n")
        (tmp_path / "NOTICE").write_text(
            "Maintainer: Test\nStandard Terms: https://example.com/terms\n"
            "Jurisdiction: California\nOPL v1.4\nAI training: opted out.\n")
        (tmp_path / "main.py").write_text("# SPDX-License-Identifier: OPL-1.4\nprint('hi')\n")
        tool = str(Path(__file__).resolve().parent.parent / "tools" / "opl_check.py")
        result = subprocess.run(
            [sys.executable, tool, str(tmp_path), "--skip-remote"],
            capture_output=True, text=True)
        assert result.returncode == 0
        assert "5 passed" in result.stdout
