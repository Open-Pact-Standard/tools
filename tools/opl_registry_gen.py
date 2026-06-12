#!/usr/bin/env python3
# SPDX-License-Identifier: OPL-1.3.1
"""OPL Registry Generator

Generates a REGISTRY.json file for Tier 1 adopters of the Open-Pact License v1.3.1.
Usage: python3 opl_registry_gen.py [--non-interactive] [--output REGISTRY.json]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone


BANNER = """
  OPL Registry Generator v1.3.1
  Generate a REGISTRY.json for Tier 1 adoption.
"""


def ask(prompt: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    while True:
        val = input(f"  {prompt}{suffix}: ").strip()
        if val:
            return val
        if default:
            return default
        print("    This field is required.")


def ask_choice(prompt: str, options: list[str], default: str | None = None) -> str:
    print(f"  {prompt}:")
    for i, opt in enumerate(options, 1):
        marker = " (default)" if opt == default else ""
        print(f"    {i}. {opt}{marker}")
    while True:
        val = input("  Choice [number]: ").strip()
        if not val and default:
            return default
        try:
            idx = int(val) - 1
            if 0 <= idx < len(options):
                return options[idx]
        except ValueError:
            pass
        print("    Invalid choice.")


def ask_yes_no(prompt: str, default: bool = True) -> bool:
    suffix = " [Y/n]" if default else " [y/N]"
    while True:
        val = input(f"  {prompt}{suffix}: ").strip().lower()
        if not val:
            return default
        if val in ("y", "yes"):
            return True
        if val in ("n", "no"):
            return False
        print("    Please enter y or n.")


# Single source of truth for version: read from __init__.py
import re as _version_re
from pathlib import Path as _version_Path
try:
    _version_file = (_version_Path(__file__).resolve().parent / "__init__.py").read_text()
except FileNotFoundError:
    raise SystemExit("ERROR: tools/__init__.py not found — cannot determine version")
_version_match = _version_re.search(r"__version__\s*=\s*\"([^\"]+)\"", _version_file)
if _version_match:
    __version__ = _version_match.group(1)
else:
    raise SystemExit("ERROR: Could not read __version__ from tools/__init__.py")


def main():
    parser = argparse.ArgumentParser(description="Generate REGISTRY.json for OPL Tier 1 adopters")
    parser.add_argument("--version", action="version", version=f"OPL Adoption Tools {__version__}")
    parser.add_argument("--output", "-o", default="REGISTRY.json",
                        help="Output file (default: REGISTRY.json)")
    parser.add_argument("--non-interactive", action="store_true",
                        help="Use defaults instead of prompting")
    parser.add_argument("--maintainer", help="Maintainer name")
    parser.add_argument("--jurisdiction", help="Governing jurisdiction")
    parser.add_argument("--terms-url", help="Standard Terms URL")
    args = parser.parse_args()

    print(BANNER)

    if args.non_interactive:
        maintainer = args.maintainer or "Your Name or Organization"
        jurisdiction = args.jurisdiction or "California, United States"
        terms_url = args.terms_url or "https://example.com/standard-terms"
    else:
        maintainer = ask("Maintainer name (individual or organization)")
        jurisdiction = ask_choice("Governing jurisdiction", [
            "California, United States", "Delaware, United States",
            "New York, United States", "England and Wales",
            "Ontario, Canada", "Berlin, Germany",
            "New South Wales, Australia", "Singapore", "Dublin, Ireland",
        ], default="California, United States")
        terms_url = ask("Standard Terms URL (must be HTTPS)")
        if not terms_url.startswith("https://"):
            print("  Warning: Standard Terms URL should use HTTPS.")

    # Fee tiers
    print("\n  -- Fee Tiers --")
    if args.non_interactive:
        tiers = [
            {"name": "Small", "description": "Organizations with fewer than 10 employees",
             "fee_usd": 0, "conditions": "Free for organizations with fewer than 10 employees"},
            {"name": "Medium", "description": "Organizations with 10-100 employees",
             "fee_usd": 500, "conditions": "Annual fee per organization"},
            {"name": "Large", "description": "Organizations with more than 100 employees",
             "fee_usd": 2000, "conditions": "Annual fee per organization"},
        ]
    else:
        tiers = []
        print("  Enter tier details. Type 'done' at the tier name prompt to finish.\n")
        while True:
            name = input("  Tier name (or 'done'): ").strip()
            if name.lower() == "done":
                break
            if not name:
                print("    Tier name is required.")
                continue
            desc = input(f"    Description for '{name}': ").strip()
            fee_str = input(f"    Fee in USD (0 for free): ").strip()
            try:
                fee = int(fee_str) if fee_str else 0
            except ValueError:
                print("    Invalid number, defaulting to 0.")
                fee = 0
            conditions = input(f"    Conditions (e.g. 'Annual fee', 'One-time'): ").strip()
            tiers.append({
                "name": name, "description": desc,
                "fee_usd": fee, "conditions": conditions or "None specified",
            })
            print(f"    Added tier: {name} (${fee})\n")
        if not tiers:
            tiers = [{"name": "Standard", "description": "All commercial users",
                      "fee_usd": 0, "conditions": "Contact maintainer for pricing"}]

    # Payment methods
    print("\n  -- Payment Instructions --")
    if args.non_interactive:
        payment_methods = [{"method": "email",
                           "details": "Contact maintainer for payment instructions"}]
    else:
        payment_methods = []
        available = ["Stripe", "GitHub Sponsors", "Email", "Smart Contract", "Other"]
        print("  Add payment methods (enter 0 to finish):")
        for i, m in enumerate(available, 1):
            print(f"    {i}. {m}")
        while True:
            val = input("  Choice [number, or 0 to finish]: ").strip()
            if val == "0" or not val:
                break
            try:
                idx = int(val) - 1
                if 0 <= idx < len(available):
                    method = available[idx]
                    details = input(f"    Details for {method} (URL or instructions): ").strip()
                    entry: dict = {"method": method.lower(), "details": details}
                    if details.startswith("http"):
                        entry["url"] = details
                    payment_methods.append(entry)
                    print(f"    Added: {method}\n")
            except ValueError:
                print("    Invalid choice.")
        if not payment_methods:
            payment_methods = [{"method": "email",
                               "details": "Contact maintainer for payment instructions"}]

    # Derivative reciprocity
    print("\n  -- Derivative Reciprocity --")
    if args.non_interactive:
        reciprocity = True
    else:
        reciprocity = ask_yes_no("Require derivatives to also use OPL?", default=True)
    reciprocity_note = (
        "Derivatives must be licensed under OPL-1.3.1 or later."
        if reciprocity else
        "Derivatives may use any compatible license."
    )

    # AI training
    print("\n  -- AI Training --")
    if args.non_interactive:
        ai_allowed = False
    else:
        ai_allowed = ask_yes_no("Allow AI training on your codebase by default?", default=False)
    ai_note = (
        "AI training is permitted." if ai_allowed else
        "AI training requires explicit written permission from the Maintainer."
    )

    registry = {
        "schema_version": "1.0",
        "license": "OPL-1.3.1",
        "maintainer": maintainer,
        "jurisdiction": jurisdiction,
        "standard_terms_url": terms_url,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "fee_tiers": tiers,
        "payment_methods": payment_methods,
        "derivative_reciprocity": reciprocity,
        "derivative_reciprocity_note": reciprocity_note,
        "ai_training": {"allowed": ai_allowed, "note": ai_note},
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)

    print(f"\n  REGISTRY.json written to {args.output}")
    print(f"  - {len(tiers)} fee tier(s)")
    print(f"  - {len(payment_methods)} payment method(s)")
    print(f"  - Derivative reciprocity: {'required' if reciprocity else 'optional'}")
    print(f"  - AI training: {'allowed' if ai_allowed else 'restricted'}")
    print("\n  Commit this file to your repository root.\n")


if __name__ == "__main__":
    main()
