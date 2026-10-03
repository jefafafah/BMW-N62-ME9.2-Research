#!/usr/bin/env python3
"""Decode an 8x8 REDABM matrix from a user-supplied binary.

Example:
    python tools/redabm_decode.py path/to/28f200f3t.bin 0xC5510
"""
from __future__ import annotations
import sys
from pathlib import Path

if len(sys.argv) != 3:
    raise SystemExit("usage: redabm_decode.py <binary> <offset>")

path = Path(sys.argv[1])
offset = int(sys.argv[2], 0)
data = path.read_bytes()[offset:offset+64]
if len(data) != 64:
    raise SystemExit("not enough data")

print("phase  " + "  ".join(f"s{i}" for i in range(1,9)))
for row in range(8):
    vals = data[row*8:(row+1)*8]
    print(f"{row+1:>5}  " + "  ".join(f"{v:02X}" for v in vals))

print("\nbit counts:")
for col in range(8):
    counts = [data[row*8+col].bit_count() for row in range(8)]
    print(f"step {col+1}: {counts}")
