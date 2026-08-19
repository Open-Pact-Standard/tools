# W1 — Canary Enforcement Chain: Real-User Dogfood Findings

Date: 2026-08-19 · Repo: `open-pact-tools` (main, clean). Chain exercised as a
maintainer would, on throwaway trees under `/tmp` only (never the real repo).

Scope walked:
1. `embed` (3 canaries, num == 3 source files) into a realistic `.py×2 + .js×1` repo
2. `canary_check.py` drift hook on the clean embedded repo
3. simulated theft → `verify` against a "rival" tree
4. `evidence` on the rival tree → `merkle_proven` behavior
5. `obfuscate.py` on a source file → behavior preserved? does output run?
6. `hunt` subcommand once (`gh` present + authed)

Environment: Python 3.11.15, Node v24.14.0, `gh /usr/bin/gh` authed (KidIkaros).

---

## CRITICAL

### C1. Watermark strategy writes syntactically-INVALID Python
Exposed: Step 1 (embed) → every later step that imports/parses the file.

`canary_embedder.py:224` inserts, for any `.py` whose first line is a module
docstring (`"""..."""` or `'''...'''`), the line

```
  Internal reference: <token>
```

with a **2-space indent and no `#` comment marker**. A bare, indented identifier
inserted between the docstring and the first `import` is an
`IndentationError: unexpected indent`.

Real-user impact: a maintainer embeds canaries into a real Python project and
their own files stop importing / stop parsing. The `demo_project/src/app.py`
fails with `IndentationError` immediately after embed. Because the file is
broken, PyPI builds, `python -m compileall`, and any import-based test suite at
maintainer-side all fail. The drift hook (`check`) still passes (it hashes
bytes, never parses), which masks the breakage — "green" CI + a repo that can't
run.

Verified: `ast.parse(app.py)` → `IndentationError`; `obfuscate.py` (step 5)
also aborts on it (`ast.parse` failed). The `#`-comment branch and the
`# Module reference: <token>` fallback (lines ~226/236) are correct; only the
docstring-insert branch drops the comment marker.

Fix direction: emit `# Internal reference: <token>` (or use the existing
`#`-prefixed variants) on the docstring path.

---

## HIGH

### H1. `verify` / `evidence` only match WATERMARK tokens — variable & deadcode are undetectable
Exposed: Step 3, Step 4.

Detection is a literal substring scan: `canary_embedder.py:385` /
`if secret in content:`. But two of the three embedding strategies never place
the token secret verbatim in the file:
- **variable** embeds `const CANARY_E7408D3EEE0C = "7daa2a3c0eb1517a"` — the
  name is `CANARY_…` (uppercase, `CANARY_` prefix) and the value is an unrelated
  hex; the literal secret `canary_e7408d3eee0c` appears nowhere.
- **deadcode** injects derived markers (`_validate_9565`, `_marker_9565d474`)
  and never writes `canary_e2a6a96687c8`.

Result: of the 3 planted tokens, only the watermark token was ever found. A
rival that copies **only** the variable-marked file (e.g. our `frontend.js`)
prints `No canary tokens found.`, exit 0 — a false-clean result. A single-file
theft of `frontend.js` or a deadcode-marked file is invisible despite a real
token being physically present. `--num-canaries N` and the manifest advertise N
canaries, but ~2/3 are unenforceable leads in practice.

The tool partially admits this ("variable-encoded canaries are not
text-searchable / watermark ones are", line 607) — but it is more severe than
"not text-searchable": `verify` can't match them at all, ever. Either the
embedding strategies should write the literal secret, or `verify` must
re-derive the variable-encoded / deadcode markers from the secret.

### H2. The only enforceable strategy (watermark) is the one that breaks the file
Exposed: Steps 1/3/5 together.

C1 + H1 compose into one worst-case: the *only* strategy `verify` can prove is
the watermark literal — and the watermark literal is exactly the injection that
makes the Python file unparseable (C1). So the "enforceable trace" is produced
by the step that corrupts the artifact. Until C1 is fixed, the enforcement path
is: embed → file broken → detection works only because the corrupt literal is
present.

---

## MEDIUM

### M1. Canaries cluster onto files — no per-file guarantee; whole modules left unmarked
Exposed: Step 1.

`--num-canaries 3` over 3 files landed 2 tokens in `src/app.py`, 1 in
`src/frontend.js`, and **0 in `src/buffer.py`**. `num-canaries == file count`
does not mean one token per file. A standalone, self-contained module like
`buffer.py` is a *more* plausible single-file theft target than the entry point,
yet it is completely unwatermarked. A maintainer believing "I watermarked my
whole package" has unmarked, freely-copyable files. Decisions to make: embed one
per `.py`/`.js` file by default (or round-robin so every eligible file >=1), and
surface any file that received 0 tokens in the embed summary.

### M2. `merkle_proven` is always false when the thief renames the file
Exposed: Step 4.

`evidence` sets `merkle_proven=True` only when the per-file fingerprint
(path + hash) matches the recorded release. When we copied `src/app.py` to a
rival and legitimately renamed it `core.py` — the realistic theft — the byte-
identical content produced `merkle_proven=False` and the gate downgraded the
match to "leads, not proof." Only a whole-repo, path-preserving clone yielded
`proven=True`. The behavior is internally consistent and conservative (genuinely
fine in that respect), but the documented "litigation evidence" goal degrades
exactly in the common rename case. Worth documenting loudly so an owner doesn't
expect a strong Merkle verdict from a renamed suspect copy.

---

## LOW

### L1. `verify` no-match message renders as literal `\nNo canary tokens found.\n`
Exposed: Step 3 (`/tmp/focus_front`, variable-only theft).

The message is printed with escaped newlines (`\n` backslash-n) instead of real
newline characters, so the terminal shows the raw sequence
`\nNo canary tokens found.\n`. Cosmetic, but it looks like a bug on the exact
(false-clean) path H1 produces.

### L2. No reverse/deobfuscate command despite `--recover`
Exposed: Step 5.

`obfuscate.py -r rec.json` writes a rename-map + marker/guard recovery dict, but
the CLI exposes no way to apply it back to readable source. A maintainer who
obfuscates a file has no in-tool path back to the maintainable form and must
keep a pre-obfuscation copy. The recovery artifact exists with no consumer.

### L3. `hunt` swallows gh/search transport failures → false-negative masked
Exposed: Step 6 (de-scoped, noted for completeness).

`_gh_search_code` catches `FileNotFoundError`/`SubprocessError` and returns
`[]`, so a transient network error or `gh` auth blip is reported identically to
"no copies found" (exit 0). The output's "BLIND SPOTS" caveat is good, but a
failed search is indistinguishable from a clean search.

### L4. `evidence` on an unrelated / zero-match target reports success
Exposed: Step 4.

Running `evidence` on a clean, unrelated project still prints
`Evidence package written to: <file>`, `Matches: 0`, exit 0, with no warning
that this package contains nothing probative. A maintainer pointing evidence at
the wrong target gets a clean-looking (empty) package rather than a prompt to
re-target.

---

## GENUINELY FINE

- **`embed` CLI + manifest separation.** Clear output; the PUBLIC payload
  (`release_payload.json`) correctly strips `secret`, `embedding_type`, and
  recovery fields — it carries only `token_id`, `merkle_leaf`, `merkle_proof`.
  No secret/salt leak in the publishable artifact. Salt is masked in stdout.
- **`canary_check.py` drift hook.** Clean embedded repo → `OK: repo matches the
  recorded fingerprint. No drift.` exit 0. The `.canary/` directory is correctly
  excluded from the tree hash (no self-drift) — verified with both
  `canary_check.py` and `canary_embedder.py check`.
- **`evidence` `merkle_proven` mechanics.** When the suspect file has the same
  relative path and content as the recorded release (whole-repo clone),
  `merkle_proven=True` and the gate is `merkle-proof`. The mechanism is sound.
- **`obfuscate.py`.** Genuinely preserves behavior: obfuscating `buffer.py` and
  running the output through the renamed identifiers reproduced
  append/read/len/repr exactly; obfuscating the (fixed) `app.py` variant produced
  an output that RUNS and prints the identical `{'kind': 'hello', 'ts': 1}`.
  Identifiers are deterministic and keyed to the canary secret, a fingerprint
  guard is fused (`OPL_FINGERPRINT_INSPECT == <hash>`), and a base64
  `canary_…::marker` is embedded. Recovery keys written to the requested path.
- **`hunt`.** Exit 0, clear verbosity, and explicit "BLIND SPOTS" + "no match
  ≠ safe" framing. De-scoped feature; UX for a non-packaging hunt path is clean.

---

## OPEN ISSUES (NOT done — follow-ups)

- **[CRITICAL]** Fix watermark Python injection (`canary_embedder.py:224`):
  docstring path inserts a non-comment indented line → `IndentationError`. Must
  prefix the reference with `#`.
- **[HIGH]** Reconcile detection with embedding: `verify`/`evidence` use literal
  `secret in content`, but variable + deadcode strategies never write the secret
  verbatim → ~2/3 of planted tokens are undetectable and single-file theft is
  visibly missed (see L1 for the confusing no-match display). Choices: (a) embed
  the literal secret in every strategy, or (b) make `verify` re-derive
  variable/deadcode markers from the secret per manifest.
- **[MED]** Guarantee per-file coverage or explicitly flag files that got 0
  tokens at embed time (M1).
- **[MED]** Document/set expectations that renamed copies will not reach
  `merkle_proven` (M2) — or relax the path binding for byte-identical content.
- **[LOW]** L1 literal-`\n` print; L2 add a `--derecover`/reverse command for
  `--recover` keys; L3 have `hunt` surface transport errors; L4 have `evidence`
  flag a zero-match package.

---

## Repro recipe (all under /tmp, nothing touched the real repo)

```
R=/tmp/canary_dogfood; mkdir -p $R/src
# 3 realistic source files (.py x2, .js x1): app.py, buffer.py, frontend.js
python3 canary_embedder.py embed --source $R --project-id 7 --distribution-id v1.0.0 \
  --salt <hex> --num-canaries 3 \
  --output $R/.canary/manifest.json --public-output $R/.canary/release_payload.json
python3 canary_check.py --repo $R --payload $R/.canary/release_payload.json   # clean -> exit 0
# theft: cp app.py rival/src/core.py ; cp buffer.py rival/src/buf.py ; cp frontend.js rival/web/frontend.js
python3 canary_embedder.py verify --source rival --manifest $R/.canary/manifest.json  # 1/3 tokens
python3 canary_embedder.py evidence --manifest ... --suspect-source rival --output ev.json
python3 obfuscate.py src/app.py -s <watermark-secret> -o app.obf.py -r rec.json
python3 canary_embedder.py hunt --manifest $R/.canary/manifest.json   # gh present
```