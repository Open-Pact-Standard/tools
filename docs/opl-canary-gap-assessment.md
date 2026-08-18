# Canary Token — Gap Assessment Plan

**Context:** Pushing the bounds of the canary token as a *product* before it's
presented to a first user. Method: product-gap-assessment skill — build a real
repo, walk the lifecycle, severity-tier every finding.

## Confirmed findings (severity-tiered)
- **G1 · HIGH — no `-V` / `--version` on the canary CLI**
  - **Where:** `canary_embedder.py` argparse (subparsers only, no version option).
  - **Impact:** scriptability + version-consistency. `canary_embedder.py -V` →
    `error: unrecognized arguments: -V`. The tool's version (1.4, from
    `tools/_version.py`) is not surfaced. Every CLI should answer `-V`/`--version`,
    and it must agree with the `OPL-1.4` / distribution concept.
  - **Fix plan:** add `-V`/`--version` to both `canary_embedder.py` and
    `canary_check.py`, printing the tools version + the OPL version it enforces.
  - **Verify:** `canary_embedder.py -V` → `OPL-1.4 tool v1.4`; exit 0.

- **G2 · MEDIUM — malformed manifest → raw Python traceback**
  - **Where:** `canary_embedder.py` `cmd_check` (`json.load(f)`, line ~602).
  - **Impact:** feeding a corrupt/truncated manifest to `check --payload` dumps a
    full traceback, not a clean error. Hostile/user error handling.
  - **Fix plan:** wrap `json.load` in try/except → clean `cannot parse manifest at <path>`.
  - **Verify:** `check --payload <{bad json}>` → clean error, exit 1, no traceback.

## Healthy (no finding)
- `check --payload <missing>` → clean, helpful message (no crash).
- `embed --source <missing>` → clean `not a directory`.

## To-still-check (walk the rest of the journey)
- [ ] `-V`/`--version` present on ALL subcommands' parent
- [ ] version string consistency across tools
- [ ] `evidence` subcommand on a malformed manifest
- [ ] `verify` on a manifest with corrupted canary tokens
- [ ] competitive positioning (origin-crypto-sdk relationship already answered)

---
## WALK RESULTS (live)
- **G1 CONFIRMED** — `canary_embedder.py -V` → rc=2, `unrecognized arguments: -V`.
- **G2 CONFIRMED** — `check --payload <{bad json>` → full traceback (json.load).
- **G3 (missing manifest) CLEAN** — helpful message, no crash.
- **G5 (missing source) CLEAN** — "not a directory".

## Execution order
1. G1 (version flags) + G2 (traceback) — the two real gaps.
2. Walk remaining journey steps.
3. Full sweep: suite + ruff, then commit.

## RESOLVED
- **G1 FIXED** — `-V`/`--version` added to `canary_embedder.py` and `canary_check.py`;
  both print `OPL-1.4 ... v1.4` (from `tools/_version.py`). Guarded by
  `test_cli_version_flag`. Verified live (real output above).
- **G2 FIXED** — added `_load_manifest()`; all 5 manifest reads (check/verify/
  evidence/build-merkle/fingerprint) now route through it. Malformed JSON →
  clean `Error: cannot parse manifest at <path>` + exit 1, no traceback. Guarded
  by `test_malformed_manifest_errors_cleanly`. Verified live across all subcommands.
- **Full journey re-walked after fixes:** embed → check green → modify → drift red,
  all clean. 508 tests / 97% / ruff clean.