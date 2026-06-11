"""Tests for opl_migrate.py"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from opl_migrate import detect_old_license, scan_manifests, generate_migration_report


class TestDetectOldLicense:
    def test_mit_license(self, tmp_path):
        (tmp_path / "LICENSE").write_text("MIT License\n\nPermission is hereby granted, free of charge...\n")
        assert detect_old_license(tmp_path) == "MIT"

    def test_apache_license(self, tmp_path):
        (tmp_path / "LICENSE").write_text("Apache License Version 2.0, January 2004\n")
        assert detect_old_license(tmp_path) == "Apache-2.0"

    def test_gpl3_license(self, tmp_path):
        (tmp_path / "LICENSE").write_text("GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007\n")
        assert detect_old_license(tmp_path) == "GPL-3.0"

    def test_gpl2_license(self, tmp_path):
        (tmp_path / "LICENSE").write_text("GNU GENERAL PUBLIC LICENSE Version 2, June 1991\n")
        assert detect_old_license(tmp_path) == "GPL-2.0"

    def test_bsd3_license(self, tmp_path):
        (tmp_path / "LICENSE").write_text("BSD 3-Clause License\n\nCopyright...\n")
        assert detect_old_license(tmp_path) == "BSD-3-Clause"

    def test_bsd2_license(self, tmp_path):
        (tmp_path / "LICENSE").write_text("BSD 2-Clause License\n")
        assert detect_old_license(tmp_path) == "BSD-2-Clause"

    def test_opl_license_returns_none(self, tmp_path):
        (tmp_path / "LICENSE").write_text("Open-Pact License v1.3.1\n")
        assert detect_old_license(tmp_path) is None

    def test_no_license_returns_none(self, tmp_path):
        assert detect_old_license(tmp_path) is None

    def test_package_json_license(self, tmp_path):
        (tmp_path / "package.json").write_text(json.dumps({"name": "test", "license": "MIT"}))
        assert detect_old_license(tmp_path) == "MIT"

    def test_spdx_header_in_license(self, tmp_path):
        (tmp_path / "LICENSE.md").write_text("# License\nSPDX-License-Identifier: Apache-2.0\n")
        assert detect_old_license(tmp_path) == "Apache-2.0"

    def test_license_md_variant(self, tmp_path):
        (tmp_path / "LICENSE.md").write_text("MIT License\n")
        assert detect_old_license(tmp_path) == "MIT"


class TestScanManifests:
    def test_package_json(self, tmp_path):
        (tmp_path / "package.json").write_text(json.dumps({"license": "MIT"}))
        manifests = scan_manifests(tmp_path)
        assert len(manifests) == 1
        assert "package.json" in manifests[0][0]

    def test_cargo_toml(self, tmp_path):
        (tmp_path / "Cargo.toml").write_text('[package]\nname = "test"\nlicense = "MIT"\n')
        manifests = scan_manifests(tmp_path)
        assert len(manifests) == 1
        assert "Cargo.toml" in manifests[0][0]

    def test_pyproject_toml(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text('[project]\nlicense = "MIT"\n')
        manifests = scan_manifests(tmp_path)
        assert len(manifests) == 1
        assert "pyproject.toml" in manifests[0][0]

    def test_setup_py(self, tmp_path):
        (tmp_path / "setup.py").write_text('setup(name="test", license="MIT")\n')
        manifests = scan_manifests(tmp_path)
        assert len(manifests) == 1
        assert "setup.py" in manifests[0][0]

    def test_no_manifests(self, tmp_path):
        assert scan_manifests(tmp_path) == []

    def test_multiple_manifests(self, tmp_path):
        (tmp_path / "package.json").write_text(json.dumps({"license": "MIT"}))
        (tmp_path / "pyproject.toml").write_text('[project]\nlicense = "MIT"\n')
        manifests = scan_manifests(tmp_path)
        assert len(manifests) == 2


class TestGenerateMigrationReport:
    def test_report_content(self, tmp_path):
        (tmp_path / "main.py").write_text("print('hi')\n")
        (tmp_path / "LICENSE").write_text("MIT License\n")
        (tmp_path / "package.json").write_text(json.dumps({"license": "MIT"}))
        files = [tmp_path / "main.py"]
        report = generate_migration_report(tmp_path, "MIT", files)
        assert "# OPL Migration Report" in report
        assert "MIT" in report
        assert "OPL-1.3.1" in report
        assert "main.py" in report
        assert "Next Steps" in report
        assert "opl_init.py" in report

    def test_report_with_manifests(self, tmp_path):
        (tmp_path / "package.json").write_text(json.dumps({"license": "MIT"}))
        report = generate_migration_report(tmp_path, "MIT", [])
        assert "Package Manifests" in report
        assert "package.json" in report

    def test_report_empty(self, tmp_path):
        report = generate_migration_report(tmp_path, "Unknown", [])
        assert "# OPL Migration Report" in report
        assert "0" in report


class TestCLI:
    def test_help(self):
        tool = str(Path(__file__).resolve().parent.parent / "tools" / "opl_migrate.py")
        result = subprocess.run([sys.executable, tool, "--help"], capture_output=True, text=True)
        assert result.returncode == 0
        assert "--from" in result.stdout
        assert "--dry-run" in result.stdout
        assert "--report" in result.stdout

    def test_non_interactive_scan(self, tmp_path):
        (tmp_path / "LICENSE").write_text("MIT License\n")
        (tmp_path / "main.py").write_text("print('hi')\n")
        tool = str(Path(__file__).resolve().parent.parent / "tools" / "opl_migrate.py")
        result = subprocess.run([sys.executable, tool, str(tmp_path), "--non-interactive"], capture_output=True, text=True)
        assert result.returncode == 0
        assert "MIT" in result.stdout
        assert "1.3.1" in result.stdout
