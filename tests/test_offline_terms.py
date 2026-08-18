# SPDX-License-Identifier: OPL-1.4
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from opl_check import check_standard_terms_url


def _notice_with(url: str, tmp_path: Path) -> Path:
    d = tmp_path / "repo"
    d.mkdir()
    (d / "NOTICE").write_text(
        f"Maintainer: Acme\nStandard Terms: {url}\nJurisdiction: US\nOPL\n"
    )
    return d


def test_offline_check_passes_without_network(tmp_path):
    repo = _notice_with("https://acme.com/terms", tmp_path)
    # offline=True must NOT call urlopen; should pass on HTTPS+present alone.
    r = check_standard_terms_url(repo, offline=True)
    assert r.passed is True
    assert "offline" in r.message.lower()


def test_offline_check_fails_on_http_not_https(tmp_path):
    repo = _notice_with("http://acme.com/terms", tmp_path)
    r = check_standard_terms_url(repo, offline=True)
    assert r.passed is False
    assert "HTTPS" in r.message


def test_offline_check_fails_when_no_url(tmp_path):
    repo = _notice_with("no url here", tmp_path)
    r = check_standard_terms_url(repo, offline=True)
    assert r.passed is False
