# W3 — Polish the Studio `canary` adapter's sign path

Date: 2026-08-19 · Repo: `open-pact-tools` (branch main, working tree)
Scope: `tools/opl_adapters.py` (the `canary` adapter) + `tests/test_opl_adapters_coverage.py`.
Depends: W2 (`docs/W2-signed-chain-verify.md`) proved the origin-canary signed chain closes;
W3 makes that signing reliable to drive *through the Studio/harness surface*.

All live runs used a **throwaway identity + passphrase** under `/tmp` only. No identity
blob, passphrase, or secret was committed; the repo got code + tests + this doc only.

---

## What signing previously required (from W2, reconfirmed)

- `origin identity keygen` → encrypted 94-byte v2 blob (`ORGB`, tier embedded) + recovery phrase.
- `origin-canary sign -m <manifest> -i <id>.id` → signed commitment. Non-interactive support is
  **only** via `-P, --passphrase-file`; otherwise it calls `rpassword::prompt_password`, which
  **cannot run without a tty** (exit 1: `passphrase prompt failed`).
- Output lands wherever `sign` is invoked — its `--out` defaults to `canary_commitment.json` in
  the **caller's CWD**.
- `verify-commitment -c <commitment>` validates the hybrid Ed25519 + Falcon-1024 signatures.

## What was broken in the adapter's sign path

The old `_canary` invoked signing as:

```
sign --manifest <m> --identity <blob>        # no -P, no --out, no cwd
```

1. **No passphrase path → guaranteed prompt failure in automation.** With no `--passphrase-file`,
   a Studio/harness run (non-tty) hits the rpassword prompt, which errors. The old code surfaced
   the raw binary stderr as `Signing failed: ...` and the run's consequences were muddy.
2. **Commitment landed in the harness CWD, not the repo.** Without `--out`, the signed commitment
   was silently dropped wherever the `opl_adapters.py` process happened to run — so the repo looked
   unsigned/self-inconsistent and `verify-commitment` couldn't be run in-place.
3. **No clean "signing skipped" report.** `sign=true` without an identity merely appended a sentence;
   a hard failure was not surfaced as a real result.
4. **Canary-sign failures were not classified.** Any non-zero sign (including the *expected*
   wrong-passphrase case) became a generic "Signing failed: ..." with no actionable guidance.

## What W3 changed (`tools/opl_adapters.py`)

New `canary` adapter params + CLI flags:

- `passphrase_file` (`--passphrase_file`) — the way to sign non-interactively. The Studio/harness
  cannot answer the interactive prompt, so this is now required when `sign=true` **with** an identity.
- `commitment_path` (`--commitment_path`, default `.canary/canary_commitment.json`) — where the
  signed commitment is written. Defaults **beside the manifest, in-repo**, instead of the caller's CWD.
- `strategies` (`--strategies`) — pass-through to `origin-canary embed --strategies`. Fixes the
  W2-CL4 trap where the default strategy mix embedded into a single-language tree and `embed`
  hard-failed ("not enough eligible files"), so the adapter could never reach signing on a real
  Python-only repo. Default matches origin-canary's default, so existing behaviour is unchanged
  when the flag is omitted.

Sign logic rewrites (the `_canary` sign block):

- **Fail fast before any embed** when `sign=true` + identity is given but no `--passphrase_file`:
  a clear, actionable "this can't work in a non-tty harness" message, and the **repo is left
  untouched** (no wasted embed). Previously it would burn an embed run, then fail on the prompt.
- Sign runs with `--out <in-repo commitment>` and `--passphrase-file <file>` when provided. On
  success, `outputs["commitment"]` is populated and the consequence prints the in-place
  `verify-commitment` command.
- Sign subprocess is wrapped in try/except: a spawn/timeout error now yields a clean message
  ("embedded-but-unsigned, not corrupted") instead of a raw traceback.
- Sign failures are **classified**: a passphrase/decryption error → "wrong passphrase (or corrupt
  identity blob) — 'decryption failed'", with an open sentence; any other non-zero → the binary's
  stderr is surfaced as the reason. Either way the result is `ok=false` and the consequence states
  the tree is **embedded-but-unsigned, not half-signed**, and that *no partial commitment was
  written* (origin-canary only writes the commitment file on success).
- `sign=true` with no identity → clean "signing skipped (embed-only)"; `sign=false` → clean
  "embed-only (no post-quantum signature)". Both are explicit, never silent.

## Regression tests added (`tests/test_opl_adapters_coverage.py`)

A self-contained stub `origin-canary` binary (created in `tmp_path`) drives the adapter
deterministically — no dependency on the real Rust binary or a real identity blob. New tests:

- `test_sign_requires_passphrase_file_fast_fail` — ok=false, actionable message, **repo untouched**.
- `test_sign_success_writes_commitment_in_repo` — ok=true, commitment written **inside** the repo.
- `test_sign_wrong_passphrase_clear_message_no_partial` — ok=false, clear passphrase reason,
  manifest present but **no partial commitment** written.
- `test_sign_generic_failure_surfaces_stderr` — non-passphrase non-zero surfaces binary stderr.
- `test_sign_skip_when_no_identity` and `test_sign_false_is_embed_only` — clean skip/embed-only.
- `test_sign_subprocess_exception_is_clean` — a raised sign subprocess is a clean message.
- `TestCanaryCliParams.test_parse_sign_params` — new CLI args parse into params.

`python3 -m pytest tests/test_opl_adapters_coverage.py -q` → **52 passed**, exit 0.
`opl_adapters.py` coverage: 93% (unchanged); every new sign-path line is covered. The repo's
`--cov=tools --cov-fail-under=70` gate still reports TOTAL 27% because 9 of 10 tool modules
(`opl_check.py`, `opl_init.py`, …) have no tests — a pre-existing, whole-repo condition, arithmetic
proof below — it predates and is orthogonal to W3.

## Live exercise (real binary + real throwaway identity)

Command targeted by the task (with a strategy override + a passphrase file, which the fix adds):

```
python3 tools/opl_adapters.py --run canary --json --repo <tmp> --distribution_id v1.0 \
  --project_id 1 --num_canaries 6 --strategies variable.python,deadcode.python \
  --sign true --identity <keygen>.id --passphrase_file <pass.txt>
```

- **Happy path** → `ok: true`; manifest + `canary_commitment.json` both under `<repo>/.canary/`;
  consequence names the verify command. `origin-canary verify-commitment -c <repo>/.canary/canary_commitment.json`
  → **VALID**, Ed25519 valid, Falcon-1024 valid. The repo is self-consistent; the chain closes.
- **Fast-fail (no passphrase)** → `ok: false`; clear guidance; repo unchanged (no tokens, no `.canary`).
- **Wrong passphrase** → `ok: false`; "wrong passphrase (or corrupt identity blob) — 'decryption failed'";
  `<repo>/.canary/canary_manifest.json` exists but **no** `canary_commitment.json` (no half-signed state).

## Adapter sign UX (summary)

- Signing through the Studio surface is now **reliable and non-interactive**: passphrase via file,
  commitment in-repo, clear messaging for every misconfiguration, and no partial/corrupt state.
- Every failure is an explicit, actionable result — not a raw traceback or a bare exit code.
- The one capability-gap left to the user is that **the passphrase still has to exist as a file**
  (no env-var/keyring option upstream) — see O1 below.

## OPEN-ISSUES

- **O1 (upstream, W2-O2 still open):** origin-canary `sign`/`fingerprint` accept a passphrase only
  via `-P file` or an interactive prompt. The adapter now cleanly requires/passes the file path, but
  there is still no env-var or keyring option. A keyring/env path would remove the "sensitive file on
  disk" step for the Studio. Out of scope for the adapter (would be an origin-canary change).
- **O2 (coverage harness):** the repo's `--cov=tools --cov-fail-under=70` gate fails at TOTAL 27%,
  but only because the other nine `tools/*.py` modules have no test files. Even a 100%-covered
  `opl_adapters.py` cannot reach the 70% bar (363/1252 statements ≈ 29% max for that module's share
  alone). Someone should either add smoke tests to the other modules or scope `--cov` to the modules
  that actually have tests. Not fixed here — this task covered only the opl_adapters sign path.
- **O3 (W2-CL4 persists in the embed step):** origin-canary `embed` still hard-fails (exit 1, no
  manifest) rather than degrading gracefully when the default strategy mix can't place the requested
  token count. The adapter now lets the caller pass a matching `--strategies` override, which is the
  practical workaround; the embed binary itself is unchanged.
- **O4 (uncommitted doc + code):** per task instructions this doc and the adapter/tests changes were
  left uncommitted in the working tree, alongside concurrent W5 edits to `canary_embedder.py` in the
  same repo. Decide commit/PR sequencing before tagging anything.