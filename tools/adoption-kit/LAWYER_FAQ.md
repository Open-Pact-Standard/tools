# OPL — Lawyer FAQ

*For enterprise counsel reviewing OPL-1.4 (or use of an OPL-licensed dependency).
Not legal advice; cites the license text. Every answer traces to a section.*

**1. Is OPL "open source"?**
No. OPL restricts commercial use unless the user pays per the Maintainer's
Standard Terms (§3.3). It is a *fair-source* license, not an OSI-approved
open-source license. Do not classify it as open source in your OSS inventory.

**2. Is it copyleft / reciprocal?**
No. There is no GPL-style reciprocity or "viral" clause. The Functional
Equivalent restriction was **removed in v1.4** (§3.6 note). Using the Work
commercially requires payment; it does not obligate you to open your own code.

**3. What are our obligations if we use it commercially?**
Maintain a reachable contact (§4.1), keep a Valid Standard Terms URL or declare
Personal-Use-only (§4.3), and pay per the Maintainer's published terms (§3.3).
Per-Version commercial terms may be pinned immutably in a `COMMERCIAL_TERMS.md`
(§13) — that file *is* your contract for that Version.

**4. Patent grant?**
Yes — each Contributor grants a royalty-free patent license for their
contribution (§6), terminating against any party that asserts patents against
the Work. Standard, benign.

**5. How does it terminate?**
There is **no termination-for-convenience or breach-forfeiture** in the ordinary
sense. Rights continue unless the Work converts to Apache-2.0 via the
abandonment (§5) or DOSP (§5.1) triggers. Those triggers are *automatic
conversions*, not license revocations of already-granted rights.

**6. What happens if the Maintainer abandons the project?**
If no Maintainer is reachable for the declared period (default 36 months), the
Work **automatically converts to Apache License 2.0** (§5). No fiscal sponsor, no
public notice, no counter-process. Your use rights survive the conversion.

**7. Can we get scheduled open-source conversion?**
Yes — if the Maintainer opted into DOSP in `NOTICE` (§5.1), each Version converts
to Apache-2.0 N months after its first public release. If `NOTICE` is silent,
there is no scheduled conversion (opt-out by default).

**8. GPL / LGPL compatibility?**
N/A. OPL is not an OSI license and its commercial-use restriction is
incompatible with GPL's permission-to-commercialize. Do not combine OPL code
into a GPL project. Combining into a permissively-licensed (Apache/MIT/BSD)
project is fine as long as you honor OPL's commercial-use payment for the OPL
portion.

**9. Who governs OPL?**
The Open-Pact-Standard org (Ikaros Digital LLC). OPL is **not** under the Fair
Source movement or any external registry. It is interoperable (converts to
Apache-2.0) but independent.

**10. What about AI training?**
Controlled by the OPL-AI addendum, **opt-in** via `NOTICE` (default: opted out,
addendum not incorporated). If opted out, OPL places no AI-training restriction.

**11. Is the license text stable?**
Yes. It is the contract; no on-chain or registry dependency. Updates are versioned
(OPL-1.4 → v1.4.1 clarifications). The `OPL-1.4` SPDX identifier is stable across
clarification patches.
