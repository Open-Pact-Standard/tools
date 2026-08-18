# SPDX-License-Identifier: OPL-1.4
"""In-process tests for opl_studio.py — page rendering + HTTP handler routing.

Drives the Handler class without a real socket by substituting a fake
`self` carrying the methods the handler calls (send_response, send_header,
end_headers, wfile, headers). This exercises do_GET/do_POST routing and the
page-builder functions for coverage.
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import opl_studio as studio


class FakeHandler:
    """Minimal stand-in for BaseHTTPRequestHandler that captures output."""

    def __init__(self, path: str, method: str = "GET", body: bytes = b""):
        self.path = path
        self.command = method
        self._body = body
        self.headers = SimpleNamespace(
            get=lambda k, d=None: str(len(body)) if k == "Content-Length" else d
        )
        self.rfile = io.BytesIO(body)
        self.wfile = io.BytesIO()
        self.sent = SimpleNamespace(code=200, ctype="", body=b"")
        self._resp_code = 200
        self._headers = {}

    def send_response(self, code):
        self._resp_code = code
        self.sent.code = code

    def send_header(self, k, v):
        self._headers[k] = v

    def end_headers(self):
        pass

    def _send(self, body: bytes, ctype: str = "text/html; charset=utf-8", code: int = 200):
        self.sent.code = code
        self.sent.ctype = ctype
        self.wfile.write(body)
        self._resp_code = code

    def read_body(self) -> bytes:
        return self.wfile.getvalue()


def _handler(path: str, method: str = "GET", body: bytes = b"") -> FakeHandler:
    return FakeHandler(path, method, body)


def test_page_wraps_head_and_foot():
    out = studio.page("<h1>Hi</h1>").decode()
    assert out.startswith("<!doctype html>")
    assert "<h1>Hi</h1>" in out
    assert out.strip().endswith("</html>")


def test_adapters_page_renders_catalogue():
    out = studio.adapters_page()
    ids = [a["id"] for a in studio.adapters.catalogue()]
    for i in ids:
        assert i in out


def test_adapters_js_has_no_broken_newlines():
    """Regression guard for the 'click does nothing' bug: the page is generated
    by a Python f-string, and escaped JS newlines (\\n inside .join('\\n')) were
    being converted to real newlines, producing a syntax error that killed the
    entire script block (clicking a capability did nothing).

    This checks every JS string-literal newline escape survived as '\\n'
    (backslash + n), not a raw newline byte inside quotes.
    """
    out = studio.adapters_page()
    import re
    script = re.search(r"<script>(.*?)</script>", out, re.S).group(1)
    i = 0
    n_joins = 0
    while True:
        i = script.find("join('", i)
        if i < 0:
            break
        n_joins += 1
        q = script.find("'", i)
        e = script.find("'", q + 1)
        arg = script[q + 1:e]
        # A real newline inside the single-quoted arg is a break.
        assert "\n" not in arg, f"broken JS newline in join at offset {i}: {arg!r}"
        # Must be the JS-valid escape (backslash + n), not a bare backslash mess.
        assert "\\n" in arg or arg == "", f"unexpected join arg {arg!r}"
        i = q + 1
    assert n_joins >= 4, f"expected several join calls, got {n_joins}"


def test_kit_page_no_kit_dir():
    out = studio.kit_page()
    assert "Adoption Kit" in out


def test_do_get_home():
    h = _handler("/")
    studio.Handler.do_GET(h)
    assert h._resp_code == 200
    assert "OPL Studio" in h.read_body().decode()


def test_do_get_adapters():
    h = _handler("/adapters")
    studio.Handler.do_GET(h)
    assert h._resp_code == 200
    assert "Studio" in h.read_body().decode()


def test_do_get_kit():
    h = _handler("/kit")
    studio.Handler.do_GET(h)
    assert h._resp_code == 200
    assert "Adoption Kit" in h.read_body().decode()


def test_do_get_unknown_404():
    h = _handler("/nope")
    studio.Handler.do_GET(h)
    assert h._resp_code == 404
    assert "Not found" in h.read_body().decode()


def test_do_get_kit_missing_file_404():
    h = _handler("/kit/does-not-exist.md")
    studio.Handler.do_GET(h)
    assert h._resp_code == 404


def test_do_post_api_adapter_unknown_id():
    payload = json.dumps({"id": "nope", "params": {}}).encode()
    h = _handler("/api/adapter", "POST", payload)
    studio.Handler.do_POST(h)
    assert h._resp_code == 200
    data = json.loads(h.read_body())
    assert data["ok"] is False


def test_do_post_api_adapter_scan_report():
    payload = json.dumps({
        "id": "scan", "params": {
            "repo": str(Path(__file__).resolve().parent.parent),
            "mode": "report", "skip_remote": "true",
        }
    }).encode()
    h = _handler("/api/adapter", "POST", payload)
    studio.Handler.do_POST(h)
    assert h._resp_code == 200
    data = json.loads(h.read_body())
    assert "outputs" in data


def test_do_post_api_adapter_custom_opl(tmp_path):
    payload = json.dumps({
        "id": "custom-opl", "params": {
            "out": str(tmp_path / "out"),
            "maintainer": "Acme <ops@acme.com>",
            "terms_url": "https://acme.com/terms",
        }
    }).encode()
    h = _handler("/api/adapter", "POST", payload)
    studio.Handler.do_POST(h)
    assert h._resp_code == 200
    data = json.loads(h.read_body())
    assert data["ok"] is True
    assert "LICENSE" in data["outputs"]


def test_do_post_api_adapter_custom_opl_hard_block(tmp_path):
    payload = json.dumps({
        "id": "custom-opl", "params": {
            "out": str(tmp_path / "out"),
            "dosp": "forever_frozen", "fair_source_label": "fair_source",
        }
    }).encode()
    h = _handler("/api/adapter", "POST", payload)
    studio.Handler.do_POST(h)
    data = json.loads(h.read_body())
    assert data["ok"] is False
    assert any("HARD BLOCK" in m for m in data["messages"])


def test_do_post_api_adapter_bad_json():
    h = _handler("/api/adapter", "POST", b"{not json")
    studio.Handler.do_POST(h)
    assert h._resp_code == 400


def test_do_post_unknown_path_400():
    h = _handler("/unknown", "POST", b"{}")
    studio.Handler.do_POST(h)
    assert h._resp_code == 400


def test_main_parses_args_and_binds_localhost(monkeypatch):
    captured = {}

    class FakeServer:
        def __init__(self, addr, handler):
            captured["addr"] = addr

        def serve_forever(self):
            return None

        def server_close(self):
            return None

    monkeypatch.setattr(studio, "ThreadingHTTPServer", FakeServer)
    monkeypatch.setattr(studio.adapters, "run_tool", lambda *a, **k: None)

    monkeypatch.setattr(sys, "argv", ["opl_studio.py", "--port", "9123", "--no-browser"])
    rc = studio.main()
    assert rc == 0
    assert captured["addr"] == ("127.0.0.1", 9123)


def _real_send(h):
    """Bind the REAL Handler._send onto the fake so its body is exercised."""
    h._send = studio.Handler._send.__get__(h)
    return h


def test_real_send_and_log_message():
    h = _real_send(_handler("/"))
    studio.Handler.do_GET(h)
    assert h._resp_code == 200
    assert h.read_body()
    assert h._headers["Content-Type"].startswith("text/html")
    assert h._headers["Content-Length"] == str(len(h.read_body()))
    # log_message is a no-op; calling it directly covers the override.
    studio.Handler.log_message(h, "GET %s", "/")


def test_do_get_kit_serves_text_file(tmp_path, monkeypatch):
    (tmp_path / "GUIDE.md").write_text("# Guide\n")
    monkeypatch.setattr(studio, "KIT_DIST", tmp_path)
    h = _real_send(_handler("/kit/GUIDE.md"))
    studio.Handler.do_GET(h)
    assert h._resp_code == 200
    assert b"# Guide" in h.read_body()
    assert h._headers["Content-Type"].startswith("text/plain")


def test_do_get_kit_serves_zip(tmp_path, monkeypatch):
    (tmp_path / "kit.zip").write_bytes(b"PK\x03\x04rest")
    monkeypatch.setattr(studio, "KIT_DIST", tmp_path)
    h = _real_send(_handler("/kit/kit.zip"))
    studio.Handler.do_GET(h)
    assert h._resp_code == 200
    assert h._headers["Content-Type"] == "application/zip"


def test_do_get_kit_traversal_blocked(tmp_path, monkeypatch):
    (tmp_path / "sub").mkdir()
    monkeypatch.setattr(studio, "KIT_DIST", tmp_path / "sub")
    h = _real_send(_handler("/kit/../secret.txt"))
    studio.Handler.do_GET(h)
    assert h._resp_code == 404


def test_kit_page_lists_docs_and_zip(tmp_path, monkeypatch):
    (tmp_path / "GUIDE.md").write_text("# Guide\n")
    (tmp_path / "opl-adoption-kit.zip").write_bytes(b"PK")
    monkeypatch.setattr(studio, "KIT_DIST", tmp_path)
    monkeypatch.setattr(studio, "KIT_ZIP", tmp_path / "opl-adoption-kit.zip")
    out = studio.kit_page()
    assert "GUIDE.md" in out
    assert "opl-adoption-kit.zip" in out


def test_main_builds_kit_when_dist_missing(tmp_path, monkeypatch):
    calls = []

    class FakeServer:
        def __init__(self, addr, handler):
            pass

        def serve_forever(self):
            return None

        def server_close(self):
            return None

    monkeypatch.setattr(studio, "KIT_DIST", tmp_path / "does-not-exist")
    monkeypatch.setattr(studio, "ThreadingHTTPServer", FakeServer)
    monkeypatch.setattr(studio.adapters, "run_tool", lambda *a, **k: calls.append(a))
    monkeypatch.setattr(sys, "argv", ["opl_studio.py", "--port", "9126", "--no-browser"])
    rc = studio.main()
    assert rc == 0
    assert calls, "make_kit should run when KIT_DIST is missing"


def test_main_webbrowser_and_keyboardinterrupt(monkeypatch):
    class FakeServer:
        def __init__(self, addr, handler):
            pass

        def serve_forever(self):
            raise KeyboardInterrupt

        def server_close(self):
            pass

    monkeypatch.setattr(studio, "ThreadingHTTPServer", FakeServer)
    monkeypatch.setattr(studio.adapters, "run_tool", lambda *a, **k: None)
    # webbrowser.open is imported inside main(); patch the module attribute so
    # no real browser window opens.
    monkeypatch.setattr("webbrowser.open", lambda url: True)
    monkeypatch.setattr(sys, "argv", ["opl_studio.py", "--port", "9127"])  # browser branch
    rc = studio.main()
    assert rc == 0
