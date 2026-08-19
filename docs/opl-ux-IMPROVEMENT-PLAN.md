# OPL UX — Improvement Plan (phased, promote-and-retire)

Sequenced so the alpha-blocking set (missing information flows) ships first. Each
phase is independently verifiable. No big-bang rewrite.

## Phase 0 — close the missing information flows (highest leverage, alpha-blocking)
- **F1:** Add a "Using OPL software" surface to the public site — a tab/panel written
  for the *commercial user / adopter-of-an-OPL-work*, answering:
  - Free for personal use, education, research — no payment, no account.
  - Commercial use requires payment; the maintainer's Standard Terms URL (in NOTICE)
    is where you see pricing and pay.
  - After 36 consecutive months of maintainer unreachability the work converts to
    Apache-2.0 (you are protected).
  - If `OPL-AI: opted in` is in NOTICE, do not train AI on the code.
  - You owe the maintainer a licensing inquiry response within 60 days if asked.
- **F2:** Mirror the CLI `opl_adopt` next-steps block on the site Adopt panel
  ("what you receive, no key to store, 3 steps"). Keep the two in sync.

## Phase 1 — complete the M1→M2 handoff
- **F3:** Ship a Standard Terms page *template* (a copy-paste HTML or a `opl_init
  --terms-template` generator) so "publish your terms page" is one step, not a void.
- **F4:** Add a consumer-facing "compliance hint" — e.g. `opl_check --as-user` that
  reads a repo's NOTICE and prints the user's obligations in plain language. (Reuses
  the existing check machinery; new output mode only.)

## Phase 2 — align goals & incentives (lower leverage, do last)
- **F5:** Reframe site copy to the two-sided goal ("sustainable software via a
  license that respects both maker and user"), not producer-centric.
- **F6:** Surface the maintainer's terms/pay link from the adopted repo (e.g. a
  generated `COMMERCIAL.md` or a badge in NOTICE) so M2's compliance path is one click.

## Verification gate (per audit Step 4)
- Behavioral, not text: load the site, confirm the new "Using OPL" panel renders and
  states the four obligations; confirm the Adopt panel shows the next-steps block.
- `opl_check --as-user` on a fixture repo prints the user's duties.
- Re-run the full suite (548 green baseline) after any tool change.
