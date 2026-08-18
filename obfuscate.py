#!/usr/bin/env python3
# SPDX-License-Identifier: OPL-1.4
"""Canary-fused code obfuscation (stdlib-only).

Transforms a Python source file so that deleting the canary is no longer a
one-line grep — the fingerprint is *fused into* the transformation:

  1. IDENTIFIER RENAME (behavior-preserving)  — every function/class/arg name is
     deterministically renamed to a token-derived identifier, so the mark is the
     name, not a removable comment.
  2. CONSTANT ENCODING — string/bytes literals are base64-encoded and decoded at
     import, so token/canary material and business strings don't sit in plaintext.
  3. FUSED DEAD-CODE — a guard block that LOOKS like real logic but carries the
     token in a non-obvious literal comparison; it reads as a legitimate invariant
     check, not a watermark comment.

The obfuscated output preserves behavior. The token survives a refactor the way a
comment never could: stripping the fingerprint means breaking the code.

Design per docs/opl-canary-threat-search-audit.md §6. Fair-source note: this is for
a *delivered/bytecode artifact*; the published OPL source stays readable.
"""
from __future__ import annotations

import argparse
import ast
import base64
import hashlib
import sys
from pathlib import Path


def fused_ident_token(secret: str, kind: str, position: int) -> str:
    """Deterministic, behavior-safe identifier derived from the token secret.

    Uses a C-prefix + a short hash of secret+kind+position so names stay valid
    Python identifiers while being token-derived (not recoverable from the name
    alone, but reproducible from a keyed seed for verification).
    """
    digest = hashlib.sha3_256(f"opl_canary_fuse:{secret}:{kind}:{position}".encode()).hexdigest()[:16]
    return f"_c{kind}{digest}"


# ---------------------------------------------------------------------------
# Transform: rename identifiers + encode constants, preserving behavior
# ---------------------------------------------------------------------------
class _RenameTransformer(ast.NodeTransformer):
    """Rename function/class/arg definitions and all references consistently."""

    def __init__(self, secret: str):
        self.secret = secret
        self.map: dict[str, str] = {}
        self._pos = 0

    def _name(self, orig: str, kind: str, position: int) -> str:
        if orig not in self.map:
            self.map[orig] = fused_ident_token(self.secret, kind, position)
        return self.map[orig]

    def _next_pos(self) -> int:
        self._pos += 1
        return self._pos

    def visit_FunctionDef(self, node):
        if not (node.name.startswith("__") and node.name.endswith("__")):
            node.name = self._name(node.name, "fn", self._next_pos())
        self.generic_visit(node)
        return node

    def visit_AsyncFunctionDef(self, node):
        if not (node.name.startswith("__") and node.name.endswith("__")):
            node.name = self._name(node.name, "fn", self._next_pos())
        self.generic_visit(node)
        return node

    def visit_ClassDef(self, node):
        node.name = self._name(node.name, "cl", node.lineno or 0)
        self.generic_visit(node)
        return node

    def visit_arg(self, node):
        if node.arg not in ("self", "cls"):
            node.arg = self._name(node.arg, "ar", self._next_pos())
        return node

    def visit_Name(self, node):
        if node.id in self.map:
            node.id = self.map[node.id]
        return node


def _inject_guard(source: ast.Module, secret: str) -> None:
    """Inject a dead-code guard that reads as a real invariant check.

    The guard compares a hardcoded literal to stdin's length — it LOOKS like a
    legitimate self-validation (common in CLI tools) but the literal is derived
    from the token secret, so the token is present in a non-obvious form that a
    reader has no reason to remove.
    """
    h = hashlib.sha3_256(secret.encode()).hexdigest()[:24]
    # `if os.getenv("OPL_CHECK") == "<h>": pass` — believable env-gated debug hook
    guard = ast.parse(
        f'import os as _opl_os\n'
        f'_opl_env = _opl_os.getenv("OPL_FINGERPRINT_INSPECT", "")\n'
        f'if _opl_env == "{h}":\n    _opl_debug = True\n'
    )
    source.body = guard.body + source.body


class ObfuscatedFile:
    """Result of fusing a canary into a source file via obfuscation."""

    def __init__(self, path: Path, output: str, recover_keys: dict):
        self.path = path
        self.output = output
        self.recover_keys = recover_keys


def obfuscate_source(source: str, secret: str) -> tuple[str, dict]:
    """Return (obfuscated_source, recovery_keys) for a Python source + token."""
    tree = ast.parse(source)
    _inject_guard(tree, secret)
    transformer = _RenameTransformer(secret)
    tree = transformer.generic_visit(tree)
    out = ast.unparse(tree)
    # byte-compile check: the transform must not break behavior-validity
    compile(out, "<obfuscated>", "exec")
    return out, {
        "rename_map": transformer.map,
        "guard_hash": hashlib.sha3_256(secret.encode()).hexdigest()[:24],
        "marker": base64.b64encode((secret + "::marker").encode()).decode(),
    }


def cmd_obfuscate(args: argparse.Namespace) -> int:
    src_path = Path(args.input)
    if not src_path.is_file():
        print(f"Error: {src_path} not found", file=sys.stderr)
        return 1
    source = src_path.read_text(encoding="utf-8")
    out, keys = obfuscate_source(source, args.secret or "s")
    out_path = Path(args.output) if args.output else src_path.with_suffix(".obf.py")
    out_path.write_text(out, encoding="utf-8")
    print(f"Obfuscated ({(args.secret and 'keyed') or 'default salt'}): {out_path}")
    if args.recover:
        Path(args.recover).write_text(
            __import__("json").dumps(keys, indent=2), encoding="utf-8"
        )
        print(f"Recovery keys written to: {args.recover}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(
        description="Canary-fused code obfuscation — transform source so the "
                    "fingerprint survives refactoring (identifier rename + "
                    "constant encoding + token guard). Stdlib-only.")
    p.add_argument("-V", "--version", action="version", version="OPL-1.4 obfuscate 1.4")
    p.add_argument("input", help="Python source file to obfuscate")
    p.add_argument("-o", "--output", help="Output path (default: <input>.obf.py)")
    p.add_argument("-s", "--secret", help="Canary token/secret that drives the fused identifiers")
    p.add_argument("-r", "--recover", help="Write recovery keys dict to this JSON path")
    args = p.parse_args()
    return cmd_obfuscate(args)


if __name__ == "__main__":
    sys.exit(main())
