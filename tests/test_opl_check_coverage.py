# SPDX-License-Identifier: OPL-1.4
"""In-process coverage tests for opl_check.py (TDD: write tests, run, PASS).

These tests exercise every branch of opl_check.py to lift line/branch
coverage from the ~48% baseline toward ~90%:

  * check_standard_terms_url  (offline + online/monkeypatched urlopen)
  * main() in-process         (--json, --offline, --skip-remote, --check,
                                --strict, --exclude, --version, non-dir, human)
  * check_spdx_headers         (collect_files is None branch, >5 missing suffix)
  * check_notice              (copyright / jurisdiction / OPL-reference gaps)
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import opl_check
from opl_check import (
    check_notice,
    check_opl_ai,
    check_spdx_headers,
    check_standard_terms_url,
    main,
)


# --------------------------------------------------------------------------- #
# Helpers for the URL-fetch tests (monkeypatched urllib.request.urlopen)
# --------------------------------------------------------------------------- #
class FakeResp:
    """Minimal stand-in for a urllib response used as a context manager."""

    def __init__(self, content_type: str = "text/html", body: bytes = b""):
        self._content_type = content_type
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    @property
    def headers(self):
        return {"Content-Type": self._content_type}

    def read(self):
        return self._body


class FakeUrlOpen:
    """urlopen replacement that distinguishes HEAD vs GET by request method.

    - HEAD returns the configured response (default: valid text/html).
    - GET either raises (get_raises) or returns a body-bearing response.
    """

    def __init__(self, head_resp: FakeResp | None = None, get_raises: bool = False,
                 get_body: bytes = b""):
        self.head_resp = head_resp or FakeResp()
        self.get_raises = get_raises
        self.get_body = get_body

    def __call__(self, req, timeout=10):
        if getattr(req, "method", None) == "HEAD":
            return self.head_resp
        if self.get_raises:
            raise Exception("simulated GET failure")
        return FakeResp(body=self.get_body)


def write_notice(root: Path, text: str):
    (root / "NOTICE").write_text(text, encoding="utf-8")


# =========================================================================== #
# check_standard_terms_url
# =========================================================================== #
class TestStandardTermsUrl:
    def test_no_notice(self, tmp_path):
        r = check_standard_terms_url(tmp_path)
        assert r.passed is False
        assert "no NOTICE" in r.message

    def test_no_url_in_notice(self, tmp_path):
        write_notice(tmp_path, "Maintainer: Jane\nJurisdiction: CA\nOPL v1.4\n")
        r = check_standard_terms_url(tmp_path)
        assert r.passed is False
        assert "No URL found" in r.message

    def test_url_not_https_online(self, tmp_path):
        write_notice(tmp_path, "Standard Terms: http://example.com/terms\n")
        r = check_standard_terms_url(tmp_path)
        assert r.passed is False
        assert "HTTPS" in r.message

    def test_url_trailing_punct_offline_ok(self, tmp_path):
        # Trailing period must be stripped; URL stays https -> offline pass.
        write_notice(tmp_path, "Standard Terms: https://example.com/terms.\n")
        r = check_standard_terms_url(tmp_path, offline=True)
        assert r.passed is True
        assert "offline" in r.message

    def test_http_url_offline_fail(self, tmp_path):
        write_notice(tmp_path, "Standard Terms: http://insecure.example/terms\n")
        r = check_standard_terms_url(tmp_path, offline=True)
        assert r.passed is False
        assert "HTTPS" in r.message

    def test_offline_https_pass(self, tmp_path):
        write_notice(tmp_path, "Standard Terms: https://example.com/terms\n")
        r = check_standard_terms_url(tmp_path, offline=True)
        assert r.passed is True

    def test_online_head_non_html(self, tmp_path, monkeypatch):
        write_notice(tmp_path, "Standard Terms: https://example.com/terms\n")
        monkeypatch.setattr(urllib.request, "urlopen",
                            FakeUrlOpen(head_resp=FakeResp(content_type="application/json")))
        r = check_standard_terms_url(tmp_path)
        assert r.passed is False
        assert "does not return HTML" in r.message
        assert r.severity == "warning"

    def test_online_http_error(self, tmp_path, monkeypatch):
        write_notice(tmp_path, "Standard Terms: https://example.com/terms\n")
        exc = urllib.error.HTTPError("https://example.com/terms", 404, "nf", {}, None)
        monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout=10: (_ for _ in ()).throw(exc))
        r = check_standard_terms_url(tmp_path)
        assert r.passed is False
        assert "HTTP 404" in r.message

    def test_online_url_error(self, tmp_path, monkeypatch):
        write_notice(tmp_path, "Standard Terms: https://example.com/terms\n")
        exc = urllib.error.URLError("host-unreachable")
        monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout=10: (_ for _ in ()).throw(exc))
        r = check_standard_terms_url(tmp_path)
        assert r.passed is False
        assert "unreachable" in r.message
        assert r.severity == "warning"

    def test_online_generic_error(self, tmp_path, monkeypatch):
        write_notice(tmp_path, "Standard Terms: https://example.com/terms\n")
        monkeypatch.setattr(urllib.request, "urlopen",
                            lambda req, timeout=10: (_ for _ in ()).throw(RuntimeError("boom")))
        r = check_standard_terms_url(tmp_path)
        assert r.passed is False
        assert r.severity == "warning"

    def test_online_get_full_content_pass(self, tmp_path, monkeypatch):
        write_notice(tmp_path, "Standard Terms: https://example.com/terms\n")
        body = (b"<html><body>Price $10 per month fee. "
                b"Commercial use license terms agreement. "
                b"Contact us at email@example.com</body></html>")
        monkeypatch.setattr(urllib.request, "urlopen", FakeUrlOpen(get_body=body))
        r = check_standard_terms_url(tmp_path)
        assert r.passed is True
        assert "valid and publishes" in r.message

    def test_online_get_missing_keywords_warning(self, tmp_path, monkeypatch):
        write_notice(tmp_path, "Standard Terms: https://example.com/terms\n")
        body = b"<html><body>lorem ipsum dolor sit amet</body></html>"
        monkeypatch.setattr(urllib.request, "urlopen", FakeUrlOpen(get_body=body))
        r = check_standard_terms_url(tmp_path)
        assert r.passed is False
        assert r.severity == "warning"
        assert "may be missing" in r.message

    def test_online_get_exception_returns_reachable(self, tmp_path, monkeypatch):
        write_notice(tmp_path, "Standard Terms: https://example.com/terms\n")
        monkeypatch.setattr(urllib.request, "urlopen", FakeUrlOpen(get_raises=True))
        r = check_standard_terms_url(tmp_path)
        assert r.passed is True
        assert "reachable" in r.message


# =========================================================================== #
# check_spdx_headers (extra branches)
# =========================================================================== #
class TestSpdxHeadersBranches:
    def test_collect_files_unavailable(self, tmp_path, monkeypatch):
        monkeypatch.setattr(opl_check, "collect_files", None)
        monkeypatch.setattr(opl_check, "has_spdx", None)
        r = check_spdx_headers(tmp_path, [])
        assert r.passed is False
        assert "Cannot import opl_spdx_inject" in r.message
        assert r.severity == "warning"

    def test_many_missing_spdx_suffix(self, tmp_path):
        (tmp_path / "good.py").write_text("# SPDX-License-Identifier: OPL-1.4\n")
        for i in range(7):
            (tmp_path / f"missing_{i}.py").write_text(f"def f{i}(): pass\n")
        r = check_spdx_headers(tmp_path, [])
        assert r.passed is False
        assert "files missing SPDX headers" in r.message
        assert "+2 more" in r.message

    def test_exclude_pattern(self, tmp_path):
        (tmp_path / "a.py").write_text("def a(): pass\n")
        (tmp_path / "gen.py").write_text("def gen(): pass\n")
        # exclude gen.py -> only a.py remains and it lacks SPDX
        r = check_spdx_headers(tmp_path, [r"gen\.py$"])
        assert r.passed is False
        assert "1 files missing" in r.message


# =========================================================================== #
# check_notice (remaining field-gap branches)
# =========================================================================== #
class TestNoticeFieldGaps:
    def test_missing_copyright_only(self, tmp_path):
        notice = ("Standard Terms: https://example.com/terms\n"
                  "Jurisdiction: California\nOPL v1.4\n")
        write_notice(tmp_path, notice)
        r = check_notice(tmp_path)
        assert r.passed is False
        assert "copyright/maintainer" in r.message

    def test_missing_opl_reference(self, tmp_path):
        notice = ("Maintainer: Jane\n"
                  "Standard Terms: https://example.com/terms\n"
                  "Jurisdiction: California\n")
        write_notice(tmp_path, notice)
        r = check_notice(tmp_path)
        assert r.passed is False
        assert "OPL reference" in r.message

    def test_notice_txt_variant(self, tmp_path):
        notice = ("Maintainer: Jane\n"
                  "Standard Terms: https://example.com/terms\n"
                  "Jurisdiction: California\nOPL v1.4\n")
        (tmp_path / "NOTICE.txt").write_text(notice)
        r = check_notice(tmp_path)
        assert r.passed is True

    def test_no_notice_at_all(self, tmp_path):
        r = check_notice(tmp_path)
        assert r.passed is False
        assert "No NOTICE" in r.message

    def test_missing_standard_terms_url_only(self, tmp_path):
        notice = ("Maintainer: Jane\nJurisdiction: California\nOPL v1.4\n")
        write_notice(tmp_path, notice)
        r = check_notice(tmp_path)
        assert r.passed is False
        assert "standard terms URL" in r.message

    def test_missing_jurisdiction_only(self, tmp_path):
        notice = ("Maintainer: Jane\n"
                  "Standard Terms: https://example.com/terms\nOPL v1.4\n")
        write_notice(tmp_path, notice)
        r = check_notice(tmp_path)
        assert r.passed is False
        assert "jurisdiction" in r.message


class TestOplAiBranches:
    def test_no_notice(self, tmp_path):
        r = check_opl_ai(tmp_path)
        assert r.passed is False
        assert "no NOTICE" in r.message

    def test_ai_opt_out(self, tmp_path):
        write_notice(tmp_path, "Maintainer: Test\nOPL-AI: opted out.\n")
        r = check_opl_ai(tmp_path)
        assert r.passed is True
        assert "OPL-AI" in r.message



# =========================================================================== #
# main() — in-process
# =========================================================================== #
def make_compliant_repo(root: Path) -> None:
    (root / "LICENSE.md").write_text("Open-Pact License v1.4\n")
    (root / "NOTICE").write_text(
        "Maintainer: Jane Doe\n"
        "Standard Terms: https://example.com/terms\n"
        "Jurisdiction: California, United States\n"
        "OPL Version: 1.4\n"
        "OPL-AI: opted out.\n"
    )
    (root / "main.py").write_text("# SPDX-License-Identifier: OPL-1.4\nprint('hi')\n")


def run_main(argv, chdir: Path | None = None):
    saved = sys.argv
    sys.argv = argv
    cwd = None
    try:
        if chdir is not None:
            cwd = Path.cwd()
            # monkeypatch-style chdir via os
            import os
            os.chdir(chdir)
        try:
            main()
        finally:
            if cwd is not None:
                import os
                os.chdir(cwd)
    finally:
        sys.argv = saved


class TestMainInProcess:
    def test_version(self, capsys):
        with pytest.raises(SystemExit) as e:
            run_main(["opl_check.py", "--version"])
        assert e.value.code == 0
        assert "OPL Adoption Tools 1.4" in capsys.readouterr().out

    def test_json_output_pass(self, tmp_path, capsys):
        make_compliant_repo(tmp_path)
        with pytest.raises(SystemExit) as e:
            run_main(["opl_check.py", str(tmp_path), "--json", "--offline"])
        assert e.value.code == 0
        out = capsys.readouterr().out
        data = json.loads(out)
        assert isinstance(data, list)
        names = {d["check"] for d in data}
        assert {"license", "notice", "standard-terms-url", "spdx-headers", "opl-ai"} <= names

    def test_human_output_pass(self, tmp_path, capsys):
        make_compliant_repo(tmp_path)
        with pytest.raises(SystemExit) as e:
            run_main(["opl_check.py", str(tmp_path), "--offline"])
        assert e.value.code == 0
        out = capsys.readouterr().out
        assert "[PASS]" in out
        assert "passed," in out

    def test_skip_remote(self, tmp_path, capsys):
        make_compliant_repo(tmp_path)
        with pytest.raises(SystemExit) as e:
            run_main(["opl_check.py", str(tmp_path), "--skip-remote"])
        assert e.value.code == 0
        out = capsys.readouterr().out
        assert "Skipped (--skip-remote)" in out

    def test_check_mode_failing_exits_nonzero(self, tmp_path, capsys):
        # No LICENSE => license check fails (error) => --check exits 1.
        (tmp_path / "NOTICE").write_text(
            "Maintainer: Jane\nStandard Terms: https://example.com/terms\n"
            "Jurisdiction: CA\nOPL v1.4\n"
        )
        (tmp_path / "main.py").write_text("# SPDX-License-Identifier: OPL-1.4\n")
        with pytest.raises(SystemExit) as e:
            run_main(["opl_check.py", str(tmp_path), "--check", "--offline"])
        assert e.value.code == 1
        data = json.loads(capsys.readouterr().out)
        assert any(d["check"] == "license" and not d["passed"] for d in data)

    def test_strict_warning_becomes_error(self, tmp_path, capsys):
        # LICENSE present but references no OPL -> warning normally.
        (tmp_path / "LICENSE").write_text("MIT License\n")
        (tmp_path / "NOTICE").write_text(
            "Maintainer: Jane\nStandard Terms: https://example.com/terms\n"
            "Jurisdiction: CA\nOPL v1.4\n"
        )
        with pytest.raises(SystemExit) as e:
            run_main(["opl_check.py", str(tmp_path), "--offline", "--strict"])
        assert e.value.code == 1

    def test_exclude_flag(self, tmp_path, capsys):
        make_compliant_repo(tmp_path)
        # add a stray file without SPDX but excluded
        (tmp_path / "generated.py").write_text("def x(): pass\n")
        with pytest.raises(SystemExit) as e:
            run_main(["opl_check.py", str(tmp_path), "--offline",
                      "--exclude", r"generated\.py$"])
        assert e.value.code == 0

    def test_nonexistent_directory(self, tmp_path, capsys):
        missing = tmp_path / "does_not_exist"
        with pytest.raises(SystemExit) as e:
            run_main(["opl_check.py", str(missing)])
        assert e.value.code == 1
        assert "not a directory" in capsys.readouterr().err

    def test_offline_url_fail_propagates(self, tmp_path, capsys):
        # NOTICE references http (not https) -> standard-terms-url error.
        (tmp_path / "LICENSE.md").write_text("Open-Pact License v1.4\n")
        (tmp_path / "NOTICE").write_text(
            "Maintainer: Jane\nStandard Terms: http://insecure.example/terms\n"
            "Jurisdiction: CA\nOPL v1.4\n"
        )
        (tmp_path / "main.py").write_text("# SPDX-License-Identifier: OPL-1.4\n")
        with pytest.raises(SystemExit) as e:
            run_main(["opl_check.py", str(tmp_path), "--offline"])
        assert e.value.code == 1

    def test_online_path_through_main(self, tmp_path, capsys, monkeypatch):
        # Exercise the bare online branch (check_standard_terms_url(root))
        # via main with a monkeypatched urlopen returning a valid page.
        make_compliant_repo(tmp_path)
        body = (b"<html><body>Price $10 per month fee. "
                b"Commercial use license terms agreement. "
                b"Contact us at email@example.com</body></html>")
        monkeypatch.setattr(urllib.request, "urlopen", FakeUrlOpen(get_body=body))
        with pytest.raises(SystemExit) as e:
            run_main(["opl_check.py", str(tmp_path), "--check"])
        assert e.value.code == 0
        data = json.loads(capsys.readouterr().out)
        assert any(d["check"] == "standard-terms-url" and d["passed"] for d in data)
