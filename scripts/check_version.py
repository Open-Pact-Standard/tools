#!/usr/bin/env python3
# SPDX-License-Identifier: OPL-1.3.1
"""Verify that all tools read version from __init__.py (single source of truth)."""
import re
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent.parent

    # Read canonical version from __init__.py
    init_file = root / "tools" / "__init__.py"
    if not init_file.exists():
        print("ERROR: tools/__init__.py not found")
        return 1

    init_text = init_file.read_text()
    m = re.search(r'__version__\s*=\s*"([^"]+)"', init_text)
    if not m:
        print("ERROR: No __version__ found in tools/__init__.py")
        return 1
    canonical = m.group(1)
    print(f"Canonical version in __init__.py: {canonical}")

    # Verify each tool uses __version__ (single source) instead of hardcoded string
    tools_with_issues = []
    tools_ok = 0
    for fp in sorted(root.glob("tools/opl_*.py")):
        text = fp.read_text()
        has_fstring = bool(
            re.search(r'version=f"OPL Adoption Tools \{__version__\}', text)
        )
        has_hardcoded = bool(
            re.search(r'version="OPL Adoption Tools [0-9]+\.[0-9]+', text)
        )
        if has_hardcoded and not has_fstring:
            tools_with_issues.append(
                f"  {fp.name}: has hardcoded version"
            )
        elif has_fstring:
            tools_ok += 1
        else:
            tools_with_issues.append(f"  {fp.name}: no --version found")

    print(f"Tools using __version__: {tools_ok}/6")
    if tools_with_issues:
        print("ERROR: Some tools have hardcoded versions:")
        for issue in tools_with_issues:
            print(issue)
        return 1

    print("All tools correctly use __version__ from __init__.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
