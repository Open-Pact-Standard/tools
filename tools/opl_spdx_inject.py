#!/usr/bin/env python3
"""OPL SPDX Header Injector

Scans a repository and adds SPDX-License-Identifier headers to source files
that don't already have them. Supports all common languages and file types.

Usage:
    python3 opl_spdx_inject.py [directory] [--dry-run] [--exclude pattern] [--check]
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

COMMENT_STYLES = {
    "py": ("# ", ""), "rb": ("# ", ""), "pl": ("# ", ""),
    "sh": ("# ", ""), "bash": ("# ", ""), "zsh": ("# ", ""),
    "yml": ("# ", ""), "yaml": ("# ", ""), "toml": ("# ", ""),
    "ini": ("# ", ""), "cfg": ("# ", ""), "conf": ("# ", ""),
    "js": ("// ", ""), "ts": ("// ", ""), "jsx": ("// ", ""),
    "tsx": ("// ", ""), "java": ("// ", ""), "c": ("// ", ""),
    "h": ("// ", ""), "cpp": ("// ", ""), "hpp": ("// ", ""),
    "cc": ("// ", ""), "cxx": ("// ", ""), "go": ("// ", ""),
    "rs": ("// ", ""), "swift": ("// ", ""), "kt": ("// ", ""),
    "kts": ("// ", ""), "scala": ("// ", ""), "cs": ("// ", ""),
    "proto": ("// ", ""), "zig": ("// ", ""), "d": ("// ", ""),
    "r": ("# ", ""), "R": ("# ", ""),
    "lua": ("-- ", ""), "hs": ("-- ", ""), "elm": ("-- ", ""),
    "sql": ("-- ", ""),
    "html": ("<!-- ", " -->"), "xml": ("<!-- ", " -->"), "svg": ("<!-- ", " -->"),
    "css": ("/* ", " */"), "scss": ("/* ", " */"), "sass": ("// ", ""),
    "less": ("// ", ""),
    "json": ("// ", ""),
    "ex": ("# ", ""), "exs": ("# ", ""),
    "erl": ("% ", ""), "hrl": ("% ", ""),
    "jl": ("# ", ""),
    "ml": ("(* ", " *)"), "mli": ("(* ", " *)"),
    "clj": (";; ", ""), "cljs": (";; ", ""),
    "lisp": ("; ", ""), "el": ("; ", ""),
    "vhdl": ("-- ", ""), "v": ("// ", ""), "sv": ("// ", ""),
    "vhd": ("-- ", ""),
    "tex": ("% ", ""), "sty": ("% ", ""), "dtx": ("% ", ""),
    "asm": ("; ", ""), "s": ("; ", ""), "S": ("# ", ""),
    "Makefile": ("# ", ""), "Dockerfile": ("# ", ""),
    "Containerfile": ("# ", ""),
    "gitignore": ("# ", ""), "dockerignore": ("# ", ""), "env": ("# ", ""),
}

SHEBANG_LANGS = {
    "#!/usr/bin/env python": "py", "#!/usr/bin/python": "py",
    "#!/usr/bin/env bash": "sh", "#!/usr/bin/env sh": "sh",
    "#!/bin/bash": "sh", "#!/bin/sh": "sh",
    "#!/usr/bin/env ruby": "rb", "#!/usr/bin/env node": "js",
    "#!/usr/bin/env perl": "pl",
}

SPDX_RE = re.compile(r"SPDX-License-Identifier:", re.IGNORECASE)

SKIP_DIRS = {
    ".git", ".hg", ".svn", "node_modules", "__pycache__", ".tox",
    ".mypy_cache", ".pytest_cache", ".eggs", "dist", "build",
    ".venv", "venv", "env", ".env", ".cargo", "target",
    "vendor", "third_party", "external", ".next", ".nuxt",
}

SKIP_FILES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "Cargo.lock", "poetry.lock", "Gemfile.lock",
    "go.sum", "composer.lock", "Pipfile.lock",
}


def detect_language(filepath: Path) -> str | None:
    name = filepath.name
    if name in COMMENT_STYLES:
        return name
    ext = filepath.suffix.lstrip(".")
    if ext in COMMENT_STYLES:
        return ext
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            first = f.readline(200)
            for shebang, lang in SHEBANG_LANGS.items():
                if first.startswith(shebang):
                    return lang
    except (OSError, UnicodeDecodeError):
        pass
    return None


def make_header(lang: str) -> str:
    prefix, suffix = COMMENT_STYLES[lang]
    return f"{prefix}SPDX-License-Identifier: OPL-1.3.1{suffix}"


def has_spdx(filepath: Path) -> bool:
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            head = f.read(4096)
            return bool(SPDX_RE.search(head))
    except (OSError, UnicodeDecodeError):
        return True


def is_binary(filepath: Path) -> bool:
    try:
        with open(filepath, "rb") as f:
            chunk = f.read(8192)
            return b"\x00" in chunk
    except OSError:
        return True


def inject_header(filepath: Path, lang: str, dry_run: bool = False) -> bool:
    header = make_header(lang)
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except (OSError, UnicodeDecodeError):
        return False
    if content.startswith("#!"):
        first_newline = content.index("\n")
        new_content = content[:first_newline + 1] + header + "\n" + content[first_newline + 1:]
    else:
        new_content = header + "\n" + content
    if not dry_run:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)
    return True


def collect_files(root: Path, exclude_patterns: list[str]) -> list[Path]:
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fname in filenames:
            fpath = Path(dirpath) / fname
            if fname in SKIP_FILES:
                continue
            if is_binary(fpath):
                continue
            rel = str(fpath.relative_to(root))
            if any(re.search(pat, rel) for pat in exclude_patterns):
                continue
            lang = detect_language(fpath)
            if lang is None:
                continue
            files.append(fpath)
    return files


# Single source of truth for version: read from __init__.py
try:
    from pathlib import Path
    _ns = {}
    exec((Path(__file__).resolve().parent / "__init__.py").read_text(), _ns)
    __version__ = _ns["__version__"]
except FileNotFoundError:
    raise SystemExit("ERROR: tools/__init__.py not found — cannot determine version")

def main():
    parser = argparse.ArgumentParser(
        description="Add SPDX-License-Identifier: OPL-1.3.1 headers to source files"
    )
    parser.add_argument("--version", action="version", version=f"OPL Adoption Tools {__version__}")
    parser.add_argument("directory", nargs="?", default=".",
                        help="Root directory to scan (default: .)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be changed without modifying files")
    parser.add_argument("--exclude", action="append", default=[],
                        help="Regex pattern to exclude (repeatable)")
    parser.add_argument("--check", action="store_true",
                        help="Exit non-zero if any files are missing headers")
    args = parser.parse_args()

    root = Path(args.directory).resolve()
    if not root.is_dir():
        print(f"Error: {root} is not a directory", file=sys.stderr)
        sys.exit(1)

    files = collect_files(root, args.exclude)
    missing = [f for f in files if not has_spdx(f)]

    if args.check:
        if missing:
            print(f"Found {len(missing)} file(s) missing SPDX headers:")
            for f in missing:
                print(f"  {f.relative_to(root)}")
            sys.exit(1)
        else:
            print(f"All {len(files)} source files have SPDX headers.")
            sys.exit(0)

    mode = "[DRY RUN] " if args.dry_run else ""
    if not missing:
        print(f"{mode}All {len(files)} source files already have SPDX headers.")
        return

    count = 0
    for fpath in missing:
        lang = detect_language(fpath)
        rel = fpath.relative_to(root)
        if inject_header(fpath, lang, args.dry_run):
            count += 1
            print(f"  {mode}Added header: {rel} ({lang})")

    print(f"\n{mode}Modified {count} file(s).")
    if args.dry_run:
        print("Run without --dry-run to apply changes.")


if __name__ == "__main__":
    main()
