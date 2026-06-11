# Open-Pact Standard — Adoption Tools

Free, open-source tools for adopting the [Open-Pact License (OPL) v1.3.1](https://github.com/Open-Pact-Standard/license).

These tools help maintainers configure, validate, and manage their OPL-licensed repositories.
All tools are standalone Python scripts with no external dependencies (standard library only).

## Quick Start

```bash
# 1. Generate your NOTICE file
python3 tools/opl_init.py

# 2. Add SPDX headers to all source files
python3 tools/opl_spdx_inject.py .

# 3. Validate your setup
python3 tools/opl_check.py .

# 4. (Optional) Generate a REGISTRY.json for Tier 1 adoption
python3 tools/opl_registry_gen.py
```

## Tools

### License Adoption

| Tool | Description |
|------|-------------|
| [`opl_init.py`](tools/opl_init.py) | **NOTICE Generator** — Interactive CLI that creates a valid NOTICE file with all required fields: maintainer, jurisdiction, Standard Terms URL, OPL-AI opt-in, and more. |
| [`opl_spdx_inject.py`](tools/opl_spdx_inject.py) | **SPDX Header Injector** — Scans a repository and adds `SPDX-License-Identifier: OPL-1.3.1` to every source file. Supports 60+ languages. Respects shebangs, skips binaries and vendored deps. |
| [`opl_check.py`](tools/opl_check.py) | **Compliance Checker** — Validates that your repo is correctly configured: LICENSE.md exists, NOTICE has required fields, Standard Terms URL is reachable and returns HTML, all files have SPDX headers. |
| [`opl_registry_gen.py`](tools/opl_registry_gen.py) | **Registry Generator** — Creates a `REGISTRY.json` for Tier 1 adopters who want to publish a structured fee schedule so licensees can self-serve. |
| [`opl_migrate.py`](tools/opl_migrate.py) | **Migration Helper** — For projects switching from MIT, Apache-2.0, GPL, or BSD to OPL. Auto-detects current license, identifies files needing updates, and generates a migration report. |

### Canary Tokens (OPL-1.1 Legacy)

| Tool | Description |
|------|-------------|
| [`canary_embedder.py`](canary_embedder.py) | Embeds canary tokens into text and binary files to detect unauthorized redistribution. |
| [`js_embedder.py`](js_embedder.py) | JavaScript-specific canary token embedder for web assets. |
| [`cicd_pipeline.py`](cicd_pipeline.py) | CI/CD pipeline integration for automated canary token embedding. |

### Standard Terms Template

| File | Description |
|------|-------------|
| [`standard-terms.html`](tools/standard-terms.html) | Ready-to-customize HTML page for publishing your Standard Terms. Pre-filled with 5 payment patterns (Stripe, GitHub Sponsors, email, smart contract, tiered pricing). Host this at the URL you declare in your NOTICE file. |

## Detailed Usage

### `opl_init.py` — NOTICE Generator

```bash
# Interactive mode (recommended)
python3 tools/opl_init.py

# Non-interactive with flags
python3 tools/opl_init.py --non-interactive \
  --maintainer "Acme Corp" \
  --jurisdiction "California, United States" \
  --terms-url "https://acme.com/standard-terms"

# Custom output path
python3 tools/opl_init.py --output NOTICE.md
```

### `opl_spdx_inject.py` — SPDX Header Injector

```bash
# Dry run — see what would change
python3 tools/opl_spdx_inject.py . --dry-run

# Apply changes
python3 tools/opl_spdx_inject.py .

# Check only (CI-friendly — exits non-zero if headers are missing)
python3 tools/opl_spdx_inject.py . --check

# Exclude specific paths
python3 tools/opl_spdx_inject.py . --exclude "generated/" --exclude "\.min\.js$"
```

### `opl_check.py` — Compliance Checker

```bash
# Full check
python3 tools/opl_check.py .

# JSON output for CI
python3 tools/opl_check.py . --json

# Strict mode (warnings become errors)
python3 tools/opl_check.py . --strict

# Skip URL reachability check (offline)
python3 tools/opl_check.py . --skip-remote
```

### `opl_registry_gen.py` — Registry Generator

```bash
# Interactive mode
python3 tools/opl_registry_gen.py

# Non-interactive
python3 tools/opl_registry_gen.py --non-interactive \
  --maintainer "Acme Corp" \
  --jurisdiction "California, United States" \
  --terms-url "https://acme.com/standard-terms" \
  --output REGISTRY.json
```

### `opl_migrate.py` — Migration Helper

```bash
# Auto-detect current license and show migration plan
python3 tools/opl_migrate.py .

# Specify current license
python3 tools/opl_migrate.py . --from MIT

# Generate a migration report
python3 tools/opl_migrate.py . --from Apache-2.0 --report

# Dry run
python3 tools/opl_migrate.py . --from MIT --dry-run
```

## CI/CD Integration

Add OPL compliance checks to your CI pipeline:

```yaml
# GitHub Actions example
name: OPL Compliance
on: [push, pull_request]
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Check SPDX headers
        run: python3 tools/opl_spdx_inject.py . --check
      - name: Check OPL compliance
        run: python3 tools/opl_check.py . --skip-remote
```

## Requirements

- Python 3.10+
- No external dependencies (standard library only)
- `opl_check.py` URL validation requires network access (skip with `--skip-remote`)

## License

These tools are provided as free examples for the OPL community.
See the [Open-Pact License v1.3.1](https://github.com/Open-Pact-Standard/license/blob/main/LICENSE.md) for the license text itself.
