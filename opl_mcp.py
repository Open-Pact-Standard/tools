#!/usr/bin/env python3
# SPDX-License-Identifier: OPL-1.4
"""opl-mcp — MCP server exposing the Open-Pact License Studio (OPL) to any agent
harness (Hermes, Claude Code, Codex, Cursor, …) via the Model Context Protocol.

Every tool is a thin wrapper over the Studio's JSON contract:
    python3 opl_adapters.py --run <id> --json [--key value ...]

This server holds NO license logic of its own — it delegates to opl_adapters.py,
so the capability surface stays single-sourced. No secrets are ever sent to the
LLM beyond what the tools explicitly return.

Run (stdio, the default MCP transport; see mcp/README.md for install):
    pip install fastmcp
    fastmcp run opl_mcp.py:mcp            # dev/stdin-stdout
    fastmcp install claude-code opl_mcp.py

The `fastmcp` + `mcp` packages are thin transports only; everything licensing-
related lives in the OPL tools repo. fastmcp is imported lazily so the `_run`
helper (and in-process tests) work even where the transport is absent.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = HERE / "tools"

# The MCP transport is optional for the core helper; it is imported lazily so
# _run() and tests work without fastmcp present.
mcp = None


def _run(id: str, params: dict) -> dict:
    """Run an OPL Studio adapter (canonical param dict) and return its JSON result.

    Import opl_adapters directly so the MCP layer never has to translate param
    names to CLI flags (dosp_months -> --dosp-months etc.) — the adapter's own
    param dict is the single source of truth.
    """
    try:
        sys.path.insert(0, str(TOOLS))
        import opl_adapters as adapters
        # Repo-based adapters (scan, adopt-full, migrate) need `root` derived from
        # params["repo"] — mirror the Studio's /api/adapter handler, which computes
        # root from the repo param rather than passing root=None.
        repo = (params or {}).get("repo", "").strip()
        root = Path(repo) if repo and Path(repo).is_dir() else None
        res = adapters.run_adapter(id, root, params or {})
        return {
            "ok": res.ok,
            "outputs": res.outputs,
            "messages": res.messages,
            "consequence": res.consequence,
        }
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


_CAPABILITIES = [
    "adopt",
    "custom-opl",
    "scan",
    "kit",
    "migrate",
    "research",
    "adopt-full",
]


def _setup():
    """Import the transport and register the per-capability tools."""
    global mcp
    try:
        from mcp.server.fastmcp import FastMCP
    except Exception as exc:  # fastmcp not installed — server cannot run
        mcp = None
        _setup._transport_error = str(exc)  # type: ignore[attr-defined]
        return
    mcp = FastMCP("opl-studio")

    def _cap(name: str):
        def tool(params: str = "{}") -> str:
            try:
                p = json.loads(params) if params else {}
            except Exception:
                return json.dumps({"ok": False,
                                   "error": "params must be a JSON object string"})
            return json.dumps(_run(name, p), indent=2)
        tool.__name__ = f"opl_{name.replace('-', '_')}"
        tool.__doc__ = (f"Run the OPL '{name}' capability. `params` is a JSON object "
                        f"string of the capability's fields (see opl_adapters.py / the "
                        f"Studio catalogue). Returns the Studio JSON result.")
        return mcp.tool()(tool)

    for _c in _CAPABILITIES:
        _cap(_c)

    @mcp.tool()
    def run_adapter(id: str, params: str = "{}") -> str:
        """Run any OPL Studio adapter by id. params is a JSON object string. Common
        ids: adopt, custom-opl, scan, kit, migrate, research, adopt-full."""
        try:
            p = json.loads(params) if params else {}
        except Exception:
            return json.dumps({"ok": False,
                               "error": "params must be a JSON object string"})
        return json.dumps(_run(id, p), indent=2)


# Primed on import only if the transport is available. Same names the tests use:
# opl_<capability> functions become available only after a successful _setup().
_setup()


if __name__ == "__main__":
    if mcp is None:
        sys.stderr.write("error: fastmcp not installed. Run the MCP server in an "
                         "isolated venv: python3 -m venv .venv-mcp && "
                         ".venv-mcp/bin/pip install fastmcp && .venv-mcp/bin/python opl_mcp.py\n")
        sys.exit(1)
    mcp.run()
