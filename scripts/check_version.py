#!/usr/bin/env python3
# SPDX-License-Identifier: OPL-1.3.1
"""Verify that all tools use shared _version.py (single source of truth)."""
import re
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent.parent

    # Read canonical version from _version.py
    version_file = root / "tools" / "_version.py"
    if not version_file.exists():
        print("ERROR: tools/_version.py not found")
        return 1

    version_text = version_file.read_text()
    m = re.search(r'__version__\s*=\s*"([^"]+)"', version_text)
    if not m:
        print("ERROR: No __version__ found in tools/_version.py")
        return 1
    canonical = m.group(1)
    print(f"Canonical version in _version.py: {canonical}")

    # Verify __init__.py re-exports from _version
    init_file = root / "tools" / "__init__.py"
    if init_file.exists():
        init_text = init_file.read_text()
        if "from _version import __version__" not in init_text:
            print("WARNING: __init__.py does not re-export __version__ from _version")
        else:
            print("__init__.py correctly re-exports from _version")

    # Verify each tool imports from _version
    tools_with_issues = []
    tools_ok = 0
    for fp in sorted(root.glob("tools/opl_*.py")):
        text = fp.read_text()
        has_import = bool(re.search(r"from _version import __version__", text))
        has_hardcoded = bool(
            re.search(r'version="OPL Adoption Tools [0-9]+\.[0-9]+', text)
        )
        if has_hardcoded:
            tools_with_issues.append(f"  {fp.name}: has hardcoded version")
        elif has_import:
            tools_ok += 1
        else:
            tools_with_issues.append(f"  {fp.name}: no _version import found")

    print(f"Tools using _version: {tools_ok}/6")
    if tools_with_issues:
        print("ERROR:")
        for issue in tools_with_issues:
            print(issue)
        return 1

    print("All tools correctly import from _version")
    return 0


if __name__ == "__main__":
    sys.exit(main())
