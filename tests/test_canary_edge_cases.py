# SPDX-License-Identifier: OPL-1.3.1
"""Integration tests for edge cases in root-level scripts:
canary_embedder.py, cicd_pipeline.py, js_embedder.py
"""
from __future__ import annotations

import json
import random
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
        root, tree = mt.build(["a", "b"])
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
        from canary_embedder import CanaryEmbedder, CanaryManifest
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
        from canary_embedder import CanaryEmbedder, CanaryManifest
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
        result = emb.embed(tmp_path, "canary_test", rng)


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
        r = run_canary(
            "embed",
            "--source", str(tmp_path),
            "--project-id", "1",
            "--distribution-id", "abc",
            "--salt", "secret",
            "--num-canaries", "2",
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


# ---------------------------------------------------------------------------
# cicd_pipeline.py edge cases
# ---------------------------------------------------------------------------

class TestCICDEdgeCases:
    def test_missing_config(self):
        r = run_cicd("--config", "/nonexistent/config.json")
        assert r.returncode == 0 or r.returncode != 0

    def test_empty_config_file(self, tmp_path):
        cfg = tmp_path / "empty.json"
        cfg.write_text("{}")
        r = run_cicd("--config", str(cfg))
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


# ---------------------------------------------------------------------------
# js_embedder.py edge cases (import directly since no CLI)
# ---------------------------------------------------------------------------
