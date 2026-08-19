# OPL Ecosystem — Roadmap

**Date:** 2026-08-18 · Status after: canary litigation path defined, hunt de-scoped.

---

## The one line that should guide everything
**OPL's P0 is adoption (enforcement is the enabler, not the product).** The canary
work we just finished proved the *enforcement* story; enforcement exists to make
*adoption* low-risk and defensible. The recurring gap in every systems-check has
been: **strong supply (tools), ~zero demand (one pilot adopter).** The highest
leverage is pulling demand forward, not adding more tooling.

---

## Phase 0 — Land ONE pilot (the actual goal; HIGHEST leverage)
Everything is fork-ready; none of it matters without a named adopter.

1. **Pick one candidate** from `~/opl-business/opl-pilot-outreach.md` (fair-source
   maintainer / framework author, not a big corps or hobby repo).
2. **Dogfood the exact offer we'd send:** on a representative repo, run
   adopt → verify → evidence end-to-end as a *user* (we've proven each piece; run
   the joined flow once, on disk).
3. **Send the Adopt+Validate pass** (free) with the copy-paste email.
4. **Deliver a real thing back:** a working adopted repo + canary evidence run, so
   the pilot has a tangible artifact, not a pitch.

**Done when:** one named maintainer is publicly or privately on board; we have a
real adoption + enforcement artifact to show for it.

*Guardrail:* no more tooling unless it directly unblocks this.

---

## Phase 1 — Harden the enforcement product (only as the pilot demands)
The litigation path (embed → verify → evidence) is the packaged story. It's solid,
but has open edges a pilot will hit:

| Gap | Priority | Note |
|-----|----------|------|
| Signed evidence via `origin-canary sign` needs `origin identity keygen`; **`origin` CLI not yet built/verified end-to-end** | Med | Build `origin`, run the full signed-commitment chain once; prove the PQ-signed evidence actually closes. |
| Evidence gate is path-keyed → a *renamed* copy is a lead, not proof | Med | Honest, but a pilot may ask "what if they renamed it?" — decide the answer (structural-hash vs path-keyed) deliberately. |
| `hunt` F1/F2/F3 (false-safety, machine-status, owner-fork filter) | Low | **Keep de-scoped.** Only harden if a real user demands proactive search. |

---

## Phase 2 — Close the site/story (only what serves adoption)
- **Live demo artifact:** a *real* "adopted repo + canary-proof" walkthrough a
  prospect can click (replaces static feature cards with one tangible example).
- **Adopters page** — only after the first pilot exists (don't build an empty page).

*Definitely NOT now:* the hosted-Studio fork, SECURITY page, 404, analytics — all
deferred until there's demand to serve. (Ponytail: don't build surfaces for no user.)

---

## Phase 3 — Business (only after a pilot says yes)
- Free self-host stays free. **Hosted service = build Custom OPL + embed canary
  tokens** for the adopter who doesn't want to run it — the fair paid frontier.
- Business docs (pricing is placeholder $295–1,595) already live privately in
  `~/opl-business/`; keep them off GitHub. Do NOT build billing/infra until a
  first buyer exists.

---

## Non-negotiables (carried from this session)
- **Dogfood before "done."** Green tests ≠ done; the user clicks the product and
  challenges it (caught the click-does-nothing JS bug, the no-LICENSE adopt, the
  gh-missing false-safety — all only surfaced by using it).
- **Reactive litigation is the product; `hunt` is a source tool.** Don't re-promote
  proactive search.
- **Don't duplicate origin-canary.** PQ signing lives in the Rust crate; Python
  stays the simple embed/CI tool.
- **Branding:** site speaks only about OPL. Website reflects substantive changes.

---

## What we are NOT doing (deferred with triggers)
- Extensible-Kit / validate-terms capability — until a user asks.
- Hosted Studio SaaS — until the pilot needs it.
- `hunt` as a product — until a user demands proactive search AND F1 is closed.
- Multi-host search (GitLab/Bitbucket), REST fallback for `gh` — until a second
  consumer appears.
- Analytics / SECURITY page / 404 — until there's traffic.

---

## The decision that matters
The roadmap takes **Phase 0 (find the pilot)** ahead of **Phase 1 (harden more
tools)**. If we keep building enforcement features, we get a shinier engine for a
car with no driver. Pick the one candidate, dogfood the exact offer, send it.