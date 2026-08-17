# SPDX-License-Identifier: OPL-1.4
"""In-process tests for opl_migrate.py — license detection, manifest scan, report, CLI."""
from __future__ import annotations

import sys
from pathlib import Path

tools_dir = str(Path(__file__).resolve().parent.parent / "tools")
if tools_dir not in sys.path:
    sys.path.insert(0, tools_dir)
import opl_migrate as migrate


def _run_main(argv, capsys):
    old = sys.argv
    sys.argv = ["opl_migrate.py", *argv]
    try:
        migrate.main()
        return 0
    except SystemExit as e:
        return int(e.code or 0)
    finally:
        sys.argv = old


class TestDetectOldLicense:
    def test_mit_license_file(self, tmp_path):
        (tmp_path / "LICENSE").write_text("MIT License\nPermission is hereby granted, free of charge\n")
        assert migrate.detect_old_license(tmp_path) == "MIT"

    def test_apache_license_file(self, tmp_path):
        (tmp_path / "LICENSE").write_text("Apache License 2.0\nLicensed under the Apache License\n")
        assert migrate.detect_old_license(tmp_path) == "Apache-2.0"

    def test_gpl3_license_file(self, tmp_path):
        (tmp_path / "LICENSE").write_text("GNU GENERAL PUBLIC LICENSE Version 3\n")
        assert migrate.detect_old_license(tmp_path) == "GPL-3.0"

    def test_spdx_mit(self, tmp_path):
        (tmp_path / "LICENSE").write_text("SPDX-License-Identifier: MIT\n")
        assert migrate.detect_old_license(tmp_path) == "MIT"

    def test_package_json(self, tmp_path):
        (tmp_path / "package.json").write_text('{"license": "MIT"}')
        assert migrate.detect_old_license(tmp_path) == "MIT"

    def test_none(self, tmp_path):
        assert migrate.detect_old_license(tmp_path) is None


class TestScanManifests:
    def test_package_json(self, tmp_path):
        (tmp_path / "package.json").write_text('{"license":"MIT"}')
        assert any("package.json" in p for p, _ in migrate.scan_manifests(tmp_path))

    def test_cargo_toml(self, tmp_path):
        (tmp_path / "Cargo.toml").write_text('license = "MIT"\n')
        assert any("Cargo.toml" in p for p, _ in migrate.scan_manifests(tmp_path))

    def test_pyproject_toml(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text('[project]\nlicense = "MIT"\n')
        assert any("pyproject.toml" in p for p, _ in migrate.scan_manifests(tmp_path))

    def test_setup_py(self, tmp_path):
        (tmp_path / "setup.py").write_text('setup(license="MIT")\n')
        assert any("setup.py" in p for p, _ in migrate.scan_manifests(tmp_path))

    def test_empty(self, tmp_path):
        assert migrate.scan_manifests(tmp_path) == []


class TestGenerateMigrationReport:
    def test_with_files_and_manifests(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "a.py").write_text("print(1)\n")
        (tmp_path / "package.json").write_text('{"license":"MIT"}')
        r = migrate.generate_migration_report(tmp_path, "MIT", [tmp_path / "src" / "a.py"])
        assert "OPL Migration Report" in r
        assert "MIT" in r
        assert "package.json" in r

    def test_no_manifests(self, tmp_path):
        (tmp_path / "a.py").write_text("print(1)\n")
        r = migrate.generate_migration_report(tmp_path, "Apache-2.0", [])
        assert "Next Steps" in r
        assert "Package Manifests" not in r


class TestMain:
    def test_version(self, capsys):
        rc = _run_main(["--version"], capsys)
        assert rc == 0
        assert "OPL Adoption Tools 1.4" in capsys.readouterr().out

    def test_non_dir_exit(self, tmp_path, capsys):
        rc = _run_main([str(tmp_path / "ghost")], capsys)
        assert rc == 1

    def test_non_interactive_with_from_and_report_dryrun(self, tmp_path, capsys):
        (tmp_path / "LICENSE").write_text("MIT License\nPermission is hereby granted, free of charge\n")
        (tmp_path / "a.py").write_text("print(1)\n")
        rc = _run_main([str(tmp_path), "--from", "MIT", "--non-interactive",
                        "--report", "--dry-run"], capsys)
        assert rc == 0
        out = capsys.readouterr().out
        assert "Migration" in out

    def test_non_interactive_report_writes_file(self, tmp_path, capsys):
        (tmp_path / "LICENSE").write_text("MIT License\nPermission is hereby granted, free of charge\n")
        (tmp_path / "a.py").write_text("print(1)\n")
        rc = _run_main([str(tmp_path), "--from", "MIT", "--non-interactive", "--report"], capsys)
        assert rc == 0
        assert (tmp_path / "OPL_MIGRATION_REPORT.md").exists()

    def test_no_old_license_non_interactive(self, tmp_path, capsys):
        # no LICENSE detected and --non-interactive -> proceeds with "Unknown"
        (tmp_path / "A.py").write_text("print(1)\n")
        rc = _run_main([str(tmp_path), "--non-interactive", "--report"], capsys)
        assert rc == 0

    def test_default_listing_branch(self, tmp_path, capsys):
        # No --report: prints files needing SPDX headers, old-SPDX files,
        # and manifests to update (covers the else branch of main()).
        (tmp_path / "LICENSE").write_text("MIT License\nPermission is hereby granted, free of charge\n")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "a.py").write_text("print(1)\n")  # missing SPDX
        (tmp_path / "src" / "b.py").write_text("# SPDX-License-Identifier: MIT\nprint(2)\n")
        (tmp_path / "package.json").write_text('{"license": "MIT"}')
        rc = _run_main([str(tmp_path), "--from", "MIT", "--non-interactive"], capsys)
        assert rc == 0
        out = capsys.readouterr().out
        assert "a.py" in out            # missing SPDX header listing
        assert "b.py" in out            # old MIT SPDX header listing
        assert "package.json" in out    # manifest listing
        assert "Next steps" in out
