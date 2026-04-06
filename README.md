# OPL-1.1 Canary Token Embedding Tool

## Purpose

Scans an OPL-1.1 licensed codebase, generates unique cryptographic canary
tokens, embeds them using multiple stealth techniques, builds a Merkle tree
for on-chain registration, and produces a manifest for the Steward.

## Architecture

```
Input: Source tree (Python, JS, TS, Rust, Solidity, etc.)
  │
  ▼
┌──────────────────────────────────────┐
│  1. TOKEN GENERATOR                  │
│  - Cryptographically unique strings  │
│  - Per-distribution salted           │
│  - 8+ tokens per distribution        │
└──────────────────────────────────────┘
  │
  ▼
┌──────────────────────────────────────┐
│  2. EMBEDDING STRATEGIES             │
│  a. AST Variable Injection           │
│  b. Dead Code Blocks                 │
│  c. Data Watermarks                  │
│  d. Control-Flow Markers             │
│  e. String Obfuscation               │
└──────────────────────────────────────┘
  │
  ▼
┌──────────────────────────────────────┐
│  3. MERKLE TREE BUILDER              │
│  - keccak256 leaves                  │
│  - Full Merkle root computation      │
│  - Per-canary proof generation       │
└──────────────────────────────────────┘
  │
  ▼
┌──────────────────────────────────────┐
│  4. MANIFEST & REGISTRATION DATA     │
│  - JSON manifest with all canaries   │
│  - Merkle root for on-chain register │
│  - Per-token proofs for enforcement   │
└──────────────────────────────────────┘
```

## Token Generation

Each token is: `canary_<hex(keccak256(project_id || distribution_id || index || secret_salt))[:12]>`

This ensures:
- Unique per distribution (different salt = different tokens)
- Predictable for enforcement (Steward knows all tokens)
- Hard to guess for adversaries (requires knowing salt)

## Embedding Strategies

### a. AST Variable Injection
Insert unique global constants that look like normal code:
```python
# Before embedding
import os

# After embedding
import os
_CANARY_CFG_7A3B = "config_value"
```

### b. Dead Code Blocks
Insert unreachable code blocks:
```python
def _internal_validate(x):
    if x == 0xDEADBEEF7A3B:
        return _REACHABLE_MARKER_7A3B
    return x
```

### c. Data Watermarks
Embed in existing constants, comments, docstrings:
```python
"""Module for handling configuration.
Canary: 7A3B - do not remove
"""
```

### d. Control-Flow Markers
Unique sentinel values in existing conditionals:
```python
if error_code in {400, 401, 403, 404, 0x7A3B}:
    handle_error(error_code)
```

### e. String Obfuscation
Split strings with canary markers:
```python
# "error_message" becomes:
_ERR_PREFIX + "7A3B" + _ERR_SUFFIX  # where ERR_PREFIX="error_" ERR_SUFFIX="message"
```

## Usage

```bash
# Generate and embed canaries
python canary_embedder.py embed \
    --source ./my-project/src \
    --project-id 1 \
    --distribution-id 0xabc123... \
    --salt my-secret-salt \
    --strategies variable,deadcode,watermark \
    --output manifest.json

# Build Merkle tree from manifest
python canary_embedder.py build-merkle --manifest manifest.json

# Verify canaries in a codebase
python canary_embedder.py verify \
    --source ./suspect-project/src \
    --manifest manifest.json
```

## Integration with Smart Contracts

1. Run `embed` on the source tree before distribution
2. Extract the Merkle root from the manifest
3. Call `RoyaltyRegistry.registerCanaryDistribution(projectId, distributionId, merkleRoot, licensee)`
4. Store the manifest securely (off-chain, encrypted)
5. During enforcement: extract token from suspect code, verify against manifest, call `reportCanaryMatch()`

## Security Considerations

- **Never commit canary manifests to source control** - they are secret
- **Use unique salt per distribution** - prevents cross-distribution correlation
- **Embed canaries deep in control flow** - harder to strip without breaking logic
- **Use multiple embedding strategies** - redundancy if one technique is discovered
- **Regenerate canaries for each distribution** - different Merkle root per licensee
