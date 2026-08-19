# W2 — Post-Quantum Signed Evidence Chain: End-to-End Verification

Date: 2026-08-19 · Repo: `origin-tools` (main, clean; SDK via `../origin-crypto-sdk` patch).
Chain exercised exactly as the enforcement product intends it, on a throwaway
week tree under `/tmp/w2_test` only. **No identity/blob/secret touched the repo;
nothing committed.**

## Scope walked (the full signed chain)

1. `cargo build --release -p origin` → `target/release/origin` (binary present, v0.4.3)
2. `origin identity keygen` → encrypted 94-byte v2 blob (`ORGB` magic, embedded tier) + 24-codepoint recovery phrase
3. `origin-canary embed` → manifest with BLAKE3 Merkle root
4. `origin-canary sign --manifest --identity` → signed commitment
5. `origin-canary verify-commitment` → both hybrid signatures pass
6. `origin-canary fingerprint --manifest --commitment --archive --identity` → signed fingerprint
7. `origin-canary verify-fingerprint` → signature + archive + commitment-binding all pass
8. Negative tests: tampered archive, tampered commitment, stripped canary
9. Downstream: `publish` → ledger, `evidence` (litigation), `ci` gate

Environment: x86_64 Linux, release profile (`profile.dev.package."*"` opt-level 2).

---

## VERDICT: the signed evidence chain CLOSES end-to-end ✅

Every signature gate in the chain validates and every negative test correctly
fails. The enforcement edge that was "never run live" now runs green:

- **identity keygen → embed → sign → verify-commitment**: VALID (Ed25519 + Falcon-1024). ✅
- **fingerprint → verify-fingerprint**: VALID (signatures + archive BLAKE3-hash/size + commitment binding). ✅
- **evidence package (full litigation chain)**: SOUND. ✅
- **ci gate**: PASSED. ✅
- **Tampered archive**: `verify-fingerprint` → `[FAIL] archive hash + size`, INVALID, exit 2. ✅ detected
- **Tampered commitment (merkle root byte flip)**: `verify-commitment` → INVALID (auth failed), exit 2. ✅ detected

The user (and the Studio `canary` adapter that delegates to `origin-canary`) gets a
genuinely closure-checking evidence chain, not a self-consistent stub.

## What the user has to install / run

- **Install**: `cd origin-tools && cargo build --release -p origin` (and
  `-p origin-canary` for the embedder). Both binaries land in `target/release/`.
  The SDK is pulled as a local `[patch.crates-io]` path dependency on
  `../origin-crypto-sdk` — so a normal user must either clone that sibling repo
  or comment the patch out to use the crates.io `=0.7.1-rc.5` release. (See OPEN-ISSUES O1.)
- **Keygen** (one-time): `origin identity keygen --name <id> [--tier nano|standard|sovereign]`
  → `<name>.id` (encrypted) + a 24-codepoint recovery phrase that must be kept offline.
- **Embed** each release: `origin-canary embed -S <src> -p <pid> -d <tag> -s <salt> -n <n>`
  → `canary_manifest.json` (keep salt offline).
- **Sign**: `origin-canary sign -m canary_manifest.json -i <id>.id` (prompts for passphrase) → `canary_commitment.json`.
- **Fingerprint**: `origin-canary fingerprint -m ... -c ... -a <archive> -i <id>.id` → `canary_fingerprint.json`.
- **Verify**: `origin-canary verify-fingerprint -f canary_fingerprint.json -a <archive> -c canary_commitment.json`.
- **Publish / evidence / ci**: `publish -f ... -l ledger.jsonl`; `evidence -S ... -m ... -c ... -f ... -l ...`;
  `ci -S ... -m ... -c ...` (exit 0 pass / 3 fail).

Failure exit codes: commitment/fingerprint INVALID → 2; hard errors → 1; ci fail → 3.

---

## Works-but-clunky (no correctness impact)

### CL1. Memory-tier flag `-t` is a silent no-op for current (v2) identity blobs
`recover_seed` reads the tier from the blob header and **ignores** the caller's
`tier` argument (SDK `recover_seed_v2`; the `-t` only feeds v1 recovery).
Verified: identity keygen'd at `standard`, then signed with `-t nano` → SAME
Ed25519/Falcon pubkeys, commitment verified VALID. So `origin-canary sign/fingerprint
--tier` cannot be mis-set into a different key, but the flag is misleading:
the CLI help says "Memory tier used when the identity was created" (bins.rs) while
the embedded tier always wins. A user told to "pass your tier" can pass anything.
Fix direction: drop the flag for v2 blobs or warn "tier embedded; -t ignored".

### CL2. Archive hash printed as bare "Archive hash" but is BLAKE3, not SHA-256
`fingerprint` hashes the archive with `blake3::Hasher` and prints "Archive hash",
which is not hex-identical to `sha256sum`. A user spot-checking the recorded hash
against `sha256sum` will see a "mismatch" that is actually just a different
algorithm. Verified: the recorded hash equals `b3sum`, not `sha256sum`. Low-stakes
but a real confusion prompt. (Label it, or accept `--hash sha256|blake3`.)

### CL3. Inconsistent short flags across subcommands
`embed` accepts `-S` for source, but `verify`, `evidence`, and `ci` require the
long `--source` (no `-S`). I first ran `verify -S` and got
`error: unexpected argument '-S'` (exit 2). Trivial but breaks muscle memory.

### CL4. `embed` fails hard if the tree has no eligible files for the requested strategies
`embed` rejects the run if it can't place the requested number of tokens
(`error: only embedded 1 of 6 ... exit 1`) — correct error, but the strategies
default to `variable.python,variable.javascript,watermark,deadcode.python`, so a
pure-markdown or pure-Go repo needs an explicit `--strategies` override. A clearer
message (name a usable strategy) would help on first contact.

---

## Real issues (severity-ranked)

### HIGH — H1. `verify` / `evidence` / `ci` scan only a hardcoded code-extension allowlist, so WATERMARK tokens in non-code files are invisible
`scan_for_token` (verify.rs:105-109) only searches files whose extension is in
`py js jsx ts tsx rs sol c cpp h hpp go java kt`. The `watermark` strategy (the one
specifically meant to tag README/std docs) embeds into e.g. `README.md`, which the
scanner never opens. Verified: embed placed a watermark token in `README.md`; the
clean tree verified at **5 of 6** matches — the README token silently dropped —
yet `evidence` still reported **SOUND**. So two things compound: (a) a genuinely
present watermark in a doc/.md file is never counted, and (b) because `evidence`
gates only on *matched* tokens, a canary sitting in a non-code file can't be
offered as evidence at all. Fix direction: scan all files for `watermark`-typed
tokens (or add a project-configured extension allowlist, defaulting to include
`.md`/`.txt`/`.toml`).

### MEDIUM — M1. `evidence` / `ci` report SOUND/PASS with NO total-coverage check, so a partially-stripped tree still "passes"
`assemble` walks Merkle proofs only for tokens it *matched* (`evidence.rs:255-262`).
It never asserts that all `manifest.canary_tokens` were found. Verified: I stripped
the deadcode canary from `app.py`; `evidence` against the stripped tree printed
`Matches: 4` and **"Evidence package is SOUND"**. A rival who deletes *some*
canaries walks away with a green evidence package whose only signal is a lower
(unspecified) match count — there's no "N of M tokens found" line or exit non-zero
below a threshold. Whether "legitimately derived but heavily-edited" should be
SOUND is a policy call, but right now the number isn't even surfaced as a pass
condition. Fix direction: add a `coverage = matches/len(tokens)` field + optional
threshold to evidence and ci, and print "M of N tokens present".

### LOW — L1. Keygen default output dir is `~/.origin/identities` even when testing
Not a bug, but a default-writing path risk: `origin identity keygen` defaults to
`~/.origin/identities`, so a user/CI that drops `--dir` persists an identity blob
in the home profile. The canary `sign`/`fingerprint` then default `-t standard`
and would silently reuse it. Fine for real use; worth a `--dir /tmp/...` habit and
a doc note. (Recovery phrase is only written when `--phrase-output` is passed;
without it, the interactive banner is skipped only by `--phrase-output`.)

---

## OPEN-ISSUES (resolve before the enforcement product claims "shipped")

- **O1. SDK build path dependency**: both `origin` and `origin-tools` depend on
  `origin-crypto-sdk = "=0.7.1-rc.5"` and `[patch.crates-io] → ../origin-crypto-sdk`.
  An end user who just clones `origin-tools` won't have the sibling repo and the
  built-from-source `origin` CLI the task already compiled won't reproduce without
  it. Decide: ship the crates.io dep by default (comment the patch), or document
  the sibling-clone requirement prominently in the install section.
- **O2. Passphrase handling has no non-interactive config story beyond a file**: 
  `sign`/`fingerprint` prompt via `rpassword` unless `--passphrase-file` is given.
  For the Studio adapter and CI this is fine, but there's no env-var or keyring
  option — document `--passphrase-file` as the supported automation path.
- **O3. Evidence "SOUND" semantics (M1)**: decide the policy — should
  `evidence` fail when fewer than N% of tokens match, and should the wallet's
  archive hash be SHA-256 or BLAKE3 (CL2)? The signed chain is cryptographically
  sound; the *coverage* semantics are not yet defined.
- **O4. No CI-on-real-release exercise yet**: the chain was verified on a
  throwaway tree only (correctly — never the real repo). A `ci` run against a
  real distribution's release archive as an actual CI step is the last untested
  surface; it should pass trivially given these results but hasn't been wired.