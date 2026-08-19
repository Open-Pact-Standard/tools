# W4 — Harden Integrity Decisions (evidence path, hunt false-safety)

Date: 2026-08-19 · Repo: `open-pact-tools` (main). Scope: the integrity
**decisions** in the canary enforcement loop that were previously "picked" but
not deliberately decided + tested. W2 (`docs/W2-signed-chain-verify.md`) proved
the origin-canary PQ-signed chain closes end-to-end, so the signing reality is
known before this work set evidence semantics. This document records the three
decisions, the deliberate rationale, what changed, and the regression test that
locks each one in.

The enforcement loop here is the **Python, stdlib-only** `canary_embedder.py`
(Merkle / token-presence evidence + `hunt` triage). Cryptographic artefact
signing lives in the Rust `origin-canary` chain (Ed25519 + Falcon-1024 per W2)
and deliberately stays out of this Python tool.

**No license-repo changes; git tags `v1.0.0` / `v1.0.1` untouched.** No secrets
committed. Findings doc left uncommitted alongside the W1/W2 docs.

---

## Decision 1 — Evidence strength is content-tiered, not just path-keyed

**Problem.** `verify_evidence_gate` previously set `merkle_proven=True` only
when the suspect file's *relative path AND content* matched a recorded release
file. A byte-identical copy under a *different* path (the realistic theft —
attacker renames `src/app.py` to `core.py`) collapsed to `merkle_proven=False`
and was reported as an undifferentiated "lead, not proof" (W1 finding M2). That
under-states the evidence: a byte-identical file is *cryptographically* proven
to be a copy by `sha3_256` hash equality alone, independent of its path.

**Decision.** Introduce a two-tier provable-strength model instead of a single
hard path-keyed gate:

- `merkle_proven=True` — path **and** content match a recorded release file.
  Strongest: the exact file at the same relative path, Merkle path-binding intact.
- `content_identical=True` (+ `identical_to=<recorded path>`) — content matches a
  recorded release file under a **different** path (a rename/relocation).
  `sha3_256` equality proves byte-identity, so this is a **provable fact**, not
  a bare lead — it is simply not Merkle path-bound. It is reported distinctly so
  an owner never mistakes path-binding for mere byte-equality.
- Neither — a token literal is present but the bytes differ from every recorded
  release file → still a bare lead (honest: presence of a token is not proof the
  *file* was copied unmodified).

This keeps conservative honesty (a rename is never claimed as a full Merkle
proof) while never discarding real cryptographic signal.

**Changed.** `canary_embedder.py` `verify_evidence_gate`: normalized the recorded
`source_files` map once, built a reverse hash→[paths] index, and populated
`merkle_proven` / `content_identical` / `identical_to` per matched file.
`cmd_evidence` now prints a `Content-identical (renamed)` count.

**Test.** `TestW4IntegrityDecisions::test_evidence_renamed_copy_is_content_identical`
(renamed copy → `content_identical=True`, `identical_to="src/core.py"`,
`merkle_proven=False`) and `test_evidence_edited_copy_stays_a_lead` (edited copy
→ both flags `False`).

---

## Decision 2 — `hunt` false-safety is fixed; `hunt` stays de-scoped / non-product

**Problem.** `_gh_search_code` swallowed `gh` missing or erroring and returned
`[]`, so a broken/unauthenticated search collapsed to "No copies found on GitHub
code search." (exit 0) — F1 false-safety: a failed tool impersonating a clean
sweep (W1 finding L3). `hunt` is de-scoped from the enforcement product (per
ROADMAP: litigation is the reactive retrieve-and-prove path; `hunt` is a
tool, not packaged).

**Decision.** **Fix** the false-safety (option b) **and explicitly mark the tool
non-product** (option c) — both are low-cost and complementary; making it a
*product feature* was rejected:

- `_gh_search_code` now returns `(hits, tool_state)` distinguishing
  `ok` / `gh_missing` / `search_failed`. `cmd_hunt` aborts on the first
  non-`ok` token with a clear error and `exit 1`, always stating *"This is a TOOL
  FAILURE, not a 'no copies' result."* It never prints "No copies found" when the
  search could not run.
- `cmd_hunt`'s docstring carries a `DE-SCOPED / NOT PRODUCT` banner so future
  maintainers do not grow it into product surface. It remains a standalone
  triage net: a hit is a LEAD; only `verify` + `evidence` prove.

Not chosen: (a) leave as-is (keeps the false-safety), or turning `hunt` into an
enforcement feature (out of the de-scoped mandate).

**Changed.** `canary_embedder.py` `_gh_search_code` (tuple return) and
`cmd_hunt` (tool-state abort + non-product framing).

**Test.** `test_hunt_failed_gh_is_not_no_copies` (broken `gh` shim → exit≠0,
no "No copies found", `TOOL FAILURE` present) and
`test_hunt_missing_gh_is_explicit` (no `gh` on PATH → exit≠0, "not installed").
Both use a PATH shim so they are hermetic and never hit the real GitHub.

---

## Decision 3 — Evidence does NOT require a signature; a *supplied* signed commitment MUST bind or fail-closed

**Problem.** W2 proved `origin-canary sign` works (Ed25519 + Falcon-1024). The
question: should the Python `evidence` path require the signature?

**Decision.** Two-part, deliberately:

1. **Do NOT hard-require a signature** for an evidence package. The Merkle /
   token-presence match is the probative fact of *copying* and is valid standalone
   against the public payload. Requiring a signature would block legitimate
   offline evidence assembly and conflate two distinct facts — content-provenance
   (did they copy?) vs. record-authentication (is this manifest the owner's?).
2. **A *supplied* signed commitment MUST bind to THIS manifest's `merkle_root`
   or the run fails closed (exit 2) and no evidence file is written.** A signed
   commitment that disagrees with the manifest makes the package internally
   self-contradictory; that must never be recorded as a litigation artifact.
3. The package always records `release_authentication` (`signed` true/false) so
   a user never mistakes an unsigned record for a signed one.

Caveat honoured from W2: this **Python stdlib-only** tool does *not* perform or
verify Ed25519 / Falcon-1024 signatures (that is origin-canary's job via
`verify-commitment`). It only cross-checks the merkle_root *binding* and states
in the package that the crypto signatures themselves must be verified by
`origin-canary verify-commitment`. We never rebuild or fake PQ crypto in Python
(deliberate prior convergence decision, reverted once).

**Changed.** `canary_embedder.py`: new `_assess_release_authentication()`, new
`evidence --signed-commitment <path>` input, `release_authentication` field on
every evidence package, and fail-closed (exit 2, no write) on a non-binding
commitment. `cmd_evidence` prints `AUTHENTICATED` / `UNSIGNED` as appropriate.

**Test.** `test_release_authentication_binding` (unit), 
`test_evidence_signed_commitment_binds_via_cli` (CLI happy path → `signed: true`),
and `test_evidence_nonbinding_commitment_fails_closed` (exit 2, no file written).

---

## Decisions table

| # | Decision | Rationale | What changed | Regression test |
|---|----------|-----------|--------------|-----------------|
| 1 | Renamed-but-byte-identical copies are **content provable** (`content_identical` + `identical_to`), not bare leads; full Merkle proof still requires path AND content | `sha3_256` equality is cryptographic proof of copying independent of path; the old all-or-nothing path-keyed gate under-sold real evidence. Conversely, byte-identity ≠ Merkle path-binding, so the two stay distinct | `verify_evidence_gate` builds a reverse hash index; per-match `content_identical`/`identical_to` populated; `match_count` split surfaced by `cmd_evidence` | `test_evidence_renamed_copy_is_content_identical`, `test_evidence_edited_copy_stays_a_lead` |
| 2 | `hunt` false-safety is **fixed** (tool-state is never collapsed to "no copies") AND `hunt` is **explicitly marked non-product** | A failed/missing search impersonating a clean sweep is F1 false-safety; de-scoping is already policy, so fix the flag on what remains a triage tool — do not grow it into the product | `_gh_search_code` → `(hits, tool_state)`; `cmd_hunt` aborts non-zero on tool failure; `DE-SCOPED / NOT PRODUCT` banner added | `test_hunt_failed_gh_is_not_no_copies`, `test_hunt_missing_gh_is_explicit` |
| 3 | Evidence does **not require** a signature, but a *supplied* signed commitment **must bind** (fail-closed) and the auth state is always recorded | Content-provenance (copying) is independent of record-authentication; requiring crypto would block offline use. A self-contradictory commitment must never be written as evidence | `_assess_release_authentication()`, `evidence --signed-commitment`, `release_authentication` field, exit-2 / no-write on mismatch | `test_release_authentication_binding`, `test_evidence_signed_commitment_binds_via_cli`, `test_evidence_nonbinding_commitment_fails_closed` |

---

## Status of the three decisions (real CLI dogfooded, not just unit-tested)

- **D1**: rename → `content_identical: true, identical_to: "src/core.py"`, exit 0. ✅
- **D2**: broken `gh` → exit 1, "TOOL FAILURE, not a 'no copies' result"; missing `gh` → exit 1, "`gh` CLI is not installed". No collapse. ✅
- **D3**: matching commitment → `AUTHENTICATED`; non-binding → exit 2, no evidence file written. ✅
- Full suite: **80 passed** (73 existing + 7 new). Repo-wide coverage `fail-under` on
  untested `tools/*.py` is a pre-existing condition, unrelated to this scope.

---

## CRITICAL integrity issue surfaced (open, not in this scope — must be tracked)

**`verify` / `evidence` still only scan a hardcoded code-extension allowlist**
(`SUPPORTED_EXTENSIONS`), so a **watermark token planted in a non-code file
(e.g. `README.md`) is invisible** to detection — and W2 (H1) observed that a
clean tree with one such token still produced evidence reported **SOUND**
because `evidence` gates only on *matched* tokens. This is the single most
integrity-relevant open flaw in the enforcement loop, and it interacts with W4
Decision 1: the new `content_identical` tier cannot help a renamed copy of a
`.md` canary, because the canary was never detected to begin with.

Compounding W2 issues (still open): no total-coverage threshold (`evidence`
exits SOUND below 100% matches — W2 M1), and W1 H1 (variable + deadcode
strategies never write the token literal, so those tokens are undetectable by
the literal scan). **Recommended next work (NOT done here):** make
`watermark`-typed tokens scan `.md`/`.txt`/non-code files, and add an
`M of N tokens present` + coverage requirement to `evidence`/`ci`. These are
deliberately out of W4's three decision items; they remain OPEN.