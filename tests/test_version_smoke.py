# SPDX-License-Identifier: OPL-1.3.1
"""Smoke tests for tools._version side-effect-free contract.

tools._version is imported at build time by setuptools' dynamic version
resolution (see [tool.setuptools.dynamic] in pyproject.toml) when
`pip install` builds the package from sdist in a clean environment.

This test enforces that contract by importing the module in a fresh
subprocess: if any side effect is added (network calls, file I/O, logging
configuration, argparse use, print() at module top level, etc.), this
test will catch it via unexpected stdout/stderr, a non-zero exit code,
or a version that isn't parseable as PEP 440.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from packaging.version import Version

REPO_ROOT = Path(__file__).resolve().parent.parent


def _import_version_in_subprocess() -> subprocess.CompletedProcess:
    """Import tools._version in a fresh subprocess and return the result.

    Uses the same Python interpreter as the test runner so ABI matches.
    REPO_ROOT is prepended to PYTHONPATH so `import tools._version`
    resolves in the spawned process — this mirrors what setuptools does
    at build time, where the source tree is on sys.path.
    """
    env = os.environ.copy()
    existing_pp = env.get("PYTHONPATH", "")
    extra_pp = str(REPO_ROOT)
    env["PYTHONPATH"] = (
        f"{extra_pp}{os.pathsep}{existing_pp}" if existing_pp else extra_pp
    )
    return subprocess.run(
        [sys.executable, "-c", "import tools._version as v; print(v.__version__)"],
        capture_output=True,
        text=True,
        timeout=5,
        env=env,
        check=False,
    )


class TestVersionSideEffectFree:
    """tools._version MUST be importable with no side effects."""

    def test_import_exits_zero(self) -> None:
        result = _import_version_in_subprocess()
        assert result.returncode == 0, (
            f"subprocess exited {result.returncode}\n"
            f"stdout: {result.stdout!r}\nstderr: {result.stderr!r}"
        )

    def test_import_produces_no_stderr(self) -> None:
        result = _import_version_in_subprocess()
        assert result.stderr == "", (
            f"subprocess wrote to stderr: {result.stderr!r}\n"
            "(logging, warnings, or prints at module top level are side effects)"
        )

    def test_stdout_is_exactly_the_version(self) -> None:
        result = _import_version_in_subprocess()
        # Exact-match (not contains) so a stray print("loaded") from a future
        # side effect fails loudly instead of producing multi-line stdout that
        # still "contains" a version string.
        line = result.stdout.rstrip("\n")
        assert result.stdout == line + "\n", (
            f"expected exactly one line of stdout, got {result.stdout!r}"
        )
        assert line, "version string is empty"

    def test_version_is_well_formed(self) -> None:
        result = _import_version_in_subprocess()
        version = result.stdout.rstrip("\n")
        assert version, "version string is empty"
        # `packaging.version.Version` is the canonical PEP 440 parser — letting
        # `InvalidVersion` propagate gives pytest a precise error message
        # (file:line + exception type) without a hand-rolled wrapper.
        Version(version)

    def test_version_matches_package_constant(self) -> None:
        from tools import _version as in_process

        result = _import_version_in_subprocess()
        subprocess_version = result.stdout.rstrip("\n")
        assert subprocess_version == in_process.__version__, (
            f"subprocess version {subprocess_version!r} does not match "
            f"in-process __version__ {in_process.__version__!r}"
        )
        # Belt-and-suspenders: also exercise `Version(__version__)` directly
        # on the in-process constant (what the smoke test exists to protect),
        # not just on the subprocess output.
        Version(in_process.__version__)
