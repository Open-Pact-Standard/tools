#!/usr/bin/env python3
# SPDX-License-Identifier: OPL-1.4
"""OPL Studio — localhost adoption studio (internal capability catalogue +
live visual builder). Stdlib only, local-first, NO external network calls. Compiles
to real files you own. The browser only ever talks to 127.0.0.1:<port>.

Capabilities (adopt, scan, kit, research, adopt-full) are registered in
opl_adapters.py as an internal plugin layer. A separate packages/adapters/opl-studio/
is a real Paperclip adapter if/when this Studio should be dispatchable from
Paperclip's orchestration; these are distinct layers."

Run:  python3 opl_studio.py            # http://localhost:8771
      python3 opl_studio.py --port 9xxx --no-browser

See opl_adapters.py for the integrations catalogue (each capability is a pluggable
Adapter; the studio discovers them and renders the catalogue). This is the local
precursor to a possible hosted service; the adapters are the future API surface.
"""
from __future__ import annotations

import argparse
import html
import json
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import opl_adapters as adapters

HERE = Path(__file__).resolve().parent
KIT_DIST = HERE / "adoption-kit" / "dist"
KIT_ZIP = KIT_DIST / "opl-adoption-kit.zip"
PY = __import__("sys").executable

PAGE_HEAD = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>OPL Studio</title>
<style>
:root{--bg:#0f1115;--fg:#e6e6e6;--acc:#6cf;--mut:#9aa;--card:#171a21;--ok:#5c5;--bad:#f66;--warn:#fc6}
*{box-sizing:border-box}body{margin:0;font:15px/1.5 system-ui,sans-serif;background:var(--bg);color:var(--fg)}
nav{display:flex;gap:1rem;padding:.8rem 1.2rem;background:#11141a;border-bottom:1px solid #222}
nav a{color:var(--acc);text-decoration:none;font-weight:600}
main{max-width:1000px;margin:0 auto;padding:1.5rem}
h1{font-size:1.5rem}h2{font-size:1.1rem;margin-top:1.4rem}
.card{background:var(--card);border:1px solid #222;border-radius:10px;padding:1rem 1.2rem;margin:1rem 0}
label{display:block;margin:.5rem 0 .2rem;color:var(--mut);font-size:.82rem}
input,select,textarea{width:100%;padding:.5rem;background:#0c0e12;color:var(--fg);border:1px solid #2a2f38;border-radius:6px;font:inherit}
button{margin-top:.8rem;background:var(--acc);color:#06121f;border:0;border-radius:6px;padding:.6rem 1rem;font-weight:700;cursor:pointer}
button.sec{background:#2a2f38;color:var(--fg)}
.row{display:grid;grid-template-columns:1fr 1fr;gap:1rem}
@media(max-width:720px){.row{grid-template-columns:1fr}}
pre{background:#0c0e12;border:1px solid #222;border-radius:6px;padding:.8rem;overflow:auto;white-space:pre-wrap;max-height:340px}
.pass{color:var(--ok)}.fail{color:var(--bad)}.warn{color:var(--warn)}.info{color:var(--mut)}
.note{color:var(--mut);font-size:.85rem}.conseq{background:#13161c;border-left:3px solid var(--warn);padding:.6rem .8rem;margin:.5rem 0;font-size:.85rem}
.code{font-family:ui-monospace,Menlo,monospace;background:#0c0e12;padding:.2rem .4rem;border-radius:4px}
.cat{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:1rem}
.cap{background:var(--card);border:1px solid #222;border-radius:10px;padding:1rem;cursor:pointer}
.cap:hover{border-color:var(--acc)}
.cap h3{margin:.2rem 0;color:var(--acc);font-size:1rem}
.cap p{color:var(--mut);font-size:.82rem;margin:0}
.hidden{display:none}
</style></head><body>
<nav><a href="/">Home</a><a href="/adapters">Studio</a><a href="/kit">Kit</a></nav>
<main>"""

PAGE_FOOT = "</main></body></html>"


def page(body: str) -> bytes:
    return (PAGE_HEAD + body + PAGE_FOOT).encode("utf-8")


HOME = """
<h1>OPL Studio</h1>
<p>Adopt the Open-Pact License into your project from your browser. Local-first:
no accounts, no upload. The Studio is built on a <b>pluggable adapter catalogue</b>
— each capability (adopt, scan, research, kit) is an adapter you can extend.</p>
<div class="card"><h2>Install &amp; launch</h2>
<pre>git clone https://github.com/Open-Pact-Standard/tools
cd tools
python3 opl_studio.py</pre>
<p>Open <span class="code">http://localhost:8771</span>. Stop with <span class="code">Ctrl-C</span>.</p></div>
<div class="card"><h2>Philosophy</h2>
<p>Like Paperclip compiles UIs to code you own, OPL Studio compiles your choices into
real files in your repo — <span class="code">NOTICE</span>, <span class="code">LICENSE</span>,
SPDX headers. The app never holds your license; the artifacts live in your project.</p></div>
"""


def adapters_page() -> str:
    caps = "".join(
        f'<div class="cap" onclick="openCap(\'{a["id"]}\')"><h3>{html.escape(a["title"])}</h3>'
        f'<p>{html.escape(a["description"])}</p></div>'
        for a in adapters.catalogue()
    )
    return f"""
<h1>Studio</h1>
<p class="note">Pick a capability. Each is a registered internal tool (see opl_adapters.py).
A real Paperclip adapter for dispatching Studio from Paperclip's harness lives separately
under packages/adapters/opl-studio/ — this local site is the in-process catalogue.</p>
<div class="cat">{caps}</div>
<div id="panel" class="hidden"></div>
<script>
const CAT = {json.dumps(adapters.catalogue())};
function _esc(s){{return (s||'').replace(/</g,'&lt;');}}
function openCap(id){{
  const a = CAT.find(x=>x.id===id);
  let fields = a.params.map(p=>{{
    let inp;
    if(p.kind==='bool') inp=`<input type="checkbox" name="${{p.name}}" ${{p.default==='true'?'checked':''}} style="width:auto">`;
    else if(p.kind==='select') inp=`<select name="${{p.name}}">${{p.options.map(o=>`<option ${{o===p.default?'selected':''}}>${{o}}</option>`).join('')}}</select>`;
    else inp=`<input name="${{p.name}}" type="${{p.kind==='number'?'number':'text'}}" value="${{p.default||''}}">`;
    return `<label>${{p.label}}${{p.help?`<span class="note"> — ${{p.help}}</span>`:''}}</label>${{inp}}`;
  }}).join('');
  let live = (id==='adopt') ? `<div class="conseq" id="conseq"></div>
     <div class="row"><div><h2>NOTICE (preview)</h2><pre id="out-notice"></pre></div>
     <div><h2>LICENSE (Custom OPL, preview)</h2><pre id="out-license"></pre></div></div>`
     : (id==='custom-opl') ? `<div class="conseq" id="conseq"></div>
        <div><h2>LICENSE (Custom OPL, preview)</h2><pre id="out-license"></pre></div>
        <div><h2>NOTICE</h2><pre id="out-notice"></pre></div>`
     : (id==='scan') ? `<pre id="out"></pre><div id="diff" class="diff hidden"></div>
        <button id="applyBtn" class="hidden" onclick="applyDiff()">Apply — adopt OPL</button>` : `<pre id="out"></pre>`;
  document.getElementById('panel').className='';
  document.getElementById('panel').innerHTML = `<div class="card"><h2>${{a.title}}</h2>
     ${{fields}}
     <button onclick="runCap('${{id}}')">Run</button>
     <button class="sec" onclick="document.getElementById('panel').className='hidden'">Close</button></div>${{live}}`;
  if(id==='adopt'||id==='custom-opl') document.querySelectorAll('#panel input,#panel select').forEach(e=>e.addEventListener('input',()=>previewAdopt('${{id}}')));
}}
function collect(id){{
  const a=CAT.find(x=>x.id===id); const f={{}};
  a.params.forEach(p=>{{const el=document.querySelector(`#panel [name="${{p.name}}"]`);
    if(!el)return; f[p.name]= el.type==='checkbox'?(el.checked?'true':'false'):el.value;}});
  return f;
}}
function runCap(id){{
  const f=collect(id);
  fetch('/api/adapter',{{method:'POST',headers:{{'Content-Type':'application/json'}},
    body:JSON.stringify({{id, params:f}})}}).then(r=>r.json()).then(d=>{{
    if(id==='scan' && d.outputs && d.outputs.diff){{
      const diff = JSON.parse(d.outputs.diff);
      document.getElementById('out').textContent =
        diff.checks.map(c=>`[${{c.passed?'PASS':'FAIL'}}] ${{c.check}}: ${{c.message}}`).join('\\n');
      if(diff.proposed && Object.keys(diff.proposed).length){{
        document.getElementById('diff').classList.remove('hidden');
        document.getElementById('diff').textContent =
          Object.entries(diff.proposed).map(([k,v])=>`# ${{k}}\\n${{v}}`).join('\\n\\n');
        document.getElementById('applyBtn').classList.remove('hidden');
      }}
      return;
    }}
    if(id==='adopt' && f.write!=='true'){{ renderAdopt(d); return; }}
    let out=document.getElementById(id==='adopt'?'out-license':'out');
    out.textContent = (d.outputs?Object.entries(d.outputs).map(([k,v])=>`# ${{k}}\\n${{v}}`).join('\\n\\n'):'') + (d.messages?('\\n'+d.messages.join('\\n')):'') + (d.consequence?('\\n'+d.consequence):'');
  }});
}}
function previewAdopt(id){{
  const f=collect(id);
  fetch('/api/adapter',{{method:'POST',headers:{{'Content-Type':'application/json'}},
    body:JSON.stringify({{id, params:f}})}}).then(r=>r.json()).then(d=>{{
    if(d.outputs){{ if(d.outputs.NOTICE)document.getElementById('out-notice').textContent=d.outputs.NOTICE;
      if(d.outputs['LICENSE (Custom OPL)'])document.getElementById('out-license').textContent=d.outputs['LICENSE (Custom OPL)'];
      if(d.outputs.LICENSE)document.getElementById('out-license').textContent=d.outputs.LICENSE; }}
    var c=document.getElementById('conseq');
    if(c){{ c.textContent=(d.consequence||'')+(d.messages&&d.messages.length?('\\n'+d.messages.join('\\n')):''); }}
  }});
}}
function renderAdopt(d){{
  if(d.outputs){{ if(d.outputs.NOTICE)document.getElementById('out-notice').textContent=d.outputs.NOTICE;
    if(d.outputs['LICENSE (Custom OPL)'])document.getElementById('out-license').textContent=d.outputs['LICENSE (Custom OPL)'];
    if(d.outputs.LICENSE)document.getElementById('out-license').textContent=d.outputs.LICENSE; }}
  if(d.consequence){{ var c=document.getElementById('conseq'); if(c) c.textContent=d.consequence; }}
}}
function applyDiff(){{
  const f=collect('scan');
  const params={{repo:f.repo, maintainer:f.maintainer||'', jurisdiction:f.jurisdiction||'United States',
                terms_url:f.terms_url||'', opl_ai:f.opl_ai||'out', confirm:'true'}};
  fetch('/api/adapter',{{method:'POST',headers:{{'Content-Type':'application/json'}},
    body:JSON.stringify({{id:'adopt-full',params}})}}).then(r=>r.json()).then(d=>{{
    document.getElementById('diff').textContent =
      (d.outputs?Object.entries(d.outputs).map(([k,v])=>`# ${{k}}\\n${{v}}`).join('\\n\\n'):'') +
      (d.messages?('\\n'+d.messages.join('\\n')):'') + (d.consequence?('\\n'+d.consequence):'');
  }});
}}
</script>"""


def kit_page() -> str:
    docs = ""
    if KIT_DIST.exists():
        for f in sorted(KIT_DIST.rglob("*.md")):
            rel = f.relative_to(KIT_DIST)
            docs += f'<li><a href="/kit/{urllib.parse.quote(str(rel))}">{html.escape(str(rel))}</a></li>'
    zip_link = '<p><a href="/kit/opl-adoption-kit.zip"><button>Download Kit (.zip)</button></a></p>' if KIT_ZIP.exists() else ""
    return f"""<h1>Adoption Kit</h1><p>Read the docs, or download the whole Kit as a zip.</p>{zip_link}
<div class="card"><h2>Documents</h2><ul>{docs or '<li>(run install.sh to build)</li>'}</ul></div>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def _send(self, body: bytes, ctype: str = "text/html; charset=utf-8", code: int = 200):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        if u.path in ("/", "/index.html"):
            return self._send(page(HOME))
        if u.path == "/adapters":
            return self._send(page(adapters_page()))
        if u.path == "/kit":
            return self._send(page(kit_page()))
        if u.path.startswith("/kit/"):
            rel = urllib.parse.unquote(u.path[len("/kit/"):])
            fp = (KIT_DIST / rel).resolve()
            if (KIT_DIST in fp.parents or fp == KIT_ZIP.resolve()) and fp.exists():
                ct = "application/zip" if fp.suffix == ".zip" else "text/plain; charset=utf-8"
                return self._send(fp.read_bytes(), ct)
            return self._send(page('<div class="card fail">Not found.</div>'), code=404)
        return self._send(page('<div class="card fail">Not found.</div>'), code=404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        u = urllib.parse.urlparse(self.path)
        if u.path == "/api/adapter":
            try:
                data = json.loads(raw)
            except Exception:
                return self._send(b"bad json", code=400)
            aid = data.get("id", "")
            params = data.get("params", {})
            repo = params.get("repo", "").strip()
            root = Path(repo) if repo and Path(repo).is_dir() else None
            res = adapters.run_adapter(aid, root, params)
            return self._send(json.dumps({
                "ok": res.ok, "outputs": res.outputs,
                "messages": res.messages, "consequence": res.consequence,
            }).encode(), "application/json")
        return self._send(b"bad request", code=400)


def main() -> int:
    ap = argparse.ArgumentParser(description="OPL Studio — localhost adoption studio")
    ap.add_argument("--port", type=int, default=8771)
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()
    if not KIT_DIST.exists() or not any(KIT_DIST.iterdir()):
        adapters.run_tool("adoption-kit/make_kit.py", cwd=str(HERE))
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    url = f"http://127.0.0.1:{args.port}"
    print(f"OPL Studio running at {url}  (Ctrl-C to stop; local-only)")
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
    __import__("sys").exit(main())
