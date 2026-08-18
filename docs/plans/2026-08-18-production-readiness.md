# Production-Readiness Plan — OPL Studio + Canary + Website

**Date:** 2026-08-18
**Scope:** open-pact-tools, open-pact-license, open-pact-standard.github.io
**Lens:** systems-design (Meadows leverage ladder)
**Status:** ✅ COMPLETE — all phases landed, all three repos pushed, v1.4.3 tagged, site live.

## P0 (one line)
A dev team can adopt OPL into a repo and keep it verifiably OPL-compliant as the
repo evolves — across every commit, release, and detector run — as a seamless
automated operation, with the canary fingerprint staying cryptographically sound
over time.

---

## Confirmed gaps (by leverage)

| # | LP | Gap | Sev | Repo |
|---|----|-----|-----|------|
| G1 | #6 info flow | Canary manifest embeds secret salt + all token secrets → forgeable if shared | VERY HIGH | tools |
| G2 | #8 balancing loop | Canary self-pollutes its own source when run against its repo | HIGH | tools |
| G3 | #3 goals | Manifest records `project_id: null` → no attestation of what was fingerprinted | MED | tools |
| G4 | #6 info flow | Non-deterministic sparse coverage; no "covers whole repo" notion | MED | tools |
| G5 | #8 loop | No CI/update hook re-verifies `file_hash` as repo evolves | MED | tools |
| G6 | prod-readiness | Studio localhost-only, no headless contract hardening; adapter 10 uncommitted edits | LOW-MED | tools |
| G7 | #3 goals/identity | **Version drift across ecosystem**: published v1.3.1 vs tools+license-draft v1.4(.3); website + NOTICE.example stale | **HIGH** | all |

---

## Production-ready order (leverage-first, additive)

### Phase A — Canary cryptographic soundness (G1, G2, G3)
1. Split canary output: **public payload** (merkle root, file_hash, token proofs,
   no secrets) vs **private store** (salt + secrets, gitignored).
2. Embargo secret from the manifest; require `project_id` (fail, not null).
3. Self-exclusion: embedder never injects into `canary_embedder.py` / manifest.
4. Commit the leak fix with tests.

### Phase B — Repo coverage + identity (G4)
5. Deterministic whole-repo coverage (token per file derived from tree).
6. `project_id`/repo identity required + recorded.

### Phase C — The update loop (G5)
7. `canary_verify --against <manifest>` hashes current tree vs manifest `file_hash`.
8. Thin `canary_check.py` CI step on tools CI; document for adopters.

### Phase D — Studio production readiness (G6)
9. Commit/land the pending adapter edits (user's uncommitted work).
10. Headless contract hardening + README harness surface.

### Phase E — Website update (G7 + outward face)
11. Refresh `open-pact-standard.github.io` to current versioned state.
12. Sync `NOTICE.example` + README version strings.

---

## Version decision needed (BLOCKER for Phase E)
OPL-1.4 is a **draft** (1.4.3) in the license repo — only **v1.3.1 is published/tagged**,
but tools already ship OPL-1.4. The website and docs must advertise ONE truth.
Options:
- (a) Publish OPL-1.4 (tag v1.4.3, mark released) → then website = v1.4 everywhere.
- (b) Keep 1.3.1 as published; retract tools/docs to 1.3.1 (large, backwards).
- (c) Website states "v1.4 draft" + links to draft LICENSE, keeps 1.3.1 as published.

Recommended: **(a)** — tools and vi docs are already at 1.4; publish the draft.