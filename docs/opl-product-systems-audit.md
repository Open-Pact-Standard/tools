# OPL Product — Systems-Thinking Audit (grounding check)

**Date:** 2026-08-18
**Lens:** Meadows leverage-point ladder (systems-thinking-audit)
**Scope:** the OPL user-facing product surface — adoption (adopt-full), canary
enforcement, Studio server, MCP server, custom-opl builder
**Note:** this is a **grounding** audit done behaviorally (probed the running
system), not a re-run of the test suite. It answers "is the product solid enough
to hand to a pilot?" — not "do the tests pass?" (they do.)

---

## Map of the system

- **Stocks:** the user's repo (tree, NOTICE, LICENSE.md, SPDX headers), the
  canary manifest pair (private secrets + public Merkle payload), adoption files.
- **Flows:** adopt (write NOTICE/LICENSE/SPDX), canary embed, drift-check,
  compliance scan.
- **Feedback loops:**
  - **B1 (integrity / balancing):** canary drift-check fails red on change →
    maintainer reconciles → license stays honest. → **Verified working** (exit 1
    on drift, exit 0 on unchanged).
  - **B2 (correctness / balancing):** `opl_check` refuses green until
    LICENSE/NOTICE/SPDX valid. → **Had a hole in the write path** (see F1,
    fixed & re-verified 5/5).
- **Boundary (controllable vs observable):** the tools control files the user
  owns. The browser/MCP control nothing beyond what the adapters accept.

---

## Findings (leverage-ranked)

| # | Leverage | Gap | Severity | Effort |
|---|----------|-----|----------|--------|
| **F1** | **LP5 Info flow** (write path) | `adopt-full` reported success without writing `LICENSE.md` (preview-only license); repo left non-compliant while `consequence` admitted it and returned `ok:true`. | **HIGH** | **FIXED** in `480bab0`; re-verified opl_check 5/5 |
| **F2** | **LP8 Balancing** (MCP root) | MCP server passed `root=None` to repo-based tools, so `scan`/`adopt-full`/`migrate` failed through MCP even with `repo` given. The drift-check loop was unreachable via the harness surface. | **HIGH** | **FIXED** in `480bab0`; MCP scan returns output |
| **F3** | **LP10 Structure** (orphaned parallel implementations) | Root-level `js_embedder.py`, `cicd_pipeline.py`, `fix_opl_check.py` are **outside** the declared lint/test gate, duplicating canary logic that also lives in `tools/`. Risk: drift between two sources of truth. | **MED** | Medium |
| **F4** | **LP5 Info flow** (arbitrary path) | `/api/adapter` + MCP accept any `repo` path → can scan/read any local dir the process can see. Localhost-only mitigates reach, but a harness gets broad read access. | **MED** | Medium (a `--allow-path` root)
| **F5** | **LP8 Balancing** (canary modifies source) | `embed` **writes tracking tokens into the repo it fingerprints** (WatermarkEmbedder). This is *by design*, but it means fingerprinting is not side-effect-free — a user must expect their tree to change. Not currently surfaced to the user before embed. | **LOW-MED** | Low (print a warning)

---

## Verified healthy (no action)

- Studio binds `127.0.0.1` loopback only — not exposed to the network. ✓
- Kit path traversal blocked (404 on `../..` and URL-encoded attempts); legit fetch 200. ✓
- Canary public payload contains **no** secret salt / no canary secret (verified live). ✓
- `adopt-full` defaults `confirm` to no-write (destructive write never implicit). ✓
- Canary drift-check works symmetrically (drift→exit 1 red, unchanged→exit 0 green). ✓
- Adoption produces a genuinely compliant repo (opl_check 5/5 after later fix). ✓

---

## Phased recommendation (promote-and-retire, no big-bang)

- **Phase 1 (done):** F1, F2 — the two alpha-blocking findings are fixed and
  regression-guarded.
- **Phase 2 ✅ (done, F5):** pre-embed notice now printed before any file is
  modified — "embedding distributes tracking tokens across files and modifies
  them; review before committing." Confirmed live + regression-guarded.
- **Phase 3 (F3, by trigger not default):** when a second consumer of canary
  logic appears, consolidate `js_embedder.py`/`cicd_pipeline.py`/`fix_opl_check.py`
  into `tools/` or state explicitly they are legacy-docs-only. **Defer** until a
  real second input forces it (Ponytail rule) — deleting/deduping working legacy
  now is churn, not leverage.
- **Phase 4 (F4, only if a multi-tenant/cross-user surface appears):** add a
  `--allow-path` sandbox root to the adapters/MCP. **Defer** — localhost-only
  today.

---

## Verdict

The product is **grounded enough to pilot**, not to scale. The two things that
would have genuinely broken a first user (adopt not writing a license; harness
unable to run repo tools) are found and fixed *because* it was dogfooded. The
remaining items (F3 orphaned scripts, F5 embed-side-effect surprise, F4
arbitrary-path breadth) are quality/debt items — none is pilot-blocking, and F5
is a 10-minute fix worth doing before a real user hits it.

**Standing gap (unchanged):** no *named* pilot. The product now survives a real
user; the open question is who that user is.