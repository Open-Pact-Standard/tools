# SPDX-License-Identifier: OPL-1.4
"""In-process unit tests for opl_init.py to maximize coverage."""
from __future__ import annotations

import argparse
import builtins
import sys
import urllib.error
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from opl_init import (
    ask,
    generate_notice,
    interactive_mode,
    main,
    validate_number,
    validate_url,
    validate_url_live,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def make_input(values):
    it = iter(values)

    def _input(prompt=""):
        return next(it)

    return _input


class FakeHeaders:
    def __init__(self, content_type=""):
        self._ct = content_type

    def get(self, key, default=""):
        if key.lower() == "content-type":
            return self._ct
        return default


class FakeResponse:
    def __init__(self, status=200, content_type="text/html"):
        self.status = status
        self.headers = FakeHeaders(content_type)


# ---------------------------------------------------------------------------
# ask()
# ---------------------------------------------------------------------------
class TestAsk:
    def test_returns_value_no_validator(self, monkeypatch):
        monkeypatch.setattr(builtins, "input", lambda p: "hello")
        assert ask("Name") == "hello"

    def test_returns_default_when_blank(self, monkeypatch):
        monkeypatch.setattr(builtins, "input", lambda p: "")
        assert ask("Name", default="Bob") == "Bob"

    def test_returns_prompted_value_over_default(self, monkeypatch):
        monkeypatch.setattr(builtins, "input", lambda p: "Sue")
        assert ask("Name", default="Bob") == "Sue"

    def test_validator_rejects_then_accepts(self, monkeypatch, capsys):
        inputs = iter(["x", "valid"])
        monkeypatch.setattr(builtins, "input", lambda p: next(inputs))
        result = ask("Maintainer", validator=lambda v: len(v) > 3,
                     err_msg="Too short.")
        captured = capsys.readouterr()
        assert result == "valid"
        assert "Too short." in captured.out

    def test_validator_none_accepts_immediately(self, monkeypatch):
        monkeypatch.setattr(builtins, "input", lambda p: "anything")
        assert ask("Thing", validator=None) == "anything"


# ---------------------------------------------------------------------------
# validate_url / validate_number (already covered, kept for completeness)
# ---------------------------------------------------------------------------
class TestValidateUrl:
    @pytest.mark.parametrize("url,expected", [
        ("https://example.com", True),
        ("http://example.com", False),
        ("ftp://example.com", False),
        ("example.com", False),
        ("", False),
    ])
    def test_various(self, url, expected):
        assert validate_url(url) is expected


class TestValidateNumber:
    def test_valid(self):
        assert validate_number("36", 12, 60) is True

    def test_low_high_bounds(self):
        assert validate_number("12", 12, 60) is True
        assert validate_number("60", 12, 60) is True

    def test_out_of_range(self):
        assert validate_number("5", 12, 60) is False
        assert validate_number("100", 12, 60) is False

    def test_non_numeric(self):
        assert validate_number("abc", 12, 60) is False

    def test_default_range(self):
        assert validate_number("1") is True
        assert validate_number("120") is True
        assert validate_number("0") is False
        assert validate_number("121") is False


# ---------------------------------------------------------------------------
# validate_url_live
# ---------------------------------------------------------------------------
class TestValidateUrlLive:
    def test_success_html(self, monkeypatch):
        monkeypatch.setattr(urllib.request, "urlopen",
                            lambda req, timeout=10: FakeResponse(200, "text/html"))
        ok, msg = validate_url_live("https://example.com")
        assert ok is True
        assert msg == "OK"

    def test_success_text_plain(self, monkeypatch):
        monkeypatch.setattr(urllib.request, "urlopen",
                            lambda req, timeout=10: FakeResponse(200, "text/plain"))
        ok, _msg = validate_url_live("https://example.com")
        assert ok is True

    def test_non_html_content_type(self, monkeypatch):
        monkeypatch.setattr(urllib.request, "urlopen",
                            lambda req, timeout=10: FakeResponse(200, "application/json"))
        ok, msg = validate_url_live("https://example.com")
        assert ok is False
        assert "application/json" in msg

    def test_http_error_status(self, monkeypatch):
        monkeypatch.setattr(urllib.request, "urlopen",
                            lambda req, timeout=10: FakeResponse(404, "text/html"))
        ok, msg = validate_url_live("https://example.com")
        assert ok is False
        assert "HTTP 404" in msg

    def test_network_exception(self, monkeypatch):
        def boom(req, timeout=10):
            raise urllib.error.URLError("connection refused")
        monkeypatch.setattr(urllib.request, "urlopen", boom)
        ok, msg = validate_url_live("https://example.com")
        assert ok is False
        assert "connection refused" in msg


# ---------------------------------------------------------------------------
# generate_notice — exercise every branch
# ---------------------------------------------------------------------------
class TestGenerateNotice:
    def _base(self, **overrides):
        ns = dict(
            version="1.4",
            maintainer="Jane Doe <jane@example.com>",
            jurisdiction="California, United States",
            terms_url="https://example.com/terms",
            opl_ai="opted out.",
            abandonment="36",
            dosp="",
            commercial_terms="",
            trademark=None,
        )
        ns.update(overrides)
        return argparse.Namespace(**ns)

    def test_default_all_omitted(self):
        result = generate_notice(self._base())
        assert "OPL Version: 1.4" in result
        assert "Maintainer: Jane Doe" in result
        assert "Governing Jurisdiction: California" in result
        assert "Standard Terms URL: https://example.com/terms" in result
        assert "OPL-AI: opted out." in result
        assert "Abandonment" not in result
        assert "DOSP" not in result
        assert "Commercial Terms" not in result
        assert "Trademark" not in result
        assert result.endswith("\n")

    def test_custom_abandonment_present(self):
        result = generate_notice(self._base(abandonment="24"))
        assert "Abandonment Period: 24" in result

    def test_dosp_present(self):
        result = generate_notice(self._base(dosp="36"))
        assert "DOSP Period: 36" in result

    def test_commercial_terms_present(self):
        result = generate_notice(self._base(commercial_terms="COMMERCIAL.md"))
        assert "Commercial Terms file: COMMERCIAL.md" in result

    def test_trademark_present(self):
        result = generate_notice(self._base(trademark="MyMark® is a registered trademark"))
        assert "Trademark Notice: MyMark®" in result

    def test_ai_opt_in_text(self):
        result = generate_notice(self._base(
            opl_ai="opted in. AI training is restricted under the OPL-AI addendum (v1.4)."))
        assert "opted in" in result


# ---------------------------------------------------------------------------
# interactive_mode
# ---------------------------------------------------------------------------
# NOTE: raw_dosp / commercial_terms / trademark asks use default="" — a blank
# entry loops forever in ask() (blank is falsy, so it never validates). So we
# feed non-blank values. raw_dosp="999" is invalid -> args.dosp becomes "".
INTERACTIVE_INPUTS = [
    "Jane Doe <jane@example.com>",   # maintainer
    "Germany",                        # jurisdiction
    "https://example.com/terms",      # terms_url
    "out",                            # ai
    "36",                             # abandonment
    "999",                            # raw_dosp (invalid -> blanked to "")
    "COMMERCIAL.md",                  # commercial_terms
    "MyMark®",                        # trademark
]


class TestInteractiveMode:
    def test_basic_defaults(self, monkeypatch):
        monkeypatch.setattr(builtins, "input", make_input(list(INTERACTIVE_INPUTS)))
        # success HTML -> covers `if ok` branch
        monkeypatch.setattr(urllib.request, "urlopen",
                            lambda req, timeout=10: FakeResponse(200, "text/html"))
        args = interactive_mode()
        assert args.version == "1.4"
        assert args.maintainer == "Jane Doe <jane@example.com>"
        assert args.jurisdiction == "Germany"
        assert args.terms_url == "https://example.com/terms"
        assert args.opl_ai == "opted out."
        assert args.abandonment == "36"
        assert args.dosp == ""  # raw_dosp "999" invalid -> blanked
        assert args.commercial_terms == "COMMERCIAL.md"
        assert args.trademark == "MyMark®"

    def test_ai_opt_in_and_warning_path(self, monkeypatch):
        inputs = list(INTERACTIVE_INPUTS)
        inputs[3] = "in"  # ai -> in
        monkeypatch.setattr(builtins, "input", make_input(inputs))
        # raise -> covers `else` (WARNING) branch in interactive_mode
        def boom(req, timeout=10):
            raise urllib.error.URLError("boom")
        monkeypatch.setattr(urllib.request, "urlopen", boom)
        args = interactive_mode()
        assert "opted in" in args.opl_ai

    def test_dosp_valid_number(self, monkeypatch):
        inputs = list(INTERACTIVE_INPUTS)
        inputs[5] = "24"  # raw_dosp valid
        monkeypatch.setattr(builtins, "input", make_input(inputs))
        monkeypatch.setattr(urllib.request, "urlopen",
                            lambda req, timeout=10: FakeResponse(200, "text/html"))
        args = interactive_mode()
        assert args.dosp == "24"

    def test_dosp_invalid_number_blanked(self, monkeypatch):
        inputs = list(INTERACTIVE_INPUTS)
        inputs[5] = "999"  # raw_dosp invalid (out of range)
        monkeypatch.setattr(builtins, "input", make_input(inputs))
        monkeypatch.setattr(urllib.request, "urlopen",
                            lambda req, timeout=10: FakeResponse(200, "text/html"))
        args = interactive_mode()
        assert args.dosp == ""  # validate_number fails -> blanked


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------
class TestMain:
    def test_non_interactive_writes_file(self, tmp_path, monkeypatch):
        out = tmp_path / "NOTICE"
        monkeypatch.setattr(sys, "argv", [
            "opl_init.py", "--non-interactive",
            "--maintainer", "Test Corp <test@example.com>",
            "--jurisdiction", "California, United States",
            "--terms-url", "https://example.com/terms",
            "--output", str(out),
        ])
        main()
        assert out.exists()
        content = out.read_text()
        assert "Test Corp" in content
        assert "California" in content
        assert "https://example.com/terms" in content
        assert "OPL Version: 1.4" in content

    def test_non_interactive_ai_in_and_optionals(self, tmp_path, monkeypatch):
        out = tmp_path / "NOTICE"
        monkeypatch.setattr(sys, "argv", [
            "opl_init.py", "--non-interactive",
            "--maintainer", "X",
            "--jurisdiction", "US",
            "--terms-url", "https://x.com/t",
            "--opl-ai", "in",
            "--abandonment", "24",
            "--dosp", "36",
            "--commercial-terms", "COMMERCIAL.md",
            "--trademark", "MyMark®",
            "--output", str(out),
        ])
        main()
        content = out.read_text()
        assert "opted in" in content
        assert "Abandonment Period: 24" in content
        assert "DOSP Period: 36" in content
        assert "Commercial Terms file: COMMERCIAL.md" in content
        assert "Trademark Notice: MyMark®" in content

    def test_non_interactive_missing_required_exits(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", [
            "opl_init.py", "--non-interactive",
            "--maintainer", "X",
            # missing jurisdiction and terms-url
        ])
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1

    def test_interactive_main_writes_file(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        inputs = list(INTERACTIVE_INPUTS)
        inputs[6] = "COMMERCIAL.md"  # commercial_terms truthy -> covers extra next-steps
        monkeypatch.setattr(builtins, "input", make_input(inputs))
        monkeypatch.setattr(urllib.request, "urlopen",
                            lambda req, timeout=10: FakeResponse(200, "text/html"))
        monkeypatch.setattr(sys, "argv", ["opl_init.py"])  # no --non-interactive
        main()
        out = tmp_path / "NOTICE"
        assert out.exists()
        content = out.read_text()
        assert "Jane Doe" in content
        assert "COMMERCIAL.md" in content

    def test_interactive_main_overwrite_abort(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        out = tmp_path / "NOTICE"
        out.write_text("PRE-EXISTING CONTENT\n")
        # inputs: 8 asks, then the overwrite prompt answer "n"
        inputs = list(INTERACTIVE_INPUTS) + ["n"]
        monkeypatch.setattr(builtins, "input", make_input(inputs))
        monkeypatch.setattr(urllib.request, "urlopen",
                            lambda req, timeout=10: FakeResponse(200, "text/html"))
        monkeypatch.setattr(sys, "argv", ["opl_init.py"])
        main()
        # file must remain unchanged (aborted)
        assert out.read_text() == "PRE-EXISTING CONTENT\n"

    def test_interactive_main_overwrite_confirm(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        out = tmp_path / "NOTICE"
        out.write_text("PRE-EXISTING CONTENT\n")
        inputs = list(INTERACTIVE_INPUTS) + ["y"]
        monkeypatch.setattr(builtins, "input", make_input(inputs))
        monkeypatch.setattr(urllib.request, "urlopen",
                            lambda req, timeout=10: FakeResponse(200, "text/html"))
        monkeypatch.setattr(sys, "argv", ["opl_init.py"])
        main()
        assert "Jane Doe" in out.read_text()
