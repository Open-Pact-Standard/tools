# OPL Studio

A **local** web app for adopting the Open-Pact License — no accounts, no upload,
no network egress (except what the adoption tools themselves do). Launch it from
your terminal and drive the whole adoption flow from a browser.

## Install & launch

```bash
git clone https://github.com/Open-Pact-Standard/tools
cd tools
./install.sh          # builds the Adoption Kit + zip, prints the launch command
python3 opl_studio.py # serves http://localhost:8771 and opens your browser
```

Stop with `Ctrl-C`.

## What it does

- **Adopt** — fill a short form (maintainer, jurisdiction, terms URL, DOSP,
  abandonment). Every choice shows its *consequence* before you commit. It
  previews the NOTICE/LICENSE diff, and only writes to your repo when you confirm.
- **Build a Custom OPL** — assemble a bespoke OPL variant from **8 vetted
  fragment slots** (commercial model, DOSP, abandonment, OPL-AI, rate stability,
  derivative, trademark, jurisdiction). Hard-block and **Fair Source** checks run
  live as you choose; output lands in a `custom-opl-out/` dir you own.
- **Scan** — point at any repo and run `opl_check` read-only to see if it's
  OPL-compliant.
- **Enforce with canary tokens** — embed canary tokens into a repo and option-
  ally sign the release fingerprint with **origin-canary's hybrid Ed25519 +
  Falcon-1024** (post-quantum) identity. Delegates to the Rust `origin-canary`
  binary (from origin-tools); integrity-only embed falls back to the Python
  canary tool if it's absent. This is the single place post-quantum signing
  lives (see docs/opl-canary-signing-decision.md).
- **Kit** — read the Adoption Kit docs and download them as a zip.

## Design

See `adoption-kit/ADOPTION_SYSTEM.md`. The studio is the local precursor to a
possible future hosted service; the adoption curve lives at *understanding*
(consequence preview, Level 6) and the *validator* (Scan, Level 8), not at
friction. The repo operation is **in-place with preview/confirm** — it never
silently mutates your files.

## Requirements

Python 3.9+ (standard library only — `http.server`, `webbrowser`). No pip
dependencies.

## Harness / agent interface (no browser needed)

Any orchestrator — Paperclip, Claude Code, Codex, a cron job, or `curl` — can
build a license on behalf of a user by calling the JSON entry point directly:

```bash
python3 opl_adapters.py --run adopt-full --json \
  --repo /path/to/repo \
  --maintainer "Acme Corp <ops@acme.com>" \
  --jurisdiction "United States" \
  --terms_url "https://acme.com/terms" \
  --dosp 36 \
  --confirm true
```

With `--confirm false` (default) it returns `{ok, outputs:{NOTICE,LICENSE}, consequence}`
without writing. With `--confirm true` it writes NOTICE + SPDX in place and runs
`opl_check`, returning the result in `outputs.opl_check`. Output is JSON on
stdout — designed for machines; the Studio browser UI calls the same adapter.

A real **Paperclip adapter** that dispatches this CLI from Paperclip's
orchestration layer lives under
`packages/adapters/opl-studio/` (`execute(ctx)` spawns
`opl_adapters.py --run adopt-full --json` and returns a structured
`AdapterExecutionResult`). The browser UI and the harness path share the same
internal plugin layer — neither is a "wrapper"; the Paperclip adapter is the
bridge to Paperclip's scheduler/sandbox.
