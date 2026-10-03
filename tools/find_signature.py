#!/usr/bin/env python3
"""Find an exact byte signature from a reference binary in a target binary.

Use this as one primitive for porting known calibration regions. A unique byte
match is evidence, not proof that the semantic symbol is identical.
"""
from __future__ import annotations
import sys
from pathlib import Path

if len(sys.argv) not in (5, 6):
    raise SystemExit("usage: find_signature.py <reference> <target> <ref_offset> <length> [target_start]")

ref = Path(sys.argv[1]).read_bytes()
tgt = Path(sys.argv[2]).read_bytes()
ref_off = int(sys.argv[3], 0)
length = int(sys.argv[4], 0)
target_start = int(sys.argv[5], 0) if len(sys.argv) == 6 else 0
sig = ref[ref_off:ref_off+length]
if len(sig) != length:
    raise SystemExit("reference slice too short")

hits=[]
pos=tgt.find(sig, target_start)
while pos >= 0:
    hits.append(pos)
    pos=tgt.find(sig, pos+1)

print(f"signature={sig.hex()}")
print(f"hits={len(hits)}")
for h in hits:
    print(f"0x{h:X}  delta=0x{h-ref_off:X}")
