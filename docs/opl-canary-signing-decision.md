# Canary post-quantum signing — decision record (2026-08-18)

## What happened
Attempted to add hybrid Ed25519 + Falcon-1024 post-quantum signing to the
Python `canary_embedder.py` via the origin-crypto-sdk's example CLI
(`--sign-seed` shelling to `origin-crypto`). Systems-thinking-audit revealed
this was a **parallel, inferior reimplementation** of machinery that already
exists in origin-tools: `origin/canary` (the `origin-canary` Rust crate).

## Decision
**Post-quantum signing lives in `origin-tools/origin-canary`, not the Python
canary.** The `--sign-seed` / `--verify-signature` over-build was reverted
(commit `f5e59bc` → reverted by `e24e847`). Running two overlapping canaries
is a maintenance liability.

## Where the real thing lives
- `~/Coding/Gold/origin-tools/origin-canary` — Rust crate + `origin-canary` CLI.
- Does: embed → sign (hybrid Ed25519 + Falcon-1024 via `origin identity keygen`,
  an encrypted identity, NOT a raw seed flag) → fingerprint → ledger → evidence → ci.
- Uses BLAKE3 hashing; all crypto underwritten by `origin-crypto-sdk`.
- Build: `cargo build --release` in that crate → `target/release/origin-canary`.

## What the Python canary stays good at
`canary_embedder.py` / `canary_check.py` remain the simple local embed + CI
drift-hook (stdlib-only, zero deps). They are NOT the provenance/signing tool.

## Next step (not started)
Decide whether the OPL Studio should invoke `origin-canary` when present, and
document that path. Until that's explicit, the Python tool documents PQ signing
as "use `origin-canary sign`" and does not attempt it internally.