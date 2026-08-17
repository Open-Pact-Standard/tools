#!/usr/bin/env python3
# SPDX-License-Identifier: OPL-1.4
"""OPL Studio adapter layer — Paperclip-style integrations catalogue.

Each capability the studio exposes is an *Adapter*: a self-describing plugin with
a parameter schema and a run() that operates on a repo (or locally) and returns
structured output. The studio discovers adapters from REGISTRY and renders them
as a catalogue; new capabilities are added by registering a new Adapter — no
server changes. This is the "bring-your-own / integrations catalogue" pattern
from paperclipai/paperclip, kept local-only and stdlib-only.

Adapters are the future API surface: if OPL Studio later becomes a hosted service,
these same adapters are what the service calls.
"""
from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

HERE = Path(__file__).resolve().parent
PY = sys.executable

# Base OPL license text (for live LICENSE preview) — resolved lazily.
BASE_LICENSE = (HERE.parent / ".." / "open-pact-license" / "LICENSE.md").resolve()


@dataclass
class Param:
    name: str
    label: str
    kind: str = "text"          # text | select | number | bool | repo
    default: str = ""
    options: list[str] = field(default_factory=list)
    help: str = ""


@dataclass
class AdapterResult:
    ok: bool
    outputs: dict[str, str] = field(default_factory=dict)   # name -> text content
    messages: list[str] = field(default_factory=list)
    consequence: str = ""


@dataclass
class Adapter:
    id: str
    title: str
    description: str
    params: list[Param]
    run: Callable[[Path | None, dict], AdapterResult]


REGISTRY: dict[str, Adapter] = {}


def register(a: Adapter) -> Adapter:
    REGISTRY[a.id] = a
    return a


def run_tool(script: str, *args: str, cwd: str | None = None):
    cmd = [PY, str(HERE / script), *args]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=60, cwd=cwd)
        return p.returncode, p.stdout, p.stderr
    except Exception as e:  # noqa: BLE001
        return -1, "", str(e)


# ---------------------------------------------------------------------------
# Adapters
# ---------------------------------------------------------------------------

register(Adapter(
    id="adopt",
    title="Adopt OPL",
    description="Generate NOTICE + LICENSE for a repo from your choices. Preview first; "
                "write only when you confirm.",
    params=[
        Param("repo", "Repository path", "repo", ""),
        Param("maintainer", "Maintainer (name <email>)", "text", "",
              help="Who maintains the work."),
        Param("jurisdiction", "Governing Jurisdiction", "text", "United States",
              help="Any jurisdiction — you write it. OPL §9.4 covers all."),
        Param("terms_url", "Standard Terms URL", "text", "",
              help="HTTPS page publishing your commercial-use pricing."),
        Param("commercial_model", "Commercial model", "select", "paid_standard_terms",
              ["paid_standard_terms", "free_for_all", "personal_only"],
              help="paid = payment required; free = open; personal = non-commercial only."),
        Param("opl_ai", "OPL-AI addendum", "select", "out", ["out", "in"],
              help="opt in to restrict AI training on your code."),
        Param("abandonment", "Abandonment (months)", "number", "36",
              help="Silence this long → Work auto-converts to Apache-2.0."),
        Param("dosp", "DOSP period (months, blank=none)", "number", "",
              help="Scheduled auto-conversion to Apache-2.0 per version. Blank = never."),
        Param("derivative", "Derivative notice", "select", "light_copyleft",
              ["light_copyleft", "off"]),
        Param("trademark", "Trademark notice", "text", ""),
        Param("write", "Write into repo", "bool", "false",
              help="If true, writes NOTICE + injects SPDX in place. Else preview only."),
    ],
    run=lambda root, p: _adopt(root, p),
))


def _adopt(root: Path | None, p: dict) -> AdapterResult:
    write = str(p.get("write", "false")).lower() in ("1", "true", "on", "yes")
    jur = p.get("jurisdiction") or "United States"
    args = [
        "--non-interactive",
        "--maintainer", p.get("maintainer", ""),
        "--jurisdiction", jur,
        "--terms-url", p.get("terms_url", ""),
        "--opl-ai", p.get("opl_ai", "out"),
        "--abandonment", p.get("abandonment", "36"),
        "--dosp", p.get("dosp", ""),
        "--commercial-terms", "",
    ]
    out_dir = str(root) if (write and root) else None
    if write and root:
        rc, so, se = run_tool("opl_init.py", *args, "--output", str(root / "NOTICE"))
        rc2, so2, se2 = run_tool("opl_spdx_inject.py", str(root))
        return AdapterResult(rc == 0, {}, [so.strip(), so2.strip()],
                            "Wrote NOTICE + injected SPDX headers into your repo.")
    # Preview: emit NOTICE to a temp location and assemble a Custom OPL LICENSE.
    import tempfile
    tmp = Path(tempfile.mkdtemp())
    rc, so, se = run_tool("opl_init.py", *args, "--output", str(tmp / "NOTICE"))
    notice = (tmp / "NOTICE").read_text() if (tmp / "NOTICE").exists() else se
    lic = _assemble_license(p, jur)
    cons = _consequence_text(p)
    return AdapterResult(rc == 0, {"NOTICE": notice, "LICENSE (Custom OPL)": lic},
                         [], cons)


def _assemble_license(p: dict, jur: str) -> str:
    """Assemble a Custom OPL LICENSE variant for live preview via custom_opl.py."""
    import tempfile
    out = Path(tempfile.mkdtemp()) / "out"
    args = [
        "--commercial-model", p.get("commercial_model", "paid_standard_terms"),
        "--dosp", "months" if p.get("dosp") else "off",
        "--abandonment", "convert_apache",
        "--opl-ai", p.get("opl_ai", "out"),
        "--derivative", p.get("derivative", "light_copyleft"),
        "--trademark", "asserted" if p.get("trademark") else "none",
        "--jurisdiction", "free_text",
        "--jurisdiction-value", jur,
        "--out", str(out),
    ]
    if p.get("dosp"):
        args += ["--dosp-months", str(p["dosp"])]
    rc, so, se = run_tool("custom-opl/custom_opl.py", *args)
    lic_path = out / "LICENSE"
    if lic_path.exists():
        return lic_path.read_text()
    return so or se or "(license assembly unavailable)"


def _consequence_text(p: dict) -> str:
    bits = []
    if p.get("dosp"):
        bits.append(f"DOSP={p['dosp']}mo: each version's source auto-converts to Apache-2.0 "
                     f"{p['dosp']} months after release — even if you stay active.")
    else:
        bits.append("DOSP=off: no scheduled conversion; you keep full source-available control.")
    bits.append(f"Abandonment={p.get('abandonment','36')}mo: silence that long → Apache-2.0 for everyone.")
    if p.get("commercial_model") == "personal_only":
        bits.append("Commercial model=personal_only: all commercial use prohibited.")
    elif p.get("commercial_model") == "free_for_all":
        bits.append("Commercial model=free_for_all: no payment required for any use.")
    else:
        bits.append("Commercial model=paid: users must pay per your published Terms URL "
                    "(dead/empty URL → unenforceable).")
    return "  • " + "\n  • ".join(bits)


register(Adapter(
    id="scan",
    title="Scan / Compliance check",
    description="Read-only: run opl_check against a repo and report OPL compliance.",
    params=[
        Param("repo", "Repository path", "repo", ""),
        Param("skip_remote", "Skip remote URL check (offline)", "bool", "false"),
    ],
    run=lambda root, p: _scan(root, p),
))


def _scan(root: Path | None, p: dict) -> AdapterResult:
    if not root or not root.is_dir():
        return AdapterResult(False, {}, ["Repository not found."])
    skip = ["--skip-remote"] if str(p.get("skip_remote", "false")).lower() in ("1", "true", "on") else []
    rc, so, se = run_tool("opl_check.py", *skip, str(root))
    return AdapterResult(rc == 0, {"opl_check": so}, [se] if se else [])


register(Adapter(
    id="kit",
    title="Build Adoption Kit",
    description="Assemble the Adoption Kit (docs + worked example) and a downloadable zip.",
    params=[],
    run=lambda root, p: _kit(root, p),
))


def _kit(root: Path | None, p: dict) -> AdapterResult:
    import shutil
    rc, so, se = run_tool("adoption-kit/make_kit.py")
    zip_path = HERE / "adoption-kit" / "dist" / "opl-adoption-kit.zip"
    try:
        if not zip_path.exists():
            shutil.make_archive(str(zip_path.with_suffix("")), "zip", zip_path.parent)
    except Exception:  # noqa: BLE001
        pass
    files = sorted(str(f.name) for f in (HERE / "adoption-kit" / "dist").rglob("*.md")) if (HERE / "adoption-kit" / "dist").exists() else []
    out = "\n".join(files) or "(run make_kit.py)"
    return AdapterResult(rc == 0, {"kit files": out}, [so.strip()])


register(Adapter(
    id="research",
    title="Jurisdiction research",
    description="Pull the verified statute anchors for a jurisdiction from RESEARCH_BASE.md. "
                "Shows the catalogue is extensible to new capability adapters.",
    params=[
        Param("jurisdiction", "Jurisdiction (e.g. Germany, US, Brazil, Japan)", "text", "Germany"),
    ],
    run=lambda root, p: _research(root, p),
))


def _research(root: Path | None, p: dict) -> AdapterResult:
    rb = HERE.parent.parent / "open-pact-license" / "RESEARCH_BASE.md"
    if not rb.exists():
        return AdapterResult(False, {}, ["RESEARCH_BASE.md not found."])
    text = rb.read_text(encoding="utf-8")
    want = (p.get("jurisdiction") or "Germany").strip().lower()
    # Extract the paragraph mentioning the jurisdiction.
    import re
    hit = ""
    for line in text.splitlines():
        if want in line.lower():
            hit = line.strip()
            break
    out = hit or f"No specific anchor indexed for '{want}'. RESEARCH_BASE.md covers 15+EU jurisdictions."
    return AdapterResult(True, {"research": out}, [])


# ---------------------------------------------------------------------------
# Full-pipeline adapter: "drive the Adoption Kit" end-to-end.
# ---------------------------------------------------------------------------
register(Adapter(
    id="adopt-full",
    title="Adopt OPL (full kit drive)",
    description="One adapter that drives the whole adoption kit end-to-end: build the "
                "Adoption Kit, assemble NOTICE + Custom OPL LICENSE, write + inject SPDX "
                "into the repo, then run the compliance validator. Requires a repo path.",
    params=[
        Param("repo", "Repository path", "repo", "",
              help="Required. The repo NOTICE/headers will be written into."),
        Param("maintainer", "Maintainer (name <email>)", "text", ""),
        Param("jurisdiction", "Governing Jurisdiction", "text", "United States",
              help="Any jurisdiction — you write it. OPL §9.4 covers all."),
        Param("terms_url", "Standard Terms URL", "text", "",
              help="HTTPS page publishing your commercial-use pricing."),
        Param("commercial_model", "Commercial model", "select", "paid_standard_terms",
              ["paid_standard_terms", "free_for_all", "personal_only"]),
        Param("opl_ai", "OPL-AI addendum", "select", "out", ["out", "in"]),
        Param("abandonment", "Abandonment (months)", "number", "36"),
        Param("dosp", "DOSP period (months, blank=none)", "number", ""),
        Param("derivative", "Derivative notice", "select", "light_copyleft",
              ["light_copyleft", "off"]),
        Param("trademark", "Trademark notice", "text", ""),
        Param("confirm", "Write into repo (set true to commit)", "bool", "false",
              help="The full drive previews first. Set true to actually write + validate."),
    ],
    run=lambda root, p: _adopt_full(root, p),
))


def _adopt_full(root: Path | None, p: dict) -> AdapterResult:
    repo = p.get("repo", "").strip()
    if not repo or not Path(repo).is_dir():
        return AdapterResult(False, {}, [],
                            "adopt-full requires a valid 'repo' path.")
    confirm = str(p.get("confirm", "false")).lower() in ("1", "true", "on", "yes")
    # Step 1: build the Adoption Kit (dist + zip) — surfaces it for download.
    kit_rc, kit_out, kit_err = run_tool("adoption-kit/make_kit.py", cwd=str(HERE))
    # Step 2: assemble NOTICE + Custom LICENSE (preview).
    license_p = {k: v for k, v in p.items() if k != "repo" and k != "confirm"}
    adopt_res = _adopt(root, {**license_p, "write": "false"})
    # Step 3: if confirmed, write in place.
    msg = []
    if kit_out.strip():
        msg.append(f"kit: {kit_out.strip()[:120]}")
    if not confirm:
        cons = adopt_res.consequence or "Preview only — set confirm=true to write to your repo."
        return AdapterResult(True, adopt_res.outputs, msg, cons)
    # Confirmed: write NOTICE + inject SPDX, then validate.
    write_res = _adopt(root, {**license_p, "write": "true"})
    msg.extend(write_res.messages)
    scan_rc, scan_out, _ = run_tool("opl_check.py", "--skip-remote", str(root))
    outputs = dict(adopt_res.outputs)
    outputs["opl_check"] = scan_out
    cons = "Repo written + validated. Remaining manual step: add OPL LICENSE.md to repo root." \
        if scan_rc == 0 else "Written, but opl_check found issues — see opl_check output."
    return AdapterResult(write_res.ok, outputs, msg, cons)


def catalogue() -> list[dict]:
    return [{
        "id": a.id, "title": a.title, "description": a.description,
        "params": [vars(p) for p in a.params],
    } for a in REGISTRY.values()]


def run_adapter(id: str, root: Path | None, params: dict) -> AdapterResult:
    a = REGISTRY.get(id)
    if not a:
        return AdapterResult(False, {}, [f"Unknown adapter: {id}"])
    return a.run(root, params)
