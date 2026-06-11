"""Tests for opl_init.py"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from opl_init import validate_url, validate_number, generate_notice, ask
import argparse


class TestValidateUrl:
    def test_valid_https(self):
        assert validate_url("https://example.com/terms") is True

    def test_invalid_http(self):
        assert validate_url("http://example.com/terms") is False

    def test_invalid_no_scheme(self):
        assert validate_url("example.com/terms") is False

    def test_invalid_empty(self):
        assert validate_url("") is False


class TestValidateNumber:
    def test_valid_in_range(self):
        assert validate_number("36", 12, 60) is True

    def test_valid_at_low(self):
        assert validate_number("12", 12, 60) is True

    def test_valid_at_high(self):
        assert validate_number("60", 12, 60) is True

    def test_below_range(self):
        assert validate_number("5", 12, 60) is False

    def test_above_range(self):
        assert validate_number("100", 12, 60) is False

    def test_non_numeric(self):
        assert validate_number("abc", 12, 60) is False

    def test_custom_range(self):
        assert validate_number("3", 1, 5) is True
        assert validate_number("6", 1, 5) is False


class TestGenerateNotice:
    def test_basic_generation(self):
        args = argparse.Namespace(
            version="1.3.1", maintainer="Jane Doe <jane@example.com>",
            jurisdiction="California, United States",
            terms_url="https://example.com/terms",
            opl_ai="opted out.", abandonment="36", trademark=None
        )
        result = generate_notice(args)
        assert "OPL Version: 1.3.1" in result
        assert "Maintainer: Jane Doe" in result
        assert "California, United States" in result
        assert "https://example.com/terms" in result
        assert "opted out" in result

    def test_with_ai_opt_in(self):
        args = argparse.Namespace(
            version="1.3.1", maintainer="Test",
            jurisdiction="Delaware", terms_url="https://example.com/terms",
            opl_ai="opted in. AI training is restricted under the OPL-AI addendum (v1.3.1).",
            abandonment="36", trademark=None
        )
        result = generate_notice(args)
        assert "opted in" in result

    def test_with_custom_abandonment(self):
        args = argparse.Namespace(
            version="1.3.1", maintainer="Test",
            jurisdiction="Delaware", terms_url="https://example.com/terms",
            opl_ai="opted out.", abandonment="24", trademark=None
        )
        result = generate_notice(args)
        assert "Abandonment Period: 24" in result

    def test_with_trademark(self):
        args = argparse.Namespace(
            version="1.3.1", maintainer="Test",
            jurisdiction="Delaware", terms_url="https://example.com/terms",
            opl_ai="opted out.", abandonment="36",
            trademark="MyProject is a registered trademark of Test Corp."
        )
        result = generate_notice(args)
        assert "Trademark Notice: MyProject" in result

    def test_default_abandonment_excluded(self):
        args = argparse.Namespace(
            version="1.3.1", maintainer="Test",
            jurisdiction="Delaware", terms_url="https://example.com/terms",
            opl_ai="opted out.", abandonment="36", trademark=None
        )
        result = generate_notice(args)
        assert "Abandonment" not in result


class TestCLI:
    def test_help(self):
        tool = str(Path(__file__).resolve().parent.parent / "tools" / "opl_init.py")
        result = subprocess.run([sys.executable, tool, "--help"], capture_output=True, text=True)
        assert result.returncode == 0
        assert "--non-interactive" in result.stdout
        assert "--maintainer" in result.stdout
        assert "--jurisdiction" in result.stdout
        assert "--terms-url" in result.stdout
        assert "--opl-ai" in result.stdout

    def test_non_interactive_generates_file(self, tmp_path):
        tool = str(Path(__file__).resolve().parent.parent / "tools" / "opl_init.py")
        out = tmp_path / "NOTICE"
        result = subprocess.run([
            sys.executable, tool, "--non-interactive",
            "--maintainer", "Test Corp <test@example.com>",
            "--jurisdiction", "California, United States",
            "--terms-url", "https://example.com/terms",
            "--output", str(out)
        ], capture_output=True, text=True)
        assert result.returncode == 0
        assert out.exists()
        content = out.read_text()
        assert "Test Corp" in content
        assert "California" in content
        assert "https://example.com/terms" in content
        assert "1.3.1" in content
