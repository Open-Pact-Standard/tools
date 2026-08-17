# SPDX-License-Identifier: OPL-1.4
"""In-process tests for opl_spdx_inject.py — header generation, detection, injection, CLI."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import opl_spdx_inject as spdx


class TestMakeHeader:
    def test_py(self):
        assert spdx.make_header("py") == "# SPDX-License-Identifier: OPL-1.4"

    def test_js(self):
        assert spdx.make_header("js") == "// SPDX-License-Identifier: OPL-1.4"

    def test_html(self):
        assert spdx.make_header("html") == "<!-- SPDX-License-Identifier: OPL-1.4 -->"

    def test_css(self):
        assert spdx.make_header("css") == "/* SPDX-License-Identifier: OPL-1.4 */"

    def test_custom_version(self):
        assert spdx.make_header("py", "1.3.1") == "# SPDX-License-Identifier: OPL-1.3.1"

    def test_unknown_lang_raises(self):
        with pytest.raises(KeyError):
            spdx.make_header("zzz")


class TestHasSpdx:
    def test_present(self, tmp_path):
        f = tmp_path / "a.py"
        f.write_text("# SPDX-License-Identifier: OPL-1.4\nprint(1)\n")
        assert spdx.has_spdx(f) is True

    def test_absent(self, tmp_path):
        f = tmp_path / "a.py"
        f.write_text("print(1)\n")
        assert spdx.has_spdx(f) is False

    def test_unreadable_returns_true(self, tmp_path):
        f = tmp_path / "ghost.py"
        assert spdx.has_spdx(f) is True


class TestIsBinary:
    def test_text_not_binary(self, tmp_path):
        f = tmp_path / "a.py"
        f.write_bytes(b"print('hello')\n")
        assert spdx.is_binary(f) is False

    def test_binary_detected(self, tmp_path):
        f = tmp_path / "a.bin"
        f.write_bytes(b"\x00\x01\x02\x03")
        assert spdx.is_binary(f) is True

    def test_missing_returns_true(self, tmp_path):
        assert spdx.is_binary(tmp_path / "nope") is True


class TestDetectLanguage:
    def test_by_extension(self, tmp_path):
        f = tmp_path / "x.js"
        assert spdx.detect_language(f) == "js"

    def test_by_filename(self, tmp_path):
        f = tmp_path / "Dockerfile"
        assert spdx.detect_language(f) == "Dockerfile"

    def test_by_shebang(self, tmp_path):
        f = tmp_path / "script"
        f.write_text("#!/usr/bin/env python\nprint(1)\n")
        assert spdx.detect_language(f) == "py"

    def test_unknown(self, tmp_path):
        f = tmp_path / "data.unknownext"
        assert spdx.detect_language(f) is None

    def test_binary_with_known_ext_resolves_by_ext(self, tmp_path):
        # detect_language keys off extension/name/shebang, not content — a
        # binary .py is still detected as 'py' (binary skipping happens later
        # in collect_files via is_binary()).
        f = tmp_path / "x.py"
        f.write_bytes(b"\x00\x01")
        assert spdx.detect_language(f) == "py"


class TestInjectHeader:
    def test_no_shebang(self, tmp_path):
        f = tmp_path / "a.py"
        f.write_text("print(1)\n")
        assert spdx.inject_header(f, "py") is True
        assert f.read_text().startswith("# SPDX-License-Identifier: OPL-1.4\n")

    def test_with_shebang(self, tmp_path):
        f = tmp_path / "a.py"
        f.write_text("#!/usr/bin/env python\nprint(1)\n")
        assert spdx.inject_header(f, "py") is True
        out = f.read_text()
        assert out.startswith("#!/usr/bin/env python\n# SPDX-License-Identifier: OPL-1.4\n")

    def test_dry_run_does_not_write(self, tmp_path):
        f = tmp_path / "a.py"
        f.write_text("print(1)\n")
        assert spdx.inject_header(f, "py", dry_run=True) is True
        assert "SPDX" not in f.read_text()

    def test_custom_version(self, tmp_path):
        f = tmp_path / "a.py"
        f.write_text("x\n")
        spdx.inject_header(f, "py", license_version="1.3.1")
        assert "OPL-1.3.1" in f.read_text()

    def test_oserror_returns_false(self, tmp_path):
        assert spdx.inject_header(tmp_path, "py") is False


class TestCollectFiles:
    def test_collects_source(self, tmp_path):
        (tmp_path / "a.py").write_text("x\n")
        (tmp_path / "b.js").write_text("x\n")
        files = spdx.collect_files(tmp_path, [])
        assert len(files) == 2

    def test_skips_skip_dirs(self, tmp_path):
        (tmp_path / "node_modules").mkdir()
        (tmp_path / "node_modules" / "c.py").write_text("x\n")
        (tmp_path / "a.py").write_text("x\n")
        files = spdx.collect_files(tmp_path, [])
        assert all("node_modules" not in str(f) for f in files)

    def test_skips_lock_files(self, tmp_path):
        (tmp_path / "package-lock.json").write_text("{}")
        (tmp_path / "a.py").write_text("x\n")
        files = spdx.collect_files(tmp_path, [])
        assert all(f.name != "package-lock.json" for f in files)

    def test_exclude_pattern(self, tmp_path):
        (tmp_path / "a.py").write_text("x\n")
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "t.py").write_text("x\n")
        files = spdx.collect_files(tmp_path, [r"tests/.*"])
        assert all("tests" not in str(f) for f in files)

    def test_skips_unknown_language(self, tmp_path):
        (tmp_path / "data.txt").write_text("x\n")
        (tmp_path / "a.py").write_text("x\n")
        files = spdx.collect_files(tmp_path, [])
        assert all(f.suffix == ".py" for f in files)


def _run_main(argv, capsys):
    old = sys.argv
    sys.argv = ["opl_spdx_inject.py", *argv]
    try:
        spdx.main()
        return 0
    except SystemExit as e:
        return int(e.code or 0)
    finally:
        sys.argv = old


class TestMain:
    def test_version(self, capsys):
        rc = _run_main(["--version"], capsys)
        assert rc == 0
        assert "OPL Adoption Tools 1.4" in capsys.readouterr().out

    def test_non_dir_exit(self, tmp_path, capsys):
        rc = _run_main([str(tmp_path / "ghost")], capsys)
        assert rc == 1

    def test_empty_tree_exit(self, tmp_path, capsys):
        rc = _run_main([str(tmp_path)], capsys)
        assert rc == 1

    def test_check_missing_fails(self, tmp_path, capsys):
        (tmp_path / "a.py").write_text("print(1)\n")
        rc = _run_main([str(tmp_path), "--check"], capsys)
        assert rc == 1

    def test_check_all_present_ok(self, tmp_path, capsys):
        (tmp_path / "a.py").write_text("# SPDX-License-Identifier: OPL-1.4\nprint(1)\n")
        rc = _run_main([str(tmp_path), "--check"], capsys)
        assert rc == 0

    def test_dry_run_injects(self, tmp_path, capsys):
        (tmp_path / "a.py").write_text("print(1)\n")
        rc = _run_main([str(tmp_path), "--dry-run"], capsys)
        assert rc == 0
        assert "SPDX" not in (tmp_path / "a.py").read_text()

    def test_real_inject(self, tmp_path, capsys):
        (tmp_path / "a.py").write_text("print(1)\n")
        rc = _run_main([str(tmp_path)], capsys)
        assert rc == 0
        assert "SPDX" in (tmp_path / "a.py").read_text()

    def test_license_version_flag(self, tmp_path, capsys):
        (tmp_path / "a.py").write_text("print(1)\n")
        rc = _run_main([str(tmp_path), "--license-version", "1.3.1"], capsys)
        assert rc == 0
        assert "OPL-1.3.1" in (tmp_path / "a.py").read_text()
