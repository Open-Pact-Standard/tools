#!/usr/bin/env python3
# SPDX-License-Identifier: OPL-1.3.1
"""OPL Compliance Checker

Validates that a repository is correctly configured for OPL v1.3.1.
Usage: python3 opl_check.py [directory] [--json] [--strict] [--skip-remote]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path

try:
    sys.path.insert(0, str(Path(__file__).parent))
    from opl_spdx_inject import collect_files, has_spdx
except ImportError:
    collect_files = None
    has_spdx = None


class CheckResult:
    def __init__(self, name: str, passed: bool, message: str, severity: str = "error"):
        self.name = name
        self.passed = passed
        self.message = message
        self.severity = severity

    def to_dict(self) -> dict:
        return {"check": self.name, "passed": self.passed,
                "message": self.message, "severity": self.severity}


def check_license(root: Path) -> CheckResult:
    for name in ["LICENSE.md", "LICENSE", "LICENCE.md", "LICENCE"]:
        p = root / name
        if p.exists():
            content = p.read_text(encoding="utf-8", errors="ignore")
            if "Open-Pact License" in content or "OPL" in content:
                return CheckResult("license", True, f"Found {name} with OPL reference")
            return CheckResult("license", False, f"{name} exists but does not reference OPL", "warning")
    return CheckResult("license", False, "No LICENSE.md found in repo root")


def check_notice(root: Path) -> CheckResult:
    for name in ["NOTICE", "NOTICE.md", "NOTICE.txt"]:
        p = root / name
        if p.exists():
            content = p.read_text(encoding="utf-8", errors="ignore")
            missing = []
            if not re.search(r"(?i)copyright|maintainer", content):
                missing.append("copyright/maintainer")
            if not re.search(r"(?i)standard.terms|standard-terms", content):
                missing.append("standard terms URL")
            if not re.search(r"(?i)jurisdiction|governing", content):
                missing.append("jurisdiction")
            if not re.search(r"(?i)OPL|Open-Pact", content):
                missing.append("OPL reference")
            if missing:
                return CheckResult("notice", False, f"{name} missing fields: {', '.join(missing)}")
            return CheckResult("notice", True, f"{name} has all required fields")
    return CheckResult("notice", False, "No NOTICE file found")


def check_standard_terms_url(root: Path) -> CheckResult:
    notice_content = None
    for name in ["NOTICE", "NOTICE.md", "NOTICE.txt"]:
        p = root / name
        if p.exists():
            notice_content = p.read_text(encoding="utf-8", errors="ignore")
            break
    if not notice_content:
        return CheckResult("standard-terms-url", False, "Cannot check URL: no NOTICE file")

    urls = re.findall(r"https?://[^\s\"'<>]+", notice_content)
    if not urls:
        return CheckResult("standard-terms-url", False, "No URL found in NOTICE")

    url = urls[0].rstrip(".,;)")
    if not url.startswith("https://"):
        return CheckResult("standard-terms-url", False, f"URL must use HTTPS: {url}")

    try:
        req = urllib.request.Request(url, method="HEAD",
                                     headers={"User-Agent": "OPL-Checker/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            ct = resp.headers.get("Content-Type", "")
            if "text/html" not in ct:
                return CheckResult("standard-terms-url", False,
                                   f"URL does not return HTML (got {ct}): {url}", "warning")
            return CheckResult("standard-terms-url", True,
                               f"Standard Terms URL is reachable: {url}")
    except urllib.error.HTTPError as e:
        return CheckResult("standard-terms-url", False, f"URL returned HTTP {e.code}: {url}")
    except urllib.error.URLError as e:
        return CheckResult("standard-terms-url", False,
                           f"URL unreachable ({e.reason}): {url}", "warning")
    except Exception as e:
        return CheckResult("standard-terms-url", False,
                           f"URL check failed ({e}): {url}", "warning")


def check_spdx_headers(root: Path, exclude_patterns: list) -> CheckResult:
    if collect_files is None:
        return CheckResult("spdx-headers", False,
                           "Cannot import opl_spdx_inject module", "warning")
    files = collect_files(root, exclude_patterns)
    if not files:
        return CheckResult("spdx-headers", True, "No source files found (skipped)", "info")
    missing = [f.relative_to(root) for f in files if not has_spdx(f)]
    if missing:
        preview = ", ".join(str(m) for m in missing[:5])
        suffix = f" (+{len(missing)-5} more)" if len(missing) > 5 else ""
        return CheckResult("spdx-headers", False,
                           f"{len(missing)} files missing SPDX headers: {preview}{suffix}")
    return CheckResult("spdx-headers", True,
                       f"All {len(files)} source files have SPDX headers")


def check_opl_ai(root: Path) -> CheckResult:
    for name in ["NOTICE", "NOTICE.md", "NOTICE.txt"]:
        p = root / name
        if p.exists():
            content = p.read_text(encoding="utf-8", errors="ignore")
            if re.search(r"(?i)opl.ai|ai.training|opt.in|opt.out", content):
                return CheckResult("opl-ai", True,
                                   "OPL-AI configuration found in NOTICE", "info")
            return CheckResult("opl-ai", False,
                               "No OPL-AI configuration in NOTICE (optional)", "info")
    return CheckResult("opl-ai", False, "Cannot check OPL-AI: no NOTICE file", "info")


# Single source of truth for version: read from __init__.py
try:
    _version_file = (Path(__file__).resolve().parent / "__init__.py").read_text()
except FileNotFoundError:
    raise SystemExit("ERROR: tools/__init__.py not found — cannot determine version")
_version_match = re.search(r"__version__\s*=\s*\"([^\"]+)\"", _version_file)
if _version_match:
    __version__ = _version_match.group(1)
else:
    raise SystemExit("ERROR: Could not read __version__ from tools/__init__.py")


def main():
    parser = argparse.ArgumentParser(
        description="Check OPL v1.3.1 compliance for a repository")
    parser.add_argument("--version", action="version", version=f"OPL Adoption Tools {__version__}")
    parser.add_argument("directory", nargs="?", default=".",
                        help="Repository root (default: .)")
    parser.add_argument("--json", action="store_true",
                        help="Output results as JSON")
    parser.add_argument("--strict", action="store_true",
                        help="Treat warnings as errors")
    parser.add_argument("--skip-remote", action="store_true",
                        help="Skip URL reachability check")
    parser.add_argument("--exclude", action="append", default=[],
                        help="Exclude pattern for SPDX check")
    args = parser.parse_args()

    root = Path(args.directory).resolve()
    if not root.is_dir():
        print(f"Error: {root} is not a directory", file=sys.stderr)
        sys.exit(1)

    results = [
        check_license(root),
        check_notice(root),
    ]
    if not args.skip_remote:
        results.append(check_standard_terms_url(root))
    else:
        results.append(CheckResult("standard-terms-url", True,
                                   "Skipped (--skip-remote)", "info"))
    results.append(check_spdx_headers(root, args.exclude))
    results.append(check_opl_ai(root))

    if args.json:
        print(json.dumps([r.to_dict() for r in results], indent=2))
    else:
        errors = warnings = infos = passes = 0
        for r in results:
            if r.passed:
                icon = "PASS"
            elif r.severity == "warning":
                icon = "WARN"
            elif r.severity == "info":
                icon = "INFO"
            else:
                icon = "FAIL"
            print(f"  [{icon}] [{r.name}] {r.message}")
            if r.passed:
                passes += 1
            elif r.severity == "warning":
                warnings += 1
            elif r.severity == "info":
                infos += 1
            else:
                errors += 1
        print()
        print(f"  {passes} passed, {errors} errors, {warnings} warnings, {infos} info")

    exit_code = 0
    for r in results:
        if not r.passed and r.severity == "error":
            exit_code = 1
        if args.strict and not r.passed and r.severity == "warning":
            exit_code = 1
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
