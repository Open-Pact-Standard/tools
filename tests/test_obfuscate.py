# SPDX-License-Identifier: OPL-1.4
"""Tests for obfuscate.py — canary-fused code obfuscation."""
from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture
def demo_source() -> str:
    return (
        "class Req:\n"
        "    def __init__(self, method, body):\n"
        "        self.method = method\n"
        "        self.body = body\n"
        "def handle(req):\n"
        "    if req.method == 'GET':\n"
        "        return {'status': 200, 'len': len(req.body)}\n"
        "    return {'status': 405}\n"
        "def compute(x):\n"
        "    return x * 2 + 1\n"
        "print(handle(Req('GET', b'hi')))\n"
        "print(compute(5))\n"
    )


class TestObfuscateFusedCanary:
    def test_behavior_preserved(self, demo_source):
        from obfuscate import obfuscate_source

        out, _keys = obfuscate_source(demo_source, "canary_secret_1")
        a = subprocess.run([sys.executable, "-c", demo_source], capture_output=True, text=True)
        b = subprocess.run([sys.executable, "-c", out], capture_output=True, text=True)
        assert a.returncode == b.returncode == 0, b.stderr
        assert a.stdout == b.stdout

    def test_dunder_names_kept(self, demo_source):
        from obfuscate import obfuscate_source

        src = "class A:\n    def __init__(self):\n        pass\n"
        out, _k = obfuscate_source(src, "s")
        assert "__init__" in out

    def test_fingerprint_survives_comment_strip(self, demo_source):
        """The token-derived guard hash is code (not a comment), so stripping
        comments must leave it — proving the fingerprint isn't one-line-removable."""
        from obfuscate import obfuscate_source

        secret = "canary_deadbeefcafe"
        out, _keys = obfuscate_source(demo_source, secret)
        # strip comments (the old kill for comment-canaries)
        stripped = "\n".join(ln for ln in out.splitlines() if not ln.strip().startswith("#"))
        guard_hash = hashlib.sha3_256(secret.encode()).hexdigest()[:24]
        assert guard_hash in stripped
        compile(stripped, "<stripped>", "exec")

    def test_identifier_rename_is_keyed_and_deterministic(self, demo_source):
        from obfuscate import obfuscate_source

        a, _k1 = obfuscate_source(demo_source, "secret_A")
        b, _k2 = obfuscate_source(demo_source, "secret_A")
        c, _k3 = obfuscate_source(demo_source, "secret_B")
        assert a == b, "same secret -> identical obfuscation (reproducible evidence)"
        assert a != c, "different secret -> different names (distinct fingerprint)"

    def test_cli_writes_output(self, tmp_path):
        src = tmp_path / "a.py"
        src.write_text("def foo(x):\n    return x\n")
        r = subprocess.run(
            [sys.executable, str(ROOT / "obfuscate.py"), str(src),
             "-s", "sk", "-o", str(tmp_path / "a.obf.py")],
            capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        assert (tmp_path / "a.obf.py").exists()
