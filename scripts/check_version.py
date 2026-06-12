#!/usr/bin/env python3
# SPDX-License-Identifier: OPL-1.3.1
"""Verify that all tools report the same version string."""
import glob
import re
import sys
from pathlib import Path

def main() -> int:
    root = Path(__file__).resolve().parent.parent
    versions: dict[str, str] = {}

    # Check each tool
    for fp in sorted(root.glob("tools/opl_*.py")):
        with open(fp) as f:
            for line in f:
                m = re.search(r'version="OPL Adoption Tools ([^"]+)"', line)
                if m:
                    versions[fp.name] = m.group(1)
                    break

    # Check __init__.py
    init_file = root / "tools" / "__init__.py"
    if init_file.exists():
        with open(init_file) as f:
            for line in f:
                m = re.search(r'__version__\s*=\s*"([^"]+)"', line)
                if m:
                    versions["__init__.py"] = m.group(1)
                    break

    if not versions:
        print("ERROR: No version strings found in any tool")
        return 1

    unique = set(versions.values())
    if len(unique) != 1:
        print("ERROR: Version mismatch across files:")
        for name, ver in sorted(versions.items()):
            print(f"  {name}: {ver}")
        return 1

    print(f"Version consistent: {unique.pop()}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
