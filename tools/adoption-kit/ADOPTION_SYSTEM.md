# OPL Adoption System — Systems Design (Goal & Loop Map)

*Design anchor for the OPL adoption tooling. Per systems-design skill (Meadows):
the goal (Level 3) and feedback loops (Level 8) come first; commands (Level 12)
are a means. This document is the reference the tooling serves — not the other way
around.*

---

## Step 0 — Paradigm & Goal (the gate)

**Who is this for?** A maintainer who wants to apply OPL to their project
*correctly* — without writing a license from scratch, and without accidentally
giving away or over-restricting their work.

**What is it FOR?** *Correct, understood adoption.* Not "running a CLI." The
operational purpose is: a project that, once "OPL-adopted," is legally coherent
(NOTICE + LICENSE + live terms URL + SPDX + validated) **and** whose maintainer
*understands the consequences* of their choices.

**P0 (non-negotiable):** An adopted project is actually legally coherent.
**P1:** The maintainer understands the consequences of their choices (DOSP
converts code on a schedule; abandonment; commercial tier needs a real page).
**P2:** Low mechanical friction (the commands).
**P3:** Polished orchestration / extra docs.

*P1 > P2.* The adoption curve is steep at understanding, not at typing. Any
intervention that lowers friction (P2) but not understanding (P1) is low-leverage.

---

## System map

**Stocks:** adopter understanding · adopted projects (OPL in the wild) ·
commercial relationships · legal-risk exposure.

**Flows:** adoption (project picks OPL) · mis-adoption (wrong/missing config) ·
abandonment→Apache conversion · commercial payments.

**Boundary:** controllable = the tooling + the NOTICE/LICENSE it emits.
Observable-only = the adopter's comprehension (we can't *measure* it; we surface
consequences and rely on the balancing loop).

---

## Feedback loops

- **R1 (virtuous, reinforcing):** more adopters → more real-world validation →
  more confidence → more adopters.
- **B1 (balancing, GOOD):** `opl_check` validates → catches mis-config → reduces
  legal-risk stock → adoption continues safely. *This loop was silently broken by
  the 1.3.1 staleness; restored.*
- **R2 (vicious, reinforcing):** confusing/opaque tooling → adopter doesn't
  understand consequences → picks a simpler license (MIT) → OPL loses the
  adoption. **This loop determines the curve.** Attacked by the consequence-
  preview (Level 6 info flow) in `opl_init`.
- **B2 (drift, dangerous — Shifting the Burden):** adopter accepts all defaults
  without understanding → defaults become a crutch → self-understanding atrophies.
  Mitigated by surfacing what each default *means* (consequence-preview), not by
  removing defaults.

---

## Leverage points (intervene here, in order)

| Level | Intervention | Status |
|---|---|---|
| 3 (Goals) | This document: explicit "correctly adopted" definition | done |
| 6 (Info flow) | Consequence-preview in `opl_init` before each commitment | done |
| 8 (Balancing) | `opl_check` validates for OPL-1.4 (was 1.3.1) | done |
| 10/12 (Structure/params) | A `opl adopt` wrapper chaining the 5 commands | **deferred** — lowest leverage |

**Wrong-direction warning (per-axis):** the intuitive push is "make adoption
easier/faster" (more wrapper, more automation). Wrong direction — that's Level 12
and does nothing for the curve. Right direction: make adoption **understood**
(surface consequences, enforce the validator). Push only changes that deepen
understanding while preserving autonomy.

---

## Open findings (not fixed, tracked)

- `opl_check` flags `Cargo.toml` as missing SPDX header though it carries
  `license = "OPL-1.4"` in its structured field. Manifest files shouldn't be
  scanned for comment-style headers. Defer until a second false-positive appears.
- No single `opl adopt` orchestrator. Deferred: low leverage until P1 is solved.

---

*This map is the source of truth for adoption-tooling changes. Before adding a
command or flag, ask: does it raise P1 (understanding) or only P2 (friction)?*
