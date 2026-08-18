# OPL Canary Tokens — How It Works & Routine-Update UX

**Date:** 2026-08-18 · **Walked live**, end to end, as a maintainer would.

## What canary does (3 jobs)

1. **Fingerprint a release** — a release (e.g. v1.0.0) gets a Merkle root over the
   tree + `N` planted tokens.
2. **Detect a modified repo (drift)** — `check` compares current hash vs the
   recorded manifest; a dev commit after release shows exact changed files.
3. **Prove a mis-copied tree** — `verify` scans a *suspect* tree and, using the
   offline private manifest, finds the planted tokens that mark it as derived
   from a specific OPL release.

## The live walkthrough (real outputs)

### Release fingerprint → PRIVATE + PUBLIC split
- **PRIVATE manifest** (`.canary/priv.json`): the *secret* salt + every token's
  secret + Merkle proofs. **Never commit/distribute.** Needed for `verify`.
- **PUBLIC payload** (`.canary/pub.json`): Merkle root, tree hash, per-file hashes,
  per-token *proofs only* — no secrets. Safe to publish.

### Routine updates — the important part
DRIFT IS EXPECTED between releases. A normal dev commit after v1.0.0 produces:
```
MODIFIED: src/shapes.py
DRIFT DETECTED: ... run `embed` to re-fingerprint if this is an intentional release
```
That **red signal is the feature, not noise**: it means CI is guarding "the tree
shipped as v1.0.0," not "the live repo." The routine-update rhythm is:

1. Ship v1.0.0 → `embed` → record Merkle root in a **GPG-signed git tag / release notes**.
2. Dev work continues on the repo (`check` may show drift — expected).
3. Ship v1.1.0 → `embed` **again with a NEW `--distribution-id`** → new Merkle root.
4. `check` against the v1.1.0 manifest is GREEN (tree matches what was shipped).

Each release therefore carries its **own** fingerprint; `check` guards the shipped
tree, and a release manifest outliving its tree drift is the correct, intended state.

### Proving a competitor's copy
`verify --source <rival> --manifest <priv>` found the planted canary in a copied
file and reported the source distribution (v1.0.0 + Merkle root), with a `evidence`
command that assembles the litigation package.

## UX issues found this walkthrough (beyond earlier pass)
- **U4 cache/FIXED** embed crashed if `--output` pointed into a non-existent dir
  (e.g. `.canary/`) — raw `FileNotFoundError` traceback. Now auto-creates parents.
- **U5 (minor)** Step-3/4 output duplicates (manifest-write block and summary both
  print "Step 3: Building Merkle tree" + "Step 4"). Cosmetic but confusing.
- (Earlier pass) embed onboarding fixed: salt auto-generated + persisted, worked
  examples in `--help`.

## Verdict
Canary is functionally right for its job — release fingerprinting, drift guarding,
and copy provenance all work. The routine-update model (re-embed per release,
drift = expected between releases) is correct and now demonstrated. Remaining polish
is U5 (remove duplicated step banners).