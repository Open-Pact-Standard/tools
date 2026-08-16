# OPL Adoption Kit — System Design

*Designed with the system-design discipline: requirements first, then components,
then tradeoffs. (The infra blocks of system-design — queues, sharding — don't
apply to a documentation/trust artifact; the four-step process and the
"requirements before solutions" principle do.)*

## 1. Requirements (Step 1 — scope)

### Functional
- **F1. Corporate Approval Packet** — a single document a company's legal/
  procurement/architecture-review board can read to approve OPL adoption
  (or use of an OPL-licensed dependency). Covers: what OPL is, obligations,
  commercial-use mechanics, conversion triggers, risk assessment, red lines.
- **F2. Worked example** — a real, already-adopted project shown end-to-end
  (origin-canary: NOTICE + COMMERCIAL_TERMS + SPDX + the 90-test suite that
  proves the tooling holds up). "Here is a live OPL project, not a toy."
- **F3. "Why OPL" one-pager** — a 1-page executive summary for a decision-maker
  who will not read the full license.
- **F4. Lawyer FAQ** — answers to the questions enterprise counsel actually ask
  (copyleft? patent? termination? GPL compatibility? what happens on abandonment?
  is it "open source"?).
- **F5. Generator glue** — a single `make_kit` entry that assembles the Packet
  from the worked example + templates, so it never drifts from the real license.

### Non-functional
- **NF1. Local-first, zero-accounts** — like everything OPL: no SaaS, no upload.
- **NF2. Single source of truth** — the Kit MUST NOT fork license text; it
  references `LICENSE.md` (v1.4.1) and the `opl-adopt`/`custom_opl` tooling.
- **NF3. Honest boundary** — must state OPL is NOT OSI open source and NOT under
  Fair.io; must not overclaim fair-source for Source-Available variants.
- **NF4. Auditable** — every claim in the Packet is traceable to a license
  section or a test.

### Out of scope (ponytail — don't build)
- No hosted submission portal. No registry. No "license as a service."
- No legal advice engine. The Kit informs; a lawyer decides.

### Scale / audience
- Audience: engineering leads, OSPO, procurement, enterprise counsel.
- Volume: low (read per adoption decision), not a high-QPS service.

## 2. High-level design (Step 2)

```
                    OPL Adoption Kit (local, zero-accounts)
                                  │
   ┌──────────────┬───────────────┴───────────────┬──────────────────┐
   ▼              ▼                                ▼                  ▼
WHY_OPL.md   CORPORATE_APPROVAL_PACKET.md    LAWYER_FAQ.md      worked-example/
(1-pager)    (decision doc)                  (Q&A)             (origin-canary
   │              │                              │                live artifacts)
   └──────────────┴───────────────┬──────────────┴──────────────────┘
                                  ▼
                        make_kit.py  (assembles Packet from
                        LICENSE.md + opl-adopt output + templates;
                        asserts claims trace to §-references)
                                  ▼
                        DISTRIBUTION: copied into adopting repo's
                        /OPL-ADOPTION-KIT/ or published as a release asset
```

Data flow: `LICENSE.md` (v1.4.1) + `origin-canary` (worked example) + templates
→ `make_kit.py` → 4 artifacts + the worked-example dir.

## 3. Critical components (Step 3)

### 3.1 CORPORATE_APPROVAL_PACKET.md
The load-bearing artifact. Structure (each section cites a §):
1. Summary (1 para: free personal, paid commercial, Maintainer sets price).
2. License model (two-tier, Polyform Mixed; cite §3.3).
3. Obligations (NOTICE, reachable contact, Standard Terms URL; cite §4, §13).
4. Commercial Use mechanics (how payment works; cite §3.3, §3.7 wind-down).
5. Conversion triggers (abandonment §5; DOSP opt-in §5.1; target Apache-2.0).
6. Risk assessment (copyleft: NONE; patent grant: §6; termination: none except
   abandonment; GPL compatibility: N/A — OPL is not OSI; note this honestly).
7. Red lines (no forced conversion; creator autonomy; zero-infra).
8. Approval sign-off block (roles: Eng lead, Legal, Procurement).

### 3.2 worked-example/ (origin-canary)
Copies the *real* generated files: NOTICE, COMMERCIAL_TERMS.md, LICENSE (OPL-1.4),
and a README noting the 90-test suite + tamper-detection as evidence the tooling
is sound. This is the "see, it's real" proof.

### 3.3 make_kit.py (the integrity guard)
- Reads LICENSE.md, asserts the version is OPL-1.4.x.
- Assembles the Packet by substituting the worked-example's actual
  Maintainer / DOSP / jurisdiction into template slots.
- **Claim-trace check**: greps the Packet for `§N` references and verifies each
  cited section still exists in LICENSE.md (fails the build if a cited section
  was removed — prevents drift).
- Outputs the 4 artifacts + worked-example into a target dir.

### 3.4 LAWYER_FAQ.md + WHY_OPL.md
Static, maintained by hand (they're prose, not generated), but `make_kit.py`
includes them verbatim and asserts they contain the required boundary phrases
("not OSI open source", "independently governed").

## 4. Tradeoffs (Step 4)

| Decision | Tradeoff | Chosen |
|---|---|---|
| Generate Packet vs hand-write | Gen risks drift; hand-write risks staleness | **Hybrid**: templates + `make_kit` assertion that cited § still exist |
| Bundle license text in Kit | Drift from canonical LICENSE.md | **No** — Kit references, never copies, the license |
| Cover Source-Available variants | Could overclaim fair-source | **Explicit boundary**: Kit's fair-source claims apply only to DOSP/abandonment-enabled variants |
| Publish as website vs repo artifact | Website = infra we don't want | **Repo artifact** (zero-accounts, local-first) |

## 5. Score (system-design Quick Diagnostic, adapted)

| Diagnostic | Pass? |
|---|---|
| Requirements listed (F1–F5, NF1–NF4)? | ✅ |
| Estimate / scale stated (low-volume doc, not a service)? | ✅ (N/A infra, stated) |
| Redundancy / SPOF? | N/A — static artifact; SPOF = LICENSE.md, which is the canonical source (acceptable) |
| "DB scaling" → analog: source-of-truth discipline? | ✅ (single source, make_kit asserts no drift) |
| Cache → analog: pre-built artifacts? | ✅ (Packet pre-assembled, not computed at read time) |
| Async/queues? | N/A |
| Monitoring? | ✅ analog: `make_kit` claim-trace check = build-time verification |
| Deployment? | ✅ analog: `make_kit` produces the distributable; copy to repo or release asset |

**Score: 9/10** — fails only the literally-inapplicable infra rows (redundancy,
queues), which don't apply to a local documentation artifact. The design satisfies
requirements, source-of-truth discipline, build-time verification, and a clear
distribution plan, with tradeoffs named.

## 6. Build order (next)
1. `worked-example/` — copy origin-canary's real files (NOTICE, COMMERCIAL_TERMS, LICENSE).
2. `CORPORATE_APPROVAL_PACKET.md` template.
3. `LAWYER_FAQ.md`, `WHY_OPL.md`.
4. `make_kit.py` — assembly + claim-trace assertion.
5. Run `make_kit` → verify artifacts build and cited §-refs resolve.
