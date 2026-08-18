# Canary Ecosystem — Systems Design Analysis

**Date:** 2026-08-18 · **Lens:** Meadows (systems-design skill)
**Scope:** embed → fused obfuscation → verify → remote "hunt" search, as ONE system.

---

## Step 0 — Paradigm & Goal gate

**Paradigm (what is it actually FOR, deduced from structure, not the tagline):**
The canary ecosystem is the **enforcement backbone of the fair-source economic
model**. Open-Pact keeps source public and readable (that's the offer); the only
thing that protects it is *attribution + deterrence*. The canary exists to give
the license **teeth**: if someone ships the code without complying, the owner can
prove *which release* was taken and respond credibly. Without the canary, the
license is a request; with it, a contract with evidence.

**P0 goal (one line):** *Detect, attribute, and deter unauthorized use of
fair-source code with evidence that survives transformation, so the owner can
enforce the license.*
- NOT "prevent copying" (canaries are evidence, not access control — a determined
  adversary strips them).
- NOT "protect the source" (source stays readable; that's the fair-source deal).

**Who is it for?** The OPL adopters (maintainers) who need enforceable
attribution, and secondarily the legal/community proof the evidence supports.

---

## Step 1 — Stocks & flows

| Stock | Inflow | Outflow | Buffer role |
|-------|--------|---------|-------------|
| Token secrets (salt + per-token) | embed | → private manifest | secrets store; the entire verification key |
| Private manifest | embed | → verify/evidence inputs | "only the owner decides who's a thief" asymmetry |
| Public payload | embed | → CI `check`, published fingerprint | public integrity record |
| Obfuscated deliverable | fused obfuscation | → shipped artifact | the fingerprint carrier |
| Theft candidates | `verify` / (future) `hunt` | → evidence → enforcement action | evidence buffer feeding the attribution loop |

---

## Step 2 — Feedback loops

- **B1 (attribution / integrity loop):** embed → publish fingerprint → CI `check`
  on every commit → drift red → re-fingerprint. Keeps "shipped tree = recorded
  tree." *Healthy.* Need a noted delay: drift is only as fresh as the CI run —
  a payload published once and never re-checked decays (Meadows "multiply by 3").

- **B2 (deterrence loop):** theft suspected → `verify` finds token → `evidence`
  → enforcement → would-be copiers hesitate → less theft. *This is the loop the
  ecosystem exists for.* Today it only fires **reactively** (someone hands you a
  suspect tree). The "hunt" capability would add proactive fire.

- **R1 (adoption loop):** more maintainers adopt OPL → more trees carry canaries
  → the network of marked code grows → more theft is detectable → enforcement
  gets credible → more adopt → **virtuous**. This is the true growth engine; the
  canary is its sensor.

- **Gap — no balancing loop on verification truth.** Nothing stops a maintainer
  from *overcounting* a match (false attribution) or *undercounting* (false
  security). The token is 12-hex — high entropy, so false positives are rare —
  but there's no human/threshold gate between "match found" and "it's theft."
  Evidence → action should have a sanity boundary (e.g. require the Merkle proof,
  not just a token hit).

---

## Step 3 — Traps

- **Shifting the burden (B):** currently the "hunt" idea risks becoming a
  *crutch* — "I searched GitHub, so I'm safe." That's false security: GH search
  only sees **public repos**, misses **private forks** and **non-GitHub hosts**,
  and the variable-encoded canaries aren't text-searchable. Defense: hunt
  output must print its blind spots; fuse Watermark comments for searchability;
  treat a "no match" as "not found here," never "not stolen."

- **Drift to low performance (R+B):** the fingerprint only "stays alive" if
  maintainers re-embed per release and keep CI running. Let adoption ship a tree
  without fresh canaries → the whole ecosystem's coverage silently erodes.
  Defense: make re-embedding an obvious, low-friction release step.

- **Not vulnerable to:** tragedy-of-commons (single/adopter-owned), escalation
  (no arms-race built in), success-to-successful (network effect is the *goal*
  here, not a pathology).

---

## Step 4 — Leverage ranking (highest → lowest)

| # | LP | Intervention | Leverage | Effort |
|---|----|--------------|----------|--------|
| 1 | **3 Goals** | State the P0 explicitly (doc) — the system is *enforcement*, not prevention | High | now (done) |
| 2 | **6 Info flows** | **Proactive "hunt"** — the reactive-only hole: owners can't find copies unless handed a directory | High | Med |
| 3 | **8 Balancing** | **Evidence sanity gate** — require Merkle proof + human threshold before "it's theft," not a bare token hit | High | Low-Med |
| 4 | **6 Info flows** | Surface remote-search **blind spots plainly** (public-only, var-encoded missed) so no false "I'm safe" | High | Low |
| 5 | **5 Rules** | Make **re-embed-per-release** a gated habit (release checklist / CI hook demanding fresh payload) | Med | Low |
| 6 | **4 Self-org** | Fused obfuscation keyed to the token — fingerprint *is* the behavior, so it survives refactor (BUILT) | Med | done |
| 7 | **12 Params** | Tokens-per-tree, search throttle/rate, page size | Low | — |

**The honest read:** the highest-leverage *remaining* move is **#2 (hunt)** — it's
the info-flow that turns the system reactive → proactive, which is what actually
serves enforcement. #3 and #4 are the balancing-loop guardrails that keep that new
power from creating false accusations or false security. The fused-obfuscation (#6)
is already built — it's the *carrier*, not the goal.

---

## Step 5 — The fork this analysis points to

The ecosystem's center of gravity is **B2 (deterrence)**, and B2 only pulls if it
fires **without requiring the victim to already hold the thief's directory**. So:

- **Build `hunt` (LP #6, the info-flow gap)** — but ONLY with the blind-spot
  honesty and the evidence-gate built in, so it strengthens B2 instead of
  weakening integrity.
- **Add the evidence sanity gate (LP #8)** alongside it — a bare token hit is a
  *lead*, not proof; only the Merkle proof closes the loop.

That's the leverage-ordered plan. Everything else (throttling, token counts,
which languages to fuse) is Level-12 tuning that should wait for a real second
input.

---

*Analysis doc. Obfuscation mechanism already shipped (`feb2764`); `hunt` and the
evidence gate are the next high-leverage interventions.*