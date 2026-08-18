# SPDX-License-Identifier: OPL-1.4
"""In-process tests for opl_mcp.py — the MCP server's adapter dispatch helper.

The helper `_run` is exercised directly (no MCP broker needed); it proves the
tool surface maps onto the real opl_adapters registry. The FastMCP tool
registration is lazy (requiring the optional transport), so these tests only
assert tool names when the transport is available in the environment.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import opl_mcp as m


def test_run_custom_opl():
    res = m._run("custom-opl", {
        "out": "/tmp/mcp_test_custom", "maintainer": "Acme <ops@acme.com>",
        "terms_url": "https://acme.com/terms", "dosp": "months", "dosp_months": "24",
    })
    assert res["ok"] is True
    assert "LICENSE" in res["outputs"]
    assert "Customization Schedule" in res["outputs"]["LICENSE"]


def test_run_unknown_adapter():
    res = m._run("does-not-exist", {})
    assert res["ok"] is False


def test_run_scan_offline(tmp_path):
    res = m._run("scan", {"repo": str(tmp_path), "mode": "report", "skip_remote": "true"})
    assert "ok" in res


def test_run_custom_opl_hard_block():
    res = m._run("custom-opl", {
        "out": "/tmp/mcp_test_block", "dosp": "forever_frozen",
        "fair_source_label": "fair_source",
    })
    assert res["ok"] is False
    assert any("HARD BLOCK" in x for x in res["messages"])


def test_run_adopt_preview():
    # License preview assembles even when full NOTICE generation needs more input.
    res = m._run("adopt", {"write": "false", "maintainer": "Acme <ops@acme.com>"})
    assert "LICENSE (Custom OPL)" in res.get("outputs", {})


def test_capability_ids_lazy():
    # _CAPABILITIES is always populated; tool registration depends on fastmcp.
    assert "custom-opl" in m._CAPABILITIES


def test_tools_registered_when_transport_present():
    # If fastmcp is installed in this env, the modules must have registered the
    # per-capability tools plus the generic dispatcher.
    if m.mcp is not None:
        for expected in ("opl_adopt", "opl_custom_opl", "opl_scan", "opl_kit",
                         "opl_migrate", "opl_research", "opl_adopt_full", "run_adapter"):
            assert callable(getattr(m, expected, None)), f"missing {expected}"
