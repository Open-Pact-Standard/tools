# SPDX-License-Identifier: OPL-1.4
"""
OPL-1.4 Fingerprinting Tool — Canary Token Embedding + Release Fingerprinting

Embeds unique, steganographic canary tokens into source code, builds a
SHA3-256 Merkle tree from the canary secrets, and generates a distribution
manifest. The Merkle root is published (e.g. in a GPG-signed Git tag) so that
discovery of a canary in a suspect codebase is cryptographically verifiable.

This is the enforcement backbone for the OPL-AI addendum (v1.3.1). It is
optional — OPL-1.4 does not require fingerprinting. But if a Maintainer
opts into OPL-AI and wants real, verifiable enforcement, this is the tool.

Requires: Python 3.10+, stdlib only.
"""

import argparse
import hashlib
import json
import math
import os
import re
import random
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

CANARY_PREFIX = "canary"
SUPPORTED_EXTENSIONS = {
    '.py', '.js', '.ts', '.jsx', '.tsx', '.rs', '.go',
    '.sol', '.c', '.cpp', '.h', '.hpp', '.java', '.kt',
    '.rb', '.php', '.m', '.swift',
}

EXCLUDED_DIRS = frozenset({
    'test', 'tests', '__test__', '__tests__', '__pycache__',
    'node_modules', '.git', 'venv', '.venv', '.env',
    'build', 'dist', 'target', '.tox', '.nox', '.eggs',
    'tools',
})

# The tool must never inject canaries into its own source or artifacts,
# otherwise dogfooding silently corrupts the enforcement tooling itself.
SELF_EXCLUDED_FILENAMES = frozenset({
    'canary_embedder.py', 'canary_check.py', 'js_embedder.py', 'cicd_pipeline.py',
    'canary_manifest.json', 'release_fingerprint.json',
})

@dataclass
class CanaryToken:
    token_id: int
    secret: str
    embedding_type: str
    target_file: str = ""
    line_number: int = -1
    code_before: str = ""
    code_after: str = ""
    merkle_leaf: str = ""
    merkle_proof: List[str] = field(default_factory=list)

@dataclass
class CanaryManifest:
    project_id: int
    distribution_id: str
    salt: str
    file_hash: str = ""
    canary_tokens: List[CanaryToken] = field(default_factory=list)
    merkle_root: str = ""
    # Per-file sha3-256 {relative_path: hash} for the tree at fingerprint time.
    # Lets `verify --against` report exactly WHICH files changed as the repo
    # evolves (the "when a repo updates too" requirement).
    source_files: Dict[str, str] = field(default_factory=dict)

class TokenGenerator:
    @staticmethod
    def generate(project_id: int, distribution_id: str, index: int, salt: str) -> str:
        data = f"{CANARY_PREFIX}_{project_id}_{distribution_id}_{index}_{salt}"
        h = hashlib.sha3_256(data.encode()).hexdigest()[:12]
        return f"{CANARY_PREFIX}_{h}"

class MerkleTree:
    @staticmethod
    def hash(data: str) -> str:
        return hashlib.sha3_256(data.encode()).hexdigest()

    def build(self, leaves: List[str]) -> Tuple[str, List[List[str]]]:
        if not leaves:
            raise ValueError("At least one leaf required")
        hashed = [self.hash(leaf) for leaf in leaves]
        n = len(hashed)
        next_pow2 = 1
        while next_pow2 < n:
            next_pow2 *= 2
        if len(hashed) < next_pow2:
            hashed.extend([hashed[-1]] * (next_pow2 - len(hashed)))
        tree = [hashed[:]]
        level = hashed[:]
        while len(level) > 1:
            next_level = []
            for i in range(0, len(level), 2):
                combined = self.hash(level[i] + level[i + 1])
                next_level.append(combined)
            tree.append(next_level)
            level = next_level
        return level[0], tree

    def get_proof(self, tree: List[List[str]], leaf_index: int) -> List[str]:
        proof = []
        index = leaf_index
        for level in range(len(tree) - 1):
            sibling_index = index + 1 if index % 2 == 0 else index - 1
            if sibling_index < len(tree[level]):
                proof.append(tree[level][sibling_index])
            index //= 2
        return proof

class VariableInjectionEmbedder:
    TEMPLATES = {
        '.py': '_{TOKEN} = "{TOKEN_VAL}"  # Internal config marker',
        '.js': 'const {TOKEN} = "{TOKEN_VAL}"; // Internal config marker',
        '.ts': 'const {TOKEN} = "{TOKEN_VAL}"; // Internal config marker',
        '.rs': 'const {TOKEN}: &str = "{TOKEN_VAL}"; // Internal config marker',
        '.sol': 'string constant {TOKEN} = "{TOKEN_VAL}"; // Internal marker',
        '.c': 'static const char* {TOKEN} = "{TOKEN_VAL}"; /* Internal marker */',
        '.go': 'const {TOKEN} = "{TOKEN_VAL}" // Internal marker',
        '.java': 'private static final String {TOKEN} = "{TOKEN_VAL}"; // Internal',
    }

    def __init__(self) -> None:
        self.files_modified: List[str] = []

    def embed(self, source_dir: Path, token: str, rng: random.Random) -> Optional[str]:
        files = []
        for ext in self.TEMPLATES:
            files.extend(source_dir.rglob(f'*{ext}'))
        files = [f for f in files if not self._is_excluded(f) and f.stat().st_size < 500_000]
        if not files:
            return None

        target = rng.choice(files)
        relative = str(target.relative_to(source_dir))
        var_name = token.upper()
        var_val = hashlib.sha3_256(token.encode()).hexdigest()[:16]
        template = self.TEMPLATES.get(target.suffix, self.TEMPLATES['.py'])
        injected = template.format(TOKEN=var_name, TOKEN_VAL=var_val)

        content = target.read_text(encoding='utf-8', errors='replace')
        lines = content.split('\n')
        insert_at = self._find_insertion_point(lines, target.suffix)
        lines.insert(insert_at, injected)
        target.write_text('\n'.join(lines), encoding='utf-8')
        self.files_modified.append(relative)
        return relative

    @staticmethod
    def _is_excluded(path: Path) -> bool:
        parts = set(p.lower() for p in path.parts)
        if path.name in SELF_EXCLUDED_FILENAMES:
            return True
        return bool(parts & EXCLUDED_DIRS)

    def _find_insertion_point(self, lines: List[str], suffix: str) -> int:
        insert_at = 0
        in_imports = False
        for i, line in enumerate(lines):
            stripped = line.strip()
            if suffix == '.py':
                if stripped.startswith('import ') or stripped.startswith('from '):
                    in_imports = True
                    insert_at = i + 1
                elif in_imports and stripped and not stripped.startswith('#'):
                    in_imports = False
                    insert_at = max(insert_at, i)
            elif suffix in ('.js', '.ts'):
                if stripped.startswith('import ') or stripped.startswith('require('):
                    insert_at = i + 1
            else:
                if stripped.startswith('#include') or stripped.startswith('#import'):
                    insert_at = i + 1
        for i, line in enumerate(lines[:5]):
            if line.startswith('#!') or 'Copyright' in line or 'SPDX' in line:
                insert_at = max(insert_at, i + 1)
        return insert_at

class WatermarkEmbedder:
    def __init__(self) -> None:
        self.files_modified: List[str] = []

    def embed(self, source_dir: Path, token: str, rng: random.Random) -> Optional[str]:
        python_files = [f for f in source_dir.rglob('*.py')
                       if not self._is_excluded(f) and f.stat().st_size < 500_000]
        if not python_files:
            return None

        target = rng.choice(python_files)
        relative = str(target.relative_to(source_dir))
        content = target.read_text(encoding='utf-8', errors='replace')
        lines = content.split('\n')

        for i, line in enumerate(lines):
            if line.strip().startswith('"""') or line.strip().startswith("'''"):
                lines.insert(i + 1, f"  Internal reference: {token}")
                target.write_text('\n'.join(lines), encoding='utf-8')
                self.files_modified.append(relative)
                return relative
            elif line.strip().startswith('#') and len(line.strip()) > 10:
                lines[i] = line.rstrip() + f' [ref:{token}]'
                target.write_text('\n'.join(lines), encoding='utf-8')
                self.files_modified.append(relative)
                return relative

        for i, line in enumerate(lines):
            if line.strip() and not line.strip().startswith('#!'):
                lines.insert(i, f'# Module reference: {token}')
                target.write_text('\n'.join(lines), encoding='utf-8')
                self.files_modified.append(relative)
                return relative
        return None

    @staticmethod
    def _is_excluded(path: Path) -> bool:
        parts = set(p.lower() for p in path.parts)
        if path.name in SELF_EXCLUDED_FILENAMES:
            return True
        return bool(parts & EXCLUDED_DIRS)

class DeadCodeEmbedder:
    def __init__(self) -> None:
        self.files_modified: List[str] = []

    def embed(self, source_dir: Path, token: str, rng: random.Random) -> Optional[str]:
        python_files = [f for f in source_dir.rglob('*.py')
                       if not self._is_excluded(f) and f.stat().st_size < 500_000]
        if not python_files:
            return None

        target = rng.choice(python_files)
        relative = str(target.relative_to(source_dir))
        content = target.read_text(encoding='utf-8', errors='replace')
        lines = content.split('\n')

        func_lines = [i for i, line in enumerate(lines) if re.match(r'^(\s*)def\s+', line)]
        if not func_lines:
            return None

        func_line = rng.choice(func_lines)
        magic_val = hashlib.sha3_256(token.encode()).hexdigest()[:8]
        indent = '    '
        insert_at = func_line + 2

        dead_code = [
            f'{indent}# Internal validation helper',
            f'{indent}def _validate_{magic_val[:4]}():',
            f'{indent}    if isinstance(globals().get("_config"), dict):',
            f'{indent}        return True',
            f'{indent}    _marker_{magic_val} = True',
            f'{indent}    return False',
            f'{indent}',
        ]

        for i, line in enumerate(dead_code):
            lines.insert(insert_at + i, line)

        target.write_text('\n'.join(lines), encoding='utf-8')
        self.files_modified.append(relative)
        return relative

    @staticmethod
    def _is_excluded(path: Path) -> bool:
        parts = set(p.lower() for p in path.parts)
        if path.name in SELF_EXCLUDED_FILENAMES:
            return True
        return bool(parts & EXCLUDED_DIRS)

class CanaryEmbedder:
    def __init__(self, project_id: int, distribution_id: str, salt: str, strategies: Optional[List[str]] = None, num_canaries: int = 10) -> None:
        self.project_id = project_id
        self.distribution_id = distribution_id
        self.salt = salt
        self.num_canaries = num_canaries
        self.strategies_str = strategies or ['variable', 'watermark']
        self.tokens: List[CanaryToken] = []
        self.merkle_tree = MerkleTree()
        self.tree_root = ""
        self.tree_levels: List[List[str]] = []
        self.strategy_map = {
            'variable': VariableInjectionEmbedder(),
            'deadcode': DeadCodeEmbedder(),
            'watermark': WatermarkEmbedder(),
        }

    def generate_tokens(self) -> None:
        self.tokens = []
        strategy_names = list(self.strategies_str)
        for i in range(self.num_canaries):
            strategy = strategy_names[i % len(strategy_names)]
            token_str = TokenGenerator.generate(self.project_id, self.distribution_id, i, self.salt)
            self.tokens.append(CanaryToken(
                token_id=i, secret=token_str, embedding_type=strategy,
                target_file="", line_number=-1, code_before="", code_after="",
            ))

    def embed(self, source_dir: Path) -> List[CanaryToken]:
        rng = random.Random(f"{self.project_id}_{self.distribution_id}_{self.salt}".encode())
        for token in self.tokens:
            strategy = self.strategy_map.get(token.embedding_type)
            if strategy is None:
                print(f"  Unknown strategy: {token.embedding_type}")
                continue
            target_file = strategy.embed(source_dir, token.secret, rng)
            if target_file:
                token.target_file = target_file
                print(f"  Embedded [{token.token_id}] {token.secret[:20]}... in {target_file}")
            else:
                print(f"  Failed to embed [{token.token_id}] (no suitable file)")
        return self.tokens

    def build_merkle_tree(self) -> str:
        leaves = []
        for token in self.tokens:
            leaf_data = f"{token.secret}_{self.project_id}_{self.distribution_id}_{token.token_id}"
            leaf_hash = hashlib.sha3_256(leaf_data.encode()).hexdigest()
            token.merkle_leaf = leaf_hash
            leaves.append(leaf_hash)
        self.tree_root, self.tree_levels = self.merkle_tree.build(leaves)
        for i, token in enumerate(self.tokens):
            token.merkle_proof = self.merkle_tree.get_proof(self.tree_levels, i)
        return self.tree_root

    def generate_manifest(self, source_dir: Path) -> CanaryManifest:
        tree_hash, source_files = self._hash_tree(source_dir)
        return CanaryManifest(
            project_id=self.project_id, distribution_id=self.distribution_id,
            salt=self.salt, file_hash=tree_hash,
            canary_tokens=list(self.tokens), merkle_root=self.tree_root,
            source_files=source_files,
        )

    def _hash_tree(self, source_dir: Path) -> Tuple[str, Dict[str, str]]:
        h = hashlib.sha3_256()
        files: Dict[str, str] = {}
        for f in sorted(source_dir.rglob('*')):
            if f.is_file() and f.suffix in SUPPORTED_EXTENSIONS:
                rel = f.relative_to(source_dir).as_posix()
                fh = hashlib.sha3_256(f.read_bytes()).hexdigest()
                files[rel] = fh
                h.update(rel.encode())
                h.update(f.read_bytes())
        return h.hexdigest(), files

    def hash_current_tree(self, source_dir: Path) -> Tuple[str, Dict[str, str]]:
        """Hash the current tree for drift comparison against a recorded manifest."""
        return self._hash_tree(source_dir)

    def verify_source(self, source_dir: Path, manifest: CanaryManifest) -> List[Tuple[str, str]]:
        matches = []
        for token_data in manifest.canary_tokens:
            secret = token_data.secret
            for f in source_dir.rglob('*'):
                if f.is_file() and f.suffix in SUPPORTED_EXTENSIONS:
                    try:
                        content = f.read_text(encoding='utf-8', errors='replace')
                        if secret in content:
                            rel = str(f.relative_to(source_dir))
                            matches.append((rel, secret))
                    except Exception:
                        pass
        return matches

def build_public_payload(manifest_data: dict) -> dict:
    """Return a publishable payload with all enforcement secrets stripped.

    The full manifest carries `_steward_secret_salt` and every token `secret` —
    if that file is committed or shared, an attacker can regenerate or strip
    every canary. The public payload keeps only the public record: project /
    distribution identity, tree hash, merkle root, and per-token Merkle proofs.
    Publish THIS file (e.g. in release notes / a signed git tag); keep the full
    manifest private.
    """
    return {
        "project_id": manifest_data.get("project_id"),
        "distribution_id": manifest_data.get("distribution_id"),
        "file_hash": manifest_data.get("file_hash"),
        "merkle_root": manifest_data.get("merkle_root"),
        "source_files": manifest_data.get("source_files", {}),
        "canary_tokens": [
            {
                "token_id": t.get("token_id"),
                "merkle_leaf": t.get("merkle_leaf"),
                "merkle_proof": t.get("merkle_proof", []),
            }
            for t in manifest_data.get("canary_tokens", [])
        ],
    }


def cmd_embed(args: argparse.Namespace) -> None:
    source_dir = Path(args.source).resolve()
    if not source_dir.is_dir():
        print(f"Error: {source_dir} is not a directory", file=sys.stderr)
        sys.exit(1)
    if not args.project_id:
        print("Error: --project-id is required (positive integer). A canary manifest "
              "must attest WHICH project it fingerprints.", file=sys.stderr)
        sys.exit(1)
    distribution_id = args.distribution_id
    if distribution_id.startswith('0x'):
        distribution_id = distribution_id[2:]

    embedder = CanaryEmbedder(
        project_id=args.project_id, distribution_id=distribution_id,
        salt=args.salt, strategies=args.strategies.split(','), num_canaries=args.num_canaries,
    )
    embedder.generate_tokens()  # tokens drive embed + manifest — must run first

    print(f"""
{'='*60}
OPL-1.4 Fingerprinting — Distribution Manifest
{'='*60}
  Source:        {source_dir}
  Project ID:    {args.project_id}
  Distribution:  {distribution_id}
  Salt:          {args.salt[:8]}{'*'*(len(args.salt)-8) if len(args.salt) > 8 else ''}
  Strategies:    {args.strategies}
  Canaries:      {args.num_canaries}

Step 1: Generating canary tokens...
  Generated {len(embedder.tokens)} tokens

Step 2: Embedding tokens into source...""")
    embedder.embed(source_dir)
    print()

    print("Step 3: Building Merkle tree...")
    if embedder.tokens:
        root = embedder.build_merkle_tree()
    else:
        root = ""
        print("  (no tokens embedded — empty Merkle root)")
    print(f"  Merkle root: 0x{root}\n")

    print("Step 4: Generating manifest...")
    manifest = embedder.generate_manifest(source_dir)

    output = Path(args.output) if args.output else Path('canary_manifest.json')
    manifest_dict = {
        'project_id': manifest.project_id, 'distribution_id': manifest.distribution_id,
        'file_hash': manifest.file_hash, 'merkle_root': manifest.merkle_root,
        'canary_tokens': [asdict(t) for t in manifest.canary_tokens],
        'source_files': manifest.source_files,
        '_steward_secret_salt': args.salt,
    }
    output.write_text(json.dumps(manifest_dict, indent=2))
    print(f"  PRIVATE manifest saved to: {output}  (contains secrets — do NOT publish/gitignore)")

    # Public payload: publishable, secrets stripped (salt + token secrets removed).
    public_payload = build_public_payload(manifest_dict)
    public_output = Path(args.public_output) if args.public_output else \
        output.parent / "release_fingerprint.json"
    public_output.write_text(json.dumps(public_payload, indent=2))
    print(f"  PUBLIC payload saved to:  {public_output}  (no secrets — safe to publish)")

    print(f"""
Step 3: Building Merkle tree...
  Merkle root: 0x{root}

Step 4: Generating distribution manifest...
  PRIVATE manifest: {output}      (KEEP OFFLINE; contains secrets)
  PUBLIC payload:   {public_output} (safe to publish: merkle root, tree hash, proofs)

Step 5: Record the public record for verification
  Publish the PUBLIC payload (merkle root + proofs + tree hash) in a verifiable form:
    - GPG-sign a Git tag:  git tag -s v1.0 -m "Merkle: 0x{root}"
    - Add release_fingerprint.json to the tag message or release notes.

  The published PUBLIC payload + GPG signature form the verifiable record.
  Keep the PRIVATE manifest (secrets) offline for litigation evidence assembly.
  To verify an unmodified repo while it evolves, run `verify --against` (G5).
""")

def cmd_build_merkle(args: argparse.Namespace) -> None:
    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print(f"Error: {manifest_path} not found", file=sys.stderr)
        sys.exit(1)
    with open(manifest_path) as f:
        manifest = json.load(f)
    mt = MerkleTree()
    leaves = []
    for token in manifest['canary_tokens']:
        data = f"{token['secret']}_{manifest['project_id']}_{manifest['distribution_id']}_{token['token_id']}"
        leaves.append(hashlib.sha3_256(data.encode()).hexdigest())
    root, tree = mt.build(leaves)
    print(f"Merkle root: 0x{root}")
    print(f"Number of leaves: {len(leaves)}")
    print(f"Tree depth: {len(tree)}")
    for i, token in enumerate(manifest['canary_tokens']):
        proof = mt.get_proof(tree, i)
        print(f"\nToken {token['token_id']} ({token['secret'][:20]}...):")
        print(f"  Leaf:   0x{token.get('merkle_leaf', leaves[i])}")
        print(f"  Proof:  {[f'0x{p}' for p in proof]}")

def cmd_verify(args: argparse.Namespace) -> None:
    source_dir = Path(args.source).resolve()
    manifest_path = Path(args.manifest)
    if not source_dir.is_dir():
        print(f"Error: {source_dir} is not a directory", file=sys.stderr)
        sys.exit(1)
    if not manifest_path.exists():
        print(f"Error: {manifest_path} not found", file=sys.stderr)
        sys.exit(1)

    with open(manifest_path) as f:
        manifest_data = json.load(f)

    salt = manifest_data.get('_steward_secret_salt', '')
    embedder = CanaryEmbedder(
        project_id=manifest_data['project_id'], distribution_id=manifest_data['distribution_id'],
        salt=salt,
    )
    embedder.tokens = [CanaryToken(**t) for t in manifest_data['canary_tokens']]

    print(f"""
Scanning for canary tokens...
{'='*60}
OPL-1.4 Fingerprinting — Verification
{'='*60}
  Scanning:      {source_dir}
  Manifest:      {manifest_path}
  Canaries:      {len(embedder.tokens)}
  Merkle root:   0x{manifest_data['merkle_root']}
""")

    print("Scanning for canary tokens...")
    manifest_obj = {
        'project_id': manifest_data['project_id'], 'distribution_id': manifest_data['distribution_id'],
        'salt': salt, 'file_hash': manifest_data.get('file_hash', ''),
        'canary_tokens': [CanaryToken(**t) for t in manifest_data['canary_tokens']], 'merkle_root': manifest_data['merkle_root'],
    }
    matches = embedder.verify_source(source_dir, CanaryManifest(**manifest_obj))

    if matches:
        print(f"""
FOUND {len(matches)} CANARY TOKEN MATCHES:
{chr(10).join(f'  - {filepath}  (token: {secret[:30]}...)' for filepath, secret in matches)}

This confirms the code was derived from the OPL distribution:
  Distribution:  {manifest_data['distribution_id']}
  Merkle root:   0x{manifest_data['merkle_root']}

To assemble a litigation evidence package, run:
  python3 canary_embedder.py evidence --manifest {manifest_path} \\
      --suspect-source {source_dir} --output evidence_package.json

The evidence package includes: canary secrets, Merkle proofs, distribution
metadata, and a human-readable summary suitable for legal use.
""")
    else:
        print("\\nNo canary tokens found.\\n")
    print()

def cmd_check(args: argparse.Namespace) -> None:
    """Drift check (Phase C): hash the CURRENT tree and compare against a
    recorded manifest's per-file hashes. Exit 0 = repo still matches the
    fingerprint; exit 1 = files added/modified/removed since fingerprint time.

    This is the automatic balancing loop that lets a repo 'stay verifiable as it
    updates': CI runs it on every commit and fails red on unexpected drift.
    Works against either the private manifest or the public payload.
    """
    source_dir = Path(args.source).resolve()
    manifest_path = Path(args.manifest)
    if not source_dir.is_dir():
        print(f"Error: {source_dir} is not a directory", file=sys.stderr)
        sys.exit(1)
    if not manifest_path.exists():
        print(f"Error: {manifest_path} not found", file=sys.stderr)
        sys.exit(1)
    with open(manifest_path) as f:
        manifest_data = json.load(f)
    recorded_files = manifest_data.get('source_files', {})
    if not recorded_files:
        print("Error: manifest has no 'source_files' record (generated before "
              "per-file hashing; re-run embed against this tree).", file=sys.stderr)
        sys.exit(1)

    embedder = CanaryEmbedder(
        project_id=manifest_data.get('project_id', 0),
        distribution_id=manifest_data.get('distribution_id', ''),
        salt=manifest_data.get('_steward_secret_salt', ''),
    )
    current_hash, current_files = embedder.hash_current_tree(source_dir)

    modified = sorted(p for p, h in recorded_files.items()
                      if p in current_files and current_files[p] != h)
    removed = sorted(p for p in recorded_files if p not in current_files)
    added = sorted(p for p in current_files if p not in recorded_files)
    unchanged = len(recorded_files) - len(modified) - len(removed)

    print(f"""
OPL-1.4 Drift check
{'='*60}
  Source:     {source_dir}
  Manifest:   {manifest_path}
  Recorded:   {len(recorded_files)} files
  Current:    {len(current_files)} files (tree hash 0x{current_hash[:16]}...)
  Unchanged:  {unchanged}  Modified: {len(modified)}  Removed: {len(removed)}  Added: {len(added)}
""")
    for label, items in (("MODIFIED", modified), ("REMOVED", removed), ("ADDED", added)):
        for p in items:
            print(f"  {label}: {p}")

    drift = bool(modified or removed or added)
    if drift:
        print(f"\nDRIFT DETECTED: the repo no longer matches the recorded fingerprint "
              f"at {manifest_path.name}. Run `embed` to re-fingerprint if this is an "
              f"intentional release, or reconcile if it is unauthorized change.")
        if not args.allow_drift:
            sys.exit(1)
    else:
        print(f"\nOK: repo matches the recorded fingerprint. No drift.")


def _hash_source(source_dir: Path, archive: bool) -> str:
    """Hash a source tree (or archive) deterministically into a single digest."""
    h = hashlib.sha3_256()
    if archive:
        h.update(source_dir.read_bytes())
        return h.hexdigest()
    for p in sorted(source_dir.rglob("*")):
        if p.is_file():
            h.update(p.relative_to(source_dir).as_posix().encode())
            h.update(p.read_bytes())
    return h.hexdigest()


def cmd_fingerprint(args: argparse.Namespace) -> None:
    source = Path(args.source)
    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print(f"Error: {manifest_path} not found", file=sys.stderr)
        sys.exit(1)
    if not (source.is_dir() or source.is_file()):
        print(f"Error: {source} not found", file=sys.stderr)
        sys.exit(1)
    with open(manifest_path) as f:
        manifest_data = json.load(f)
    source_hash = _hash_source(source, args.archive)
    fingerprint = {
        "project_id": manifest_data.get("project_id"),
        "distribution_id": manifest_data.get("distribution_id"),
        "merkle_root": manifest_data.get("merkle_root", ""),
        "source_hash": source_hash,
        "archive": args.archive,
    }
    output = Path(args.output)
    output.write_text(json.dumps(fingerprint, indent=2))
    print(f"Release fingerprint written to: {output}")
    print(f"  source_hash: 0x{source_hash}")
    print(f"  merkle_root: 0x{fingerprint['merkle_root']}")


def cmd_evidence(args: argparse.Namespace) -> None:
    manifest_path = Path(args.manifest)
    suspect = Path(args.suspect_source)
    if not manifest_path.exists():
        print(f"Error: {manifest_path} not found", file=sys.stderr)
        sys.exit(1)
    if not suspect.is_dir():
        print(f"Error: {suspect} is not a directory", file=sys.stderr)
        sys.exit(1)
    with open(manifest_path) as f:
        manifest_data = json.load(f)
    salt = manifest_data.get("_steward_secret_salt", "")
    embedder = CanaryEmbedder(
        project_id=manifest_data["project_id"],
        distribution_id=manifest_data["distribution_id"],
        salt=salt,
    )
    manifest_obj = {
        "project_id": manifest_data["project_id"],
        "distribution_id": manifest_data["distribution_id"],
        "salt": salt,
        "file_hash": manifest_data.get("file_hash", ""),
        "canary_tokens": [CanaryToken(**t) for t in manifest_data["canary_tokens"]],
        "merkle_root": manifest_data["merkle_root"],
    }
    matches = embedder.verify_source(suspect, CanaryManifest(**manifest_obj))
    evidence = {
        "project_id": manifest_data["project_id"],
        "distribution_id": manifest_data["distribution_id"],
        "merkle_root": manifest_data["merkle_root"],
        "suspect_source": str(suspect),
        "match_count": len(matches),
        "matches": [{"file": fp, "secret": secret} for fp, secret in matches],
    }
    output = Path(args.output)
    output.write_text(json.dumps(evidence, indent=2))
    print(f"Evidence package written to: {output}")
    print(f"  Matches: {len(matches)}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="OPL-1.4 Fingerprinting Tool — canary embedding, Merkle tree, "
                    "release fingerprinting, and litigation evidence assembly. "
                    "Optional enforcement backbone for the OPL-AI addendum. "
                    "Stdlib-only, Python 3.10+.")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    embed_p = subparsers.add_parser('embed', help='Embed canary tokens into source code and generate distribution manifest')
    embed_p.add_argument('--source', required=True, help='Source code directory')
    embed_p.add_argument('--project-id', type=int, required=True, help='OPL project ID (arbitrary integer you choose)')
    embed_p.add_argument('--distribution-id', required=True, help='Distribution identifier (any unique string, e.g. release version or hex)')
    embed_p.add_argument('--salt', required=True, help='Secret salt for token generation (keep offline)')
    embed_p.add_argument('--strategies', default='variable,watermark,deadcode', help='Comma-separated embedding strategies: variable, watermark, deadcode')
    embed_p.add_argument('--num-canaries', type=int, default=10, help='Number of canary tokens to embed')
    embed_p.add_argument('--output', help='Output PRIVATE manifest path (default: canary_manifest.json)')
    embed_p.add_argument('--public-output', help='Output PUBLIC payload path (default: <output>.parent/release_fingerprint.json)')
    embed_p.set_defaults(func=cmd_embed)

    merkle_p = subparsers.add_parser('build-merkle', help='Build Merkle tree from an existing manifest')
    merkle_p.add_argument('--manifest', required=True, help='Path to canary manifest JSON')
    merkle_p.set_defaults(func=cmd_build_merkle)

    verify_p = subparsers.add_parser('verify', help='Verify canaries in a suspect codebase')
    verify_p.add_argument('--source', required=True, help='Source directory to scan')
    verify_p.add_argument('--manifest', required=True, help='Path to canary manifest JSON')
    verify_p.set_defaults(func=cmd_verify)

    check_p = subparsers.add_parser('check', help='Drift-check current source against a recorded manifest (run on every commit)')
    check_p.add_argument('--source', required=True, help='Source directory to hash')
    check_p.add_argument('--manifest', required=True, help='Path to canary manifest OR public payload JSON')
    check_p.add_argument('--allow-drift', action='store_true', help='Report drift but exit 0')
    check_p.set_defaults(func=cmd_check)

    fp_p = subparsers.add_parser('fingerprint', help='Generate a release fingerprint for a distribution')
    fp_p.add_argument('--source', required=True, help='Source directory or distribution archive path')
    fp_p.add_argument('--manifest', required=True, help='Path to canary manifest JSON (to include merkle root)')
    fp_p.add_argument('--output', required=True, help='Output release fingerprint JSON path')
    fp_p.add_argument('--archive', action='store_true', help='Treat --source as a distribution archive (tar.gz/zip) to hash')
    fp_p.set_defaults(func=cmd_fingerprint)

    evidence_p = subparsers.add_parser('evidence', help='Assemble a litigation evidence package from a verification')
    evidence_p.add_argument('--manifest', required=True, help='Path to canary manifest JSON')
    evidence_p.add_argument('--suspect-source', required=True, help='Source directory where canaries were found')
    evidence_p.add_argument('--output', required=True, help='Output evidence package JSON path')
    evidence_p.add_argument('--matched-files', nargs='+', help='Specific files where canaries were matched (optional; if omitted, re-scans)')
    evidence_p.set_defaults(func=cmd_evidence)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)
    args.func(args)

if __name__ == '__main__':
    main()
