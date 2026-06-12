# SPDX-License-Identifier: OPL-1.3.1
"""
OPL-1.1 Canary Token Embedding Tool (Clean Version)
"""

import argparse
import hashlib
import json
import math
import os
import re
import random
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

CANARY_PREFIX = "canary"
SUPPORTED_EXTENSIONS = {
    '.py', '.js', '.ts', '.jsx', '.tsx', '.rs', '.go',
    '.sol', '.c', '.cpp', '.h', '.hpp', '.java', '.kt',
    '.rb', '.php', '.m', '.swift',
}

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

    def _is_excluded(self, path: Path) -> bool:
        parts = set(p.lower() for p in path.parts)
        excluded = {'test', 'tests', '__pycache__', 'node_modules', '.git', 'venv', 'build', 'dist', 'target'}
        return bool(parts & excluded)

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

    def _is_excluded(self, path: Path) -> bool:
        parts = set(p.lower() for p in path.parts)
        excluded = {'test', 'tests', '__pycache__', 'node_modules', '.git', 'venv', 'build', 'dist', 'target'}
        return bool(parts & excluded)

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

    def _is_excluded(self, path: Path) -> bool:
        parts = set(p.lower() for p in path.parts)
        excluded = {'test', 'tests', '__pycache__', 'node_modules', '.git', 'venv', 'build', 'dist', 'target'}
        return bool(parts & excluded)

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
        tree_hash = self._hash_tree(source_dir)
        return CanaryManifest(
            project_id=self.project_id, distribution_id=self.distribution_id,
            salt=self.salt, file_hash=tree_hash, 
            canary_tokens=list(self.tokens), merkle_root=self.tree_root,
        )

    def _hash_tree(self, source_dir: Path) -> str:
        h = hashlib.sha3_256()
        for f in sorted(source_dir.rglob('*')):
            if f.is_file() and f.suffix in SUPPORTED_EXTENSIONS:
                h.update(f.name.encode())
                h.update(f.read_bytes())
        return h.hexdigest()

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

def cmd_embed(args: argparse.Namespace) -> None:
    source_dir = Path(args.source).resolve()
    if not source_dir.is_dir():
        print(f"Error: {source_dir} is not a directory", file=sys.stderr)
        sys.exit(1)
    distribution_id = args.distribution_id
    if distribution_id.startswith('0x'):
        distribution_id = distribution_id[2:]

    embedder = CanaryEmbedder(
        project_id=args.project_id, distribution_id=distribution_id,
        salt=args.salt, strategies=args.strategies.split(','), num_canaries=args.num_canaries,
    )

    print(f"\n{'='*60}")
    print(f"OPL-1.1 Canary Token Embedder")
    print(f"{'='*60}")
    print(f"  Source:      {source_dir}")
    print(f"  Project ID:  {args.project_id}")
    print(f"  Dist ID:     {distribution_id}")
    print(f"  Salt:        {args.salt[:8]}{'*'*(len(args.salt)-8) if len(args.salt) > 8 else ''}")
    print(f"  Strategies:  {args.strategies}")
    print(f"  Num canaries: {args.num_canaries}\n")

    print("Step 1: Generating canary tokens...")
    embedder.generate_tokens()
    print(f"  Generated {len(embedder.tokens)} tokens\n")

    print("Step 2: Embedding tokens into source...")
    embedder.embed(source_dir)
    print()

    print("Step 3: Building Merkle tree...")
    root = embedder.build_merkle_tree()
    print(f"  Merkle root: 0x{root}\n")

    print("Step 4: Generating manifest...")
    manifest = embedder.generate_manifest(source_dir)

    output = Path(args.output) if args.output else Path('canary_manifest.json')
    manifest_dict = {
        'project_id': manifest.project_id, 'distribution_id': manifest.distribution_id,
        'file_hash': manifest.file_hash, 'merkle_root': manifest.merkle_root,
        'canary_tokens': [asdict(t) for t in manifest.canary_tokens],
        '_steward_secret_salt': args.salt,
    }
    output.write_text(json.dumps(manifest_dict, indent=2))
    print(f"  Manifest saved to: {output}")

    print(f"\n{'='*60}")
    print(f"Registration Data")
    print(f"{'='*60}")
    print(f"  Contract call:")
    print(f"    royaltyRegistry.registerCanaryDistribution(")
    print(f"      projectId:    {args.project_id},")
    print(f"      distributionId: 0x{distribution_id},")
    print(f"      merkleRoot:   0x{root},")
    print(f"      issuedTo:     <licensee address>")
    print(f"    )\n")

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

    print(f"\n{'='*60}")
    print(f"OPL-1.1 Canary Token Verification")
    print(f"{'='*60}")
    print(f"  Scanning:    {source_dir}")
    print(f"  Manifest:    {manifest_path}")
    print(f"  Canaries:    {len(embedder.tokens)}")
    print(f"  Merkle root: 0x{manifest_data['merkle_root']}\n")

    print("Scanning for canary tokens...")
    manifest_obj = {
        'project_id': manifest_data['project_id'], 'distribution_id': manifest_data['distribution_id'],
        'salt': salt, 'file_hash': manifest_data.get('file_hash', ''),
        'canary_tokens': [CanaryToken(**t) for t in manifest_data['canary_tokens']], 'merkle_root': manifest_data['merkle_root'],
    }
    matches = embedder.verify_source(source_dir, CanaryManifest(**manifest_obj))

    if matches:
        print(f"\nFOUND {len(matches)} CANARY TOKEN MATCHES:")
        for filepath, secret in matches:
            print(f"  - {filepath}  (token: {secret[:30]}...)")
        print(f"\nThis confirms the code was derived from the OPL distribution:")
        print(f"  Distribution: 0x{manifest_data['distribution_id']}")
        print(f"  Manifest merkle root: 0x{manifest_data['merkle_root']}")
    else:
        print("\nNo canary tokens found.")
    print()

def main() -> None:
    parser = argparse.ArgumentParser(description='OPL-1.1 Canary Token Embedding Tool')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    embed_p = subparsers.add_parser('embed', help='Embed canary tokens into source code')
    embed_p.add_argument('--source', required=True, help='Source code directory')
    embed_p.add_argument('--project-id', type=int, required=True, help='OPL project ID')
    embed_p.add_argument('--distribution-id', required=True, help='Distribution identifier (hex)')
    embed_p.add_argument('--salt', required=True, help='Secret salt for token generation')
    embed_p.add_argument('--strategies', default='variable,watermark', help='Comma-separated strategies')
    embed_p.add_argument('--num-canaries', type=int, default=10, help='Number of canary tokens')
    embed_p.add_argument('--output', help='Output manifest path')
    embed_p.set_defaults(func=cmd_embed)

    merkle_p = subparsers.add_parser('build-merkle', help='Build Merkle tree from manifest')
    merkle_p.add_argument('--manifest', required=True, help='Path to canary manifest JSON')
    merkle_p.set_defaults(func=cmd_build_merkle)

    verify_p = subparsers.add_parser('verify', help='Verify canaries in suspect codebase')
    verify_p.add_argument('--source', required=True, help='Source directory to scan')
    verify_p.add_argument('--manifest', required=True, help='Path to canary manifest JSON')
    verify_p.set_defaults(func=cmd_verify)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)
    args.func(args)

if __name__ == '__main__':
    main()
