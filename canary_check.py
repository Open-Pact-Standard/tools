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
import subprocess
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
EMBEDDER = TOOLS_DIR / "canary_embedder.py"
DEFAULT_PAYLOAD = "canary_release.json"


def main() -> int:
    ap = argparse.ArgumentParser(description="OPL canary CI drift hook")
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