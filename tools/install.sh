#!/usr/bin/env bash
# SPDX-License-Identifier: OPL-1.4
# OPL Studio installer — local only, no network egress, no accounts.
set -euo pipefail

echo "OPL Studio installer"
echo "====================="

# 1. Resolve repo root (this script lives in tools/).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 2. Preflight: Python 3.9+ (stdlib http.server + webbrowser).
if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 not found. Install Python 3.9+ and re-run." >&2
  exit 1
fi
PYV=$(python3 -c "import sys; print(sys.version_info >= (3,9))")
if [ "$PYV" != "True" ]; then
  echo "ERROR: Python 3.9+ required." >&2
  exit 1
fi

# 3. Build the Adoption Kit dist + zip (best effort; needs the open-pact-license
#    repo sibling for the drift guard, but degrades gracefully).
echo "Building Adoption Kit..."
python3 adoption-kit/make_kit.py >/dev/null 2>&1 || echo "  (Kit build skipped — see dist/ or run make_kit.py manually)"
python3 -c "import shutil,pathlib; shutil.make_archive(str(pathlib.Path('adoption-kit/dist/opl-adoption-kit')),'zip',pathlib.Path('adoption-kit/dist'))" 2>/dev/null \
  && echo "  Kit zip ready: adoption-kit/dist/opl-adoption-kit.zip" || echo "  (zip build skipped)"

# 4. Done — print the launch command.
echo ""
echo "Install complete. Launch OPL Studio with:"
echo ""
echo "    python3 opl_studio.py"
echo ""
echo "Then open http://localhost:8771 in your browser."
echo "To stop: press Ctrl-C in this terminal."
echo ""
echo "Everything runs on your machine. No upload, no accounts."
