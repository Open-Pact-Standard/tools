# OPL Studio — UI diff view + offline-first validity gate

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Make the `scan` diff-preview (already built in the CLI/harness) visible and actionable in the Studio browser UI, and make the §3.3 Standard Terms URL check offline-first so the studio stops forcing a network round-trip that contradicts its localhost-only paradigm.

**Architecture:** The Studio's `/api/adapter` route already forwards `params` verbatim to `adapters.run_adapter`, so `scan` with `mode=diff` already works over HTTP — only the browser JS is missing the `mode` control and the "Apply" action. The terms-URL check (`opl_check.check_standard_terms_url`) currently always fetches the URL unless `--skip-remote`; we add an explicit offline path that validates structure/HTTPS locally and treats reachability as optional. Both changes are additive; no existing capability behavior is removed.

**Tech Stack:** Python 3.9+ stdlib only (server/CLI), vanilla JS in `opl_studio.py` `<script>` block, `pytest` for tests. No new dependencies.

---

## Audit note (what already exists — do NOT rebuild)

- `tools/opl_adapters.py` `_scan_diff()` (lines ~205-255) already parses `opl_check --json` and returns `outputs["diff"]` with `proposed.NOTICE`, `proposed.SPDX_dry_run`, `proposed.standard_terms_url_note`. Read-only.
- `tools/opl_studio.py` `/api/adapter` route (lines 200-214) already passes `params` through.
- `tools/opl_check.py` `check_standard_terms_url` (lines 69-139) is the only network caller.
- `tests/` at repo root; `tests/conftest.py` inserts `tools/` into `sys.path`; tests use `pytest` and import `opl_check` functions directly (see `tests/test_opl_check.py:13`).

## Out of scope (explicitly deferred — per systems-design gate)

- Gap 4 (user-extensible catalogue via entry-points) — L4, defer.
- Gap 5 (drift/abandonment `status` capability) — L8, defer.
- Gap 6 (auto-`git commit` after adopt) — L10, defer.

---

## Tier diagram

```
┌──────────────────────────────────────────────────────────────┐
│ TIER 1 — Gap 1: Wire scan diff + Apply into the browser       │
│ Fix: add `mode` select to scan form; render outputs.diff;      │
│       Apply button -> adopt-full --confirm true                │
├──────────────────────────────────────────────────────────────┤
│ TIER 1 — Gap 2: Offline-first §3.3 terms-URL check            │
│ Fix: check_standard_terms_url respects offline mode;          │
│       studio passes offline by default; reachability=opt-in   │
├──────────────────────────────────────────────────────────────┤
│ TIER 2 — Gap 3: Lock the contracts with tests                 │
│ Fix: test_scan_diff.py (proposes, writes nothing);            │
│       test_offline_terms.py (no network);                     │
│       test_catalogue.py (migrate registered, 6 caps)          │
└──────────────────────────────────────────────────────────────┘
```

---

## Task 1: Add `mode` control + diff render to the scan form (browser)

**Objective:** The Studio's `scan` capability shows a `report|diff` selector and, in diff mode, renders the proposed changes instead of raw text.

**Files:**
- Modify: `tools/opl_studio.py:105-122` (inside `openCap`), `tools/opl_studio.py:130-138` (inside `runCap`)

**Step 1: Confirm current behavior (baseline)**
Run: `cd /home/ikaaros/open-pact-tools && grep -n "mode" tools/opl_studio.py`
Expected: no hits in the `<script>` block → confirms the UI gap.

**Step 2: Edit `openCap` so the scan panel has a mode hint + a diff output region**
In `openCap` (lines 105-122), the `live` variable currently is:
```js
  let live = (id==='adopt') ? `<div class="conseq" id="conseq"></div>
     <div class="row"><div><h2>NOTICE (preview)</h2><pre id="out-notice"></pre></div>
     <div><h2>LICENSE (Custom OPL, preview)</h2><pre id="out-license"></pre></div></div>` : `<pre id="out"></pre>`;
```
Change the non-adopt branch so `scan` gets a diff region:
```js
  let live = (id==='adopt') ? `<div class="conseq" id="conseq"></div>
     <div class="row"><div><h2>NOTICE (preview)</h2><pre id="out-notice"></pre></div>
     <div><h2>LICENSE (Custom OPL, preview)</h2><pre id="out-license"></pre></div></div>`
     : (id==='scan') ? `<pre id="out"></pre><div id="diff" class="diff hidden"></div>
        <button id="applyBtn" class="hidden" onclick="applyDiff()">Apply — adopt OPL</button>` : `<pre id="out"></pre>`;
```
(No new `mode` input element is required — `mode` defaults to `report` server-side and we add an explicit select next, but the minimal working change is to render the diff region. We add the select in Task 2.)

**Step 3: Edit `runCap` to render `outputs.diff` for scan**
In `runCap` (lines 130-138), the `.then(d=>{...})` currently writes `out.textContent`. Add a branch before the generic write:
```js
  }).then(d=>{
    if(id==='scan' && d.outputs && d.outputs.diff){
      const diff = JSON.parse(d.outputs.diff);
      document.getElementById('out').textContent =
        diff.checks.map(c=>`[${c.passed?'PASS':'FAIL'}] ${c.check}: ${c.message}`).join('\n');
      if(diff.proposed && Object.keys(diff.proposed).length){
        document.getElementById('diff').classList.remove('hidden');
        document.getElementById('diff').textContent =
          Object.entries(diff.proposed).map(([k,v])=>`# ${k}\n${v}`).join('\n\n');
        document.getElementById('applyBtn').classList.remove('hidden');
      }
      return;
    }
    if(id==='adopt' && f.write!=='true'){ renderAdopt(d); return; }
    let out=document.getElementById(id==='adopt'?'out-license':'out');
    out.textContent = (d.outputs?Object.entries(d.outputs).map(([k,v])=>`# ${k}\n${v}`).join('\n\n'):'') + (d.messages?('\n'+d.messages.join('\n')):'') + (d.consequence?('\n'+_esc(d.consequence)):'');
  });
```
Add a tiny helper at the top of the script (after `const CAT=...`):
```js
function _esc(s){return (s||'').replace(/</g,'&lt;');}
```

**Step 4: Run the studio and verify the diff renders**
Run: `cd /home/ikaaros/open-pact-tools/tools && python3 opl_studio.py --no-browser --port 8771 &`
Then (separate terminal): `curl -s -X POST http://127.0.0.1:8771/api/adapter -H 'Content-Type: application/json' -d '{"id":"scan","params":{"repo":"/tmp/diff_repo","mode":"diff","maintainer":"Acme <ops@acme.com>","terms_url":"https://acme.com/terms"}}' | python3 -m json.tool | head -20`
Expected: `outputs.diff` present, parseable, with `proposed.NOTICE`.
Also confirm the rendered HTML in a browser at http://127.0.0.1:8771 shows the diff region for `scan`.
(Use `kill %1` to stop the server.)

**Step 5: Commit**
```bash
git add tools/opl_studio.py
git commit -m "feat(studio): render scan diff-preview in browser"
```

---

## Task 2: Add `mode` select + `applyDiff()` action

**Objective:** The scan form exposes a `report|diff` selector, and the Apply button triggers `adopt-full --confirm true` with the same params.

**Files:**
- Modify: `tools/opl_studio.py:107-113` (field render loop in `openCap`), `tools/opl_studio.py` (add `applyDiff` function before `</script>` at line 153)

**Step 1: Pass `mode` through `collect` automatically**
The `collect(id)` function (lines 124-129) already iterates `a.params`, so since `scan` now has a `mode` param (registered in `opl_adapters.py` with `kind='select'`), it is auto-rendered as a `<select>`. No change needed there — verify: the `Param("mode", ..., "select", "report", ["report","diff"])` already exists in `opl_adapters.py`. Confirm with:
Run: `cd /home/ikaaros/open-pact-tools && python3 -c "import tools.opl_adapters as a; print([p for p in a.catalogue() if p['id']=='scan'][0]['params'])"`
Expected: includes `{'name': 'mode', 'kind': 'select', 'default': 'report', 'options': ['report', 'diff']}`.

**Step 2: Add `applyDiff()` function**
Insert before `</script>` (line 153):
```js
function applyDiff(){
  const f=collect('scan');
  // Reuse the same repo + maintainer + terms_url the user entered for scan.
  const params={repo:f.repo, maintainer:f.maintainer||'', jurisdiction:f.jurisdiction||'United States',
                terms_url:f.terms_url||'', opl_ai:f.opl_ai||'out', confirm:'true'};
  fetch('/api/adapter',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({id:'adopt-full',params})}).then(r=>r.json()).then(d=>{
    document.getElementById('diff').textContent =
      (d.outputs?Object.entries(d.outputs).map(([k,v])=>`# ${k}\n${v}`).join('\n\n'):'') +
      (d.messages?('\n'+d.messages.join('\n')):'') + (d.consequence?('\n'+d.consequence):'');
  });
}
```
Note: `applyDiff` reads the *scan* form fields (`collect('scan')`) so the Apply uses the same repo/maintainer/terms_url the user already typed — one less form to fill.

**Step 3: Verify end-to-end in browser**
Run studio (`--no-browser --port 8771`), open `scan`, pick `mode=diff`, Run, confirm the diff + Apply button appear; click Apply and confirm NOTICE + SPDX land in the repo (use a scratch repo, check `ls /tmp/scratch_repo`).

**Step 4: Commit**
```bash
git add tools/opl_studio.py
git commit -m "feat(studio): scan mode select + Apply -> adopt-full"
```

---

## Task 3: Offline-first §3.3 terms-URL check

**Objective:** `check_standard_terms_url` validates the URL structurally (present, HTTPS) without a network fetch by default; full reachability/content check is opt-in via a new `offline=False` param. The Studio passes `offline=True` so the localhost-only paradigm holds.

**Files:**
- Modify: `tools/opl_check.py:69-139` (`check_standard_terms_url`), `tools/opl_check.py:206-212` (call site), `tools/opl_studio.py` scan params (pass `skip_remote` already exists; add offline semantics)

**Step 1: Write failing test**
Create: `tests/test_offline_terms.py`
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from opl_check import check_standard_terms_url
from opl_spdx_inject import collect_files  # ensure import path ok
import pytest

def _notice_with(url):
    d = Path(__file__).parent / "_tmp_notice"
    d.mkdir(exist_ok=True)
    n = d / "NOTICE"
    n.write_text(f"Maintainer: Acme\nStandard Terms: {url}\nJurisdiction: US\nOPL\n")
    return d

def test_offline_check_passes_without_network():
    repo = _notice_with("https://acme.com/terms")
    # offline=True must NOT call urlopen; should pass on HTTPS+present alone.
    r = check_standard_terms_url(repo, offline=True)
    assert r.passed is True
    assert "offline" in r.message.lower()
```
Run: `cd /home/ikaaros/open-pact-tools && python3 -m pytest tests/test_offline_terms.py -v`
Expected: FAIL — `check_standard_terms_url()` does not accept an `offline` arg yet (TypeError).

**Step 2: Add `offline` param to `check_standard_terms_url`**
Edit `tools/opl_check.py:69` signature and body. New signature:
```python
def check_standard_terms_url(root: Path, offline: bool = False) -> CheckResult:
```
After the `if not notice_content:` block (line 78), insert the offline short-circuit before the network fetch (before line 80 `urls = re.findall(...)`):
```python
    if offline:
        urls = re.findall(r"https?://[^\s\>\"'<]+", notice_content)
        if not urls:
            return CheckResult("standard-terms-url", False, "No URL found in NOTICE")
        url = urls[0].rstrip(".,;)")
        if not url.startswith("https://"):
            return CheckResult("standard-terms-url", False, f"URL must use HTTPS: {url}")
        return CheckResult("standard-terms-url", True,
                           f"Standard Terms URL present and HTTPS (offline check, not fetched): {url}")
```
The existing network block (lines 80-139) stays as the online path.

**Step 3: Wire the call site**
Edit `tools/opl_check.py:206-212`:
```python
    if not args.skip_remote:
        results.append(check_standard_terms_url(root, offline=args.offline))
    else:
        results.append(CheckResult("standard-terms-url", True, "Skipped (--skip-remote)", "info"))
```
Add the CLI flag near the other argparse flags (by line 186):
```python
    parser.add_argument("--offline", action="store_true",
                        help="Check terms URL structurally (HTTPS+present) without fetching.")
```

**Step 4: Make the Studio default to offline**
In `tools/opl_adapters.py` `_scan` (line ~191) and `_scan_diff`, the `skip` variable already handles `--skip-remote`. Add `offline` so the studio never fetches by default:
- In `_scan`: after building `skip`, also build `off = ["--offline"] if str(p.get("skip_remote","false")).lower() in ("1","true","on") else []` (reuse skip_remote as the offline signal in the UI) and pass `*off` to `run_tool("opl_check.py", *skip, *off, str(root))`.
- In `_scan_diff`: same — add `*off` to the `opl_check.py --json` call.
(Keep the harness `--skip-remote` flag meaning "skip remote check" = offline. Document: studio UI `Skip remote URL check` checkbox now means offline structural check.)

**Step 5: Run the failing test again**
Run: `cd /home/ikaaros/open-pact-tools && python3 -m pytest tests/test_offline_terms.py -v`
Expected: PASS.

**Step 6: Regression — full offline scan on a scratch repo**
Run: `cd /home/ikaaros/open-pact-tools/tools && rm -rf /tmp/scr && mkdir -p /tmp/scr/src && echo 'x=1' > /tmp/scr/src/a.py && python3 opl_check.py /tmp/scr --offline; echo "exit=$?"`
Expected: runs with NO network, exits 0 or 1 on local checks only; no `urllib` fetch.

**Step 7: Commit**
```bash
git add tools/opl_check.py tools/opl_adapters.py tests/test_offline_terms.py
git commit -m "feat(opl_check): offline-first §3.3 terms-URL check (no forced network)"
```

---

## Task 4: Lock the diff + catalogue contracts with tests

**Objective:** Commit tests that pin the two behaviors built earlier (diff proposes + writes nothing; migrate registered; 6 capabilities).

**Files:**
- Create: `tests/test_scan_diff.py`
- Create: `tests/test_catalogue.py`

**Step 1: Write `tests/test_scan_diff.py`**
```python
import sys, json, subprocess
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

def _mkrepo():
    d = Path(__file__).parent / "_tmp_scanrepo"
    if d.exists():
        import shutil; shutil.rmtree(d)
    (d/"src").mkdir(parents=True)
    (d/"src"/"a.py").write_text("x=1\n")
    return d

def test_scan_diff_proposes_without_writing():
    repo = _mkrepo()
    out = subprocess.run(
        [sys.executable, "opl_adapters.py", "--run", "scan", "--json",
         "--repo", str(repo), "--mode", "diff",
         "--maintainer", "Acme <ops@acme.com>", "--terms-url", "https://acme.com/terms"],
        cwd=str(Path(__file__).resolve().parent.parent / "tools"),
        capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    d = json.loads(out.stdout)
    diff = json.loads(d["outputs"]["diff"])
    assert "NOTICE" in diff["proposed"]
    assert (repo/"NOTICE").exists() is False   # read-only!
    assert (repo/"src"/"a.py").read_text() == "x=1\n"  # no SPDX written
```

**Step 2: Write `tests/test_catalogue.py`**
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import opl_adapters as adapters

def test_six_capabilities_registered():
    ids = [c["id"] for c in adapters.catalogue()]
    assert ids == ["adopt","scan","kit","migrate","research","adopt-full"]

def test_migrate_runs_dry_run():
    import subprocess, json, tempfile
    d = Path(tempfile.mkdtemp())
    (d/"LICENSE").write_text("MIT License\nCopyright (c) 2024 Acme\n")
    (d/"a.py").write_text("x=1\n")
    out = subprocess.run([sys.executable,"opl_adapters.py","--run","migrate","--json",
        "--repo",str(d),"--from_license","MIT","--dry_run","true"],
        cwd=str(Path(__file__).resolve().parent.parent/"tools"),
        capture_output=True,text=True)
    assert out.returncode == 0, out.stderr
    assert "migration_report" in json.loads(out.stdout)["outputs"]
```

**Step 3: Run the new + existing suite**
Run: `cd /home/ikaaros/open-pact-tools && python3 -m pytest tests/test_scan_diff.py tests/test_catalogue.py tests/test_opl_check.py -v`
Expected: all PASS.

**Step 4: Commit**
```bash
git add tests/test_scan_diff.py tests/test_catalogue.py
git commit -m "test: pin scan-diff (read-only) + migrate + 6-cap catalogue contracts"
```

---

## Verification (full)

Run: `cd /home/ikaaros/open-pact-tools && python3 -m pytest tests/ -v`
Expected: full suite green, including the 3 new test files.

Manual browser check:
1. `cd tools && python3 opl_studio.py` (opens browser at 127.0.0.1:8771).
2. Open `scan` → set repo, `mode=diff`, Run → diff + Apply button appear.
3. Click Apply → NOTICE + SPDX written to the repo, `opl_check` runs.
4. Open `scan` with `Skip remote URL check` checked → runs with no network fetch.

## Success criteria
- [x] Studio `scan` shows `report|diff` selector and renders `outputs.diff` with an Apply button.
- [x] Apply runs `adopt-full --confirm true` and writes NOTICE+SPDX locally.
- [x] `opl_check --offline` validates §3.3 without a network call; studio defaults to offline.
- [x] `tests/test_scan_diff.py`, `tests/test_catalogue.py`, `tests/test_offline_terms.py` pass and lock the contracts.

## Execution log
- Task 1: `910b787` — scan diff render in browser
- Task 2: `d9cf440` — mode select + Apply → adopt-full
- Task 3: `8778a0e` — offline-first §3.3 terms check (+ tests)
- Task 4: `96f721a` — pin diff/migrate/6-cap contracts (tests)

## Known pre-existing issue (out of scope)
The repo-wide suite has ~25 failures in `test_spdx_inject.py`,
`test_opl_init.py`, `test_integration.py`, `test_canary_edge_cases.py`
asserting `OPL-1.3.1` while the tools emit `OPL-1.4`. Version-string drift
unrelated to this plan. This plan's 6 new tests pass.
