# Adopt-flow dogfood — pilot: `origin-tools` (Apache-2.0 → OPL-1.4)

**Date:** 2026-08-19 · **Subject:** `opl_init.py`, `opl_migrate.py`, `opl_spdx_inject.py`, `opl_check.py`
**Pilot target:** a real Rust workspace under Apache-2.0 (214 source files) — the hardest
adoption path (migrate, not fresh adopt). Run against a COPY at `/tmp/opl_dogfood_origin`,
never the real repo.

## What I did (as a陌生 pilot would)
```
1. opl_migrate.py <dir> --from Apache-2.0 --dry-run --report   # detected Apache, 214 files
2. opl_init.py --non-interactive --maintainer ... --terms-url ... --opl-ai out --output NOTICE
3. opl_spdx_inject.py <dir> --license OPL-1.4                  # 214 headers added
4. opl_check.py <dir>                                          # 3 pass / 2 warn
```

## What worked
- Migrate detection is accurate (Apache-2.0, 214 files, 96 Apache SPDX, 100 missing).
- NOTICE generates; SPDX inject is fast and clean; check is informative.
- The chain is mechanically functional.

## Findings (UX, in pilot order)

### F1 [CRITICAL] Migrate never updates the actual LICENSE file
After the FULL chain, `LICENSE` is still the unmodified Apache-2.0 text
(`contains 'OPL'? False`). `opl_check` then warns:
`[WARN] [license] LICENSE exists but does not reference OPL`.
The pilot is left with a **self-contradictory repo** (Apache LICENSE + OPL NOTICE +
OPL SPDX) and no tool step that resolves it. `opl_migrate.py` *can* write LICENSE
(the string is in the source) but the default/--report flow only emits
`OPL_MIGRATION_REPORT.md` and tells the user to "run 3 more commands." This is the
single biggest adoption cliff: a stranger cannot finish the job with the tools given.

### F2 [HIGH] No single orchestrated "adopt" command
Four separate tools, each printing "Next steps" prose. For a 214-file workspace this
is friction amplification. A pilot wants ONE `opl_adopt` that runs
detect → notice → spdx → license-swap → check in sequence and reports a final verdict.

### F3 [MEDIUM] `opl_check` warns on an unreachable Standard Terms URL
`[WARN] [standard-terms-url] URL unreachable ... https://ikaros.digital/terms/opl`
The pilot hasn't published terms yet (step 1 of 3) and gets a warning that *looks*
like failure. Should be INFO/advisory ("publish this before release") not WARN, or
skip network check unless `--strict`.

### F4 [LOW] NOTICE is thin
`--abandonment`, `--dosp`, `--trademark`, `--commercial-terms` are accepted but the
generated NOTICE omits them from the displayed body even when supplied. Pilot can't
see what they set. Either render all set fields, or document they're optional.

### F5 [LOW] No guidance on WHERE NOTICE/LICENSE live
Tools write to CWD / declared `--output` but never say "LICENSE and NOTICE belong at
repo root." A pilot may drop NOTICE in a subdir.

## Why this matters for the widget (Option A)
The site's "Adopt OPL in five minutes" + future embedded Studio widget must not
reproduce F1/F2. The widget should call a SINGLE orchestrated adopt path that ends in
a self-consistent repo (LICENSE swapped, NOTICE+SPDX+check all green), not 4 manual
steps. **Fix the CLI first; the widget then wraps a working spine.**

## Verification note
All findings reproduced on a copy; real `origin-tools` repo untouched (still Apache-2.0, clean).
