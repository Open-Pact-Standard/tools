# OPL Studio — Systems-Thinking Audit

**Component:** Open-Pact License Studio (tools/opl_adapters.py + opl_studio.py + custom-opl/custom_opl.py + custom-opl/opl_spdx_inject.py + packages/adapters/opl-studio/)
**Lens:** Donella Meadows’ *Thinking in Systems* leverage-point ladder (see skills/software-development/systems-thinking-audit).
**Status:** Audited + all findings fixed (commit 6e3f208).

---

## 1. System map

- **Stocks (state):** repo working tree (`NOTICE`, `LICENSE.md`, source files + SPDX), the kit zip (`adoption-kit/dist/opl-adoption-kit.zip`), the *temp* Custom LICENSE (preview is discarded on confirm).
- **Flows (transformations):** `adopt-full.run()` → (1) `make_kit.py` builds kit, (2) `_adopt(preview)` assembles NOTICE+LICENSE, (3) if `confirm`→ `_adopt(write)` writes NOTICE + `opl_spdx_inject`, (4) `opl_check` validates. CLI entry (`opl_adapters.py --run ... --json`) parses params into the pipeline.
- **Reinforcing loops (R):** the consequence text shown to the user before confirming (informs choice). Note: one-shot — not re-shown on the write path.
- **Balancing loops (B):** `opl_check` read-only validator that refuses a green "complete" until the repo is actually license-compliant (NOTICE present, SPDX present, LICENSE.md present). This is the emergency restorative loop.
- **Information flows:** adopt-params → `NOTICE` (via `opl_init.py`); adopt-params → Custom LICENSE (via `custom_opl.py`); write-flow → SPDX injection (`opl_spdx_inject.py`); scan result → `{ok, opl_check, ...}` in the harness JSON.

## 2. Findings (severity by leverage, not ease)

| # | LP | Gap | Severity | Effort | Fix |
|---|----|------|----------|--------|-----|
| **F1** | **#3 Goals** (paradigm/purpose) | `opl_adapters.py` docstring + `opl_studio.py` + README + catalogue page copy all framed the **internal plugin registry** as a "Paperclip-style adapter catalogue." I verified the real Paperclip contract (`execute(ctx): Promise<AdapterExecutionResult>`, env-injected identity, TS `@paperclipai/adapter-utils`, declarative `agentConfigurationDoc`) — the Python `register(Adapter(...))` + `run()` shape is an *in-process plugin layer*, not a Paperclip adapter. Mis-attribution poisons every downstream integration decision. | **HIGH** — structural; drove the wrong TS scaffold shape. | M | Relabelled the layer as "internal plugin registry"; documented the real Paperclip adapter as the distinct `packages/adapters/opl-studio/` bridge. |
| **F2** | **#6 Missing info flow** | `terms_url` (a **required** OPL field, §3.3) was accepted by the adopt params and written into `NOTICE` (via `opl_init.py` line 150), but **dropped** when assembling the Custom LICENSE: `_assemble_license()` never passed `--terms-url`, **and** even when passed, `custom_opl.build_schedule()` never rendered the concrete URL into the §3.3 schedule line (it only *referenced* "the URL declared in `NOTICE`"). A user could preview a LICENSE that silently omitted their actual Standard Terms URL. | **HIGH** — silent invalid output. | S | (a) `_assemble_license` now passes `--terms-url`; (b) `build_schedule` renders the concrete URL into the §3.3 block for the `paid_standard_terms` model. |
| **F3** | **#8 Balancing loop (missing/gap)** | `opl_spdx_inject.py --check` reported "All 0 source files have SPDX headers" and exited 0 on a repo with **no detectable source files** (e.g. a binary-only repo: shaders, models, vendored assets). Green-on-empty is the absence of a restorative loop, not its presence. | MED | S | Now exits 1 with "No detectable source files found — cannot verify SPDX headers on an empty tree." |
| **F4** | **#8 Restore-loop gaps (in the Paperclip adapter)** | Three concrete defects in `packages/adapters/opl-studio/src/server/execute.ts`: (a) `SANDBOX_INSTALL_COMMAND = "pip install hermes-agent"` — OPL tools are not on PyPI under that name (wrong package); (b) arg builders used `JSON.stringify` on shell words → produced invalid argv for values with spaces (`--maintainer "Jane <x>"` → `--maintainer "Jane <x>"` with literal JSON quotes); (c) the `toResult` timeout path returned `{ok:false, timedOut:true}` with **no** `opl_check`/stderr, dropping the diagnostic that explains *why* it timed out. | LOW | S | (a) corrected to `pip install "git+https://github.com/Open-Pact-Standard/tools.git"`; (b) arg builders use `--key=value` (no shell); (c) timeout path now surfaces partial stderr + parsed stdout. |

## 3. Behavioral verification (proof, not text)

```bash
# F2: terms_url now flows into the assembled LICENSE
$ python3 opl_adapters.py --run adopt-full --json --repo /tmp/v \
    --maintainer 'Acme <ops@acme.com>' --terms_url https://acme.com/terms --dosp 36
# output contains 'https://acme.com/terms' in LICENSE (Custom OPL)  ✓

# F3: empty / binary-only repo fails --check (was green-on-empty)
$ python3 opl_spdx_inject.py /tmp/binonly --check
No detectable source files found — cannot verify SPDX headers on an empty tree.
# exit=1  ✓

# Python compiles
$ python3 -m py_compile opl_adapters.py custom-opl/custom_opl.py  ✓
```

## 4. Phased improvement plan (promote-and-retire, no big-bang)

- **Phase 0 (done) — relabel (F1):** stop mis-attributing the internal plugin layer to Paperclip.
- **Phase 1 (done) — restore info flow (F2):** terms_url now threads from adopt params → LICENSE §3.3.
- **Phase 2 (done) — strengthen the balancing loop (F3):** empty-scan detection fails fast.
- **Phase 3 (done) — harden the restore path (F4):** correct install command, valid argv, diagnostic on timeout.
- **Phase 4 (future) — re-shown consequence on the write path:** currently the consequence text appears only in the return value, not re-printed before the confirmed write. A future patch could echo it into the write adapter's log so the user sees the trade-offs they're committing to at confirmation time (closes the residual gap in the reinforcing loop).

## 5. Notes / non-findings

- **"Adopted Paperclip pattern" was a false positive by assumption.** Resolved by reading `packages/adapters/pi-local`, `codex-local`, and `hermes` from `paperclipai/paperclip` (cloned to `/tmp/pc_adapter_ref`): the contract is `ServerAdapterModule { execute(ctx): Promise<AdapterExecutionResult>, getConfigSchema, sessionCodec, ... }` with env-injected `PAPERCLIP_RUN_ID`/identity. The opl-studio adapter now mirrors that.
- The internal `opl_adapters.py` `register(Adapter(...))` registry is a fine *local plugin layer*; it simply is not a Paperclip adapter. They coexist: the Paperclip adapter *dispatches* the CLI which *calls* the internal adapter.
- `opl_spdx_inject.py` skipping binary files is intentional (lockfiles, vendored code); the F3 fix only changes the *aggregate* result from green to red when the scanned set is empty, not the per-file skip behavior.
