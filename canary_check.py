# SPDX-License-Identifier: OPL-1.4
"""canary_check.py — CI drift hook for OPL canary fingerprints.

Thin wrapper around `canary_embedder.py check`: on every commit/release CI
verifies the current tree still matches the recorded fingerprint (from a
committed public payload), and fails red if the repo has drifted. This is the
automatic balancing loop for 'a repo stays verifiable as it updates'.

Stdlib only. No secrets touch CI: it reads the PUBLIC payload, never the private
manifest/salt. Intentional releases re-run `embed` to emit a fresh payload.

Usage:
    python3 canary_check.py --repo . --payload canary_release.json
Exit codes: 0 = matches, 1 = drift (or config/usage error).
"""

import argparse
import importlib.util
import subprocess
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
EMBEDDER = TOOLS_DIR / "canary_embedder.py"
DEFAULT_PAYLOAD = "canary_release.json"

# Single source of truth: the OPL tools version (stdlib-only, import-safe).
_vpath = TOOLS_DIR / "tools" / "_version.py"
_vspec = importlib.util.spec_from_file_location("_opl_version", _vpath)
if _vspec and _vspec.loader:
    _vmod = importlib.util.module_from_spec(_vspec)
    _vspec.loader.exec_module(_vmod)
    __version__ = _vmod.__version__
else:
    __version__ = "1.4"


def main() -> int:
    ap = argparse.ArgumentParser(description="OPL canary CI drift hook")
    ap.add_argument("-V", "--version", action="version",
                    version=f"OPL-1.4 canary CI hook v{__version__}")
    ap.add_argument("--repo", required=True, help="Repository source directory to hash")
    ap.add_argument("--payload", default=DEFAULT_PAYLOAD,
                    help="Path to the PUBLIC canary payload (default: canary_release.json)")
    ap.add_argument("--allow-drift", action="store_true",
                    help="Report drift but exit 0 (for soft warning jobs)")
    args = ap.parse_args()

    if not Path(args.payload).exists():
        print(f"canary_check: no public payload at {args.payload}. Run `canary_embedder.py embed` "
              f"to fingerprint this release first (or set --payload to its path).", file=sys.stderr)
        return 1

    cmd = [sys.executable, str(EMBEDDER), "check",
           "--source", args.repo, "--manifest", args.payload]
    if args.allow_drift:
        cmd.append("--allow-drift")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    return 0 if args.allow_drift else proc.returncode


if __name__ == "__main__":
    sys.exit(main())