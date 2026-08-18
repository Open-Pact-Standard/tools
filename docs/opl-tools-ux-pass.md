# OPL Tools — Deep UX Pass (live findings)

**Date:** 2026-08-18 · **Status:** complete
**Method:** walked every tool as a real Maintainer — help text, defaults, prompts,
errors, output, modification behavior. Captured live, not from code review.

---

## Found & fixed

### U1 ✅ opl_init — "blank = none" was a lie (FIXED)
Interactive wizard's DOSP prompt says *"blank = none"* and Commercial-Terms /
Trademark say *"blank = skip / press Enter to skip"* — but the validator rejected
an empty answer as "Invalid input." and looped forever. A maintainer following the
on-screen instruction was stuck. **Fix:** `ask(..., allow_blank=True)` for the three
optional fields; verified blank DOSP now writes a clean NO-DOSP NOTICE.

## Verified healthy (no change needed)

- **opl_check** — excellent UX: clear PASS/FAIL, names the exact files missing SPDX,
  graceful cascading (no NOTICE → skips URL/AI checks with INFO), counts all source.
- **opl_migrate** — auto-detects MIT, clear `MIT → OPL-1.4`, shows exactly which files
  need headers, gives a 4-step next-actions list. Genuinely good.
- **opl_spdx_inject --dry-run** — clear preview, "Run without --dry-run to apply."
- **custom_opl --help / hard-block** — complete option list; hard-block is a clear,
  actionable single-line message, no traceback.
- **canary embed** — F5 pre-embed NOTICE shown, public/private manifest split explained,
  GPG/step guidance at the end.
- **opl_init --non-interactive** — clear success + next-steps; validates required fields
  with a clean error (not a crash).

## Genuine UX gaps worth hardening (ranked)

### U2 (MED) canary embed — hostile flag surface for a first-timer
`embed` requires `--project-id --distribution-id --salt --source` (4 hand-supplied,
no defaults, `--salt` is a secret) just to get started. `--help` doesn't give a
*worked example* or explain what a good project-id/distribution-id/salt look like.
A fresh user assembles this cold. **Fix:** add a `--help` usage example block, and
auto-suggest stable defaults (e.g. derive distribution-id from git, offer to generate
the salt) with explicit override.

### U3 (LOW) F5 notice has a typo
The pre-embed NOTICE says *"adds a) comment/reference line"* — the `)` is stray.
Trivial polish, but it's the first thing a user reads.

### U4 (LOW) adopt-full hides the kit build
`adopt-full` builds the Adoption Kit internally without a clear user-facing signal
of what it produced (it prints a one-line kit message). Fine, but a user can't tell
the kit landed where.

---

## Verdict

The tools are **better than their reputation suggests** — opl_check, opl_migrate,
and the non-interactive flows are genuinely well-designed. The main UX defect was
the blank-optional-field loop (U1, fixed). The one tools-level gap worth real
attention is **canary embed onboarding (U2)**: it's the most elaborate tool and has
the least guidance. Fixing U2 + the U3 typo is the honest "deep UX" deliverable.