"""Tests for opl_registry_gen.py"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

TOOL = str(Path(__file__).resolve().parent.parent / "tools" / "opl_registry_gen.py")


class TestCLI:
    def test_help(self):
        result = subprocess.run([sys.executable, TOOL, "--help"], capture_output=True, text=True)
        assert result.returncode == 0
        assert "--non-interactive" in result.stdout
        assert "--maintainer" in result.stdout
        assert "--terms-url" in result.stdout

    def test_non_interactive_generates_valid_json(self, tmp_path):
        out = tmp_path / "REGISTRY.json"
        result = subprocess.run([
            sys.executable, TOOL, "--non-interactive",
            "--maintainer", "Acme Corp",
            "--jurisdiction", "Delaware, United States",
            "--terms-url", "https://acme.com/terms",
            "-o", str(out)
        ], capture_output=True, text=True)
        assert result.returncode == 0
        assert out.exists()
        data = json.loads(out.read_text())
        assert data["schema_version"] == "1.0"
        assert data["license"] == "OPL-1.3.1"
        assert data["maintainer"] == "Acme Corp"
        assert data["jurisdiction"] == "Delaware, United States"
        assert data["standard_terms_url"] == "https://acme.com/terms"
        assert "generated_at" in data
        assert isinstance(data["fee_tiers"], list)
        assert len(data["fee_tiers"]) == 3
        assert data["fee_tiers"][0]["name"] == "Small"
        assert data["fee_tiers"][0]["fee_usd"] == 0
        assert data["fee_tiers"][1]["fee_usd"] == 500
        assert data["fee_tiers"][2]["fee_usd"] == 2000
        assert isinstance(data["payment_methods"], list)
        assert len(data["payment_methods"]) >= 1
        assert data["derivative_reciprocity"] is True
        assert "OPL-1.3.1" in data["derivative_reciprocity_note"]
        assert data["ai_training"]["allowed"] is False

    def test_non_interactive_defaults(self, tmp_path):
        out = tmp_path / "REGISTRY.json"
        result = subprocess.run([
            sys.executable, TOOL, "--non-interactive", "-o", str(out)
        ], capture_output=True, text=True)
        assert result.returncode == 0
        data = json.loads(out.read_text())
        assert data["maintainer"] == "Your Name or Organization"
        assert data["jurisdiction"] == "California, United States"
        assert "example.com" in data["standard_terms_url"]
