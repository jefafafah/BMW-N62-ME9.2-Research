#!/usr/bin/env python3
"""Print SHA-256 hashes for research input files without copying them into the repo."""
from __future__ import annotations
import hashlib
import sys
from pathlib import Path

for arg in sys.argv[1:]:
    p = Path(arg)
    h = hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    print(f"{h.hexdigest()}  {p}")
