# SPDX-License-Identifier: OPL-1.3.1
"""Tests for opl_x402.py - x402 Payment Generator"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

TOOLS_DIR = str(Path(__file__).resolve().parent.parent / "tools")
sys.path.insert(0, TOOLS_DIR)

from opl_x402 import (
    _fastapi_code,
    _flask_code,
    generate_config,
    validate_config,
)


def run_x402(*args: str) -> subprocess.CompletedProcess:
    """Run opl_x402.py with the given arguments."""
    return subprocess.run(
        [sys.executable, "opl_x402.py", *args],
        capture_output=True, text=True, cwd=TOOLS_DIR,
    )


class TestValidateConfig:
    def test_valid_config(self):
        assert validate_config("0.01", "USDC", "base") == []

    def test_negative_price(self):
        errors = validate_config("-5.00", "USDC", "base")
        assert len(errors) == 1 and "positive" in errors[0]

    def test_zero_price(self):
        assert len(validate_config("0", "USDC", "base")) == 1

    def test_invalid_price(self):
        errors = validate_config("abc", "USDC", "base")
        assert len(errors) == 1 and "Invalid price" in errors[0]

    def test_unsupported_asset(self):
        errors = validate_config("1.00", "BTC", "base")
        assert len(errors) == 1 and "Unsupported asset" in errors[0]

    def test_unsupported_chain(self):
        errors = validate_config("1.00", "USDC", "bitcoin")
        assert len(errors) == 1 and "Unsupported chain" in errors[0]

    def test_multiple_errors(self):
        assert len(validate_config("-1", "BTC", "bitcoin")) == 3


class TestGenerateFastAPICode:
    def test_generates_valid_python(self):
        compile(_fastapi_code(0.01, "USDC", "base", "Test"), "<fastapi>", "exec")

    def test_contains_402_status(self):
        code = _fastapi_code(0.01, "USDC", "base", "Test")
        assert "402" in code and "x-payment-signature" in code

    def test_contains_verification_warning(self):
        assert "Verification is NOT active" in _fastapi_code(0.01, "USDC", "base", "Test")

    def test_contains_params(self):
        code = _fastapi_code(5.00, "USDT", "ethereum", "Premium")
        assert all(x in code for x in ["USDT", "ethereum", "5.0", "Premium"])


class TestGenerateFlaskCode:
    def test_generates_valid_python(self):
        compile(_flask_code(0.01, "USDC", "base", "Test"), "<flask>", "exec")

    def test_contains_flask_and_402(self):
        code = _flask_code(0.01, "USDC", "base", "Test")
        assert "from flask import" in code and "402" in code

    def test_contains_verification_warning(self):
        assert "Verification is NOT active" in _flask_code(0.01, "USDC", "base", "Test")


class TestGenerateConfig:
    def test_config_structure(self):
        c = generate_config(1.00, "USDC", "base", "0x1234")
        assert c["x402Version"] == 1
        assert c["config"]["price"] == 1.00
        assert c["config"]["asset"] == "USDC"
        assert c["config"]["payTo"] == "0x1234"
        assert len(c["paymentChallenges"]) == 1

    def test_config_supported_networks(self):
        c = generate_config(1.00, "USDC", "base", "0x1234")
        assert "base" in c["config"]["supportedChains"]
        assert "solana" in c["config"]["supportedChains"]


class TestCLIGenerate:
    def test_fastapi_default(self):
        r = run_x402("generate", "--price", "0.01")
        assert r.returncode == 0 and "FastAPI" in r.stdout

    def test_flask(self):
        r = run_x402("generate", "--framework", "flask", "--price", "1.00")
        assert r.returncode == 0 and "flask" in r.stdout.lower()

    def test_output_file(self, tmp_path):
        out = tmp_path / "endpoint.py"
        r = run_x402("generate", "--price", "0.01", "--output", str(out))
        assert r.returncode == 0 and out.exists() and "FastAPI" in out.read_text()

    def test_invalid_price(self):
        assert run_x402("generate", "--price", "abc").returncode != 0

    def test_unsupported_asset(self):
        assert run_x402("generate", "--price", "1.00", "--asset", "BTC").returncode != 0

    def test_unsupported_chain(self):
        assert run_x402("generate", "--price", "1.00", "--chain", "bitcoin").returncode != 0


class TestCLIConfig:
    def test_config_json(self):
        r = run_x402("config", "--price", "5.00")
        assert r.returncode == 0
        c = json.loads(r.stdout)
        assert c["x402Version"] == 1 and c["config"]["price"] == 5.00

    def test_config_recipient(self):
        r = run_x402("config", "--price", "1.00", "--recipient", "0xABC")
        assert r.returncode == 0 and json.loads(r.stdout)["config"]["payTo"] == "0xABC"

    def test_default_recipient_warns(self):
        r = run_x402("config", "--price", "1.00")
        assert r.returncode == 0 and ("WARNING" in r.stderr or "burned" in r.stderr)

    def test_config_output_file(self, tmp_path):
        out = tmp_path / "x402.json"
        r = run_x402("config", "--price", "1.00", "--output", str(out))
        assert r.returncode == 0 and out.exists()

    def test_invalid_price(self):
        assert run_x402("config", "--price", "-1").returncode != 0


class TestCLIUtilities:
    def test_chains(self):
        r = run_x402("chains")
        assert r.returncode == 0 and all(x in r.stdout for x in ["base", "ethereum", "solana"])

    def test_assets(self):
        r = run_x402("assets")
        assert r.returncode == 0 and all(x in r.stdout for x in ["USDC", "USDT", "DAI"])

    def test_help(self):
        assert "x402" in run_x402("--help").stdout.lower()

    def test_no_args(self):
        assert run_x402().returncode == 1

class TestVersionConsistency:
    """Verify that all tools use __version__ (single source of truth)."""

    def test_all_tools_same_version(self):
        """All tools should use __version__ f-string, not hardcoded versions."""
        import glob as g
        import re as r
        tools_dir = Path(TOOLS_DIR)
        tools_ok = []
        for fp in sorted(tools_dir.glob("opl_*.py")):
            text = fp.read_text()
            has_fstring = bool(
                r.search(r'version=f"OPL Adoption Tools \{__version__\}' , text)
            )
            has_hardcoded = bool(
                r.search(r'version="OPL Adoption Tools [0-9]+\.[0-9]+' , text)
            )
            assert has_fstring, f"{fp.name}: should use __version__ f-string"
            assert not has_hardcoded, f"{fp.name}: still has hardcoded version"
            tools_ok.append(fp.name)
        assert len(tools_ok) == 6, f"Expected 6 tools, found {len(tools_ok)}: {tools_ok}"

    def test_init_version_is_defined(self):
        """_version.py should define __version__."""
        import re as r
        version_path = Path(TOOLS_DIR).parent / "tools" / "_version.py"
        with open(version_path) as f:
            vtext = f.read()
        m = r.search(r'__version__ = "([^"]+)"' , vtext)
        assert m, "No __version__ in _version.py"
        assert len(m.group(1).split('.')) == 3, "Version should be semver (X.Y.Z)"
