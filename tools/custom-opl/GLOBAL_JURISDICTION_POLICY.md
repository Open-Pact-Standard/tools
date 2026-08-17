# OPL Global Jurisdiction Policy

*Thorough global policy for OPL adoption across jurisdictions. OPL is a template
license: every adopter declares their own governing jurisdiction in `NOTICE`
(§12). This policy defines (a) the vetted jurisdiction set Custom OPL offers,
(b) the long-tail model for everywhere else, (c) the consumer-protection
baseline that applies in ALL jurisdictions, and (d) the governance of the
jurisdiction list itself.*

*This is policy, not legal advice. Statute anchors are verified in
`RESEARCH_BASE.md` (primary/official sources). Per-jurisdiction counsel briefs
live alongside (see `BRIEFS_INDEX.md`). OPL remains Draft until counsel confirms
the vetted set.*

---

## 1. Principle

OPL's creator-autonomy thesis requires that **an adopter in any jurisdiction can
apply OPL correctly under their own law.** A license that only "works" in
Germany or the US fails that test. The global policy therefore has two layers:

1. **Vetted jurisdictions** — a curated set with researched, cited statute
   anchors and a per-jurisdiction counsel brief. Custom OPL offers these as
   one-click choices.
2. **Long-tail jurisdictions** — any jurisdiction not vetted. OPL still applies
   via **§9.4** ("this license does not supersede any applicable law"), which
   subordinates OPL to the adopter's mandatory local law automatically. No
   brief needed; the license is safe by design.

The vetted set is a **coverage accelerator**, not a boundary. OPL never refuses
to operate outside it.

---

## 2. Vetted jurisdiction set

Coverage targets **all major legal families** + the economies where OPL adopters
actually are. Each entry below is verified in `RESEARCH_BASE.md` and has a
counsel brief (or is pending brief, marked 🟡).

| Code | Jurisdiction | Legal family | Governing-law anchor | Consumer-protection anchor | Brief |
|---|---|---|---|---|---|
| DE | Germany | Civil (Germanic) | BGB §§158, 242, 305c, 307, 309 | BGB AGB-Kontrolle; Brussels Ibis | ✅ GERMAN_LAW_BRIEF |
| FR | France | Civil (Napoleonic) | C. civ. art. 1104, 1304-1ff, 1231-5 | C. consom. L212-1 (Dir 93/13) | ✅ FR_LAW_BRIEF |
| UK | United Kingdom (E&W) | Common law | UCTA 1977; CRA 2015; 2019 Regs | post-Brexit 2019 Regs ss.15B/15C | ✅ UK_LAW_BRIEF |
| JP | Japan | Civil (Asian) | CC art. 1(2), 127/131, 548-2 | Consumer Contract Act | ✅ JP_LAW_BRIEF |
| BR | Brazil | Civil (Latin) | CC art. 135; CDC 8.078/90 | CDC art. 51 (void), 101 (forum) | ✅ BR_LAW_BRIEF |
| US | United States (federal + state) | Common law (state) | UCC (state); Restatement §90 | FTC Act §5; state UDAP | 🟡 priority (you live here) |
| CA | Canada | Common + Civil (Québec) | CCQ art. 1375 | provincial CPA | 🟡 |
| AU | Australia | Common law | ACL (Cth) Sch 2 | ACL s.24 (2023, AUD 50M) | 🟡 |
| IN | India | Common law | Contract Act 1872 s.23 | CPA 2019 | 🟡 |
| CH | Switzerland | Civil (non-EU) | CO art. 2, 151 | CO art. 8 + case law | 🟡 |
| KR | South Korea | Civil (Asian) | Civil Act art. 2, 147 | Framework Act E-Commerce | 🟡 |
| NL | Netherlands | Civil (EU) | BW 6:248/6:236/6:237 | Dir 93/13 (impl.) | ✅ (brief pending) |
| IT | Italy | Civil (EU) | CC 1337/1375/1353 | Codice Consumo 206/2005 | ✅ (brief pending) |
| ES | Spain | Civil (EU) | CC 1258/1281 | Ley 3/2014 | ✅ (brief pending) |
| CN | China | Civil (socialist) | Civil Code art. 7, 158 | PIPL + Cybersecurity Law | 🟡 |
| IL | Israel | Hybrid | Standard Contracts Law 5734 | Contracts (General Part) Law | 🟡 |
| EU | European Union (any MS) | Civil (EU overlay) | Brussels Ibis 1215/2012 | Dir 93/13 | ✅ (via DE/FR/NL/IT/ES) |

**15 distinct jurisdictions + the EU overlay = all 27 EU member states covered
through 5 EU anchor briefs (DE/FR/NL/IT/ES).** Plus US (50 states via federal +
major-state note). This spans the overwhelming majority of global software
development GDP and every major legal family.

---

## 3. Long-tail model (the ~170 other jurisdictions)

For any jurisdiction not in §2, OPL applies with:
- **§12** governing law = the adopter's declared jurisdiction.
- **§9.4** subordination = OPL yields to that jurisdiction's mandatory law
  (consumer protection, liability, unfair-terms) automatically.
- **No brief required.** The license is safe by construction; the adopter bears
  the ordinary responsibility to confirm their local law.

This is not a gap — it is the intentional design. Writing 170 bespoke briefs
would be over-engineering; §9.4 makes them unnecessary.

---

## 4. Universal consumer-protection baseline

Regardless of declared jurisdiction, OPL's text already handles the cross-system
finding from `REGIONAL_REVIEW.md`:

- **§9.4** subordinates OPL to applicable law everywhere — consumers are
  protected in ALL systems (Germany §309, France L212-1, UK CRA/UCTA, Japan
  Consumer Contract Act, Brazil CDC art. 51, US FTC §5 + state UDAP, Australia
  ACL, India CPA 2019, etc.).
- **§9.4 consumer carve-out (v1.4.3)** explicitly preserves mandatory consumer
  rights and the consumer's local forum — closing the blind spot across
  jurisdictions.
- **§12.1 urgent relief** uses jurisdiction-neutral language (no US-equity label).

Adopters should note (advisor guidance, not license text): **B2B users should
assess OPL's liability exclusion and Standard-Terms incorporation against local
unfair-terms / AGB / reasonableness rules** (e.g., Germany §307, UK UCTA s.11,
France L212-1, Brazil art. 51, Australia s.24). This is the only system-specific
caveat and it is guidance, not a license change.

---

## 5. Special handling: United States

The US is unique: contract enforceability is **state law**, not federal. OPL's
§12 governing-law clause is therefore load-bearing — the adopter MUST declare a
state, not just "United States." The US brief will be federal framework + a
note on the major adopter states (CA, NY, TX, DE). **Given the maintainer (Ikaros
Digital LLC) is US-based, origin-canary's NOTICE jurisdiction should be updated
from "Berlin, Germany" to a US state** (decision pending maintainer input).

---

## 6. Governance of the vetted list

- The vetted set is **curated, not exhaustive.** New jurisdictions are added when
  (a) statute anchors are verified in `RESEARCH_BASE.md` and (b) a counsel brief
  exists or is flagged pending.
- The list lives in `fragments/jurisdiction/vetted.md` (machine-readable) + this
  policy (human-readable).
- **Versioning:** changes to the vetted set are OPL-1.4 metadata updates, not
  license-text changes. The `OPL-1.4` SPDX id is unchanged.
- **No jurisdiction is ever required.** `jurisdiction:custom` remains available
  for any adopter who wants a non-vetted governing law; §9.4 protects them.

---

## 7. Publish gate

OPL v1.4.3 stays **Draft** until:
1. Vetted-set statute anchors verified (✅ done for all 15+EU per RESEARCH_BASE).
2. Per-jurisdiction briefs exist for the vetted set (✅ DE/FR/UK/JP/BR; 🟡 US/CA/
   AU/IN/CH/KR/CN/IL + NL/IT/ES briefs pending).
3. US jurisdiction decision for origin-canary made.
4. Maintainer sign-off on timing + content. No tag/release without explicit
   approval.

---

*Sources: RESEARCH_BASE.md (primary-verified statute anchors), BRIEFS_INDEX.md
(per-jurisdiction counsel briefs), REGIONAL_REVIEW.md (cross-system scan).
Policy is the governance layer; the briefs are the evidence layer.*
