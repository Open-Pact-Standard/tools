#!/usr/bin/env python3
# SPDX-License-Identifier: OPL-1.4
"""Custom OPL configurator — assembles a bespoke OPL variant from VETTED fragments only.

Phase A (local-first). No free-form clause editing: every output is a known-good
combination from custom-opl/fragments.json. Emits LICENSE + NOTICE +
COMMERCIAL_TERMS.md + a provenance block.

Usage:
  python3 custom_opl.py --params params.json --out ./my-custom-opl
  python3 custom_opl.py --interactive --out ./my-custom-opl
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
FRAGMENTS = json.loads((HERE / "fragments.json").read_text(encoding="utf-8"))
BASE_LICENSE = (HERE.parent.parent / ".." / "open-pact-license" / "LICENSE.md").resolve()
# Fallback: look for the license text alongside if not found above.
if not BASE_LICENSE.exists():
    for cand in [
        Path.home() / "open-pact-license" / "LICENSE.md",
        HERE / "OPL-1.4-LICENSE.md",
    ]:
        if cand.exists():
            BASE_LICENSE = cand
            break

DEFAULTS = {
    "commercial_model": "paid_standard_terms",
    "dosp": "off",
    "abandonment": "convert_apache",
    "opl_ai": "out",
    "rate_stability": "immutable_per_version",
    "derivative": "light_copyleft",
    "trademark": "none",
    "jurisdiction": "free_text",
}


def load_params_from_args(cli: argparse.Namespace) -> dict:
    if cli.params:
        return json.loads(Path(cli.params).read_text(encoding="utf-8"))
    p = dict(DEFAULTS)
    mapping = {
        "commercial_model": cli.commercial_model,
        "dosp": cli.dosp,
        "abandonment": cli.abandonment,
        "opl_ai": cli.opl_ai,
        "rate_stability": cli.rate_stability,
        "derivative": cli.derivative,
        "trademark": cli.trademark,
        "jurisdiction": cli.jurisdiction,
    }
    for k, v in mapping.items():
        if v:
            p[k] = v
    # numeric / text params
    p["dosp_months_value"] = cli.dosp_months or 36
    p["abandonment_months_value"] = cli.abandonment_months or 36
    p["jurisdiction_value"] = cli.jurisdiction_value or "United States"
    return p


def resolve_fragment(slot_key: str, option_key: str) -> tuple[str, dict]:
    slot = FRAGMENTS["fragments"][slot_key]
    if option_key not in slot["options"]:
        raise ValueError(f"Unknown option '{option_key}' for slot '{slot_key}'. "
                         f"Valid: {list(slot['options'])}")
    opt = slot["options"][option_key]
    frag_path = HERE / "fragments" / opt["file"]
    if not frag_path.exists():
        raise FileNotFoundError(f"Missing fragment file: {frag_path}")
    text = frag_path.read_text(encoding="utf-8").strip()
    return text, opt


def check_hard_blocks(params: dict, resolved: dict) -> list[str]:
    warnings = []
    is_fair_source = True
    for _slot_key, opt in resolved.items():
        if opt.get("fair_source") is False:
            is_fair_source = False
    label = params.get("fair_source_label", "auto")
    if label == "fair_source" and not is_fair_source:
        raise SystemExit(
            "HARD BLOCK: a no-conversion variant (dosp:forever_frozen or "
            "abandonment:freeze_forever) CANNOT be labeled Fair Source. "
            "Use label 'source_available'.")
    if params.get("commercial_model") == "personal_only" and params.get("dosp") == "months":
        warnings.append("WARN: personal-only work with a DOSP schedule is unusual but allowed.")
    params["_is_fair_source"] = is_fair_source
    return warnings


def build_schedule(params: dict) -> str:
    lines = ["## Customization Schedule (Custom OPL)", "",
             "This Custom OPL variant is built from the base OPL-1.4 text above, with the "
             "following slot customizations. Each overrides the corresponding base clause. "
             "The base text remains in force except where explicitly overridden here.",
             ""]
    slot_titles = {
        "commercial_model": "§3.3 Commercial Use",
        "dosp": "§5.1 Version-Based DOSP",
        "abandonment": "§5 Abandonment",
        "opl_ai": "§3.5 OPL-AI Addendum",
        "rate_stability": "§13 / Commercial Terms",
        "derivative": "§3.2 Derivative",
        "trademark": "§10 Trademark",
        "jurisdiction": "§12 Governing Law",
    }
    resolved = {}
    for slot_key, title in slot_titles.items():
        opt_key = params[slot_key]
        text, opt = resolve_fragment(slot_key, opt_key)
        # substitute numeric/text params
        text = text.replace("N months", f"{params.get('dosp_months_value', 36)} months")
        text = text.replace("the **custom value**", f"**{params.get('abandonment_months_value', 36)} months**")
        text = text.replace(
            "the jurisdiction declared in `NOTICE`",
            f"**{params.get('jurisdiction_value', 'United States')}**")
        # Inject the declared Standard Terms URL into the §3.3 schedule line so
        # the Custom LICENSE states the actual URL, not just a reference to it.
        if slot_key == "commercial_model" and params.get("commercial_model") == "paid_standard_terms":
            url = params.get("terms_url", "")
            if url:
                text = text.replace(
                    "per the Standard Terms URL published in `NOTICE`",
                    f"per the Maintainer's published Standard Terms: {url}",
                )
        resolved[slot_key] = opt
        lines.append(f"### {title} — option `{opt['id']}`")
        lines.append("")
        lines.append(text)
        lines.append("")
    params["_resolved"] = resolved
    return "\n".join(lines)


def build_provenance(params: dict) -> str:
    ts = datetime.now(timezone.utc).isoformat()
    blocks = ["## Provenance Block", "",
              f"- Generated (UTC): {ts}",
              f"- Base license: {FRAGMENTS['base_license']}",
              f"- Configurator schema: {FRAGMENTS['schema']}",
              "- Selected fragments:"]
    for slot_key, opt in params["_resolved"].items():
        blocks.append(f"  - {slot_key}: {opt['id']} ({opt['file']})")
    blocks.append(f"- Fair Source eligible: {params.get('_is_fair_source', False)}")
    blocks.append("")
    blocks.append("This document is generated from vetted fragments. It is not legal advice.")
    return "\n".join(blocks)


def generate_notice(params: dict) -> str:
    lines = ["# NOTICE file for Custom OPL (based on OPL-1.4)", "# Generated by custom_opl.py", "",
             "OPL Version: 1.4 (Custom OPL variant)",
             f"Maintainer: {params.get('maintainer', 'Unspecified')}",
             f"Governing Jurisdiction: "
             f"{params.get('jurisdiction_value', 'United States (state optional; S9.4 covers consumers)')}",
             f"Standard Terms URL: {params.get('terms_url', '')}"]
    if params.get("opl_ai") == "in":
        lines.append("OPL-AI: opted in.")
    else:
        lines.append("OPL-AI: opted out.")
    if params.get("dosp") == "months":
        lines.append(f"DOSP Period: {params.get('dosp_months_value', 36)}")
    if params.get("abandonment") in ("convert_apache", "custom"):
        lines.append(f"Abandonment Period: {params.get('abandonment_months_value', 36)}")
    if params.get("commercial_terms_file"):
        lines.append(f"Commercial Terms file: {params['commercial_terms_file']}")
    lines.append("")
    return "\n".join(lines) + "\n"


def build_validation(params: dict, resolved: dict) -> str:
    """Phase B validation gate: instructs the operator/agent to run the ported
    legal skills over the generated LICENSE + NOTICE + COMMERCIAL_TERMS, and
    records the outcome. The skills are LLM workflows (not scripts), so the gate
    is a process + checklist, not a subprocess call."""
    fs_label = "Fair Source" if params.get("_is_fair_source", False) else "Source-Available"
    blocks = [
        "## Validation Gate (Phase B)",
        "",
        f"This Custom OPL variant is **{fs_label}**. Before publishing, run the two",
        "ported legal skills below over the generated `LICENSE`, `NOTICE`, and",
        "`COMMERCIAL_TERMS.md`. They are LLM workflows — paste the prompt, attach",
        "the generated files, and record the result in `validation_manifest.json`.",
        "",
        "### 1. Interpretive-ambiguity stress-test",
        "Skill: `~/.hermes/skills/legal/ambiguity-stress-test-seth-chandler`",
        "",
        "Prompt:",
        "> Stress-test the attached Custom OPL LICENSE (contract profile) for",
        "> interpretive ambiguity. Treat the Customization Schedule and Provenance",
        f"Block as part of the instrument. Focus on: the `{params.get('dosp','off')}`",
        f"DOSP option, the `{params.get('abandonment','convert_apache')}` abandonment",
        f"option, and the `{params.get('commercial_model','paid_standard_terms')}`",
        "commercial-model option. For each seam, produce a dispute scenario with both",
        "sides' arguments and a redraft. Report coverage, not just marquee findings.",
        "",
        "### 2. Contract risk review (Commercial Terms)",
        "Skill: `~/.hermes/skills/legal/contract-risk-analyzer-sneha-ganapavarapu`",
        "",
        "Prompt:",
        "> Review the attached `COMMERCIAL_TERMS.md` for the five critical clauses",
        "> (Limitation of Liability, Indemnities, IP Ownership, Data Protection,",
        "> Termination). Flag red flags and rate severity. This is a Custom OPL",
        "> commercial-terms file; the Maintainer sets pricing, so focus on whether",
        "> the terms are internally coherent and enforceable as written.",
        "",
        "### Sign-off",
        "- [ ] Ambiguity stress-test run; seams (if any) documented in `validation_manifest.json`",
        "- [ ] Contract risk review run; commercial terms coherent",
        "- [ ] Maintainer reviewed and accepts the variant",
        "",
        "This gate is process, not a guarantee. It is not legal advice.",
    ]
    return "\n".join(blocks)


def main() -> None:
    ap = argparse.ArgumentParser(description="Assemble a Custom OPL variant from vetted fragments.")
    ap.add_argument("--params", help="JSON file with the parameter set.")
    ap.add_argument("--out", default="./custom-opl-out", help="Output directory.")
    ap.add_argument("--maintainer", default="Unspecified")
    ap.add_argument("--terms-url", default="")
    ap.add_argument("--commercial-terms-file", default="COMMERCIAL_TERMS.md")
    ap.add_argument("--fair-source-label", choices=["auto", "fair_source", "source_available"], default="auto")
    ap.add_argument("--dosp-months", type=int, default=36)
    ap.add_argument("--abandonment-months", type=int, default=36)
    ap.add_argument("--jurisdiction-value", default="United States",
                    help="Any governing jurisdiction you declare in NOTICE (free text). "
                         "No curated list. S9.4 subordinates to local mandatory law.")
    for slot in DEFAULTS:
        ap.add_argument(f"--{slot.replace('_', '-')}", choices=list(FRAGMENTS["fragments"][slot]["options"].keys()))
    cli = ap.parse_args()

    params = load_params_from_args(cli)
    params["maintainer"] = cli.maintainer
    params["terms_url"] = cli.terms_url
    params["commercial_terms_file"] = cli.commercial_terms_file
    params["fair_source_label"] = cli.fair_source_label
    params["dosp_months_value"] = cli.dosp_months
    params["abandonment_months_value"] = cli.abandonment_months
    params["jurisdiction_value"] = cli.jurisdiction_value

    if not BASE_LICENSE.exists():
        print(f"ERROR: base license not found at {BASE_LICENSE}", file=sys.stderr)
        sys.exit(1)

    base_text = BASE_LICENSE.read_text(encoding="utf-8")
    resolved = {}
    for slot_key in DEFAULTS:
        _, opt = resolve_fragment(slot_key, params[slot_key])
        resolved[slot_key] = opt
    params["_resolved"] = resolved

    warnings = check_hard_blocks(params, resolved)
    for w in warnings:
        print(w)

    schedule = build_schedule(params)
    provenance = build_provenance(params)
    out = base_text + "\n\n---\n\n" + schedule + "\n\n---\n\n" + provenance + "\n"

    out_dir = Path(cli.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "LICENSE").write_text(out, encoding="utf-8")
    (out_dir / "NOTICE").write_text(generate_notice(params), encoding="utf-8")
    (out_dir / "VALIDATION.md").write_text(build_validation(params, resolved), encoding="utf-8")
    print(f"Custom OPL variant written to {out_dir}/")
    print("  LICENSE  (base OPL-1.4 + Customization Schedule + Provenance)")
    print("  NOTICE")
    print("  VALIDATION.md  (Phase B gate: run ported legal skills, record outcome)")
    print(f"  Fair Source eligible: {params.get('_is_fair_source', False)}")
    print(f"  Fragments used: {len(resolved)}")


if __name__ == "__main__":
    main()
