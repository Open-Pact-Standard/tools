"""
JavaScript/TypeScript Canary Embedding Strategies
"""
import re
import random
import hashlib
from pathlib import Path
from typing import List, Optional

class JSEmbedder:
    """JavaScript-optimized canary embedding using AST-friendly patterns."""
    
    TEMPLATES = {
        'variable': 'const _cfg_{SHORT} = "{LONG}"; // Config',
        'const': 'const {UPPER} = "{VALUE}";',
        'comment': '/* {TOKEN} */',
    }
    
    def __init__(self):
        self.files_modified = []
    
    def embed(self, source_dir, token, rng):
        files = list(source_dir.rglob(f'*.ts') + list(source_dir.rglob(f'*.js')))
        files = [f for f in files if not self._is_excluded(f) and f.stat().st_size < 500000]
        
        if not files:
            return None
            
        target = rng.choice(files)
        relative = str(target.relative_to(source_dir))
        
        content = target.read_text(encoding='utf-8', errors='replace')
        lines = content.split('\n')
        
        short = hashlib.sha3_256(token.encode()).hexdigest()[:8]
        long = hashlib.sha3_256(f"long_{token}".encode()).hexdigest()[:16]
        upper = token.upper().replace('-', '_')
        
        strategy = rng.choice(['variable', 'const', 'comment'])
        
        if strategy == 'variable':
            line = self.TEMPLATES['variable'].format(SHORT=short[:6], LONG=long)
        elif strategy == 'const':
            line = self.TEMPLATES['const'].format(UPPER=upper[:20], VALUE=long)
        else:
            line = self.TEMPLATES['comment'].format(TOKEN=token)
        
        # Find good insertion point
        insert_at = 0
        for i, line in enumerate(lines):
            if line.strip().startswith('import') or line.strip().startswith('require'):
                insert_at = i + 1
        
        lines.insert(insert_at, line)
        target.write_text('\n'.join(lines), encoding='utf-8')
        self.files_modified.append(relative)
        return relative
    
    def _is_excluded(self, path):
        parts = set(p.lower() for p in path.parts)
        excluded = {'test', 'tests', '__test__', '__tests__', 'node_modules', '.git', 'dist', 'build', 'target'}
        return bool(parts & excluded)
