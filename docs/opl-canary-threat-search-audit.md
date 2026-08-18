# Canary Token Validation + Remote Theft-Search — Systems Audit

**Date:** 2026-08-18 · **Lens:** Meadows leverage ladder
**Subject:** `canary_embedder.py` / `canary_check.py` (Python) + `origin-canary` (Rust)
**Question:** Is the current validation flow viable, and can we add remote
(theft) detection across GitHub / code hosts?

Worked-example baseline (verified again this session):
- Public payload carries NO secret (salt/token-secret absent) — verified on disk.
- `verify` (theft) and `check` (drift/tamper) both work, behaviorally proven.
- `gh` CLI is authenticated and `gh search code` works (positive control hits,
  canary string returns clean).

---

## 1. The two validation questions (already viable)

| Question | Command | Input | Verifier |
|----------|---------|-------|----------|
| Stolen / copied code | `verify` | suspect dir + PRIVATE manifest | maintainer only (asymmetric) |
| Tampered release code | `check` / CI `canary_check` | repo + PUBLIC payload | anyone / CI |

**Viable.** Proven behaviorally: a copied canary file was detected in a foreign
tree; a modified shipped file tripped drift (exit 1).

---

## 2. Remote theft-search — viability gate (the new ask)

**Proposed capability:** search GitHub (and by extension other code hosts) for a
maintainer's canary tokens to find unauthorized copies without being handed a
suspect directory.

### Ground truth that makes it viable / not (measured this session)

- ✅ **`gh search code "<canary_string>"` works** and is authenticated. A positive
  control (`SPDX-License-Identifier: MIT`) returns real GitHub hits; a random
  canary string returns clean (correct = no theft).
- ⚠️ **Embedding strategy splits searchability.** A *VariableInjection* canary puts
  the token in a **variable NAME** (uppercased) whose VALUE is a *different*
  hash-derived hex — the full `canary_<hex>` string is NOT in the file. The
  *Watermark* canary writes `# Module reference: canary_<hex>` as a comment — that
  IS the literal searchable string. Measured: only 1 of 3 tokens in a test source
  carried the full literal token; the rest were variable-name-encoded.
  → **GitHub text search only reliably finds Watermark-embedded tokens.** This is
  the single most important limitation to design around.

### The design (remote `canary hunt` subcommand)

```
canary_repo_hunt: read private manifest → derive the literal canary strings
  → for each string: gh search code "<string>" (paginated)
  → aggregate hits as THEFT CANDIDATES (repo:path:line)
```

- **Source of truth:** the PRIVATE manifest (the salt is secret — the public
  payload CANNOT list token literals; only the maintainer can hunt). Good
  asymmetry, preserves stealth (tokens queryable only by key holder).
- **Mechanism:** `gh search code` (GH CLI, already authed) — one call per token;
  fall back to the REST API `GET /search/code?q=` if `gh` absent.
- **Rate limits:** GH code-search ~30 req/min (auth) / 10 (anon). Token counts are
  small (10-ish), so this is fine; throttle to ~1/s.
- **Coverage limits (be honest):** GitHub code search indexes **public repos**
  only; won't find private forks, non-GitHub hosts, or canaries that were
  variable-encoded (see above). It's a triage net, not a guarantee.
- **False positives:** 12-hex suffix is high-entropy; a hit is a strong signal, but
  still needs the `evidence` step to confirm (Merkle proof) before any claim.

### Leverage citation
- This is **LP #6 (Info Flows)** — the "does anyone have a copy?" signal is
  currently absent unless someone hands you a suspect dir. Adding the flow turns a
  reactive (evidence-after-suspect) system into a *proactive* one. High leverage,
  contained change.
- **LP #8 caution (the real structural cost):** remote search is a **brand-new
  surface** with an external dependency (GitHub), rate limits, and a coverage
  blind spot. It must be *clearly additive* ("hunt" is separate from the existing
  local `verify`), and its limitations surfaced, or it becomes a false sense of
  coverage ("I searched GitHub, so I'm safe" — I'm not, due to private forks +
  variable-encoding).

---

## 3. Findings table

| # | LP | Gap | Severity | Effort | Fix |
|---|----|-----|----------|--------|-----|
| R1 | #6 Info flows | No way to proactively find copies in the wild | High (feature) | Med | `canary hunt` subcommand (gh search over private manifest literals) |
| R2 | #8 Balancing | Remote search coverage blind spots (private forks, var-encoded, non-GitHub) | High | Low | State limitations in output + docs; treat as triage, not proof |
| R3 | #6 Info flows | Variable-encoded canary tokens are not text-searchable | Med | Low | Optionally co-embed a Watermark comment for remote-searchability; document the tradeoff |
| R4 | #12 Param | Rate limiting / pagination under GH code-search limits | Low | Low | throttle ~1/s, page through results |

## 4. Vulnerability check
- **Not vulnerable to:** single-user no-commons (fine), no escalation.
- **Sensitive to (trap):** *false sense of coverage* (LP #6) — "searched GitHub =
  safe." Defense: hunt output must print its blind spots plainly.

## 5. Proposed next step (needs your go) — SUPERSEDED by obfuscation direction

Build `canary hunt --manifest priv.json` (LP #6, the high-leverage add) that:
1. Reads token literals from the private manifest.
2. Queries `gh search code` per token (fallback: REST API).
3. Prints grouped **theft candidates** + a plain-language coverage caveat.
4. (Later) co-embed Watermark comments so more tokens are remotely searchable.

Not started — awaiting direction. The current local `verify`/`check` stay as-is;
`hunt` is additive.

---

## 6. Revised direction (user-named): CODE OBFUSCATION + fused canary watermark

**User direction (verbatim):** code obfuscation — "intentionally transforming source
code to make it difficult for humans or automated tools to understand, while
preserving its original functionality," to protect IP, prevent reverse engineering,
deter tampering.

**The measurement that drives it (this session):** the canary as a plain comment +
variable marker is **self-identifying** (`canary_` / `_CANARY_` / `# Internal
validation` are trivially greppable) and a naive refactor-strip took **5/5 → 2/5**
tokens. Any real obfuscation/renaming/reformatting → 0. So the fingerprint and the
obfuscation must be ONE mechanism, not two.

### The synthesis (keeps fair-source honest)
- **Published, readable source** = the OPL artifact. Not obfuscated.
- **Delivered/bytecode artifact** = obfuscated; the **canary is fused INTO** the
  transform (identifiers renamed to token-derived values, constants/strings
  encoded carrying token material, dead-code branches that look real but hash to
  the token). The fingerprint survives *because it is part of the obfuscation*,
  not a comment on top of it.

### Design (new capability)
A stdlib-only `canary obfuscate` (or `obfuscate.py`) that:
1. Parses the source AST.
2. **Renames identifiers deterministically from the token secret** — so the
   fingerprint is the name, not a removable comment. Renaming changes the source
   but preserves behavior → the name hash is the persistent mark.
3. **Encodes string/constant literals** (e.g. base-64/rot) so scanning for plain
   business strings doesn't expose the token.
4. **Injects token-surfaced dead-code branches** that look like real logic but
   carry the token in a non-obvious literal/comparison.
5. Writes the obfuscated output + updates the manifest with the new recovery key.

### Leverage
LP #4/#5 (rules/self-organization) — fusing the mark into an identifier-remap +
literal-encode changes the whole game: stripping it = stripping the behavior, so
removal is no longer a one-line grep. LP #6: the fused token still makes remote
whack-a-mole (`hunt`) meaningful for the transformed artifact.