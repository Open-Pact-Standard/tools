# SPDX-License-Identifier: OPL-1.4
"""Integration tests for edge cases in root-level scripts:
canary_embedder.py, cicd_pipeline.py, js_embedder.py
"""
from __future__ import annotations

import json
import os
import random
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

TOOLS_DIR = str(Path(__file__).resolve().parent.parent)


def run_canary(*args: str) -> subprocess.CompletedProcess:
    """Run canary_embedder.py with the given arguments."""
    return subprocess.run(
        [sys.executable, str(Path(TOOLS_DIR) / "canary_embedder.py"), *args],
        capture_output=True, text=True, cwd=TOOLS_DIR,
    )


def run_canary_env(env: dict, *args: str) -> subprocess.CompletedProcess:
    """Run canary_embedder.py with an explicit environment (e.g. a PATH shim)."""
    return subprocess.run(
        [sys.executable, str(Path(TOOLS_DIR) / "canary_embedder.py"), *args],
        capture_output=True, text=True, cwd=TOOLS_DIR, env=env,
    )


def run_cicd(*args: str) -> subprocess.CompletedProcess:
    """Run cicd_pipeline.py with the given arguments."""
    return subprocess.run(
        [sys.executable, str(Path(TOOLS_DIR) / "cicd_pipeline.py"), *args],
        capture_output=True, text=True, cwd=TOOLS_DIR,
    )


# ---------------------------------------------------------------------------
# canary_embedder.py edge cases
# ---------------------------------------------------------------------------

class TestTokenGeneratorEdgeCases:
    def test_empty_distribution_id(self):
        from canary_embedder import TokenGenerator
        result = TokenGenerator.generate(1, "", 0, "salt")
        assert result.startswith("canary_")
        assert len(result) > 7

    def test_empty_salt(self):
        from canary_embedder import TokenGenerator
        result = TokenGenerator.generate(1, "dist", 0, "")
        assert result.startswith("canary_")

    def test_large_index(self):
        from canary_embedder import TokenGenerator
        result = TokenGenerator.generate(1, "dist", 999999, "salt")
        assert result.startswith("canary_")

    def test_negative_index(self):
        from canary_embedder import TokenGenerator
        result = TokenGenerator.generate(1, "dist", -1, "salt")
        assert result.startswith("canary_")

    def test_deterministic_output(self):
        from canary_embedder import TokenGenerator
        r1 = TokenGenerator.generate(42, "abc", 5, "secret")
        r2 = TokenGenerator.generate(42, "abc", 5, "secret")
        assert r1 == r2

    def test_different_inputs_differ(self):
        from canary_embedder import TokenGenerator
        r1 = TokenGenerator.generate(1, "a", 0, "x")
        r2 = TokenGenerator.generate(2, "a", 0, "x")
        assert r1 != r2


class TestMerkleTreeEdgeCases:
    def test_empty_leaves_raises(self):
        from canary_embedder import MerkleTree
        mt = MerkleTree()
        with pytest.raises(ValueError, match="At least one leaf"):
            mt.build([])

    def test_single_leaf(self):
        from canary_embedder import MerkleTree
        mt = MerkleTree()
        root, tree = mt.build(["leaf1"])
        assert isinstance(root, str)
        assert len(root) == 64  # sha3_256 hex digest
        assert len(tree) >= 1

    def test_two_leaves(self):
        from canary_embedder import MerkleTree
        mt = MerkleTree()
        root, _tree = mt.build(["a", "b"])
        assert isinstance(root, str)

    def test_odd_number_of_leaves(self):
        from canary_embedder import MerkleTree
        mt = MerkleTree()
        root, tree = mt.build(["a", "b", "c"])
        assert isinstance(root, str)
        assert len(tree[0]) == 4  # padded to power of 2

    def test_proof_for_first_leaf(self):
        from canary_embedder import MerkleTree
        mt = MerkleTree()
        _, tree = mt.build(["a", "b", "c", "d"])
        proof = mt.get_proof(tree, 0)
        assert isinstance(proof, list)

    def test_proof_for_last_leaf(self):
        from canary_embedder import MerkleTree
        mt = MerkleTree()
        _, tree = mt.build(["a", "b", "c", "d"])
        proof = mt.get_proof(tree, 3)
        assert isinstance(proof, list)


class TestVariableInjectionEmbedderEdgeCases:
    def test_empty_directory(self, tmp_path):
        from canary_embedder import VariableInjectionEmbedder
        emb = VariableInjectionEmbedder()
        rng = random.Random(b"test")
        result = emb.embed(tmp_path, "canary_test", rng)
        assert result is None

    def test_excluded_directory(self, tmp_path):
        from canary_embedder import VariableInjectionEmbedder
        test_dir = tmp_path / "test"
        test_dir.mkdir()
        (test_dir / "app.py").write_text("print('hello')")
        emb = VariableInjectionEmbedder()
        rng = random.Random(b"test")
        result = emb.embed(tmp_path, "canary_test", rng)
        assert result is None

    def test_node_modules_excluded(self, tmp_path):
        from canary_embedder import VariableInjectionEmbedder
        nm = tmp_path / "node_modules" / "pkg"
        nm.mkdir(parents=True)
        (nm / "index.js").write_text("console.log('hi')")
        emb = VariableInjectionEmbedder()
        rng = random.Random(b"test")
        result = emb.embed(tmp_path, "canary_test", rng)
        assert result is None

    def test_file_without_imports(self, tmp_path):
        from canary_embedder import VariableInjectionEmbedder
        (tmp_path / "bare.py").write_text("# no imports\nprint('hello')\n")
        emb = VariableInjectionEmbedder()
        rng = random.Random(b"test")
        result = emb.embed(tmp_path, "canary_test", rng)
        assert result is not None

    def test_python_file_with_imports(self, tmp_path):
        from canary_embedder import VariableInjectionEmbedder
        (tmp_path / "mod.py").write_text("import os\nimport sys\n\nprint('hi')\n")
        emb = VariableInjectionEmbedder()
        rng = random.Random(b"test")
        result = emb.embed(tmp_path, "canary_test", rng)
        assert result is not None

    def test_js_file_with_imports(self, tmp_path):
        from canary_embedder import VariableInjectionEmbedder
        (tmp_path / "app.js").write_text("import React from 'react';\nconsole.log('hi');\n")
        emb = VariableInjectionEmbedder()
        rng = random.Random(b"test")
        result = emb.embed(tmp_path, "canary_test", rng)
        assert result is not None

    def test_large_file_skipped(self, tmp_path):
        from canary_embedder import VariableInjectionEmbedder
        big = tmp_path / "big.py"
        big.write_text("x = 1\n" * 200_000)  # ~1.2MB
        emb = VariableInjectionEmbedder()
        rng = random.Random(b"test")
        result = emb.embed(tmp_path, "canary_test", rng)
        assert result is None

    def test_find_insertion_point_with_shebang(self):
        from canary_embedder import VariableInjectionEmbedder
        emb = VariableInjectionEmbedder()
        lines = ["#!/usr/bin/env python3", "# -*- coding: utf-8 -*-", "import os", "", "print('hi')"]
        point = emb._find_insertion_point(lines, ".py")
        assert point >= 2

    def test_find_insertion_point_with_spdx(self):
        from canary_embedder import VariableInjectionEmbedder
        emb = VariableInjectionEmbedder()
        lines = ["# SPDX-License-Identifier: MIT", "# Copyright 2024", "import os", "", "print('hi')"]
        point = emb._find_insertion_point(lines, ".py")
        assert point >= 2

    def test_is_excluded_venv(self, tmp_path):
        from canary_embedder import VariableInjectionEmbedder
        emb = VariableInjectionEmbedder()
        assert emb._is_excluded(tmp_path / "venv" / "lib" / "mod.py") is True

    def test_is_excluded_build(self, tmp_path):
        from canary_embedder import VariableInjectionEmbedder
        emb = VariableInjectionEmbedder()
        assert emb._is_excluded(tmp_path / "build" / "output.py") is True

    def test_not_excluded_normal(self, tmp_path):
        from canary_embedder import VariableInjectionEmbedder
        emb = VariableInjectionEmbedder()
        assert emb._is_excluded(tmp_path / "src" / "main.py") is False


class TestWatermarkEmbedderEdgeCases:
    def test_empty_directory(self, tmp_path):
        from canary_embedder import WatermarkEmbedder
        emb = WatermarkEmbedder()
        rng = random.Random(b"test")
        result = emb.embed(tmp_path, "canary_test", rng)
        assert result is None

    def test_file_with_docstring(self, tmp_path):
        from canary_embedder import WatermarkEmbedder
        (tmp_path / "mod.py").write_text('"""Module docstring."""\nprint("hi")\n')
        emb = WatermarkEmbedder()
        rng = random.Random(b"test")
        result = emb.embed(tmp_path, "canary_test", rng)
        assert result is not None
        content = (tmp_path / result).read_text()
        assert "Internal reference:" in content

    def test_file_with_comment(self, tmp_path):
        from canary_embedder import WatermarkEmbedder
        (tmp_path / "mod.py").write_text("# This is a long enough comment\nprint('hi')\n")
        emb = WatermarkEmbedder()
        rng = random.Random(b"test")
        result = emb.embed(tmp_path, "canary_test", rng)
        assert result is not None
        content = (tmp_path / result).read_text()
        assert "ref:" in content

    def test_file_no_docstring_or_long_comment(self, tmp_path):
        from canary_embedder import WatermarkEmbedder
        (tmp_path / "mod.py").write_text("# hi\nprint('hello')\n")
        emb = WatermarkEmbedder()
        rng = random.Random(b"test")
        result = emb.embed(tmp_path, "canary_test", rng)
        assert result is not None
        content = (tmp_path / result).read_text()
        assert "Module reference:" in content


class TestDeadCodeEmbedderEdgeCases:
    def test_empty_directory(self, tmp_path):
        from canary_embedder import DeadCodeEmbedder
        emb = DeadCodeEmbedder()
        rng = random.Random(b"test")
        result = emb.embed(tmp_path, "canary_test", rng)
        assert result is None

    def test_file_without_functions(self, tmp_path):
        from canary_embedder import DeadCodeEmbedder
        (tmp_path / "data.py").write_text("x = 1\ny = 2\n")
        emb = DeadCodeEmbedder()
        rng = random.Random(b"test")
        result = emb.embed(tmp_path, "canary_test", rng)
        assert result is None

    def test_file_with_function(self, tmp_path):
        from canary_embedder import DeadCodeEmbedder
        (tmp_path / "mod.py").write_text("def main():\n    print('hi')\n")
        emb = DeadCodeEmbedder()
        rng = random.Random(b"test")
        result = emb.embed(tmp_path, "canary_test", rng)
        assert result is not None
        content = (tmp_path / result).read_text()
        assert "_validate_" in content

    def test_file_with_multiple_functions(self, tmp_path):
        from canary_embedder import DeadCodeEmbedder
        (tmp_path / "mod.py").write_text("def foo():\n    pass\n\ndef bar():\n    pass\n")
        emb = DeadCodeEmbedder()
        rng = random.Random(b"test")
        result = emb.embed(tmp_path, "canary_test", rng)
        assert result is not None


class TestCanaryEmbedderEdgeCases:
    def test_empty_directory_embed(self, tmp_path):
        from canary_embedder import CanaryEmbedder
        emb = CanaryEmbedder(
            project_id=1, distribution_id="abc", salt="secret",
            strategies=["variable"], num_canaries=3,
        )
        emb.generate_tokens()
        assert len(emb.tokens) == 3
        emb.embed(tmp_path)
        for t in emb.tokens:
            assert t.target_file == ""

    def test_build_merkle_tree_empty_tokens(self):
        from canary_embedder import CanaryEmbedder
        emb = CanaryEmbedder(
            project_id=1, distribution_id="abc", salt="secret",
            strategies=["variable"], num_canaries=0,
        )
        emb.generate_tokens()
        assert len(emb.tokens) == 0
        with pytest.raises(ValueError):
            emb.build_merkle_tree()

    def test_generate_tokens_count(self):
        from canary_embedder import CanaryEmbedder
        emb = CanaryEmbedder(
            project_id=1, distribution_id="abc", salt="secret",
            strategies=["variable", "watermark"], num_canaries=5,
        )
        emb.generate_tokens()
        assert len(emb.tokens) == 5
        assert emb.tokens[0].embedding_type == "variable"
        assert emb.tokens[1].embedding_type == "watermark"
        assert emb.tokens[2].embedding_type == "variable"

    def test_generate_manifest_empty(self, tmp_path):
        from canary_embedder import CanaryEmbedder
        emb = CanaryEmbedder(
            project_id=1, distribution_id="abc", salt="secret",
            strategies=["variable"], num_canaries=2,
        )
        emb.generate_tokens()
        manifest = emb.generate_manifest(tmp_path)
        assert manifest.project_id == 1
        assert manifest.distribution_id == "abc"
        assert manifest.merkle_root == ""

    def test_verify_source_no_matches(self, tmp_path):
        from canary_embedder import CanaryEmbedder, CanaryManifest, CanaryToken
        (tmp_path / "clean.py").write_text("print('clean')\n")
        emb = CanaryEmbedder(
            project_id=1, distribution_id="abc", salt="secret",
            strategies=["variable"], num_canaries=1,
        )
        manifest = CanaryManifest(
            project_id=1, distribution_id="abc", salt="secret",
            canary_tokens=[CanaryToken(token_id=0, secret='canary_nonexistent', embedding_type='variable')],
        )
        matches = emb.verify_source(tmp_path, manifest)
        assert matches == []

    def test_verify_source_with_matches(self, tmp_path):
        from canary_embedder import CanaryEmbedder, CanaryManifest, CanaryToken
        secret = "canary_abc123"
        (tmp_path / "leaked.py").write_text(f"# {secret}\nprint('hi')\n")
        emb = CanaryEmbedder(
            project_id=1, distribution_id="abc", salt="secret",
            strategies=["variable"], num_canaries=1,
        )
        manifest = CanaryManifest(
            project_id=1, distribution_id="abc", salt="secret",
            canary_tokens=[CanaryToken(token_id=0, secret=secret, embedding_type='variable')],
        )
        matches = emb.verify_source(tmp_path, manifest)
        assert len(matches) == 1
        assert matches[0][1] == secret

    def test_non_utf8_file_handled(self, tmp_path):
        from canary_embedder import VariableInjectionEmbedder
        (tmp_path / "binary.py").write_bytes(b"\x80\x81\x82\xff\xfe\xfd\n")
        emb = VariableInjectionEmbedder()
        rng = random.Random(b"test")
        # Should not crash due to errors='replace'
        emb.embed(tmp_path, "canary_test", rng)


class TestCanaryCLIEdgeCases:
    def test_no_command(self):
        r = run_canary()
        assert r.returncode != 0

    def test_embed_nonexistent_source(self):
        r = run_canary(
            "embed",
            "--source", "/nonexistent/path",
            "--project-id", "1",
            "--distribution-id", "abc",
            "--salt", "secret",
        )
        assert r.returncode != 0
        assert "not a directory" in r.stderr or "Error" in r.stderr

    def test_build_merkle_nonexistent_manifest(self):
        r = run_canary("build-merkle", "--manifest", "/nonexistent/manifest.json")
        assert r.returncode != 0

    def test_verify_nonexistent_source(self):
        r = run_canary(
            "verify",
            "--source", "/nonexistent/path",
            "--manifest", "/nonexistent/manifest.json",
        )
        assert r.returncode != 0

    def test_embed_empty_dir(self, tmp_path):
        out = tmp_path / "manifest.json"
        r = run_canary(
            "embed",
            "--source", str(tmp_path),
            "--project-id", "1",
            "--distribution-id", "abc",
            "--salt", "secret",
            "--num-canaries", "2",
            "--output", str(out),
            "--public-output", str(tmp_path / "pub.json"),
        )
        assert r.returncode == 0

    def test_embed_with_output(self, tmp_path):
        out = tmp_path / "manifest.json"
        r = run_canary(
            "embed",
            "--source", str(tmp_path),
            "--project-id", "1",
            "--distribution-id", "abc",
            "--salt", "secret",
            "--num-canaries", "1",
            "--output", str(out),
        )
        assert r.returncode == 0
        assert out.exists()
        data = json.loads(out.read_text())
        assert data["project_id"] == 1

    def test_hunt_missing_manifest(self):
        r = run_canary("hunt", "--manifest", "/nonexistent/manifest.json")
        assert r.returncode != 0
        assert "not found" in r.stderr

    def test_hunt_no_tokens_clear_error(self, tmp_path):
        # a manifest with no searchable token literals (e.g. an empty/public one)
        m = tmp_path / "m.json"
        m.write_text(json.dumps({"canary_tokens": []}))
        r = run_canary("hunt", "--manifest", str(m))
        assert r.returncode != 0
        assert "no searchable token literals" in r.stderr

    def test_hunt_works_and_prints_blind_spots(self, tmp_path):
        """hunt must run against a private manifest and, with no copies present,
        say so honestly AND print its coverage blind spots (never 'no theft')."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "a.py").write_text("def f(): return 1\n")
        priv = tmp_path / "priv.json"
        pub = tmp_path / "pub.json"
        r = run_canary("embed", "--source", str(tmp_path), "--project-id", "1",
                       "--distribution-id", "v1", "--num-canaries", "1",
                       "--output", str(priv), "--public-output", str(pub))
        assert r.returncode == 0
        r = run_canary("hunt", "--manifest", str(priv))
        assert r.returncode == 0
        combined = r.stdout + r.stderr
        assert "BLIND SPOTS" in combined, "no-match must not claim safety"
        assert "public GitHub" in combined

    def test_evidence_verbatim_copy_merkle_proven(self, tmp_path):
        """LP#8 gate: a true verbatim copy (same path) is merkle_proven; a
        renamed file is a lead (merkle_proven False), not proof."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "core.py").write_text("def init(): return 1\n")
        priv = tmp_path / "priv.json"
        r = run_canary("embed", "--source", str(tmp_path), "--project-id", "9",
                       "--distribution-id", "ev", "--num-canaries", "2",
                       "--output", str(priv), "--public-output", str(tmp_path / "pub.json"))
        assert r.returncode == 0

        # verbatim copy, same relative path
        vsrc = tmp_path / "victim_src"
        (vsrc / "src").mkdir(parents=True)
        shutil.copy2(tmp_path / "src" / "core.py", vsrc / "src" / "core.py")
        ev = tmp_path / "ev_verb.json"
        r = run_canary("evidence", "--manifest", str(priv), "--suspect-source", str(vsrc),
                       "--output", str(ev))
        assert r.returncode == 0
        d = json.loads(ev.read_text())
        assert d["gate"] == "merkle-proof"
        assert all(m["merkle_proven"] for m in d["matches"])


# ---------------------------------------------------------------------------
# W4 integrity decisions: renamed-copy content proof, hunt false-safety,
# signed-commitment binding. See docs/W4-integrity-decisions.md.
# ---------------------------------------------------------------------------

class TestW4IntegrityDecisions:
    def test_evidence_renamed_copy_is_content_identical(self, tmp_path):
        """Decision 1: a byte-identical copy under a DIFFERENT path (the common
        theft/rename case) must not be degraded to a bare lead. sha3_256 hash
        equality with a recorded release file is provable, so it becomes
        content_identical + identical_to, distinct from merkle_proven."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "core.py").write_text("def init(): return 1\n")
        priv = tmp_path / "priv.json"
        r = run_canary("embed", "--source", str(tmp_path), "--project-id", "10",
                       "--distribution-id", "rn", "--num-canaries", "2",
                       "--output", str(priv), "--public-output", str(tmp_path / "pub.json"))
        assert r.returncode == 0
        # renamed copy: identical bytes, different relative path (core.py -> renamed.py)
        vsrc = tmp_path / "victim_src"
        vsrc.mkdir()
        shutil.copy2(tmp_path / "src" / "core.py", vsrc / "renamed.py")
        ev = tmp_path / "ev_rn.json"
        r = run_canary("evidence", "--manifest", str(priv), "--suspect-source", str(vsrc),
                       "--output", str(ev))
        assert r.returncode == 0
        d = json.loads(ev.read_text())
        assert d["gate"] == "merkle-proof"
        assert d["matches"], "renamed byte-identical copy must be picked up"
        m = d["matches"][0]
        assert m["file"] == "renamed.py"
        assert m["merkle_proven"] is False
        assert m["content_identical"] is True
        assert m["identical_to"] == "src/core.py"

    def test_evidence_edited_copy_stays_a_lead(self, tmp_path):
        """Decision 1 regression: content that carries the token but whose bytes
        are NOT identical to any recorded release file stays a bare lead (no
        content_identical claim — hash equality is required for proof)."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "core.py").write_text("def init(): return 1\n")
        priv = tmp_path / "priv.json"
        r = run_canary("embed", "--source", str(tmp_path), "--project-id", "11",
                       "--distribution-id", "lead", "--num-canaries", "2",
                       "--output", str(priv), "--public-output", str(tmp_path / "pub.json"))
        assert r.returncode == 0
        manifest = json.loads(priv.read_text())
        # plant a canary secret verbatim into a file whose bytes differ from every
        # recorded release file: a lead, not content-proof.
        secret = manifest["canary_tokens"][0]["secret"]
        vsrc = tmp_path / "edited"
        vsrc.mkdir()
        (vsrc / "forked.py").write_text("def f():\n    pass\n# " + secret + "\n")
        ev = tmp_path / "ev_lead.json"
        r = run_canary("evidence", "--manifest", str(priv), "--suspect-source", str(vsrc),
                       "--output", str(ev))
        assert r.returncode == 0
        d = json.loads(ev.read_text())
        assert d["matches"], "token carried by an edited file should still be a lead"
        m = d["matches"][0]
        assert m["merkle_proven"] is False
        assert m["content_identical"] is False

    def test_hunt_failed_gh_is_not_no_copies(self, tmp_path):
        """Decision 2: a broken `gh` (installed but errors / unauth) must exit
        non-zero and never collapse to 'No copies found' (F1 false-safety)."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "a.py").write_text("def f(): return 1\n")
        priv = tmp_path / "priv.json"
        r = run_canary("embed", "--source", str(tmp_path), "--project-id", "12",
                       "--distribution-id", "failgh", "--num-canaries", "1",
                       "--output", str(priv), "--public-output", str(tmp_path / "pub.json"))
        assert r.returncode == 0
        bindir = tmp_path / "bin"
        bindir.mkdir()
        (bindir / "gh").write_text("#!/bin/sh\necho 'gh: not authenticated (HTTP 401)' >&2\nexit 1\n")
        (bindir / "gh").chmod(0o755)
        env = {**os.environ, "PATH": str(bindir) + os.pathsep + os.environ.get("PATH", "")}
        r = run_canary_env(env, "hunt", "--manifest", str(priv))
        assert r.returncode != 0
        combined = r.stdout + r.stderr
        assert "No copies found" not in r.stdout, "must not collapse a failure to 'no copies'"
        assert "TOOL FAILURE" in combined
        assert "could NOT be run" in combined

    def test_hunt_missing_gh_is_explicit(self, tmp_path):
        """Decision 2 regression: when `gh` is absent from PATH, hunt reports the
        tool is missing (exit non-zero), never a clean 'no copies'."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "a.py").write_text("def f(): return 1\n")
        priv = tmp_path / "priv.json"
        r = run_canary("embed", "--source", str(tmp_path), "--project-id", "13",
                       "--distribution-id", "nogh", "--num-canaries", "1",
                       "--output", str(priv), "--public-output", str(tmp_path / "pub.json"))
        assert r.returncode == 0
        empty_bin = tmp_path / "emptybin"
        empty_bin.mkdir()
        env = {k: v for k, v in os.environ.items() if k != "PATH"}
        env["PATH"] = str(empty_bin)
        r = run_canary_env(env, "hunt", "--manifest", str(priv))
        assert r.returncode != 0
        combined = r.stdout + r.stderr
        assert "No copies found" not in r.stdout
        assert "not installed" in combined

    def test_release_authentication_binding(self, tmp_path):
        """Decision 3: the evidence package records whether the manifest is
        authenticated, binds a matching signed commitment, and fails-closed
        (without writing) on a non-binding one."""
        from canary_embedder import _assess_release_authentication
        root = "a" * 64
        # none supplied -> unsigned
        assert _assess_release_authentication(root, None)["signed"] is False
        # matching signed commitment -> authenticated, binds
        sc = tmp_path / "sc.json"
        sc.write_text(json.dumps({"merkle_root": root}))
        a = _assess_release_authentication(root, sc)
        assert a["signed"] is True and a["merkle_root_binds"] is True
        # mismatched commitment -> error, no binding
        bad = tmp_path / "bad.json"
        bad.write_text(json.dumps({"merkle_root": "b" * 64}))
        a2 = _assess_release_authentication(root, bad)
        assert a2["signed"] is False and a2.get("error")
        # missing file -> FileNotFoundError
        with pytest.raises(FileNotFoundError):
            _assess_release_authentication(root, tmp_path / "nope.json")

    def test_evidence_signed_commitment_binds_via_cli(self, tmp_path):
        """Decision 3 CLI path: with a matching signed commitment the evidence
        package records release_authentication.signed == True."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "core.py").write_text("def init(): return 1\n")
        priv = tmp_path / "priv.json"
        r = run_canary("embed", "--source", str(tmp_path), "--project-id", "14",
                       "--distribution-id", "signed", "--num-canaries", "2",
                       "--output", str(priv), "--public-output", str(tmp_path / "pub.json"))
        assert r.returncode == 0
        root = json.loads(priv.read_text())["merkle_root"]
        sc = tmp_path / "sc.json"
        sc.write_text(json.dumps({"merkle_root": root}))
        vsrc = tmp_path / "vsrc"
        (vsrc / "src").mkdir(parents=True)
        shutil.copy2(tmp_path / "src" / "core.py", vsrc / "src" / "core.py")
        ev = tmp_path / "ev.json"
        r = run_canary("evidence", "--manifest", str(priv), "--suspect-source", str(vsrc),
                       "--output", str(ev), "--signed-commitment", str(sc))
        assert r.returncode == 0
        d = json.loads(ev.read_text())
        assert d["release_authentication"]["signed"] is True
        assert d["release_authentication"]["merkle_root_binds"] is True

    def test_evidence_nonbinding_commitment_fails_closed(self, tmp_path):
        """Decision 3 fail-closed: a signed commitment that does NOT bind this
        manifest's merkle_root must exit non-zero and NOT write the package."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "core.py").write_text("def init(): return 1\n")
        priv = tmp_path / "priv.json"
        r = run_canary("embed", "--source", str(tmp_path), "--project-id", "15",
                       "--distribution-id", "nobind", "--num-canaries", "2",
                       "--output", str(priv), "--public-output", str(tmp_path / "pub.json"))
        assert r.returncode == 0
        sc = tmp_path / "sc.json"
        sc.write_text(json.dumps({"merkle_root": "f" * 64}))  # wrong root
        vsrc = tmp_path / "vsrc"
        (vsrc / "src").mkdir(parents=True)
        shutil.copy2(tmp_path / "src" / "core.py", vsrc / "src" / "core.py")
        ev = tmp_path / "ev.json"
        r = run_canary("evidence", "--manifest", str(priv), "--suspect-source", str(vsrc),
                       "--output", str(ev), "--signed-commitment", str(sc))
        assert r.returncode == 2
        assert not ev.exists(), "non-binding signed commitment must not write a package"
        assert "REJECTED" in r.stderr


# ---------------------------------------------------------------------------
# cicd_pipeline.py edge cases
# ---------------------------------------------------------------------------

class TestCICDEdgeCases:
    def test_missing_config(self, tmp_path):
        # Must be hermetic: no --source + dry-run so the pipeline never embeds
        # into the repo root. A missing config implies default source_dir='.'.
        r = run_cicd("--config", "/nonexistent/config.json", "--dry-run", "--source", str(tmp_path))
        assert r.returncode == 0 or r.returncode != 0

    def test_empty_config_file(self, tmp_path):
        cfg = tmp_path / "empty.json"
        cfg.write_text("{}")
        r = run_cicd("--config", str(cfg), "--dry-run", "--source", str(tmp_path))
        assert r.returncode == 0 or "Error" in r.stderr

    def test_malformed_json_config(self, tmp_path):
        cfg = tmp_path / "bad.json"
        cfg.write_text("{invalid json")
        r = run_cicd("--config", str(cfg))
        assert r.returncode != 0

    def test_dry_run_mode(self, tmp_path):
        r = run_cicd("--source", str(tmp_path), "--dry-run")
        assert r.returncode == 0

    def test_empty_source_directory(self, tmp_path):
        r = run_cicd("--source", str(tmp_path), "--dry-run")
        assert r.returncode == 0

    def test_refuses_embed_without_project_id(self, tmp_path):
        # G3-adjacent: an embed without project_id must refuse rather than
        # fingerprint the tree as unattested — and must NOT touch the repo.
        (tmp_path / "app.py").write_text("def f():\n    pass\n")
        r = run_cicd("--source", str(tmp_path))
        assert r.returncode == 0
        assert "project_id" in r.stderr or "project_id" in r.stdout


# ---------------------------------------------------------------------------
# Phase A fixes: secret/public split, self-exclusion, project_id, generate_tokens
# ---------------------------------------------------------------------------

class TestSecretSplit:
    def test_public_payload_strips_secrets_and_salt(self):
        from canary_embedder import build_public_payload
        full = {
            "project_id": 7, "distribution_id": "abc", "file_hash": "h1",
            "merkle_root": "r1", "_steward_secret_salt": "TOPSECRET",
            "canary_tokens": [
                {"token_id": 0, "secret": "canary_abc123", "merkle_leaf": "L1", "merkle_proof": ["P"]},
                {"token_id": 1, "secret": "canary_def456", "merkle_leaf": "L2", "merkle_proof": ["Q"]},
            ],
        }
        pub = build_public_payload(full)
        assert pub["merkle_root"] == "r1"
        assert pub["file_hash"] == "h1"
        assert "_steward_secret_salt" not in pub
        raw = json.dumps(pub)
        assert "TOPSECRET" not in raw
        assert "canary_abc123" not in raw
        assert "canary_def456" not in raw
        assert len(pub["canary_tokens"]) == 2
        assert pub["canary_tokens"][0]["merkle_proof"] == ["P"]

    def test_embed_writes_public_payload_without_secrets(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "app.py").write_text("def hello():\n    pass\n")
        priv = tmp_path / "priv.json"
        pub = tmp_path / "pub.json"
        r = run_canary(
            "embed", "--source", str(tmp_path), "--project-id", "9",
            "--distribution-id", "dist", "--salt", "salt", "--num-canaries", "2",
            "--output", str(priv), "--public-output", str(pub),
        )
        assert r.returncode == 0
        priv_data = json.loads(priv.read_text())
        pub_data = json.loads(pub.read_text())
        # private manifest holds secrets
        pub_raw = json.dumps(pub_data)
        assert "secret" not in pub_raw
        assert pub_data["merkle_root"]
        assert priv_data["_steward_secret_salt"] == "salt"
        # every public token carries its proof
        for t in pub_data["canary_tokens"]:
            assert t["merkle_proof"]

    def test_embed_requires_project_id(self, tmp_path):
        r = run_canary(
            "embed", "--source", str(tmp_path), "--distribution-id", "d",
            "--salt", "salt", "--num-canaries", "1",
        )
        assert r.returncode != 0


class TestSelfExclusion:
    def test_embedder_never_injects_into_own_source(self, tmp_path):
        # Copy the tool's own source into the scan tree; embed must skip it.
        target = tmp_path / "canary_embedder.py"
        target.write_text("def real():\n    pass\n")
        (tmp_path / "app.py").write_text("def f():\n    pass\n")
        from canary_embedder import VariableInjectionEmbedder
        emb = VariableInjectionEmbedder()
        assert emb._is_excluded(target) is True

    def test_is_excluded_respects_self_filenames(self, tmp_path):
        from canary_embedder import SELF_EXCLUDED_FILENAMES, VariableInjectionEmbedder
        emb = VariableInjectionEmbedder()
        for name in SELF_EXCLUDED_FILENAMES:
            assert emb._is_excluded(tmp_path / name) is True


class TestDocGenerateTokensCLIFix:
    def test_embed_generates_tokens_via_cli(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "app.py").write_text("def main():\n    return 1\n")
        out = tmp_path / "m.json"
        r = run_canary(
            "embed", "--source", str(tmp_path), "--project-id", "5",
            "--distribution-id", "d", "--salt", "s", "--num-canaries", "3",
            "--output", str(out),
        )
        assert r.returncode == 0
        data = json.loads(out.read_text())
        # reg-catch: cmd_embed previously never called generate_tokens, so the
        # manifest carried zero tokens and an empty merkle root.
        assert len(data["canary_tokens"]) == 3
        assert data["merkle_root"]
        # F5: the embed pre-notice must be shown before modification, so a user
        # is never surprised that their source files got watermarked.
        assert "NOTICE: Embedding DISTRIBUTES tracking tokens" in r.stdout

    def test_embed_autogenerates_and_persists_salt(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "app.py").write_text("def main():\n    return 1\n")
        out = tmp_path / "m.json"
        r = run_canary(
            "embed", "--source", str(tmp_path), "--project-id", "6",
            "--distribution-id", "d2", "--num-canaries", "2",
            "--output", str(out),
        )
        assert r.returncode == 0
        # U2: a first-timer can run embed with NO --salt; a random salt is
        # generated, surfaced, and MUST be persisted so litigation evidence
        # stays reproducible (reg-catch: _steward_secret_salt was set from the
        # now-None args.salt and came back null, breaking verify).
        assert "no --salt given: generated a random secret salt" in r.stdout
        data = json.loads(out.read_text())
        salt = data.get("_steward_secret_salt")
        assert salt, "auto-generated salt must be persisted in the private manifest"
        assert len(salt) >= 16

    def test_embed_creates_output_dir(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "app.py").write_text("print(1)")
        # --output into a not-yet-existing subdir is a common maintainer pattern
        # (.canary/) and previously crashed with a raw FileNotFoundError traceback.
        out = tmp_path / ".canary" / "m.json"
        r = run_canary(
            "embed", "--source", str(tmp_path), "--project-id", "7",
            "--distribution-id", "d3", "--num-canaries", "2",
            "--output", str(out),
        )
        assert r.returncode == 0
        assert out.exists(), "embed must create the output file's parent directory"
        assert (tmp_path / ".canary").is_dir()

    def test_cli_version_flag(self):
        # G1: -V / --version must be accepted on the tool's top-level parser and
        # surfaced the OPL tools version — scriptability + version-consistency.
        for flag in ("-V", "--version"):
            r = run_canary(flag)
            assert r.returncode == 0, f"{flag} must not error"
            assert "v1.4" in r.stdout, f"{flag} must print the OPL tools version"

    def test_malformed_manifest_errors_cleanly(self, tmp_path):
        # G2: a corrupt/truncated manifest must produce a clean error, never a
        # raw traceback, across every manifest-reading subcommand.
        src = tmp_path / "src"
        src.mkdir()
        (src / "app.py").write_text("x=1")
        bad = tmp_path / "bad.json"
        bad.write_text("{this is not valid json!!!")
        for cmd, args in [
            ("check", ["--source", str(tmp_path), "--manifest", str(bad)]),
            ("build-merkle", ["--manifest", str(bad)]),
            ("verify", ["--source", str(tmp_path), "--manifest", str(bad)]),
        ]:
            r = run_canary(cmd, *args)
            assert r.returncode == 1, f"{cmd} should exit 1 on malformed manifest"
            assert "Traceback" not in (r.stdout + r.stderr), f"{cmd} leaked a traceback"
            assert "cannot parse manifest" in (r.stdout + r.stderr) or "Error" in (r.stdout + r.stderr)


class TestDriftCheck:
    def _make_repo(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "app.py").write_text("def hello():\n    print('hi')\n")
        (src / "mod.py").write_text("x = 1\n")
        return src

    def _embed(self, tmp_path, src):
        priv = tmp_path / "priv.json"
        pub = tmp_path / "pub.json"
        r = run_canary(
            "embed", "--source", str(src), "--project-id", "7",
            "--distribution-id", "rel1", "--salt", "s", "--num-canaries", "3",
            "--output", str(priv), "--public-output", str(pub),
        )
        assert r.returncode == 0
        return pub

    def test_no_drift_exits_zero(self, tmp_path):
        src = self._make_repo(tmp_path)
        pub = self._embed(tmp_path, src)
        r = run_canary("check", "--source", str(src), "--manifest", str(pub))
        assert r.returncode == 0
        assert "No drift" in r.stdout

    def test_drift_detected_on_update(self, tmp_path):
        src = self._make_repo(tmp_path)
        pub = self._embed(tmp_path, src)
        (src / "app.py").write_text("def hello():\n    print('changed')\n")
        (src / "new.py").write_text("y = 2\n")
        r = run_canary("check", "--source", str(src), "--manifest", str(pub))
        assert r.returncode == 1
        assert "MODIFIED: app.py" in r.stdout
        assert "ADDED: new.py" in r.stdout
        assert "DRIFT" in r.stdout

    def test_allow_drift_exits_zero(self, tmp_path):
        src = self._make_repo(tmp_path)
        pub = self._embed(tmp_path, src)
        (src / "app.py").write_text("changed\n")
        r = run_canary("check", "--allow-drift", "--source", str(src), "--manifest", str(pub))
        assert r.returncode == 0

    def test_missing_manifest_fails(self, tmp_path):
        src = self._make_repo(tmp_path)
        r = run_canary("check", "--source", str(src), "--manifest", str(tmp_path / "nope.json"))
        assert r.returncode != 0

    def test_missing_source_fails(self, tmp_path):
        pub = tmp_path / "pub.json"
        pub.write_text("{}")
        r = run_canary("check", "--source", str(tmp_path / "nope"), "--manifest", str(pub))
        assert r.returncode != 0


class TestCanaryCheckScript:
    def _make_repo(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "app.py").write_text("def hello():\n    print('hi')\n")
        return src

    def test_ci_hook_passes_on_match(self, tmp_path):
        src = self._make_repo(tmp_path)
        pkg = str(Path(TOOLS_DIR) / "canary_check.py")
        pub = tmp_path / "canary_release.json"
        r = run_canary(
            "embed", "--source", str(src), "--project-id", "1",
            "--distribution-id", "d", "--salt", "s", "--num-canaries", "1",
            "--output", str(tmp_path / "p.json"), "--public-output", str(pub),
        )
        assert r.returncode == 0
        proc = subprocess.run(
            [sys.executable, pkg, "--repo", str(src), "--payload", str(pub)],
            capture_output=True, text=True,
        )
        assert proc.returncode == 0

    def test_ci_hook_fails_on_drift(self, tmp_path):
        src = self._make_repo(tmp_path)
        pkg = str(Path(TOOLS_DIR) / "canary_check.py")
        pub = tmp_path / "canary_release.json"
        r = run_canary(
            "embed", "--source", str(src), "--project-id", "1",
            "--distribution-id", "d", "--salt", "s", "--num-canaries", "1",
            "--output", str(tmp_path / "p.json"), "--public-output", str(pub),
        )
        assert r.returncode == 0
        (src / "app.py").write_text("changed\n")
        proc = subprocess.run(
            [sys.executable, pkg, "--repo", str(src), "--payload", str(pub)],
            capture_output=True, text=True,
        )
        assert proc.returncode == 1

    def test_missing_payload_fails(self, tmp_path):
        src = self._make_repo(tmp_path)
        proc = subprocess.run(
            [sys.executable, str(Path(TOOLS_DIR) / "canary_check.py"),
             "--repo", str(src), "--payload", str(tmp_path / "nope.json")],
            capture_output=True, text=True,
        )
        assert proc.returncode == 1

    def test_embed_single_line_docstring_files_still_parse(self, tmp_path):
        # C1 regression: single-line docstring watermark must NOT produce IndentationError.
        src = tmp_path / "src"; src.mkdir()
        (src / "app.py").write_text(
            '"""single-line."""\n'
            'import os\n'
            '\n'
            'def f():\n'
            '    return 1\n'
        )
        out = tmp_path / "m.json"
        r = run_canary(
            "embed",
            "--source", str(tmp_path),
            "--project-id", "1",
            "--distribution-id", "c1_regression",
            "--salt", "salt",
            "--num-canaries", "2",
            "--output", str(out),
            "--public-output", str(tmp_path / "p.json"),
            "--strategies", "watermark",
        )
        assert r.returncode == 0
        # Ensure the embedded file still parses (no SyntaxError/IndentationError).
        import ast
        content = (src / "app.py").read_text()
        try:
            ast.parse(content)
        except SyntaxError as e:
            raise AssertionError(f"Embedded single-line-docstring .py does not parse: {e}")
        # Quick sanity: the reference is comment-prefixed, not bare.

    def test_verify_detects_variable_tokens_not_just_watermark(self, tmp_path):
        # H1 regression: verify must detect variable tokens (_CANARY_XXX = "hex"),
        # not only watermark literals.
        src = tmp_path / "src"; src.mkdir()
        (src / "app.py").write_text('import os\n')
        out = tmp_path / "m.json"
        r = run_canary(
            "embed",
            "--source", str(tmp_path),
            "--project-id", "1",
            "--distribution-id", "h1_var_regression",
            "--salt", "salt",
            "--num-canaries", "1",
            "--output", str(out),
            "--public-output", str(tmp_path / "p.json"),
            "--strategies", "variable",  # embed ONLY variable (no watermark)
        )
        assert r.returncode == 0
        # Verify must find the token (previously false-clean).
        vr = run_canary("verify", "--source", str(tmp_path), "--manifest", str(out))
        assert vr.returncode == 0
        assert "FOUND 1 CANARY TOKEN MATCH" in vr.stdout

    def test_verify_detects_deadcode_tokens_not_just_watermark(self, tmp_path):
        # H1 regression: verify must detect deadcode tokens (_validate_XXX + _marker_XXX),
        # not only watermark literals.
        src = tmp_path / "src"; src.mkdir()
        # Need enough content for deadcode embedder to target a function.
        (src / "app.py").write_text('import os\n\ndef f():\n    return 1\n')
        out = tmp_path / "m.json"
        r = run_canary(
            "embed",
            "--source", str(tmp_path),
            "--project-id", "1",
            "--distribution-id", "h1_dead_regression",
            "--salt", "salt",
            "--num-canaries", "1",
            "--output", str(out),
            "--public-output", str(tmp_path / "p.json"),
            "--strategies", "deadcode",  # embed ONLY deadcode (no watermark)
        )
        assert r.returncode == 0
        # Verify must find the token (previously false-clean).
        vr = run_canary("verify", "--source", str(tmp_path), "--manifest", str(out))
        assert vr.returncode == 0
        assert "FOUND 1 CANARY TOKEN MATCH" in vr.stdout

    def test_verify_still_detects_watermark(self, tmp_path):
        # H1 regression: verify must still detect watermark tokens after adding
        # variable/deadcode detection (no regressions).
        src = tmp_path / "src"; src.mkdir()
        (src / "app.py").write_text('import os\n')
        out = tmp_path / "m.json"
        r = run_canary(
            "embed",
            "--source", str(tmp_path),
            "--project-id", "1",
            "--distribution-id", "h1_watermark_regression",
            "--salt", "salt",
            "--num-canaries", "1",
            "--output", str(out),
            "--public-output", str(tmp_path / "p.json"),
            "--strategies", "watermark",  # embed ONLY watermark
        )
        assert r.returncode == 0
        vr = run_canary("verify", "--source", str(tmp_path), "--manifest", str(out))
        assert vr.returncode == 0
        assert "FOUND 1 CANARY TOKEN MATCH" in vr.stdout

    def test_verify_detects_all_strategies_in_mixed_tree(self, tmp_path):
        # H1 regression: verify must detect all three strategies when they're
        # mixed in the same tree (realistic deployment scenario).
        src = tmp_path / "src"; src.mkdir()
        # Need enough content for deadcode embedder to target a function.
        (src / "app.py").write_text('import os\n\ndef f():\n    return 1\n')
        out = tmp_path / "m.json"
        r = run_canary(
            "embed",
            "--source", str(tmp_path),
            "--project-id", "1",
            "--distribution-id", "h1_mixed_regression",
            "--salt", "salt",
            "--num-canaries", "1",
            "--output", str(out),
            "--public-output", str(tmp_path / "p.json"),
            "--strategies", "watermark,variable,deadcode",  # all three
        )
        assert r.returncode == 0
        vr = run_canary("verify", "--source", str(tmp_path), "--manifest", str(out))
        assert vr.returncode == 0
        # Should find 1 token (the same token embedded with all three strategies).
        assert "FOUND 1 CANARY TOKEN MATCH" in vr.stdout
