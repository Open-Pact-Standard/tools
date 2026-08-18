# Canary Token Validation — how the maintainer checks tampering / theft

**Date:** 2026-08-18 · Grounded in real, executed commands.

The canary model answers **two distinct questions**. They use different commands
and different inputs:

## Q1: "Was someone else shipping MY code?" → `verify`
Theft / unauthorized redistribution. You point the canary at a **suspect** tree
you found (a rival's repo, an app store binary, a leaked archive) and scan it for
the tokens you planted.

```
python3 canary_embedder.py verify --source <suspect_dir> --manifest <private_manifest.json>
```
- **Input:** the suspect tree + your **PRIVATE manifest** (the secret salt + token
  secrets). Only the maintainer can run this — that's the point; it's asymmetric.
- **Output:** `FOUND N CANARY TOKEN MATCHES` + exactly which files + which
  distribution (`v1.0.0`) + Merkle root.
- **Then:** `evidence --manifest <priv> --suspect-source <dir>` assembles the
  litigation package (token secrets, Merkle proofs, human-readable summary).

*Verified live:* a file copied out of a canaried repo was detected in a separate
"rival" tree → `FOUND 1 CANARY TOKEN MATCHES - src/their_core.py`.

## Q2: "Was MY released code modified?" → `check` (drift)
Tampering / unintended change to the shipped tree. Comparison against the
**published public payload**.

```
python3 canary_embedder.py check --source <repo> --payload release_fingerprint.json
# or, from CI: canary_check.py --payload release_fingerprint.json --repo .   (exit 0/1)
```
- **Input:** the repo as-is + the **public payload** (merkle root + per-file
  hashes + proofs, no secrets) — verifiable by anyone, e.g. in CI.
- **Output:** `MODIFIED: src/core.py` + tree-hash diff + exit 1 = drift.
  Exit 0 = `OK: repo matches the recorded fingerprint. No drift.`

*Verified live:* editing a shipped file → `MODIFIED: src/core.py`, `DRIFT
DETECTED`, exit 1.

## The release rhythm that makes both work
1. **Release:** `embed` → writes **private manifest** (keep offline, secret) +
   **public payload** (publish in a GPG-signed tag / release notes).
2. **Ongoing:** CI runs `check` on the public payload every commit — guards
   "the shipped tree," fails red on drift.
3. **Suspicion:** if you find a possibly-stolen copy, run `verify` (only you can,
   needs the private manifest) then `evidence` for the legal record.

## Post-quantum upgrade (origin-canary, optional)
The Rust `origin-canary` adds **signed** provenance so a *forged* fingerprint is
detectable, not just a changed one: `embed → sign → verify-commitment →
fingerprint → verify-fingerprint → evidence → ci`. Same two questions, plus an
authenticity layer (hybrid Ed25519 + Falcon-1024) over the Merkle root. Wired into
the OPL Studio as the "Enforce with canary tokens" capability.

## Key caveat (honest)
Canaries are **evidence, not access control.** A determined adversary who knows
tokens are present can strip them. The value is legal attribution and drift
detection — proving *which* release was derived and *that you authored it* — not
preventing the copy in the first place.

## Which path is the product (decision, 2026-08-18)
**Litigation is the reactive path:** owner suspects theft → *retrieves* the code →
`verify` proves provenance → `evidence` assembles the Merkle-backed package. That
is what's packaged (Studio `canary` embed+sign; site "Canary Enforcement").
A `canary hunt` subcommand exists in the source to *proactively* search public code
hosts, but it is **not a packaging target** (false-safety risk + coverage limits
unresolved). If an owner retrieves a suspect copy, the supported route is always
`verify` + `evidence`, not an upfront search.