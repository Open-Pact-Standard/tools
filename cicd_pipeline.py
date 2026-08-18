# SPDX-License-Identifier: OPL-1.3.1
"""
CI/CD Pipeline for OPL-1.1 Canary Token Embedding
Automates: scan → embed → generate manifest → prepare on-chain registration data
Designed for integration with GitHub Actions, GitLab CI, or any CI system.
"""

import json
import subprocess
import sys
import os
from pathlib import Path
from dataclasses import asdict
from datetime import datetime
from typing import Any, Dict, List, Optional

class CanaryCIPipeline:
    """Automated CI/CD pipeline for OPL-1.1 canary embedding and registration."""
    
    def __init__(self, config_path: Optional[str] = None, config: Optional[Dict[str, Any]] = None) -> None:
        if config is not None:
            self.config = config
        else:
            self.config = self._load_config(config_path)
        self.source_dir = Path(self.config.get('source_dir', '.'))
        self.project_id = self.config.get('project_id')
        self.registry_address = self.config.get('registry_address')
        self.steward_wallet = self.config.get('steward_wallet')
        self.distribution_salt = self.config.get('distribution_salt', os.urandom(16).hex())
        self.num_canaries = self.config.get('num_canaries', 12)
        self.strategies = self.config.get('strategies', ['variable', 'watermark', 'deadcode'])
        
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load pipeline configuration."""
        if config_path and Path(config_path).exists():
            with open(config_path) as f:
                return json.load(f)
        return {}
    
    def run_pipeline(self, dry_run: bool = False) -> Optional[Dict[str, Any]]:
        """Execute the full pipeline: scan → embed → manifest → register."""
        print("\n" + "="*70)
        print("OPL-1.1 Canary CI/CD Pipeline")
        print("="*70)
        
        # Step 1: Pre-scan
        print("\n[1/5] Pre-scanning source tree...")
        stats = self._scan_source()
        print(f"  Files found: {stats['total_files']}")
        print(f"  Languages: {', '.join(stats['languages'])}")
        print(f"  Total size: {stats['total_size']/1024:.1f} KB")
        
        # Step 2: Embed
        if not dry_run:
            if not self.project_id:
                print("Error: project_id is required to embed canaries. Pass --project-id "
                      "(or set it in config); refusing to fingerprint an unattested tree.",
                      file=sys.stderr)
                return {"error": "project_id required"}
            print("\n[2/5] Embedding canary tokens...")
            from canary_embedder import CanaryEmbedder
            embedder = CanaryEmbedder(
                project_id=self.project_id,
                distribution_id=self.distribution_salt[:16],
                salt=self.distribution_salt,
                strategies=self.strategies,
                num_canaries=self.num_canaries,
            )
            embedder.generate_tokens()
            embedder.embed(self.source_dir)
            
            print("\n[3/5] Building Merkle tree...")
            root = embedder.build_merkle_tree()
            print(f"  Merkle root: 0x{root}")
            
            print("\n[4/5] Generating manifest...")
            manifest = embedder.generate_manifest(self.source_dir)
            
            # Save manifest
            manifest_path = Path(self.config.get('manifest_output', 'canary_manifest.json'))
            manifest_dict = {
                'project_id': manifest.project_id,
                'distribution_id': manifest.distribution_id,
                'file_hash': manifest.file_hash,
                'merkle_root': manifest.merkle_root,
                'canary_tokens': [asdict(t) for t in manifest.canary_tokens],
                '_steward_secret_salt': self.distribution_salt,
                'created_at': datetime.utcnow().isoformat(),
                'ci_pipeline_version': '1.0.0',
            }
            manifest_path.write_text(json.dumps(manifest_dict, indent=2))
            print(f"  Manifest saved: {manifest_path}")
            
            # Step 5: Prepare registration
            print("\n[5/5] Preparing on-chain registration...")
            registration_data = self._prepare_registration(root, manifest)
            print(f"  Contract: {self.registry_address}")
            print(f"  From: {self.steward_wallet}")
            print(f"  Project ID: {self.project_id}")
            print(f"  Dist ID: 0x{manifest.distribution_id}")
            print(f"  Merkle Root: 0x{root}")
            print(f"  Gas estimate: ~50000")
            
            return registration_data
        else:
            print("\n  [DRY RUN] Skipping embed and registration")
            return None
    
    def _scan_source(self) -> Dict[str, Any]:
        """Scan source tree and report statistics."""
        stats = {'total_files': 0, 'languages': set(), 'total_size': 0}
        extensions = {}
        
        for ext in ['.py', '.js', '.ts', '.rs', '.go', '.sol', '.c', '.cpp', '.java']:
            files = list(self.source_dir.rglob(f'*{ext}'))
            count = len([f for f in files if 'test' not in str(f) and '__pycache__' not in str(f)])
            if count > 0:
                extensions[ext] = count
                stats['total_files'] += count
                stats['languages'].add(ext[1:])  # Remove the dot
                stats['total_size'] += sum(f.stat().st_size for f in files[:100])
        
        return stats
    
    def _prepare_registration(self, merkle_root: str, manifest: Any) -> Dict[str, Any]:
        """Prepare on-chain registration data."""
        return {
            'method': 'registerCanaryDistribution',
            'contract': self.registry_address,
            'from': self.steward_wallet,
            'params': {
                'projectId': self.project_id,
                'distributionId': f'0x{manifest.distribution_id}',
                'merkleRoot': f'0x{merkle_root}',
                'issuedTo': self.config.get('target_licensee', '0x0000000000000000000000000000000000000000'),
                'gasEstimate': 50000,
            },
            'manifest_path': str(Path(self.config.get('manifest_output', 'canary_manifest.json')).resolve()),
        }

def main() -> None:
    import argparse
    
    parser = argparse.ArgumentParser(description='OPL-1.1 Canary CI/CD Pipeline')
    parser.add_argument('--config', help='Pipeline config file (JSON)')
    parser.add_argument('--source', help='Source directory to scan')
    parser.add_argument('--project-id', type=int, help='OPL project ID')
    parser.add_argument('--registry', help='Registry contract address')
    parser.add_argument('--wallet', help='Steward wallet address')
    parser.add_argument('--dry-run', action='store_true', help='Simulate without making changes')
    parser.add_argument('--output', help='Output manifest file')
    parser.add_argument('--salt', help='Distribution salt override')
    
    args = parser.parse_args()
    
    config = {}
    if args.config:
        with open(args.config) as f:
            config.update(json.load(f))
    
    # Override with CLI args
    if args.source: config['source_dir'] = args.source
    if args.project_id: config['project_id'] = args.project_id
    if args.registry: config['registry_address'] = args.registry
    if args.wallet: config['steward_wallet'] = args.wallet
    if args.output: config['manifest_output'] = args.output
    if args.salt: config['distribution_salt'] = args.salt
    
    pipeline = CanaryCIPipeline(config=config)
    result = pipeline.run_pipeline(dry_run=args.dry_run)
    
    if result:
        print(f"\n" + "="*70)
        print("PIPELINE COMPLETE")
        print("="*70)
        print(f"Registration data saved to: {result.get('manifest_path', 'N/A')}")
        print(f"Ready for: cast send or forge script deployment")

if __name__ == '__main__':
    main()
