# OPL UX — Canary/Adoption Gap (systems-thinking audit, user-as-subject)

**Date:** 2026-08-19 · **Lens:** Meadows leverage ladder · **Subject:** the user who just
adopted (or is about to) and asks *"where do my fingerprints and canary tokens come from,
and how do I verify/update them?"*

## System map (the canary layer specifically)

**Stocks**
- Canary tokens embedded in source files (watermark/variable/deadcode strategies).
- A signed manifest (Ed25519 + Falcon-1024 via `origin-canary`).
- A release fingerprint (BLAKE3 Merkle commitment) + JSONL ledger entry.
- The `origin-canary` Rust binary (lives in origin-tools, NOT in open-pact-tools).

**Flows that EXIST (but are orphaned)**
- `origin-canary embed → sign → fingerprint → publish → verify → evidence → ci` — a full,
  correct provenance lifecycle. Verified real (binary present at
  `~/Coding/Gold/origin-tools/target/release/origin-canary`).
- Studio has a `canary` adapter that delegates to `origin-canary`.

**Flows that are MISSING (the gap)**
- **`opl_adopt` NEVER calls `origin-canary`.** The word "canary" appears only in the final
  success message ("run `canary_embedder.py verify`"), which points at a thin Python embedder
  (`canary_embedder.py`), not the real `origin-canary` signing engine. So after adopting, the
  user has LICENSE + NOTICE + SPDX but **zero canary tokens, zero fingerprint, zero manifest.**
- **No combined adopt+canary command.** Adopt and canary are two disconnected islands.
- **No "verify/update my tokens" loop surfaced to the user.** The user knows they *should* have
  tokens (the license itself references canary for OPL-AI) but nothing tells them when/how.
- **Two competing embedders** (`canary_embedder.py` Python vs `origin-canary` Rust) — a
  stock-and-flow-structure ambiguity (LP#10) that will confuse any user about which to run.

## Findings (severity-ranked by leverage)

| # | Leverage | Gap | Severity | Effort |
|---|----------|-----|----------|--------|
| C1 | **LP#6 info flow** | Adopt never wires canary: after `opl_adopt` the repo has no tokens/fingerprint/manifest, and nothing tells the user this is missing or how to add it. | HIGH | M |
| C2 | **LP#6 info flow** | No combined adopt+canary path; two separate commands, no orchestration. User must discover `origin-canary` by reading a code comment. | HIGH | M |
| C3 | **LP#10 stock/flow** | Two embedders (`canary_embedder.py` Python vs `origin-canary` Rust) — ambiguous which is canonical. | MED | S |
| C4 | **LP#8 balancing loop** | No recurring "verify my tokens are still present / update them on release" loop surfaced. `ci` exists but isn't wired into the adopt output or a cron. | MED | M |
| C5 | **LP#3 goals** | Site/Studio present canary as a separate "enforce" feature, not as a step in the OPL adoption journey — so users who adopted think they're "done" without tokens. | LOW | S |

## Verified-healthy
- `origin-canary` binary is real and fully featured (embed/sign/fingerprint/publish/verify/evidence/ci).
- Studio `canary` adapter delegates to the real binary (not a reimplementation).
- Python `canary_embedder.py` exists as a fallback but is NOT the signing authority.

## Resilience note
The system is **brittle for the adopter**: the license's own OPL-AI clause implies canary
use, but the adopt flow delivers none. A user who adopts and stops has a license with a
promise (OPL-AI enforcement) they cannot fulfill because the tool never created the tokens.
That is the gap you felt.

## Resolved this cycle (2026-08-19, build pass)

- **G1 (LP#6, CRITICAL):** `opl_adopt --canary` now appends `.canary/` to
  `.gitignore` (creating it if needed). The proof-of-ownership manifest can no
  longer be committed by a careless `git add .`. Verified: git reports `.canary/`
  as ignored.
- **G2 (LP#6, HIGH):** `opl_adopt --canary --install-hook` installs a
  `.git/hooks/pre-push` that re-verifies canary tokens before every push — the
  recurring "update my tokens as I change the repo" loop the user asked for.
- **C1/C2 (prior):** `--canary` embeds via origin-canary with language-fit
  strategies; `opl_check` excludes dot-dirs at any depth.

## Remaining gaps (not yet closed)

- **G3 (LP#8):** no backup/recovery path for the salt+manifest. Lose `.canary/`
  and you lose the ability to litigate. Needs: encrypted offsite backup guidance
  or a re-derivable scheme. Single point of failure.
- **G4 (LP#6):** no contributor story. A contributor who clones gets tokens in
  source but no manifest and no guidance; they can't verify and may silently
  break a token. Needs a CONTRIBUTING note + a `opl_check` mode that tolerates
  missing manifest.
- **G5 (LP#3):** site/Studio still frame canary as a separate "enforce" feature,
  not part of the adoption journey. Reinforce in copy.
- **Q4 answer (local-only, by design):** origin-canary has NO git/remote/sync in
  any command. Everything (tokens-in-source, manifest, JSONL ledger) is local.
  Provenance proof is only as durable as your local `.canary/` folder. This is a
  privacy feature, but it means the user must back up `.canary/` themselves.
