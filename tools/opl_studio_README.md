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
- **Scan** — point at any repo and run `opl_check` read-only to see if it's
  OPL-compliant.
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
