#!/usr/bin/env python3
# SPDX-License-Identifier: OPL-1.4
"""OPL Compliance Checker

Validates that a repository is correctly configured for OPL v1.4.
Usage: python3 opl_check.py [directory] [--json] [--strict] [--skip-remote] [--check]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
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


def check_standard_terms_url(root: Path, offline: bool = False) -> CheckResult:
    """Check that the Standard Terms URL is valid and contains required content.

    In offline mode the check is structural only (URL present + HTTPS) — no
    network fetch. This keeps the Studio localhost-first: reachability/content
    verification is opt-in via the online path.
    """
    notice_content = None
    for name in ["NOTICE", "NOTICE.md", "NOTICE.txt"]:
        p = root / name
        if p.exists():
            notice_content = p.read_text(encoding="utf-8", errors="ignore")
            break
    if not notice_content:
        return CheckResult("standard-terms-url", False, "Cannot check URL: no NOTICE file")

    urls = re.findall(r"https?://[^\s\>\"'<]+", notice_content)
    if not urls:
        return CheckResult("standard-terms-url", False, "No URL found in NOTICE")
    url = urls[0].rstrip(".,;)")
    if not url.startswith("https://"):
        return CheckResult("standard-terms-url", False, f"URL must use HTTPS: {url}")
    if offline:
        return CheckResult("standard-terms-url", True,
                           f"Standard Terms URL present and HTTPS (offline check, not fetched): {url}")

    # Fetch and check the page content
    try:
        req = urllib.request.Request(url, method="HEAD",
                                     headers={"User-Agent": "OPL-Checker/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            ct = resp.headers.get("Content-Type", "")
            if "text/html" not in ct:
                return CheckResult("standard-terms-url", False,
                                   f"URL does not return HTML (got {ct}): {url}", "warning")
    except urllib.error.HTTPError as e:
        return CheckResult("standard-terms-url", False, f"URL returned HTTP {e.code}: {url}")
    except urllib.error.URLError as e:
        return CheckResult("standard-terms-url", False,
                           f"URL unreachable ({e.reason}): {url}", "warning")
    except Exception as e:
        return CheckResult("standard-terms-url", False,
                           f"URL check failed ({e}): {url}", "warning")

    # Now check that the page contains substantive content
    try:
        req = urllib.request.Request(url, method="GET",
                                     headers={"User-Agent": "OPL-Checker/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
            text = re.sub(r"<[^>]+>", " ", html)
            text = re.sub(r"\s+", " ", text).lower()

            has_pricing = any(kw in text for kw in
                ["price", "$", "fee", "cost", "tariff", "payment", "pay", "usd", "year", "month", "subscription"])
            has_terms = any(kw in text for kw in
                ["commercial use", "license", "terms", "permission", "agreement", "standard terms"])
            has_contact = any(kw in text for kw in
                ["contact", "email", "mailto", "stripe", "bank", "sponsor"])

            missing = []
            if not has_pricing:
                missing.append("pricing")
            if not has_terms:
                missing.append("commercial-use terms")
            if not has_contact:
                missing.append("payment mechanism or contact")

            if missing:
                return CheckResult("standard-terms-url", False,
                    "URL reachable and HTML, but may be missing: " + ", ".join(missing) +
                    " — verify your Standard Terms page publishes pricing, commercial-use "
                    "terms, and a payment mechanism or contact.",
                    "warning")
            return CheckResult("standard-terms-url", True,
                               f"Standard Terms URL is valid and publishes required content: {url}")
    except Exception:
        return CheckResult("standard-terms-url", True,
                           f"Standard Terms URL is reachable: {url}")


def check_spdx_headers(root: Path, exclude_patterns: list[str]) -> CheckResult:
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


# Single source of truth for version: read from _version.py
from _version import __version__  # noqa: E402


def summarize_for_user(root: Path) -> str:
    """F4: consumer-side view. Reads the repo's NOTICE and prints a commercial
    USER's obligations in plain language — the balancing-loop counterpart to the
    maintainer's opl_check. Mirrors the site 'Using' tab content."""
    notice_content = None
    for name in ["NOTICE", "NOTICE.md", "NOTICE.txt"]:
        p = root / name
        if p.exists():
            notice_content = p.read_text(encoding="utf-8", errors="ignore")
            break
    if not notice_content:
        return ("  No NOTICE file found. If this is an OPL-licensed work, the NOTICE\n"
                "  should state the maintainer, jurisdiction, and Standard Terms URL.\n"
                "  Without it, you cannot confirm your commercial-use obligations.")
    def get(key: str) -> str:
        m = re.search(rf"(?i){key}\s*[:=]\s*(.+)", notice_content)
        return m.group(1).strip() if m else ""

    maintainer = get("maintainer") or get("copyright") or "(unknown maintainer)"
    jurisdiction = get("governing jurisdiction") or get("jurisdiction") or "(unspecified)"
    terms_url = get("standard terms url") or get("standard terms") or ""
    opl_ai = get("opl-ai") or get("opl.ai") or ""
    abandonment = get("abandonment period") or "36"
    lines = [
        "  You are looking at software under the Open-Pact License v1.4.",
        "",
        "  FREE for you, no payment or account:",
        "    - Personal projects, education, and research.",
        "    - Reading, modifying, and sharing the (public) source.",
        "",
        "  COMMERCIAL use REQUIRES payment:",
        f"    - Maintainer: {maintainer}",
        f"    - Standard Terms (pricing + how to pay): {terms_url or '(not declared — ask the maintainer)'}",
        f"    - Governing law: {jurisdiction}",
        "",
        "  You are protected:",
        f"    - If the maintainer is silent for {abandonment} consecutive months, the Work",
        "      converts to Apache-2.0 for everyone automatically.",
    ]
    if re.search(r"(?i)opted in", opl_ai):
        lines.append("    - OPL-AI is OPTED IN: do not train AI models on this code.")
    else:
        lines.append("    - OPL-AI: not restricted (AI training permitted unless stated elsewhere).")
    lines.append("")
    lines.append("  Respect the commercial terms and you are in the clear. No license key needed.")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check OPL v1.4 compliance for a repository")
    parser.add_argument("--version", action="version", version=f"OPL Adoption Tools {__version__}")
    parser.add_argument("directory", nargs="?", default=".",
                        help="Repository root (default: .)")
    parser.add_argument("--json", action="store_true",
                        help="Output results as JSON")
    parser.add_argument("--strict", action="store_true",
                        help="Treat warnings as errors")
    parser.add_argument("--skip-remote", action="store_true",
                        help="Skip URL reachability check")
    parser.add_argument("--offline", action="store_true",
                        help="Check terms URL structurally (HTTPS + present) without fetching")
    parser.add_argument("--exclude", action="append", default=[],
                        help="Exclude pattern for SPDX check")
    parser.add_argument("--as-user", action="store_true",
                        help="F4: print a commercial USER's obligations for this repo (consumer view)")
    parser.add_argument("--check", action="store_true",
                        help="CI mode: exit non-zero on any failure, output JSON")
    args = parser.parse_args()

    root = Path(args.directory).resolve()
    if not root.is_dir():
        print(f"Error: {root} is not a directory", file=sys.stderr)
        sys.exit(1)

    # F4: consumer-side view — print the user's obligations and stop.
    if args.as_user:
        print(summarize_for_user(root))
        return

    # --check implies --json for machine-readable CI output
    if args.check:
        args.json = True

    results = [
        check_license(root),
        check_notice(root),
    ]
    if args.skip_remote:
        results.append(CheckResult("standard-terms-url", True,
                                   "Skipped (--skip-remote)", "info"))
    elif args.offline:
        results.append(check_standard_terms_url(root, offline=True))
    else:
        results.append(check_standard_terms_url(root))
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
