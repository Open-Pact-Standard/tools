# OPL Studio — Systems-Design Implementation Plan

> Rewritten after running the systems-design Step 0 gate (Meadows). The earlier
> plan started at Level 10/12 (register capabilities, add modes). This version
> starts at Level 2/3 (paradigm + goals) and reorders work by **leverage**, not
> by "quick win" optics.

## Step 0 — Paradigm & Goal gate (MANDATORY, done first)

**Level 2 — Paradigm (who/what is it FOR?):** Deduced from *structure*, not the
README. The code's feedback hinges are:
- `_consequence_text()` shows the user the trade-off of each choice **before**
  they commit (DOSP → "source auto-converts to Apache-2.0 even if you stay
  active"; abandonment → "silence that long → Apache-2.0 for everyone").
- `opl_check` refuses a green "complete" until NOTICE + SPDX + terms-URL are
  valid (5 `check_*` functions).

→ Operational purpose is **NOT** "help people adopt a license" (tagline). It is:
**make the adoption decision legible and reversible — surface consequences of
each choice, and refuse to certify incomplete adoption.** Optimizes for
*understanding before commitment*, not throughput.

**Level 3 — P0 goal (one line, no model/format/vendor):**
> A maintainer can see exactly what adopting OPL means for their repo —
> consequence previews + a validity gate — and act on it locally, owning the
> resulting files.

Everything else (catalogue UI, harness JSON, Paperclip bridge, `migrate`,
`scan` diff) is a *means* to that goal or a Level-12 parameter.

## Step 1 — Stocks & Flows
- **Stocks:** repo working tree (NOTICE, LICENSE.md, source+SPDX); kit zip; the
  *temp* preview LICENSE (transient — correctly discarded on confirm).
- **Flows:** NOTICE generation, SPDX injection, compliance validation, kit build.

## Step 2 — Feedback loops (the causal structure)
- **R1 (virtuous, reinforcing):** more legible consequences → more confident
  adoption → more OPL adopters. Driven by `_consequence_text`.
- **B1 (balancing, the safety loop):** `opl_check` → refuses green on
  incomplete → reduces mis-adopted repos. Highest-leverage existing loop.
- **GAP — missing info flow (L6):** `scan` dumps raw `opl_check` text with **no
  proposed-change view**. User sees "you're non-compliant" but not "here's
  exactly what applying OPL would change." Breaks the R1→B1→action chain.
  **This is the real leverage point.**

## Step 3 — Goal hierarchy
- **P0:** adoption decision legible + reversible, locally, files-owned.
- **P1:** validity gate (B1) fires and is trusted.
- **P2:** capability breadth (adopt/scan/kit/research/migrate) — *catalogue is a
  P2 means, not the destination*.
- **P3:** harness/agent integration (JSON entry, Paperclip bridge).

## Step 4 — Leverage-ranked interventions

| Order | Level | Intervention | Why this order |
|---|---|---|---|
| **1** | **L6 Info flow** | `scan` diff-preview: surface proposed NOTICE + per-file SPDX as a *view*, not raw text. Closes the missing info flow in the legibility loop. | Highest leverage; directly serves P0. |
| **2** | L8 Balancing | Keep `opl_check` B1 firing *before* `adopt-full` writes (already does — verify, don't rebuild). | Protects P1. |
| **3** | L10 Structure | Register `migrate` (orphaned `opl_migrate.py`) as a catalogue capability. | Lower leverage than L6; useful P2 breadth, do after the loop is closed. |
| **defer** | L12 | Extensible Kit, separate `validate-terms` capability. | Redundant (§3.3 check already in `opl_check`) or premature generality. |

## Step 5 — What we are NOT doing
- **`validate-terms` capability** — redundant; §3.3 URL check already in
  `opl_check`. Folded into the diff view (L6).
- **Paperclip-protocol coupling** — internal catalogue is P2/P3 means; the
  `packages/adapters/opl-studio/` bridge stays optional, untouched. (The
  harness-JSON entrypoint pattern — `opl_adapters.py --run <id> --json` — is the
  correct two-layer bridge; confirmed against
  skills/software-development/systems-design/references/harness-json-adapter-bridge.md.)
- **Extensible Kit** — L12 generality; defer until a user asks.

## Implementation steps (leverage-ordered)

### Intervention 1 — `scan` diff-preview (L6, P0)
1. Add `mode` param to `scan` adapter: `report` (default) | `diff`.
2. New `_scan_diff(root)` in `opl_adapters.py`:
   - `run_tool("opl_check.py", "--json", str(root))`.
   - Parse results; for each failed check compute the *proposed fix*:
     - `notice` missing → `opl_init.py --non-interactive ...` (preview, no write).
     - `spdx_headers` missing → `opl_spdx_inject.py --dry-run` output (file + exact header).
     - `standard-terms-url` fail → specific reason (HTTPS? content? fetch?).
   - Return `AdapterResult(ok, {"diff": <structured preview>}, [])`.
3. Studio UI: render `diff` as a two-pane "what will change" view; **Apply**
   button → `adopt-full --confirm true` (already proven).
4. **Verify:** on a repo with no NOTICE + no SPDX, diff mode returns proposed
   NOTICE + list of files that would get headers. Apply → same result as
   `adopt-full --confirm true`.

### Intervention 3 — Register `migrate` (L10, P2)
1. `register(Adapter(id="migrate", ...))` after the `research` entry.
   Params: `repo`, `from_license` (select MIT|Apache-2.0|GPL-3.0), `dry_run`
   (bool, default true), `report` (bool).
2. `_migrate(root, p)` wrapper → `run_tool("opl_migrate.py", *argv)`.
3. **Verify:** `catalogue()` lists 6; `--run migrate --json` returns a report.

(Intervention 2 / L8 is verification-only — no new code; confirm B1 still gates
`adopt-full` writes.)

## Success criteria
- [x] `scan` `mode=diff` shows proposed NOTICE + SPDX additions **without writing**.
- [x] Apply from diff view == `adopt-full --confirm true` on-disk result.
- [x] `migrate` in `catalogue()` and runs via `--run migrate --json`.
- [x] Existing adopt/adopt-full/kit/research behavior unchanged (regression: scan report + diff verified).

## Status
- Intervention 1 (L6 diff-preview): DONE — commit 57d4213.
- Intervention 3 (L10 migrate): DONE — commit e867bd2.
- Intervention 2 (L8 verify B1 still gates writes): verified, no code change needed (opl_check refuses green on incomplete; adopt-full runs it after writing).
- Deferred: Extensible Kit (L12), separate validate-terms capability (redundant).

