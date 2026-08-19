# OPL UX — Design Analysis (systems-thinking audit)

**Date:** 2026-08-19 · **Lens:** Meadows *Thinking in Systems* leverage ladder
**Scope:** the UX of the OPL ecosystem as a *system of actors and information flows* —
the public site, the CLI adopt/check tools, the Studio, and the MCP surface.

## System map (what actually exists)

**Stocks**
- The OPL license text (canonical, published).
- A maintainer's `NOTICE` + `LICENSE` (per adopted repo).
- A maintainer's published Standard Terms page (external, optional).
- The canary fingerprint (optional, for theft detection).

**Actors (the two parties the license is a contract BETWEEN)**
- **M1 — Maintainer** who adopts OPL (runs `opl_adopt`, publishes terms).
- **M2 — Commercial/user** who finds an OPL work and must decide how to use it.

**Flows that exist**
- M1 → repo: `opl_adopt` writes NOTICE/LICENSE/SPDX (verified self-consistent).
- M1 → self: `opl_check` validates; `opl_adopt` now prints a plain next-steps block
  (what you got, no key needed, 3 steps).
- Site → M1: hero + Adopt panel + FAQ explain the maintainer's duties.

**Flows that are MISSING (the audit's core finding)**
- **M2 → information:** there is *no surface* that tells a commercial user their
  obligations. The license is a two-party contract, but only one party is informed.
- **M1 → M2 compliance loop:** adopt says "publish your Standard Terms page" but
  nothing *generates* that page or links it from the repo in a way M2 can find.
- **M2 → self-check:** M1 has `opl_check`/`verify`; M2 has no analogous "am I
  compliant to use this?" loop.

## Findings (severity-ranked by leverage)

| # | Leverage pt | Gap | Severity | Effort |
|---|-------------|-----|----------|--------|
| F1 | **LP#6 info flow** | Consumer/commercial-user journey is *absent*. Only the maintainer is informed. A developer who lands on an OPL repo has no surface telling them: free for personal/edu/research, commercial requires payment via the maintainer's terms URL, 36-mo silence → Apache-2.0, OPL-AI restriction if opted in. | HIGH | M |
| F2 | **LP#6 info flow (2nd)** | Site Adopt panel does not mirror the CLI's new next-steps block ("what you get / no key to store"). A visitor reading the site still can't see the maintainer's concrete post-adopt duties. | MED | S |
| F3 | **LP#9 delay** | The "publish your Standard Terms page" step is a broken loop: adopt instructs it but no template/tool produces one, so the M1→M2 compliance handoff stalls. | MED | S |
| F4 | **LP#8 balancing loop** | No consumer-side check. M1 has `opl_check` + `verify`; M2 has nothing to confirm "am I allowed to use this commercially?" | MED | M |
| F5 | **LP#3 goals** | Site is producer/OPL-centric. The two-sided goal ("sustainable software via a 2-sided license") is only half-represented; M2's reason to comply (legal safety, reputation) is unstated. | LOW | S |
| F6 | **LP#5 rules** | No incentive alignment for M2 to comply — they must hunt the terms URL; nothing surfaces "pay here" from the repo. (Depends on F1/F3.) | LOW | M |

## Verified-healthy (do NOT re-touch)
- `opl_adopt` prints a plain maintainer next-steps block (just added, verified).
- Studio binds `127.0.0.1` loopback only.
- Kit serving blocks path traversal (`../..` + URL-encoded → 404).
- Canary public payload carries no secret (salt/canary secret absent).
- `adopt-full` defaults to confirm=no-write (destructive writes never implicit).

## Resilience note
The system is *statically stable* for M1 (tools work, tests green) but **brittle for M2**:
the entire commercial-use compliance path depends on M2 spontaneously finding a
terms URL the maintainer was never helped to publish. One missing page = the
two-sided contract silently becomes one-sided. That is the UX resilience gap.
