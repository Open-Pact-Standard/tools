# Canary hunt + evidence gate — Systems-Thinking Audit (F1 …)

**Date:** 2026-08-18 · **Lens:** Meadows leverage ladder
**Subject:** `cmd_hunt` / `_gh_search_code` / `verify_evidence_gate` in `canary_embedder.py`
**Method:** read the actual code; probed the live behavior, not assumptions.

---

## Verified-healthy (background, not findings)
- `verify_evidence_gate` reads `source_files` as filename→hash STRING (the real
  schema), computes the current file hash, and only flags `merkle_proven: True`
  when it matches the recorded fingerprint. Behavioral proof: verbatim same-path
  copy → proven; renamed file → lead. Correct LP#8 balancing behavior.
- `hunt` coats candidates as LEADS, always points to verify+evidence to close a
  claim, and refuses to claim safety past the public-repo-triage reality.

---

## Findings (severity-ranked, leverage-cited)

| # | LP | Gap | Severity | Effort |
|---|----|-----|----------|--------|
| **F1** | **#6 Info flows** | **Search-tool health is invisible:** when `gh` is missing OR errors (rate/network/auth), `hunt` collapses to the SAME "No copies found on GitHub code search" + exit 0 as a genuine clean search. The mechanism's own liveness is not surfaced. A user is told "not found in public GitHub" when the truth is "no search ran." | **CRITICAL** (false-safety) | Low |
| F2 | #6 Info flows | `Hunt` prints the SAME exit-0 / no-copies message for 3 wildly different states (clean search / tool missing / tool errored). No way to distinguish them programmatically (harness/CI reads exit code 0 as "clean"). | HIGH (scriptability) | Low |
| F3 | #8 Balancing | No **count/diffing gate on hunt results** — a repo name matching the owner's own (or a fork the owner knows about) is reported identically to an unknown thief. No allowlist/filter and no explicit "this matched YOUR own repo" hint. | MEDIUM (false-positive) | Med |

**Discharged (verified data flow, not a gap):** `verify_evidence_gate`'s
`source_files` shape was already correct; `hunt` short-tokens/no-tokens/manifest-
missing all give distinct clean errors (tested in earlier suite).

---

## Division of labor (decision, 2026-08-18)
- **Litigation = REACTIVE.** The case for court is: owner suspects theft → **retrieves
  the code** → `verify` proves provenance → `evidence` assembles the Merkle-backed
  package. This is what is packaged and advertised (Studio `canary` = embed+sign via
  origin-canary; site "Canary Enforcement" = embed + drift-check on CI).
- **`hunt` = a spare tool, NOT packaged.** Keep it in the source as a CLI subcommand
  for an owner who wants to proactively probe public code hosts, but do not promote it
  as a product/packaging target yet (false-safety risk, coverage limits, owner/fork
  filtering unresolved). It is intentionally absent from the Studio adapter catalog,
  the site Tools tab, and READMEs.

---

## F1 in detail (the one that matters)
**Operational proof (this session):** a private manifest embedded, then `hunt` run
with `gh` removed from `PATH` →
```
No copies found on GitHub code search.
  ⚠ BLIND SPOTS (this is NOT proof of no theft):
   • code search indexes PUBLIC GitHub repos only
   ...
  A 'no match' here means 'not found in public GitHub' — not 'safe.'
```
exit 0. But `gh` **never ran**. The blind-spot boilerplate — which is *meant* to
prevent false safety — becomes itself the false-safety message, because it's
printed for a non-search too.

**Structural cause:** `_gh_search_code` returns `[]` both for "tool absent" and
"tool failed" and for "genuinely no hits," erasing the distinction before `cmd_hunt`
ever sees it (LP#10 stock-flow: the mechanism's liveness is dropped at the boundary).

**Leverage:** this is the single most valuable fix in the subsystem — it's the
difference between a triage net that honestly bounds its coverage and one that
tells a user "no theft found" when it did nothing.

---

## Phased improvement plan (promote-and-retire, not rewrite)

**Phase 0 (F1, alpha-blocking — LOW effort, HIGH leverage):**
Make `_gh_search_code` return the tool state, not just matches:
- Return a `(status, matches)` where status ∈ {`ok`, `no_tool`, `error`, `empty`}.
- `cmd_hunt` must NOT print "No copies found" / exit 0 when status is
  `no_tool` or `error` — instead print a distinct, loud message
  (`gh is not installed on PATH` / `GitHub search failed (rate-limited / auth / network)`)
  and exit non-zero.
- Add a regression guard: hunt-with-gh-missing must NOT print "No copies found"
  and must exit != 0.

**Phase 1 (F2, MED):** expose status machine-safely — think a `--json` flag so a
harness/CI can tell "clean search" from "couldn't search" from "found candidates"
via the exit code + a status field, not by parsing prose.

**Phase 2 (F3, MED):** allow owner/fork filtering — `--ignore-repo` (repeatable)
and a note when a match's repo equals the project's own remote (`git remote -v`),
so an owner isn't alarmed by their own tree.

**Deferred (not now):** REST fallback for CI without `gh` (nice, but only once a
real second consumer needs it — Ponytail rule); multi-host search (GitLab/Bitbucket)
(defer until a measured non-GitHub theft shows up).

---

## Decisions
- F1 is **alpha-blocking**: a false-safety on the proactive enforcement loop is the
  exact gap this subsystem exists to avoid. Fix before presenting "hunt" to a pilot.
- F2/F3 are hardening once F1 lands.

*Analysis only — implementation gated on user direction to improve.*