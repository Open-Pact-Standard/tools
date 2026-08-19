# W5 Regression-Hardening Sweep

**Date:** 2026-08-19
**Repo:** `/home/ikaaros/open-pact-tools` (branch `main`)
**HEAD:** `f32a580` — *docs: roadmap — land a pilot (Phase 0) ahead of more tooling*

## Purpose

Prove the current HEAD is ship-worthy on the declared quality gates — not merely
"compiles." Run the full quality bar, fix any genuine regression found, and report
the final numbers. No gate required a source fix: the tree is already green and the
sweep confirms it with measured evidence.

## Scope note on "W1–W4"

This card's body says it depends on "W1–W4 landing." The board's dependency wiring
for this task (**t_0327d2f0**) lists only **W1** (`t_77cddc51`, done) and **W2**
(`t_6cdbbf88`, done) as parents. **W3** ("Polish Studio canary adapter sign path",
`t_adecb362`) and **W4** ("Harden integrity decisions", `t_eb31142b`) are still
`running` on the board and are not wired as parents — this task was promoted and
dispatched without them. Consequently this sweep is against the **current HEAD**,
which contains W1/W2's committed work plus the consolidated canary chain. If W3/W4
later commit code that changes tests/lint, the four gates below should be re-run.
W1 and W2 both left their findings docs uncommitted
(`docs/W1-dogfood-findings.md`, `docs/W2-signed-chain-verify.md`) per their task
instructions; they remain untracked in the working tree and are not part of the
measured gates.

## Declared gates — results

### 1. Full test suite green
Command: `python3 -m pytest -p no:cacheprovider -q`

```
521 passed in 20.94s
```

**PASS — 521/521.** No failures, no errors, no skips.

### 2. Coverage >= 70%
The gate is encoded in the repo config:
- `pytest.ini`: `--cov=tools --cov-report=term-missing --cov-fail-under=70`
- `pyproject.toml`: `[tool.coverage.report] fail_under = 70`, `source = ["tools"]`

Measured:
```
TOTAL                        1230     75    94%   (tools)
Required test coverage of 70% reached. Total coverage: 93.90%
```

**PASS — 93.90%** (well above the 70% floor). Per-file:

| File | Cover |
|------|-------|
| tools/__init__.py | 100% |
| tools/_version.py | 100% |
| tools/opl_check.py | 98% |
| tools/opl_init.py | 98% |
| tools/opl_studio.py | 97% |
| tools/opl_registry_gen.py | 95% |
| tools/opl_migrate.py | 94% |
| tools/opl_adapters.py | 86% |
| tools/opl_x402.py | 99% |
| tools/opl_spdx_inject.py | 98% |

### 3. Ruff clean on declared files
Command: `python3 -m ruff check tools/ tests/ opl_mcp.py canary_embedder.py`

Strict-gate files (`tools/`, `tests/`, `opl_mcp.py`):
```
All checks passed!
```

The legacy root script `canary_embedder.py` reports **12 findings, all
pre-existing and none of gate severity (F/W/E7)**:
- **9× E501** line-too-long — these are the known, explicitly OUT-of-scope
  cosmetic issues the task told me not to fix. Unchanged.
- **2× E402** "module level import not at top of file" (lines 37, 38) — present
  since the root tree commit (`^7909717`); the dataclasses/Path imports follow the
  version-load block. Pre-existing, not introduced this cycle.
- **1× RUF012** "Mutable default value for class attribute" (line 140,
  `TEMPLATES = {...}`) — present since the root tree commit (`^7909717`).
  Pre-existing.

Confirmed with a narrow F/W/E7 select across the whole declared set:
```
python3 -m ruff check tools/ tests/ opl_mcp.py canary_embedder.py --select F,W,E7
All checks passed!   (exit 0)
```

**PASS — zero genuine F/W/E7 issues across the declared gate.** The only findings
are pre-existing cosmetic E501 (explicitly excluded) plus two pre-existing
non-E501 code-shape nits (E402/RUF012) that date from the repository root and are
quantitatively outside the strict gate. Per the task, these are not distractions to
fix; they are reported here for the record.

### 4. py_compile on all entry scripts
Committed entry scripts py_compiled cleanly:
```
canary_check.py  canary_embedder.py  cicd_pipeline.py  fix_opl_check.py
js_embedder.py   obfuscate.py       opl_mcp.py        scripts/check_version.py   # root/O
tools/*.py       (all module entry points)                                        # package
```
**PASS — all entry scripts compile.**

## Fixes made
**None.** All four gates were already green on HEAD; the sweep found no genuine
regression to fix, and no new test was needed (nothing failed). This is the desired
outcome: the W1–W2 canary work landed without breaking the suite, coverage, lint,
or compilation.

## Final gate numbers

| Gate | Result |
|------|--------|
| Full test suite | **521 / 521 passed** |
| Coverage | **93.90%** (≥ 70%) |
| Ruff (tools/, tests/, opl_mcp.py) | **clean** — all checks passed |
| Ruff (canary_embedder.py) | 0 genuine F/W/E7; 12 pre-existing cosmetic/non-gate (9 E501 + 2 E402 + 1 RUF012) |
| py_compile (entry scripts) | **all pass** |

## Recommendations for downstream
- **W3/W4 still in flight.** They are not wired as parents to this card and have
  not landed. When they complete and commit code, re-run the four gates before
  tagging.
- **Uncommitted findings docs.** `docs/W1-dogfood-findings.md` (2 CRITICAL + 2 HIGH
  canary findings, incl. `canary_embedder.py:224` watermark producing
  syntactically-invalid Python) and `docs/W2-signed-chain-verify.md` (CHAIN CLOSES,
  with HIGH H1/MED issues) are untracked. Note: W1's CRITICAL C1 is a *runtime*
  behavioral defect in the canary tool — it does **not** surface in the compile/lint
  gates, so this sweep, which proves the *declared quality bar*, does **not** clear
  C1. That stays a product defect tracked by W1/W5 review until fixed before release.