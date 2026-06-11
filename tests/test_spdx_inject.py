"""Tests for opl_spdx_inject.py"""
from __future__ import annotations

import os
import textwrap
from pathlib import Path

import pytest
import sys

# Add tools directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from opl_spdx_inject import (
    COMMENT_STYLES,
    SHEBANG_LANGS,
    SPDX_RE,
    SKIP_DIRS,
    SKIP_FILES,
    detect_language,
    make_header,
    has_spdx,
    is_binary,
    inject_header,
    collect_files,
)


# --- detect_language ---

class TestDetectLanguage:
    def test_py_extension(self, tmp_path):
        f = tmp_path / "main.py"
        f.write_text("print('hello')\n")
        assert detect_language(f) == "py"

    def test_js_extension(self, tmp_path):
        f = tmp_path / "app.js"
        f.write_text("console.log('hi')\n")
        assert detect_language(f) == "js"

    def test_ts_extension(self, tmp_path):
        f = tmp_path / "index.ts"
        f.write_text("export {}\n")
        assert detect_language(f) == "ts"

    def test_rs_extension(self, tmp_path):
        f = tmp_path / "main.rs"
        f.write_text("fn main() {}\n")
        assert detect_language(f) == "rs"

    def test_html_extension(self, tmp_path):
        f = tmp_path / "index.html"
        f.write_text("<html></html>\n")
        assert detect_language(f) == "html"

    def test_css_extension(self, tmp_path):
        f = tmp_path / "style.css"
        f.write_text("body { color: red; }\n")
        assert detect_language(f) == "css"

    def test_makefile_by_name(self, tmp_path):
        f = tmp_path / "Makefile"
        f.write_text("all: build\n")
        assert detect_language(f) == "Makefile"

    def test_dockerfile_by_name(self, tmp_path):
        f = tmp_path / "Dockerfile"
        f.write_text("FROM python:3.11\n")
        assert detect_language(f) == "Dockerfile"

    def test_gitignore_by_name(self, tmp_path):
        f = tmp_path / ".gitignore"
        f.write_text("__pycache__/\n")
        assert detect_language(f) is None

    def test_shebang_python(self, tmp_path):
        f = tmp_path / "script"
        f.write_text("#!/usr/bin/env python\nprint('hi')\n")
        assert detect_language(f) == "py"

    def test_shebang_bash(self, tmp_path):
        f = tmp_path / "script"
        f.write_text("#!/bin/bash\necho hi\n")
        assert detect_language(f) == "sh"

    def test_shebang_node(self, tmp_path):
        f = tmp_path / "script"
        f.write_text("#!/usr/bin/env node\nconsole.log('hi')\n")
        assert detect_language(f) == "js"

    def test_shebang_ruby(self, tmp_path):
        f = tmp_path / "script"
        f.write_text("#!/usr/bin/env ruby\nputs 'hi'\n")
        assert detect_language(f) == "rb"

    def test_unknown_extension(self, tmp_path):
        f = tmp_path / "data.xyz"
        f.write_text("some data\n")
        assert detect_language(f) is None

    def test_binary_file(self, tmp_path):
        f = tmp_path / "image.png"
        f.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00")
        assert detect_language(f) is None

    def test_go_extension(self, tmp_path):
        f = tmp_path / "main.go"
        f.write_text("package main\n")
        assert detect_language(f) == "go"

    def test_java_extension(self, tmp_path):
        f = tmp_path / "Main.java"
        f.write_text("class Main {}\n")
        assert detect_language(f) == "java"

    def test_sql_extension(self, tmp_path):
        f = tmp_path / "query.sql"
        f.write_text("SELECT 1;\n")
        assert detect_language(f) == "sql"


# --- make_header ---

class TestMakeHeader:
    def test_python_header(self):
        assert make_header("py") == "# SPDX-License-Identifier: OPL-1.3.1"

    def test_js_header(self):
        assert make_header("js") == "// SPDX-License-Identifier: OPL-1.3.1"

    def test_html_header(self):
        assert make_header("html") == "<!-- SPDX-License-Identifier: OPL-1.3.1 -->"

    def test_css_header(self):
        assert make_header("css") == "/* SPDX-License-Identifier: OPL-1.3.1 */"

    def test_lua_header(self):
        assert make_header("lua") == "-- SPDX-License-Identifier: OPL-1.3.1"

    def test_erlang_header(self):
        assert make_header("erl") == "% SPDX-License-Identifier: OPL-1.3.1"

    def test_ocaml_header(self):
        assert make_header("ml") == "(* SPDX-License-Identifier: OPL-1.3.1 *)"

    def test_makefile_header(self):
        assert make_header("Makefile") == "# SPDX-License-Identifier: OPL-1.3.1"

    def test_all_styles_produce_valid_spdx(self):
        for lang in COMMENT_STYLES:
            header = make_header(lang)
            assert SPDX_RE.search(header), f"Language {lang} header missing SPDX: {header}"
            assert "OPL-1.3.1" in header, f"Language {lang} header missing OPL-1.3.1: {header}"


# --- has_spdx ---

class TestHasSpdx:
    def test_file_with_spdx(self, tmp_path):
        f = tmp_path / "main.py"
        f.write_text("# SPDX-License-Identifier: OPL-1.3.1\nprint('hello')\n")
        assert has_spdx(f) is True

    def test_file_without_spdx(self, tmp_path):
        f = tmp_path / "main.py"
        f.write_text("print('hello')\n")
        assert has_spdx(f) is False

    def test_case_insensitive(self, tmp_path):
        f = tmp_path / "main.py"
        f.write_text("# spdx-license-identifier: MIT\nprint('hello')\n")
        assert has_spdx(f) is True

    def test_nonexistent_file(self, tmp_path):
        f = tmp_path / "nonexistent.py"
        assert has_spdx(f) is True

    def test_empty_file(self, tmp_path):
        f = tmp_path / "empty.py"
        f.write_text("")
        assert has_spdx(f) is False


# --- is_binary ---

class TestIsBinary:
    def test_text_file(self, tmp_path):
        f = tmp_path / "main.py"
        f.write_text("print('hello')\n")
        assert is_binary(f) is False

    def test_binary_file(self, tmp_path):
        f = tmp_path / "image.png"
        f.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00")
        assert is_binary(f) is True

    def test_empty_file(self, tmp_path):
        f = tmp_path / "empty.txt"
        f.write_bytes(b"")
        assert is_binary(f) is False

    def test_nonexistent_file(self, tmp_path):
        f = tmp_path / "nonexistent.bin"
        assert is_binary(f) is True


# --- inject_header ---

class TestInjectHeader:
    def test_inject_normal_file(self, tmp_path):
        f = tmp_path / "main.py"
        f.write_text("print('hello')\n")
        assert inject_header(f, "py") is True
        content = f.read_text()
        assert content.startswith("# SPDX-License-Identifier: OPL-1.3.1\n")
        assert "print('hello')" in content

    def test_inject_shebang_file(self, tmp_path):
        f = tmp_path / "script.sh"
        f.write_text("#!/bin/bash\necho hello\n")
        assert inject_header(f, "sh") is True
        content = f.read_text()
        assert content.startswith("#!/bin/bash\n# SPDX-License-Identifier: OPL-1.3.1\n")
        assert "echo hello" in content

    def test_inject_dry_run(self, tmp_path):
        f = tmp_path / "main.py"
        original = "print('hello')\n"
        f.write_text(original)
        assert inject_header(f, "py", dry_run=True) is True
        assert f.read_text() == original

    def test_inject_html_file(self, tmp_path):
        f = tmp_path / "index.html"
        f.write_text("<html></html>\n")
        assert inject_header(f, "html") is True
        content = f.read_text()
        assert "<!-- SPDX-License-Identifier: OPL-1.3.1 -->" in content

    def test_inject_preserves_content(self, tmp_path):
        f = tmp_path / "main.py"
        original = "#!/usr/bin/env python\nimport os\nprint(os.getcwd())\n"
        f.write_text(original)
        inject_header(f, "py")
        content = f.read_text()
        assert "#!/usr/bin/env python" in content
        assert "import os" in content
        assert "print(os.getcwd())" in content


# --- collect_files ---

class TestCollectFiles:
    def test_collects_python_files(self, tmp_path):
        (tmp_path / "main.py").write_text("print('hi')\n")
        (tmp_path / "utils.py").write_text("def foo(): pass\n")
        files = collect_files(tmp_path, [])
        assert len(files) == 2

    def test_skips_git_directory(self, tmp_path):
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "config").write_text("# config\n")
        (tmp_path / "main.py").write_text("print('hi')\n")
        files = collect_files(tmp_path, [])
        assert len(files) == 1

    def test_skips_node_modules(self, tmp_path):
        nm_dir = tmp_path / "node_modules"
        nm_dir.mkdir()
        (nm_dir / "lib.js").write_text("module.exports = {}\n")
        (tmp_path / "app.js").write_text("console.log('hi')\n")
        files = collect_files(tmp_path, [])
        assert len(files) == 1

    def test_skips_lock_files(self, tmp_path):
        (tmp_path / "package-lock.json").write_text("{}\n")
        (tmp_path / "app.js").write_text("console.log('hi')\n")
        files = collect_files(tmp_path, [])
        assert len(files) == 1

    def test_skips_binary_files(self, tmp_path):
        (tmp_path / "image.png").write_bytes(b"\x89PNG\x00\x00")
        (tmp_path / "main.py").write_text("print('hi')\n")
        files = collect_files(tmp_path, [])
        assert len(files) == 1

    def test_exclude_pattern(self, tmp_path):
        (tmp_path / "main.py").write_text("print('hi')\n")
        (tmp_path / "test_main.py").write_text("assert True\n")
        files = collect_files(tmp_path, ["test_"])
        assert len(files) == 1
        assert "main.py" in str(files[0])

    def test_empty_directory(self, tmp_path):
        files = collect_files(tmp_path, [])
        assert files == []

    def test_nested_directories(self, tmp_path):
        sub = tmp_path / "src" / "lib"
        sub.mkdir(parents=True)
        (sub / "core.py").write_text("# core\n")
        (tmp_path / "main.py").write_text("# main\n")
        files = collect_files(tmp_path, [])
        assert len(files) == 2


# --- CLI tests ---

class TestCLI:
    def test_help(self, tmp_path):
        import subprocess
        result = subprocess.run(
            [sys.executable, str(Path(__file__).resolve().parent.parent / "tools" / "opl_spdx_inject.py"), "--help"],
            capture_output=True, text=True
        )
        assert result.returncode == 0
        assert "SPDX" in result.stdout
        assert "--dry-run" in result.stdout

    def test_check_mode_passes(self, tmp_path):
        import subprocess
        f = tmp_path / "main.py"
        f.write_text("# SPDX-License-Identifier: OPL-1.3.1\nprint('hi')\n")
        result = subprocess.run(
            [sys.executable, str(Path(__file__).resolve().parent.parent / "tools" / "opl_spdx_inject.py"),
             str(tmp_path), "--check"],
            capture_output=True, text=True
        )
        assert result.returncode == 0
        assert "All" in result.stdout

    def test_check_mode_fails(self, tmp_path):
        import subprocess
        f = tmp_path / "main.py"
        f.write_text("print('hi')\n")
        result = subprocess.run(
            [sys.executable, str(Path(__file__).resolve().parent.parent / "tools" / "opl_spdx_inject.py"),
             str(tmp_path), "--check"],
            capture_output=True, text=True
        )
        assert result.returncode == 1
        assert "missing" in result.stdout.lower()

    def test_dry_run(self, tmp_path):
        import subprocess
        f = tmp_path / "main.py"
        f.write_text("print('hi')\n")
        result = subprocess.run(
            [sys.executable, str(Path(__file__).resolve().parent.parent / "tools" / "opl_spdx_inject.py"),
             str(tmp_path), "--dry-run"],
            capture_output=True, text=True
        )
        assert result.returncode == 0
        assert "DRY RUN" in result.stdout
        assert f.read_text() == "print('hi')\n"
