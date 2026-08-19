#!/usr/bin/env python3
# SPDX-License-Identifier: OPL-1.4
"""OPL Adopt — one-command adoption/migration to Open-Pact License v1.4.

Orchestrates the full adoption path so a pilot ends with a SELF-CONSISTENT repo:
  detect current license -> generate NOTICE -> inject SPDX headers ->
  swap LICENSE to OPL text -> update package-manifest license fields ->
  run opl_check and report a final verdict.

This closes the two biggest adoption cliffs found in dogfooding:
  F1: migrate/install left an Apache LICENSE + OPL NOTICE + OPL SPDX (contradiction).
  F2: four separate tools, each printing "Next steps" with no single path.

Reuses opl_init / opl_spdx_inject / opl_check rather than duplicating logic.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

# Allow importing sibling tools.
sys.path.insert(0, str(Path(__file__).parent))
from opl_migrate import detect_old_license, scan_manifests  # noqa: E402

# Single source of truth for version: read from _version.py
from _version import __version__  # noqa: E402

# Where the canonical OPL LICENSE text lives (repo root of open-pact-license).
# Resolve relative to this file: ../../open-pact-license/LICENSE.md
_OPL_LICENSE_SRC = (
    Path(__file__).resolve().parent.parent / "open-pact-license" / "LICENSE.md"
)
# Fallback search if the layout differs.
for _cand in [
    Path("/home/ikaaros/open-pact-license/LICENSE.md"),
    Path.home() / "open-pact-license" / "LICENSE.md",
]:
    if _cand.exists():
        _OPL_LICENSE_SRC = _cand
        break

MANIFEST_LICENSE_FIELDS = {
    "Cargo.toml": ("license", "TOML"),
    "pyproject.toml": ("license", "TOML"),
    "package.json": ("license", "JSON"),
    "setup.py": ("license", "Python"),
}


def _run_tool(name: str, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    tool = Path(__file__).parent / name
    return subprocess.run(
        [sys.executable, str(tool), *args],
        capture_output=True, text=True, cwd=str(cwd) if cwd else None,
    )


def swap_license(root: Path, dry_run: bool) -> str:
    """Replace the repo LICENSE file with the canonical OPL text (F1 fix)."""
    # Find the existing license file name to preserve the user's convention.
    existing = None
    for name in ["LICENSE", "LICENSE.md", "LICENSE.txt", "LICENCE", "LICENCE.md"]:
        p = root / name
        if p.exists():
            existing = p
            break
    target = existing or (root / "LICENSE")
    if not _OPL_LICENSE_SRC.exists():
        return f"  [SKIP] OPL LICENSE source not found at {_OPL_LICENSE_SRC}; cannot swap."
    if dry_run:
        return f"  [DRY RUN] Would replace {target.name} with OPL LICENSE text."
    shutil.copyfile(_OPL_LICENSE_SRC, target)
    return f"  Swapped {target.name} -> OPL-1.4 text."


def update_manifests(root: Path, dry_run: bool) -> list[str]:
    """Set the `license` field to OPL-1.4 in every package manifest (F1 fix)."""
    notes: list[str] = []
    for manifest_rel, (field, _kind) in MANIFEST_LICENSE_FIELDS.items():
        p = root / manifest_rel
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        import re
        # Match `license = "X"` (TOML) or `"license": "X"` (JSON) or license="X" (py).
        pat = re.compile(rf'({re.escape(field)}\s*[=:]\s*["\'])[^"\']*(["\'])', re.MULTILINE)
        new_text, n = pat.subn(rf'\1OPL-1.4\2', text)
        if n:
            if dry_run:
                notes.append(f"  [DRY RUN] Would set {manifest_rel} {field}=OPL-1.4")
            else:
                p.write_text(new_text, encoding="utf-8")
                notes.append(f"  Updated {manifest_rel} {field}=OPL-1.4")
    return notes


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Adopt OPL-1.4 in one command: NOTICE + SPDX + LICENSE swap + check.")
    parser.add_argument("--version", action="version", version=f"OPL Adoption Tools {__version__}")
    parser.add_argument("directory", nargs="?", default=".",
                        help="Repository root (default: .)")
    parser.add_argument("--from", dest="old_license",
                        help="Current license (auto-detected if omitted)")
    parser.add_argument("--maintainer", required=True,
                        help="Maintainer name and contact.")
    parser.add_argument("--jurisdiction", required=True,
                        help="Governing jurisdiction.")
    parser.add_argument("--terms-url", required=True,
                        help="Standard Terms URL (HTTPS).")
    parser.add_argument("--opl-ai", choices=["in", "out"], default="out",
                        help="OPL-AI opt-in (default: out).")
    parser.add_argument("--abandonment", default="36",
                        help="Abandonment period in months (default 36).")
    parser.add_argument("--dosp", default="",
                        help="DOSP period in months (optional; blank = none).")
    parser.add_argument("--commercial-terms", default="",
                        help="Commercial Terms filename (optional).")
    parser.add_argument("--trademark", default="",
                        help="Trademark notice (optional).")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would change without modifying files.")
    parser.add_argument("--skip-check", action="store_true",
                        help="Do not run opl_check at the end.")
    args = parser.parse_args()

    root = Path(args.directory).resolve()
    if not root.is_dir():
        print(f"Error: {root} is not a directory", file=sys.stderr)
        sys.exit(1)

    print("\n  OPL Adopt v1.4 — one-command adoption\n")

    # 0. Detect current license for the report.
    old = args.old_license or detect_old_license(root)
    print(f"  Target: {root}")
    if old:
        print(f"  Detected current license: {old} -> OPL-1.4")
    else:
        print("  Current license: (unknown) -> OPL-1.4")

    # 1. NOTICE
    print("\n  [1/5] Generating NOTICE...")
    r = _run_tool("opl_init.py", "--non-interactive",
                  "--maintainer", args.maintainer,
                  "--jurisdiction", args.jurisdiction,
                  "--terms-url", args.terms_url,
                  "--opl-ai", args.opl_ai,
                  "--abandonment", str(args.abandonment),
                  "--dosp", args.dosp,
                  "--commercial-terms", args.commercial_terms,
                  "--trademark", args.trademark,
                  "--output", str(root / "NOTICE"),
                  cwd=root)
    if r.returncode != 0:
        print(r.stderr)
        sys.exit(1)
    print("    NOTICE written.")

    # 2. SPDX headers
    print("\n  [2/5] Injecting SPDX headers...")
    # NOTE: the inject tool's flag is --license-version (it prepends "OPL-"
    # itself). Passing "--license OPL-1.4" lets argparse prefix-match to
    # --license-version and yields the invalid id "OPL-OPL-1.4". Pass a bare
    # version so the header reads "SPDX-License-Identifier: OPL-1.4".
    r = _run_tool("opl_spdx_inject.py", str(root), "--license-version", "1.4", cwd=root)
    if r.returncode != 0:
        print(r.stderr)
        sys.exit(1)
    # Summarize count from stdout lines starting with "Added header:"
    added = sum(1 for ln in r.stdout.splitlines() if ln.strip().startswith("Added header:"))
    print(f"    {added} files updated with SPDX header.")

    # 3. LICENSE swap (F1)
    print("\n  [3/5] Swapping LICENSE to OPL-1.4 text...")
    print(swap_license(root, args.dry_run))

    # 4. Manifest license fields (F1)
    print("\n  [4/5] Updating package manifests...")
    notes = update_manifests(root, args.dry_run)
    if notes:
        for n in notes:
            print(n)
    else:
        print("    No package manifests with a license field found.")

    # 5. Final check
    if not args.skip_check:
        print("\n  [5/5] Running opl_check for a final verdict...")
        # --skip-remote: the Standard Terms URL is advisory at adopt time (you
        # publish it after adopting), so don't fail/warn on an unreachable page.
        r = _run_tool("opl_check.py", str(root), "--skip-remote", cwd=root)
        print(r.stdout)
        if r.returncode != 0:
            print(r.stderr)
        # opl_check returns 0 with --skip-remote; any ERROR-level line is a real problem.
        if "0 errors" in r.stdout:
            _print_next_steps(root, args)
        else:
            print("  VERDICT: adoption ran but opl_check reported errors — review above.")


def _print_next_steps(root: Path, args) -> None:
    """Plain-language, numbered guidance for the maintainer. Answers the
    questions a first-time adopter actually has: what did I get, what do I do
    now, and is there a key/token to store (there isn't)."""
    print("\n" + "=" * 64)
    print("  OPL ADOPTION COMPLETE — what you now have & what to do")
    print("=" * 64)
    print("\n  Your repo now contains (no key, token, or account needed):")
    print("    1. LICENSE        — canonical Open-Pact License v1.4 text")
    print("    2. NOTICE         — names you as maintainer, your jurisdiction,")
    print("                       your Standard Terms URL, and OPL-AI choice")
    print("    3. SPDX headers   — every source file now carries")
    print("                       'SPDX-License-Identifier: OPL-1.4'")
    print("    4. Manifests      — package files set license = OPL-1.4")
    print("\n  You are the licensor by publishing these files. There is NO")
    print("  license key to store, no account, nothing to lose or forget.")
    print("\n  Your 3 next steps as maintainer:")
    print("    1. PUBLISH your Standard Terms page at:")
    print(f"         {args.terms_url or '(you did not set --terms-url — pick one)'}")
    print("       This is the one external dependency: commercial users are")
    print("       directed to YOUR pricing page. (A static HTML page is enough.)")
    print("    2. COMMIT the four artifacts above.")
    print("    3. (Optional) Tag a release noting 'now under OPL-1.4'.")
    print("\n  To validate later, or if you suspect copying: run")
    print("     python3 tools/opl_check.py .            # tamper/local check")
    print("     python3 canary_embedder.py verify ...   # theft check (if canary used)")
    print("=" * 64)


if __name__ == "__main__":
    main()
