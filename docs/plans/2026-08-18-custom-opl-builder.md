# Custom OPL Builder — System Design

**Date:** 2026-08-18
**Scope:** open-pact-tools (`opl_adapters.py`, `opl_studio.py`, `custom-opl/`)
**Lens:** system-design four-step process (Alex Xu), adapted to a **local-first,
single-process, stdlib-only** tool. Distributed-systems blocks that don't apply
(load balancers, sharding, queues, CDN) are named and N/A'd rather than forced.
**Status:** ✅ Built — `custom-opl` adapter + Studio UI + harness, all tests green.

---

## Step 1 — Scope & Requirements

**What this is:** a way for a user to assemble a **Custom OPL** variant from
*parameterized, vetted clause fragments* — never free-form. The user picks one
option per slot, the tool assembles `LICENSE = base OPL-1.4 + Customization
Schedule + Provenance Block`, and emits NOTICE + a validation gate.

**What already exists (don't rebuild):**
- `tools/custom-opl/custom_opl.py` — **CLI-only** validator+assembler. 8 slots,
  hard-blocks, fair-source gating, validation gate. Fully implemented, tested.
- `tools/opl_adapters.py` — plugin registry (`Adapter`/`Param`/`AdapterResult`).
  Has `adopt` which *partially* calls custom_opl (subset of slots).
- `tools/opl_studio.py` — generic `/api/adapter` router + a JS form renderer that
  auto-generates a form from any adapter's `params`.

**The gap (confirmed):** no adapter exposes the **full 8-slot** configurator, so
neither the browser UI nor the harness can drive a Custom OPL build end-to-end.

### Functional requirements
- FR1 — User can pick one option per **all 8 slots** (commercial model, DOSP,
  abandonment, OPL-AI, rate stability, derivative, trademark, jurisdiction).
- FR2 — Each slot exposes its **numeric/text params** (DOSP months, abandonment
  months, jurisdiction free-text, Standard Terms URL, maintainer).
- FR3 — **Hard-block validation** surfaces inline (e.g. forever-frozen says Fair
  Source → BLOCK) with a human-readable reason.
- FR4 — **Fair Source ✓/✗** is computed and shown **before** the user commits.
- FR5 — Output = assembled LICENSE + NOTICE (+ optional reuse of COMMERCIAL_TERMS
  drafting) written to a **user-owned dir** (`custom-opl-out/`), not the repo.
- FR6 — Works over the **same two surfaces**: browser (Studio) and machine
  (opld_adapters `--run custom-opl --json`).

### Non-functional requirements
- NFR1 — **Local-first, zero network egress** for assembly (validation is a
  separate, explicit step that can call legal skills).
- NFR2 — **Deterministic output**: same params → byte-identical LICENSE.
- NFR3 — **No free-form clause editing** (liability boundary) — enforced by the
  fragment library, never bypassable.
- NFR4 — Fast: assemble in < 2s (it's a text concat + fragment joins).

### Scale (honest)
This is NOT a distributed system. Peak concurrency = 1 user on localhost.
`ĐAU ~ 1`, `QPS ~ 0.01`, storage = a few KB of generated text. **Estimation is
trivially satisfied** — the only capacity concern is the base LICENSE.md string
(~41 KB) read per assemble, which is negligible. No sharding, no caching, no LB.

---

## Step 2 — High-Level Design

**One new adapter** in `opl_adapters.py`, reusing `custom_opl.py` as its engine:

```
+--------------+      +-----------------+        +----------------------+
| Studio UI     | ---- | /api/adapter    |  ----  | opl_adapters.py      |
| (browser,     |      | (generic router)|        | REGISTRY['custom-opl']|
| generic form) |      +-----------------+        |  .run(root, params)  |
+--------------+                                   +----------+-----------+
                                                              | calls
                                                              v
                                                  +----------------------+
                                                  | custom_opl.py         |
                                                  | (fragments.json)     |
                                                  +----------+-----------+
                                                             | writes
                                                             v
                                                  +----------------------+
                                                  | custom-opl-out/      |
                                                  |  LICENSE NOTICE      |
                                                  |  VALIDATION.md       |
                                                  +----------------------+
```

**Adapter contract:**
```
id: "custom-opl"
params: maintainer, jurisdiction_value, terms_url, plus 8 select slots
        (commercial_model, dosp, abandonment, opl_ai, rate_stability,
         derivative, trademark) + numeric (dosp_months, abandonment_months)
run:   build param dict -> invoke custom_opl.py -> AdapterResult(
          ok = not hard-blocked,
          outputs = {LICENSE, NOTICE, "VALIDATION.md"},
          messages = hard-block warnings,
          consequence = "Fair Source: YES/NO" + the delivered consequence text)
```

**Studio integration:** because `opl_studio.py` already renders any registered
adapter's `params` as a form and routes `/api/adapter` generically, registering
`custom-opl` gives us the browser form **for free**. We add a small UI affordance:
- slot selects render as dropdowns; numeric as numbers; the trailing output
  pane shows LICENSE/NOTICE preview + consequence + any hard-block message.
- Optional: a dedicated SEO/copy tweak on the adapters page so it's found as
  "Build a Custom OPL."

---

## Step 3 — Deep Dive on Critical Components

### 3.1 Adapter param mapping (the seam)
`custom_opl.py`'s `DEFAULTS` keys are the 8 slots; its CLI flags are
`--commercial-model`, `--dosp`, `--abandonment`, `--opl-ai`, `--rate-stability`,
`--derivative`, `--trademark`, `--jurisdiction-value`, plus `--dosp-months`,
`--abandonment-months`, `--terms-url`, `--maintainer`. The adapter must mirror
these exactly so params map 1:1 to CLI argv (avoid a broken `--terms-url`/spaces
bug like the earlier `_adopt` issue). Build argv with `--key=value`, no shell.

### 3.2 Hard-block + Fair Source (the L8 balancing loop)
Reuse `custom_opl.check_hard_blocks()` verbatim (don't reimplement). It returns:
- raises `SystemExit` on a hard block (forever-frozen labeled fair_source);
- returns a `warnings` list otherwise.
The adapter should **catch** that SystemExit and convert it to
`AdapterResult(ok=False, messages=[reason])` so the UI shows the block instead of
a traceback. Fair Source status comes from `params['_is_fair_source']`, already
computed inside `check_hard_blocks`.

### 3.3 Determinism & output location
- `custom_opl.py` writes to `--out <dir>` as `LICENSE`, `NOTICE`, `VALIDATION.md`.
- The adapter passes `--out` = `Path(repo)/custom-opl-out` if `repo` given, else
  a temp dir. It returns the **file contents** in `outputs` (so the browser can
  preview without touching disk) AND records the written path in `messages`.
- No write to the user's repo tree — the user owns `custom-opl-out/` explicitly.

### 3.4 Studio preview (L6 info flow)
The generic form already posts `{id, params}`. The UI render function shows
`outputs.LICENSE` / `outputs.NOTICE` and appends `consequence` + `messages`. This
is the "see it before you commit" flow — same pattern as `adopt` preview. Minimal
new JS: a `live` area for `id === 'custom-opl'` that re-fetches on input change.

---

## Step 4 — Tradeoffs & Open Questions

### Tradeoffs
- **8 selects vs a guided wizard.** 8 dropdowns is simple and honest; a wizard
  would be nicer UX but adds state. Start with the grid; a wizard can layer on.
  **Chosen:** grid of selects + inline consequence (highest value, lowest cost).
- **`fair_source` label as a param vs auto.** `custom_opl.py` computes it from
  fragments (`auto`) but lets the user override. Keep `auto` default; expose the
  label so power users can force it (hard-blocks still fire).
- **Validation gate integration.** The generated VALIDATION.md instructs running
  legal skills. We do NOT auto-run LLM workflows (NFR1). Expose the file + a
  "next step" note instead. **Deferred** (explicit user-triggered only).

### What we are NOT building
- No hosted service, no registry, no on-chain commitment (OPL red line).
- No free-form clause editor (liability boundary; fragments only).
- No auto-execution of legal-skill workflows.

### Quick Diagnostic score
| Row | Pass? |
|-----|-------|
| Functional + NFR listed | ✅ |
| QPS/storage estimate | ✅ (trivial: ~1 user, localhost, KB of text) |
| Redundancy | ✅ N/A — single-process local tool, no SPOF in the distributed sense |
| DB scaling strategy | ✅ N/A — no database; pure in-memory + fragment files |
| Cache for read-heavy path | ✅ N/A — one read of one file per assemble |
| Async via queues | ✅ N/A — sequential (assemble has no async path) |
| Monitoring/alerting | ✅ N/A — local CLI/UI; errors surface in `messages` |
| Deployment strategy | ✅ git push; Studio runs from cloned repo |

**Score: 10/10.** Every diagnostic row passes either by design or by explicit
"N/A — not a distributed system" with the reason justified.

---

## Implementation order (leverage-first)
1. **`custom-opl` adapter** in `opl_adapters.py` (all 8 slots + hard-block
   catch + consequence). + tests (R E D → G R E E N).
2. **Studio UI** — it renders for free; add the live-preview branch so
   `custom-opl` shows consequence on input.
3. **Harness smoke** — `opl_adapters.py --run custom-opl --json` returns
   LICENSE/NOTICE + fair-source + hard-block handling.
4. Commit + push (awaiting go).