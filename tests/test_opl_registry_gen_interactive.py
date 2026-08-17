# SPDX-License-Identifier: OPL-1.4
"""Tests for opl_registry_gen.py interactive ask helpers + in-process main paths."""
from __future__ import annotations

import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import opl_registry_gen as rg


def _run_main(argv):
    old = sys.argv
    sys.argv = ["opl_registry_gen.py", *argv]
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            rg.main()
        return 0, buf.getvalue()
    except SystemExit as e:
        return int(e.code or 0), buf.getvalue()
    finally:
        sys.argv = old


class TestAskHelpers:
    def test_ask_returns_value(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda p: "Acme")
        assert rg.ask("Name") == "Acme"

    def test_ask_default_when_empty(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda p: "")
        assert rg.ask("Name", default="Def") == "Def"

    def test_ask_required_loops_on_empty_then_accepts(self, monkeypatch):
        # ask() has no validator; it requires a non-empty value (or a default).
        # Feed "" then "good": first empty (no default) re-prompts, second accepted.
        seq = iter(["", "good"])
        monkeypatch.setattr("builtins.input", lambda p: next(seq))
        assert rg.ask("X") == "good"

    def test_ask_choice(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda p: "2")
        assert rg.ask_choice("Pick", ["a", "b", "c"]) == "b"

    def test_ask_yes_no_default_true(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda p: "")
        assert rg.ask_yes_no("OK?", default=True) is True

    def test_ask_yes_no_yes(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda p: "yes")
        assert rg.ask_yes_no("Opt in?") is True

    def test_ask_yes_no_out(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda p: "no")
        assert rg.ask_yes_no("Opt in?") is False


class TestNonInteractiveMain:
    def test_non_interactive_writes_registry(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rc, _ = _run_main([
            "--non-interactive",
            "--maintainer", "Acme <a@acme.com>",
            "--jurisdiction", "United States",
            "--terms-url", "https://acme.com/terms",
            "--output", str(tmp_path / "REGISTRY.json"),
        ])
        assert rc == 0
        data = json.loads((tmp_path / "REGISTRY.json").read_text())
        assert data["maintainer"] == "Acme <a@acme.com>"
        assert data["license"] == "OPL-1.4"


class TestInteractiveMain:
    def _drive(self, monkeypatch, answers):
        seq = iter(answers)
        monkeypatch.setattr("builtins.input", lambda p: next(seq))

    def test_full_interactive_flow(self, tmp_path, monkeypatch):
        # maintainer, jurisdiction choice, terms url, one fee tier (name,
        # desc, fee, conditions), done, one payment method + details, finish,
        # reciprocity yes, ai training no.
        self._drive(monkeypatch, [
            "Acme Corp",              # maintainer
            "1",                      # jurisdiction -> California, United States
            "https://acme.com/t",     # terms url
            "Small",                  # tier name
            "Fewer than 10 employees",  # tier description
            "0",                      # tier fee
            "Free tier",              # tier conditions
            "done",                   # finish tier loop
            "1",                      # payment method -> Stripe
            "https://pay.acme.com",   # payment details (url)
            "0",                      # finish payment loop
            "y",                      # derivative reciprocity
            "n",                      # ai training
        ])
        out = tmp_path / "REGISTRY.json"
        rc, _stdout = _run_main(["--output", str(out)])
        assert rc == 0
        data = json.loads(out.read_text())
        assert data["maintainer"] == "Acme Corp"
        assert data["jurisdiction"] == "California, United States"
        assert data["fee_tiers"][0]["name"] == "Small"
        assert data["fee_tiers"][0]["fee_usd"] == 0
        assert data["payment_methods"][0]["method"] == "stripe"
        assert data["payment_methods"][0]["url"] == "https://pay.acme.com"
        assert data["derivative_reciprocity"] is True
        assert data["ai_training"]["allowed"] is False

    def test_interactive_all_defaults(self, tmp_path, monkeypatch):
        # Empty answers everywhere: default jurisdiction, default Standard
        # tier, default email payment, reciprocity default True, AI default
        # False. Also a non-HTTPS terms URL triggers the warning.
        self._drive(monkeypatch, [
            "Acme",                   # maintainer
            "",                       # jurisdiction -> default California
            "http://acme.com/t",      # terms url (non-HTTPS -> warning)
            "done",                   # no tiers -> default Standard
            "",                       # payment loop: empty -> finish (default email)
            "",                       # reciprocity default True
            "",                       # ai default False
        ])
        out = tmp_path / "REGISTRY.json"
        rc, stdout = _run_main(["--output", str(out)])
        assert rc == 0
        data = json.loads(out.read_text())
        assert data["jurisdiction"] == "California, United States"
        assert data["fee_tiers"][0]["name"] == "Standard"
        assert data["payment_methods"][0]["method"] == "email"
        assert data["derivative_reciprocity"] is True
        assert data["ai_training"]["allowed"] is False
        assert "Warning" in stdout  # non-HTTPS terms URL

    def test_interactive_invalid_then_valid(self, tmp_path, monkeypatch):
        # Invalid jurisdiction choice reprompts; invalid tier fee defaults
        # to 0; out-of-range payment choice is ignored.
        self._drive(monkeypatch, [
            "A",                      # maintainer
            "abc",                    # invalid jurisdiction choice
            "3",                      # -> New York, United States
            "https://x.com",          # terms url
            "T1",                     # tier name
            "d",                      # tier description
            "bad",                    # invalid fee -> 0
            "c",                      # tier conditions
            "done",                   # finish tiers
            "99",                     # out-of-range payment choice (ignored)
            "0",                      # finish payments
            "n",                      # reciprocity -> False
            "y",                      # ai training -> True
        ])
        out = tmp_path / "REGISTRY.json"
        rc, _stdout = _run_main(["--output", str(out)])
        assert rc == 0
        data = json.loads(out.read_text())
        assert data["jurisdiction"] == "New York, United States"
        assert data["fee_tiers"][0]["fee_usd"] == 0
        assert data["derivative_reciprocity"] is False
        assert data["ai_training"]["allowed"] is True
