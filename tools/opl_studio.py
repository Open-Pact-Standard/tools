#!/usr/bin/env python3
# SPDX-License-Identifier: OPL-1.4
"""OPL Studio — localhost adoption studio.

A dependency-free local web app that lets a user adopt OPL into their project
without touching the terminal. Launched from the terminal:

    python3 opl_studio.py            # serves http://localhost:8771
    python3 opl_studio.py --port 9xxx --no-browser

No accounts, no network egress except what the adoption tools themselves do
(opl_check may fetch a Standard Terms URL the user declares). Everything runs
locally. This is the local precursor to a possible future hosted service.

Design notes (see ADOPTION_SYSTEM.md):
- Level 6 (information flow): every choice shows its CONSEQUENCE before commit.
- Level 8 (balancing loop): the Scan step runs opl_check and refuses to declare
  "adopted" until it passes.
- Repo writes are PREVIEWED (diff shown) and require explicit confirm. Never
  silent in-place mutation.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import shutil
import subprocess
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = HERE
KIT_DIST = HERE / "adoption-kit" / "dist"
KIT_ZIP = HERE / "adoption-kit" / "dist" / "opl-adoption-kit.zip"

PY = sys.executable


def run_tool(script: str, *args: str, cwd: str | None = None) -> tuple[int, str, str]:
    """Run an adoption tool as a subprocess; return (rc, stdout, stderr)."""
    cmd = [PY, str(TOOLS / script), *args]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=60, cwd=cwd)
        return p.returncode, p.stdout, p.stderr
    except Exception as e:  # noqa: BLE001
        return -1, "", f"failed to run {script}: {e}"


def ensure_kit_zip() -> None:
    """Build the Adoption Kit dist + a zip for download (best effort)."""
    if not KIT_DIST.exists() or not any(KIT_DIST.iterdir()):
        run_tool("adoption-kit/make_kit.py", cwd=str(HERE))
    if not KIT_ZIP.exists():
        try:
            shutil.make_archive(str(KIT_ZIP.with_suffix("")), "zip", KIT_DIST)
        except Exception:  # noqa: BLE001
            pass


# ---------------------------------------------------------------------------
# HTML fragments (vanilla; no JS framework)
# ---------------------------------------------------------------------------

PAGE_HEAD = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>OPL Studio</title>
<style>
:root{--bg:#0f1115;--fg:#e6e6e6;--acc:#6cf;--mut:#9aa;--card:#171a21;--ok:#5c5;--bad:#f66;--warn:#fc6}
*{box-sizing:border-box}body{margin:0;font:15px/1.5 system-ui,sans-serif;background:var(--bg);color:var(--fg)}
nav{display:flex;gap:1rem;padding:.8rem 1.2rem;background:#11141a;border-bottom:1px solid #222}
nav a{color:var(--acc);text-decoration:none;font-weight:600}
main{max-width:860px;margin:0 auto;padding:1.5rem}
h1{font-size:1.5rem}h2{font-size:1.15rem;margin-top:1.6rem}
.card{background:var(--card);border:1px solid #222;border-radius:10px;padding:1rem 1.2rem;margin:1rem 0}
label{display:block;margin:.5rem 0 .2rem;color:var(--mut);font-size:.85rem}
input,textarea,select{width:100%;padding:.5rem;background:#0c0e12;color:var(--fg);border:1px solid #2a2f38;border-radius:6px;font:inherit}
button{margin-top:.8rem;background:var(--acc);color:#06121f;border:0;border-radius:6px;padding:.6rem 1rem;font-weight:700;cursor:pointer}
button.sec{background:#2a2f38;color:var(--fg)}
pre{background:#0c0e12;border:1px solid #222;border-radius:6px;padding:.8rem;overflow:auto;white-space:pre-wrap}
.pass{color:var(--ok)}.fail{color:var(--bad)}.warn{color:var(--warn)}.info{color:var(--mut)}
.code{font-family:ui-monospace,Menlo,monospace;background:#0c0e12;padding:.2rem .4rem;border-radius:4px}
.note{color:var(--mut);font-size:.85rem}
</style></head><body>
<nav><a href="/">Home</a><a href="/adopt">Adopt</a><a href="/scan">Scan</a><a href="/kit">Kit</a></nav>
<main>"""

PAGE_FOOT = "</main></body></html>"


def page(body: str) -> bytes:
    return (PAGE_HEAD + body + PAGE_FOOT).encode("utf-8")


HOME = """
<h1>OPL Studio</h1>
<p>Adopt the Open-Pact License into your project from your browser. Everything
runs on your machine — no accounts, no upload. This is a local tool; a hosted
service may come later if it proves useful.</p>
<div class="card">
  <h2>Install &amp; launch</h2>
  <p class="note">From a terminal in this repo:</p>
  <pre>git clone https://github.com/Open-Pact-Standard/tools
cd tools
python3 opl_studio.py</pre>
  <p>Then open <span class="code">http://localhost:8771</span>. To stop, press
  <span class="code">Ctrl-C</span> in the terminal.</p>
</div>
<div class="card">
  <h2>What you can do here</h2>
  <ul>
    <li><b>Adopt</b> — fill a short form; preview the NOTICE/LICENSE diff; confirm to write it into your repo.</li>
    <li><b>Scan</b> — point at any repo and run the OPL compliance checker (read-only).</li>
    <li><b>Kit</b> — read the Adoption Kit docs and download them as a zip.</li>
  </ul>
</div>
"""


ADOPT_FORM = """
<h1>Adopt OPL</h1>
<p class="note">Every field shows its consequence before you commit. Nothing is
written to your repo until you confirm the preview.</p>
<form id="f" method="post" action="/adopt">
  <label>Repository path (absolute)</label>
  <input name="repo" placeholder="/home/you/my-project" required>
  <label>Maintainer (name &lt;email&gt;)</label>
  <input name="maintainer" placeholder="Jane Doe <jane@example.com>" required>
  <label>Governing Jurisdiction (any — you write it)</label>
  <input name="jurisdiction" value="United States">
  <label>Standard Terms URL (HTTPS page with your pricing)</label>
  <input name="terms_url" placeholder="https://example.com/terms" required>
  <label>OPL-AI addendum</label>
  <select name="opl_ai"><option value="out">opted out (AI training allowed)</option>
  <option value="in">opted in (AI training restricted)</option></select>
  <label>Abandonment period (months of silence → Apache-2.0)</label>
  <input name="abandonment" value="36" pattern="[0-9]+">
  <p class="note"><b>Consequence:</b> if you go silent this long, your Work auto-converts to Apache-2.0 for everyone.</p>
  <label>DOSP period (months; blank = never scheduled-convert)</label>
  <input name="dosp" placeholder="leave blank for none">
  <p class="note"><b>Consequence:</b> e.g. 36 → 3 years after each release its source becomes Apache-2.0 automatically, even if you're active. Blank keeps full control.</p>
  <label>Commercial Terms filename (optional)</label>
  <input name="commercial_terms" placeholder="leave blank to skip">
  <p class="note"><b>Consequence:</b> commercial users must pay per that published page; a dead/empty URL makes the commercial tier unenforceable.</p>
  <button type="submit" name="phase" value="preview">Preview changes</button>
</form>
"""


def adopt_preview(form: dict) -> str:
    repo = form.get("repo", "").strip()
    if not repo or not Path(repo).is_dir():
        return ADOPT_FORM + f'<div class="card fail">Repository not found: {html.escape(repo)}</div>'
    # Generate NOTICE into a temp location to preview, then diff against repo.
    import tempfile
    tmp = Path(tempfile.mkdtemp())
    rc, out, err = run_tool(
        "opl_init.py", "--non-interactive",
        "--maintainer", form.get("maintainer", ""),
        "--jurisdiction", form.get("jurisdiction", "United States"),
        "--terms-url", form.get("terms_url", ""),
        "--opl-ai", form.get("opl_ai", "out"),
        "--abandonment", form.get("abandonment", "36"),
        "--dosp", form.get("dosp", ""),
        "--commercial-terms", form.get("commercial_terms", ""),
        "--output", str(tmp / "NOTICE"),
    )
    notice_preview = (tmp / "NOTICE").read_text() if (tmp / "NOTICE").exists() else err
    existing = (Path(repo) / "NOTICE").read_text() if (Path(repo) / "NOTICE").exists() else "(no existing NOTICE)"
    # SPDX dry-run
    _, dry, _ = run_tool("opl_spdx_inject.py", repo, "--dry-run")
    return ADOPT_FORM + f"""
<div class="card">
  <h2>Preview — NOTICE that will be written to <span class="code">{html.escape(repo)}</span></h2>
  <pre>{html.escape(notice_preview)}</pre>
  <h2>Existing NOTICE (will be replaced)</h2>
  <pre>{html.escape(existing)}</pre>
  <h2>SPDX headers — files that would change</h2>
  <pre>{html.escape(dry or '(none)')}</pre>
  <form method="post" action="/adopt">
    {hidden(form)}
    <button type="submit" name="phase" value="confirm">Confirm &amp; write to my repo</button>
    <button type="submit" class="sec" name="phase" value="preview">Cancel / edit</button>
  </form>
</div>"""


def hidden(form: dict) -> str:
    return "".join(f'<input type="hidden" name="{k}" value="{html.escape(str(v))}">' for k, v in form.items())


def adopt_confirm(form: dict) -> str:
    repo = form.get("repo", "").strip()
    if not repo or not Path(repo).is_dir():
        return ADOPT_FORM + '<div class="card fail">Repository not found.</div>'
    # 1. Write NOTICE in place.
    rc1, _, err1 = run_tool(
        "opl_init.py", "--non-interactive",
        "--maintainer", form.get("maintainer", ""),
        "--jurisdiction", form.get("jurisdiction", "United States"),
        "--terms-url", form.get("terms_url", ""),
        "--opl-ai", form.get("opl_ai", "out"),
        "--abandonment", form.get("abandonment", "36"),
        "--dosp", form.get("dosp", ""),
        "--commercial-terms", form.get("commercial_terms", ""),
        "--output", str(Path(repo) / "NOTICE"),
    )
    # 2. Inject SPDX headers in place.
    rc2, out2, err2 = run_tool("opl_spdx_inject.py", repo)
    # 3. Run the validator (balancing loop) and report.
    rc3, chk, _ = run_tool("opl_check.py", "--skip-remote", repo)
    status = "pass" if rc1 == 0 and rc3 == 0 else "fail"
    cls = "pass" if status == "pass" else "fail"
    return f"""
<div class="card">
  <h2 class="{cls}">Adoption {'complete — repo passes OPL check' if status=='pass' else 'wrote files, but check reported issues'}</h2>
  <pre>opl_init: {'ok' if rc1==0 else 'ERROR '+html.escape(err1)}
opl_spdx_inject: {html.escape(out2.strip()[:400] or 'ok')}
opl_check:
{html.escape(chk)}</pre>
  <p class="note">Next: publish your Standard Terms page at the URL you declared, add the
  OPL LICENSE file to your repo root, then re-run Scan (without --skip-remote) to confirm the URL is live.</p>
  <a href="/scan"><button class="sec">Go to Scan</button></a>
</div>"""


def scan_page(form: dict | None = None) -> str:
    if not form:
        return """<h1>Scan a repo</h1>
<form method="post" action="/scan">
  <label>Repository path (absolute)</label>
  <input name="repo" placeholder="/home/you/my-project" required>
  <label><input type="checkbox" name="skip_remote" style="width:auto"> Skip remote URL check (offline)</label>
  <button type="submit">Run OPL check</button>
</form>"""
    repo = form.get("repo", "").strip()
    skip = "--skip-remote" if form.get("skip_remote") == "on" else ""
    if not repo or not Path(repo).is_dir():
        return '<div class="card fail">Repository not found: ' + html.escape(repo) + '</div>' + scan_page()
    rc, out, _ = run_tool("opl_check.py", *(skip and [skip] or []), repo)
    lines = []
    for line in out.splitlines():
        c = "pass" if "[PASS]" in line else "fail" if "[FAIL]" in line else "warn" if "[WARN]" in line else "info"
        lines.append(f'<div class="{c}">{html.escape(line)}</div>')
    verdict = "Repository passes OPL compliance ✅" if rc == 0 else "Issues found — see above"
    vcls = "pass" if rc == 0 else "fail"
    return f"""<h1>Scan results</h1>
<div class="card"><h2 class="{vcls}">{verdict}</h2>{''.join(lines)}</div>
<a href="/scan"><button class="sec">Scan another</button></a>"""


def kit_page() -> str:
    docs = ""
    if KIT_DIST.exists():
        for f in sorted(KIT_DIST.rglob("*.md")):
            rel = f.relative_to(KIT_DIST)
            docs += f'<li><a href="/kit/{urllib.parse.quote(str(rel))}">{html.escape(str(rel))}</a></li>'
    zip_link = ""
    if KIT_ZIP.exists():
        zip_link = f'<p><a href="/kit/opl-adoption-kit.zip"><button>Download Kit (.zip)</button></a></p>'
    return f"""<h1>Adoption Kit</h1>
<p>Read the docs, or download the whole Kit as a zip to keep locally.</p>
{zip_link}
<div class="card"><h2>Documents</h2><ul>{docs or '<li>(run make_kit.py to build)</li>'}</ul></div>"""


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):  # noqa: A002
        pass

    def _send(self, body: bytes, ctype: str = "text/html; charset=utf-8", code: int = 200):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        p = u.path
        if p == "/" or p == "/index.html":
            return self._send(page(HOME))
        if p == "/adopt":
            return self._send(page(ADOPT_FORM))
        if p == "/scan":
            return self._send(page(scan_page()))
        if p == "/kit":
            return self._send(page(kit_page()))
        if p.startswith("/kit/"):
            rel = urllib.parse.unquote(p[len("/kit/"):])
            fp = (KIT_DIST / rel).resolve()
            if KIT_DIST in fp.parents or fp == KIT_ZIP.resolve():
                if fp.exists():
                    ctype = "application/zip" if fp.suffix == ".zip" else "text/plain; charset=utf-8"
                    return self._send(fp.read_bytes(), ctype)
            return self._send(page('<div class="card fail">Not found.</div>'), code=404)
        return self._send(page('<div class="card fail">Not found.</div>'), code=404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode("utf-8", "ignore")
        form = dict(urllib.parse.parse_qsl(raw))
        u = urllib.parse.urlparse(self.path)
        if u.path == "/adopt":
            phase = form.get("phase", "preview")
            if phase == "confirm":
                return self._send(page(adopt_confirm(form)))
            return self._send(page(adopt_preview(form)))
        if u.path == "/scan":
            return self._send(page(scan_page(form)))
        return self._send(page('<div class="card fail">Bad request.</div>'), code=400)


def main() -> int:
    ap = argparse.ArgumentParser(description="OPL Studio — localhost adoption studio")
    ap.add_argument("--port", type=int, default=8771)
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()
    ensure_kit_zip()
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    url = f"http://127.0.0.1:{args.port}"
    print(f"OPL Studio running at {url}")
    print("Press Ctrl-C to stop. Nothing leaves this machine.")
    if not args.no_browser:
        try:
            import webbrowser
            webbrowser.open(url)
        except Exception:
            pass
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        srv.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
