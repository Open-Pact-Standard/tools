#!/usr/bin/env python3
"""OPL License Migration Helper

Helps projects migrate from MIT/Apache/GPL to the Open-Pact License v1.4.
Usage: python3 opl_migrate.py [directory] [--from MIT|Apache-2.0|GPL-3.0] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    sys.path.insert(0, str(Path(__file__).parent))
    from opl_spdx_inject import collect_files, detect_language, has_spdx
except ImportError:
    print("Error: opl_spdx_inject.py must be in the same directory", file=sys.stderr)
    sys.exit(1)


OLD_LICENSE_PATTERNS: dict[str, list[re.Pattern]] = {
    "MIT": [
        re.compile(r"(?i)MIT License", re.MULTILINE),
        re.compile(r"(?i)Permission is hereby granted, free of charge", re.MULTILINE),
        re.compile(r"SPDX-License-Identifier:\s*MIT", re.MULTILINE),
    ],
    "Apache-2.0": [
        re.compile(r"(?i)Apache License.*2\.0", re.MULTILINE),
        re.compile(r"(?i)Licensed under the Apache License", re.MULTILINE),
        re.compile(r"SPDX-License-Identifier:\s*Apache-2\.0", re.MULTILINE),
    ],
    "GPL-3.0": [
        re.compile(r"(?i)GNU GENERAL PUBLIC LICENSE.*Version 3", re.MULTILINE),
        re.compile(r"SPDX-License-Identifier:\s*GPL-3\.0", re.MULTILINE),
    ],
    "GPL-2.0": [
        re.compile(r"(?i)GNU GENERAL PUBLIC LICENSE.*Version 2", re.MULTILINE),
        re.compile(r"SPDX-License-Identifier:\s*GPL-2\.0", re.MULTILINE),
    ],
    "BSD-3-Clause": [
        re.compile(r"(?i)BSD 3-Clause", re.MULTILINE),
        re.compile(r"SPDX-License-Identifier:\s*BSD-3-Clause", re.MULTILINE),
    ],
    "BSD-2-Clause": [
        re.compile(r"(?i)BSD 2-Clause", re.MULTILINE),
        re.compile(r"SPDX-License-Identifier:\s*BSD-2-Clause", re.MULTILINE),
    ],
}


def detect_old_license(root: Path) -> str | None:
    for name in ["LICENSE", "LICENSE.md", "LICENSE.txt", "LICENCE", "LICENCE.md"]:
        p = root / name
        if p.exists():
            content = p.read_text(encoding="utf-8", errors="ignore")
            for lic_name, patterns in OLD_LICENSE_PATTERNS.items():
                for pat in patterns:
                    if pat.search(content):
                        return lic_name
    # Check package.json
    pkg = root / "package.json"
    if pkg.exists():
        try:
            data = json.loads(pkg.read_text())
            lic = data.get("license", "")
            if lic in OLD_LICENSE_PATTERNS:
                return lic
        except Exception:
            pass
    return None


def scan_manifests(root: Path) -> list[tuple[str, str]]:
    manifests = []
    pkg = root / "package.json"
    if pkg.exists():
        manifests.append((str(pkg), "license"))
    cargo = root / "Cargo.toml"
    if cargo.exists():
        content = cargo.read_text(encoding="utf-8", errors="ignore")
        if re.search(r"(?i)^license\s*=", content, re.MULTILINE):
            manifests.append((str(cargo), "license"))
    pyproj = root / "pyproject.toml"
    if pyproj.exists():
        content = pyproj.read_text(encoding="utf-8", errors="ignore")
        if re.search(r"(?i)license", content):
            manifests.append((str(pyproj), "license"))
    setup = root / "setup.py"
    if setup.exists():
        content = setup.read_text(encoding="utf-8", errors="ignore")
        if re.search(r"(?i)license\s*=", content):
            manifests.append((str(setup), "license"))
    return manifests


def generate_migration_report(root: Path, old_license: str, files_to_update: list[Path]) -> str:
    manifests = scan_manifests(root)
    report = f"""# OPL Migration Report

## Current License: {old_license}
## Target License: OPL-1.4 (Open-Pact License)

## Files Requiring SPDX Header Updates ({len(files_to_update)})

"""
    for f in sorted(files_to_update):
        rel = f.relative_to(root)
        lang = detect_language(f) or "unknown"
        report += f"- [x] `{rel}` ({lang})\n"
    if manifests:
        report += "\n## Package Manifests to Update\n\n"
        for path, field in manifests:
            rel = Path(path).relative_to(root)
            report += f"- [x] `{rel}` -- change `{field}` to `OPL-1.4`\n"
    report += """\n## Next Steps

1. Run `python3 opl_init.py` to generate your NOTICE file
2. Run `python3 opl_spdx_inject.py .` to add SPDX headers to all files
3. Update the license field in each package manifest listed above
4. Replace your LICENSE file with the OPL LICENSE.md
5. Publish your Standard Terms page
6. Run `python3 opl_check.py` to verify compliance
"""
    return report


# Single source of truth for version: read from _version.py
from _version import __version__  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate a project to OPL-1.4")
    parser.add_argument("--version", action="version", version=f"OPL Adoption Tools {__version__}")
    parser.add_argument("directory", nargs="?", default=".",
                        help="Repository root (default: .)")
    parser.add_argument("--from", dest="old_license",
                        help="Current license (auto-detected if omitted)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would change without modifying files")
    parser.add_argument("--report", action="store_true",
                        help="Generate a migration report (markdown)")
    parser.add_argument("--exclude", action="append", default=[],
                        help="Exclude pattern for file scanning")
    parser.add_argument("--non-interactive", action="store_true",
                        help="Use defaults, skip prompts")
    args = parser.parse_args()

    root = Path(args.directory).resolve()
    if not root.is_dir():
        print(f"Error: {root} is not a directory", file=sys.stderr)
        sys.exit(1)

    print("\n  OPL License Migration Helper v1.4\n")

    old_license = args.old_license or detect_old_license(root)
    if old_license:
        print(f"  Detected current license: {old_license}")
    else:
        print("  Could not auto-detect current license.")
        if not args.non_interactive:
            old_license = input("  Enter current license (or press Enter to skip): ").strip()
    if old_license:
        print(f"  Migrating from {old_license} -> OPL-1.4\n")
    else:
        print("  Migrating to OPL-1.4 (source license unknown)\n")

    print("  Scanning repository...")
    files = collect_files(root, args.exclude)
    missing_spdx = [f for f in files if not has_spdx(f)]

    has_old_spdx: list[Path] = []
    if old_license:
        old_pat = re.compile(
            rf"SPDX-License-Identifier:.*{re.escape(old_license)}", re.IGNORECASE)
        for f in files:
            try:
                content = f.read_text(encoding="utf-8", errors="ignore")[:4096]
                if old_pat.search(content):
                    has_old_spdx.append(f)
            except (OSError, UnicodeDecodeError):
                pass

    manifests = scan_manifests(root)

    print(f"  Found {len(files)} source files")
    print(f"  {len(missing_spdx)} files missing any SPDX header")
    if has_old_spdx:
        print(f"  {len(has_old_spdx)} files with old {old_license} SPDX header")
    print(f"  {len(manifests)} package manifests with license field\n")

    if args.report:
        report = generate_migration_report(
            root, old_license or "Unknown", missing_spdx)
        report_path = root / "OPL_MIGRATION_REPORT.md"
        if not args.dry_run:
            report_path.write_text(report, encoding="utf-8")
            print(f"  Migration report written to {report_path}")
        else:
            print(f"  [DRY RUN] Would write report to {report_path}")
    else:
        print("  Files needing SPDX headers:")
        for f in sorted(missing_spdx):
            rel = f.relative_to(root)
            lang = detect_language(f) or "?"
            marker = "[DRY RUN] " if args.dry_run else ""
            print(f"    {marker}{rel} ({lang})")

        if has_old_spdx:
            print(f"\n  Files with old {old_license} SPDX header:")
            for f in sorted(has_old_spdx):
                print(f"    {f.relative_to(root)}")

        if manifests:
            print("\n  Package manifests to update:")
            for path, field in manifests:
                print(f"    {Path(path).relative_to(root)} ({field} -> OPL-1.4)")

    print("\n  Next steps:")
    print("    1. python3 opl_init.py          # Generate NOTICE file")
    print("    2. python3 opl_spdx_inject.py   # Add SPDX headers")
    print("    3. python3 opl_check.py         # Verify compliance")
    print("    4. python3 opl_registry_gen.py   # (Optional) REGISTRY.json\n")


if __name__ == "__main__":
    main()
