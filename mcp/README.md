# OPL MCP server

Exposes the **Open-Pact License Studio** to any agent harness that speaks the
[Model Context Protocol](https://modelcontextprotocol.io) — Hermes, Claude Code,
Codex, Cursor, Goose, and others.

Single file: [`../opl_mcp.py`](../opl_mcp.py). It is a *thin transport* — it
holds no license logic, delegating every capability to `opl_adapters.py`
(the same JSON contract the browser Studio and the CLI use), so the capability
surface stays single-sourced.

## Installed tools

| Tool | Adapter | What it does |
|------|---------|--------------|
| `opl_adopt` | adopt | Generate NOTICE + LICENSE (preview or write into a repo) |
| `opl_custom_opl` | custom-opl | Build a bespoke OPL variant from 8 vetted fragment slots |
| `opl_scan` | scan | Read-only compliance check (report or diff) |
| `opl_kit` | kit | Adoption Kit docs / zip |
| `opl_migrate` | migrate | Migrate a repo from MIT/Apache/GPL to OPL |
| `opl_research` | research | Jurisdiction research |
| `opl_adopt_full` | adopt-full | Full adopt: write NOTICE + inject SPDX + validate |
| `run_adapter` | any | Generic dispatch by adapter id |

Each per-capability tool takes one argument: `params`, a JSON object string with
the capability's fields (the same fields `opl_adapters.py` accepts).

## Install & run

Run in an **isolated** venv so it never interferes with a harness's own Python
packages (Hermes ships its own `mcp` SDK; do not overwrite it):

```bash
cd <open-pact-tools>
python3 -m venv .venv-mcp
.venv-mcp/bin/pip install "fastmcp<4"
.venv-mcp/bin/python opl_mcp.py           # stdio transport
```

Register with a client (optional):

```bash
# Claude Code / Claude Desktop / Cursor / Goose
.venv-mcp/bin/fastmcp install claude-code ./opl_mcp.py
```

For Hermes, add a server entry in `~/.hermes/config.yaml` pointing at the
isolated venv's python running `opl_mcp.py` (see the `native-mcp` skill).

## Params format

Every tool takes `params` as a JSON object *string*. Example:

```
opl_custom_opl params='{"out":"/tmp/custom","maintainer":"Acme <ops@acme.com>",
                       "terms_url":"https://acme.com/terms","dosp":"months",
                       "dosp_months":"24"}'
```

Returns the Studio JSON result: `{ok, outputs, messages, consequence}`.

## Notes
- **No secrets** are sent to the harness beyond what the tools return.
- The MCP layer does **not** auto-run the legal-skill validation gate
  (`VALIDATION.md` is generated for the user to run separately).
- License: the parent tools repo is OPL-1.4.