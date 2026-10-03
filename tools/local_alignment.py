#!/usr/bin/env python3
"""Show exact matching blocks between two local binary windows.

Useful when a calibration region moved but contains small insert/delete changes.
"""
from __future__ import annotations
import sys
from difflib import SequenceMatcher
from pathlib import Path

if len(sys.argv) != 7:
    raise SystemExit("usage: local_alignment.py <ref> <target> <ref_start> <ref_end> <target_start> <target_end>")

ref = Path(sys.argv[1]).read_bytes()
tgt = Path(sys.argv[2]).read_bytes()
a0,a1 = int(sys.argv[3],0), int(sys.argv[4],0)
b0,b1 = int(sys.argv[5],0), int(sys.argv[6],0)
sm = SequenceMatcher(None, ref[a0:a1], tgt[b0:b1], autojunk=False)
for m in sm.get_matching_blocks():
    if m.size >= 4:
        ra=a0+m.a; tb=b0+m.b
        print(f"ref=0x{ra:X} target=0x{tb:X} delta=0x{tb-ra:X} size={m.size}")
