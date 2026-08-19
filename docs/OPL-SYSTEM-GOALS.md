# OPL Adoption System — Goals & Leverage (systems-design pass)

**Date:** 2026-08-19 · **Skill:** systems-design (Meadows leverage ladder)
**Scope:** the OPL adoption + canary ecosystem as a *system* the user must
mentally model, not a bag of CLI tools.

## Step 0 — Paradigm & Goal Gate (MANDATORY)

**Level 2 — Paradigm (who/what is this FOR?):**
The OPL ecosystem exists so a *maintainer* can release source-available software
under a license that (a) keeps the source public, (b) reserves paid commercial
use to the maker, and (c) gives the maker a *provable* theft-detection mechanism
(canary tokens) — without a registry, account, or key server. The operational
purpose (deduced from structure, not the tagline) is **"sustainable software via
a two-sided license the maker can actually enforce locally."** It is NOT "a
license file generator" and NOT "a SaaS."

**Level 3 — P0 goal (one line, no implementation named):**
> A first-time maintainer can adopt OPL on a real repo and, at every step, know
> *what they got, what to do next, where their secrets live, and how to recover
> them* — without reading source code or asking anyone.

Everything else (CLI flags, Studio widgets, canary strategies, git hooks) is a
*means* to that goal or a Level-12 parameter. If a feature doesn't reduce the
maintainer's uncertainty at a decision point, it's not serving P0.

## Goal Hierarchy

- **P0 (non-negotiable):** Adopting is comprehensible end-to-end. The user never
  has to ask "what do I do now / where are my tokens / how do I recover."
- **P1 (primary):** The license is actually enforceable (canary tokens present,
  manifest private, verifiable).
- **P2 (secondary):** Local-only by default (privacy); contributors can work
  without the secret.
- **P3 (nice-to-have):** Studio/MCP surface, polished copy, automation hooks.

## System Map (stocks / flows / loops)

**Stocks:** LICENSE+NOTICE+SPDX (repo artifacts); canary tokens (in source);
canary manifest+salt (private, local only); terms page (external).

**Actors:** M1 maintainer (adopts, holds secret); M2 commercial user (consumes).

**Reinforcing loop (R1):** adopt → canary → enforceable → more confident adoption.
**Balancing loop (B1):** `opl_check` / pre-push hook → flags drift → re-embed.
**Balancing loop (B2 — MISSING):** secret loss → no recovery. There is no
  restorative loop for "I lost `.canary/`." This is the G3 gap.
**Information flow (F — MISSING):** contributors receive tokens in source but no
  guidance on their role. This is the G4 gap.

## Leverage ranking of remaining gaps

| Gap | Meadows level | Leverage | Fix |
|-----|--------------|----------|-----|
| G3 secret has no recovery loop | L8 balancing | HIGH | backup path for `.canary/` |
| G4 contributors uninformed | L6 info flow | HIGH | contributor guide at adopt |
| G5 canary framed as separate feature | L3 goals | MED | copy reframes canary as part of journey |

Per the skill: build Level 3–8 first. G3 + G4 are the next builds. G5 is copy.

## Build-signal note
User said "address the UX / this system still has multiple gaps" after the
questions were answered → BUILD signal (Pitfall 8d). Proceeding to implement
G3 + G4 now, not re-audit.
