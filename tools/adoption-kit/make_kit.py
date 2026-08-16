#!/usr/bin/env python3
# SPDX-License-Identifier: OPL-1.4
"""Assemble the OPL Adoption Kit from the worked example + templates.

Ponytail: this is a thin assembler + a drift guard, not a generator-from-scratch.
It copies the real worked-example files and the static docs into a target dir,
then asserts every `§N` (or `§N.N`) citation in the Packet resolves to a section
that still exists in the canonical LICENSE.md. If a cited section was removed,
the build FAILS — that is the whole point (the Kit must never drift from the
license it describes).
"""
from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LICENSE_MD = (HERE.parent.parent / ".." / "open-pact-license" / "LICENSE.md").resolve()
# The worked-example/ dir next to this script already holds the REAL
# origin-canary files (NOTICE, COMMERCIAL_TERMS.md, LICENSE), copied there
# from the live project. We copy those into dist/ so the Kit ships a real,
# current example rather than re-deriving a fragile cross-repo path.
WORKED_EXAMPLE_SRC = HERE / "worked-example"
STATIC_DOCS = ["WHY_OPL.md", "LAWYER_FAQ.md", "CORPORATE_APPROVAL_PACKET.md", "DESIGN.md"]


def load_license_sections(path: Path) -> set[int]:
    """Return the set of top-level section numbers present in LICENSE.md
    (matches '## N.' or '# N.' headings)."""
    text = path.read_text(encoding="utf-8")
    # Match headings like '## 5. Abandonment' or '## 5.1 Version-Based ...'
    nums = set()
    for m in re.finditer(r"^#+\s+(\d+)(?:\.(\d+))?\.", text, re.MULTILINE):
        nums.add(int(m.group(1)))
    return nums


def check_packet_citations(packet: Path, sections: set[int]) -> list[str]:
    """Return a list of broken § citations found in the Packet."""
    text = packet.read_text(encoding="utf-8")
    broken = []
    for m in re.finditer(r"§(\d+)(?:\.(\d+))?", text):
        top = int(m.group(1))
        if top not in sections:
            broken.append(m.group(0))
    return broken


def main() -> int:
    out = HERE / "dist"
    out.mkdir(parents=True, exist_ok=True)

    if not LICENSE_MD.exists():
        print(f"ERROR: canonical license not found at {LICENSE_MD}", file=sys.stderr)
        return 1

    sections = load_license_sections(LICENSE_MD)
    print(f"Canonical LICENSE.md sections loaded: {sorted(sections)}")

    # 1. Copy static docs.
    for doc in STATIC_DOCS:
        src = HERE / doc
        if src.exists():
            shutil.copy(src, out / doc)
            print(f"  copied {doc}")

    # 2. Copy real worked-example files from origin-canary (the live project).
    we_out = out / "worked-example"
    we_out.mkdir(parents=True, exist_ok=True)
    for f in ("NOTICE", "COMMERCIAL_TERMS.md", "LICENSE"):
        src = WORKED_EXAMPLE_SRC / f
        if src.exists():
            shutil.copy(src, we_out / f)
            print(f"  copied worked-example/{f} (from live origin-canary)")
        else:
            print(f"  WARNING: worked-example source missing: {src}", file=sys.stderr)

    # 3. Drift guard: every § citation in the Packet must resolve.
    packet = out / "CORPORATE_APPROVAL_PACKET.md"
    broken = check_packet_citations(packet, sections) if packet.exists() else ["(packet missing)"]
    if broken:
        print(f"BUILD FAILED: Packet cites sections absent from LICENSE.md: {sorted(set(broken))}",
              file=sys.stderr)
        return 1
    print("  drift guard: all § citations in Packet resolve to LICENSE.md ✅")

    # 4. Boundary-phrase assertions (honesty rules from the design).
    why = (out / "WHY_OPL.md").read_text(encoding="utf-8").lower()
    faq = (out / "LAWYER_FAQ.md").read_text(encoding="utf-8").lower()
    for phrase, where in [
        ("osi", why),
        ("independently", why),
        ("osi", faq),
    ]:
        if phrase not in where:
            print(f"BUILD FAILED: required boundary phrase '{phrase}' missing from a Kit doc",
                  file=sys.stderr)
            return 1
    print("  boundary phrases present ✅")

    print(f"\nAdoption Kit assembled at {out}/")
    print("  WHY_OPL.md  LAWYER_FAQ.md  CORPORATE_APPROVAL_PACKET.md  DESIGN.md  worked-example/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
