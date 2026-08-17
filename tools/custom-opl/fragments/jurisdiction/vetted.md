This Custom OPL variant is governed by the laws of the vetted jurisdiction
declared in `NOTICE` (OPL-1.4 §12, base behavior).

The vetted jurisdiction set is curated in `GLOBAL_JURISDICTION_POLICY.md`.
Statute anchors are verified in `RESEARCH_BASE.md`. All major legal families and
the EU overlay (27 member states via DE/FR/NL/IT/ES) are covered. Any
jurisdiction not listed is still supported via §9.4 subordination to local law.

## Vetted jurisdictions (Custom OPL one-click choices)

| code | jurisdiction | family | governing-law anchor | consumer anchor |
|---|---|---|---|---|
| DE | Germany | civil-germanic | BGB §158, §242, §305c/307/309 | AGB-Kontrolle; Brussels Ibis |
| FR | France | civil-napoleonic | C. civ. art.1104, 1304-1ff, 1231-5 | C. consom. L212-1 (Dir 93/13) |
| UK | United Kingdom (England & Wales) | common | UCTA 1977; CRA 2015; 2019 Regs | post-Brexit ss.15B/15C |
| JP | Japan | civil-asian | CC art.1(2), 127/131, 548-2 | Consumer Contract Act |
| BR | Brazil | civil-latin | CC art.135; CDC 8.078/90 | CDC art.51 (void), art.101 (forum) |
| US | United States (federal + state) | common-state | UCC (state); Restatement §90 | FTC Act §5; state UDAP |
| CA | Canada | common + civil (QC) | CCQ art.1375 | provincial CPA |
| AU | Australia | common | ACL (Cth) Sch 2 | ACL s.24 (2023, AUD 50M) |
| IN | India | common | Contract Act 1872 s.23 | CPA 2019 |
| CH | Switzerland | civil (non-EU) | CO art.2, 151 | CO art.8 + case law |
| KR | South Korea | civil-asian | Civil Act art.2, 147 | Framework Act E-Commerce |
| NL | Netherlands | civil-eu | BW 6:248/6:236/6:237 | Dir 93/13 (impl.) |
| IT | Italy | civil-eu | CC 1337/1375/1353 | Codice Consumo 206/2005 |
| ES | Spain | civil-eu | CC 1258/1281 | Ley 3/2014 |
| CN | China | civil-socialist | Civil Code art.7, 158 | PIPL + Cybersecurity Law |
| IL | Israel | hybrid | Standard Contracts Law 5734 | Contracts (General Part) Law |
| EU | European Union (any MS) | civil-eu | Brussels Ibis 1215/2012 | Dir 93/13 |

## Notes for the configurator
- `US` covers the United States. Contract enforceability is **state law** and
  varies by state; the adopter MAY specify a state in NOTICE for B2B clarity, but
  it is **not required** — OPL's §9.4 subordinates to the user's local mandatory
  law (including state UDAP/consumer statutes) automatically, so consumer
  protection holds regardless of which state is named. The vetted registry lists
  "United States" as one jurisdiction; a state sub-note is optional advisor info.
- `EU` resolves to the adopter's member state; DE/FR/NL/IT/ES briefs cover the
  major economies, §9.4 covers the rest.
- `jurisdiction:custom` remains available for any non-vetted governing law; §9.4
  protects the adopter.
- Adding a jurisdiction = verify anchors in RESEARCH_BASE.md + (preferably) a
  counsel brief. Metadata update only; OPL-1.4 SPDX unchanged.
