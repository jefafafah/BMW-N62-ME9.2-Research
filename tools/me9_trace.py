#!/usr/bin/env python3
"""Tracing helpers for the 770B image (round 4).

    python tools/me9_trace.py outputs              # output-stage calls: channel number + value source
    python tools/me9_trace.py lookups 0x4E21C      # every curve/map lookup in a function, with the
                                                   # instructions that load its inputs and store its result

`outputs` scans for calls to the digital-output drivers INT 0xAC00 / 0xA418 (output-stage
function INT 0x38A54) and lists the digital-input reader INT 0xAB88 (INT 0x388B0) for completeness.
PWM outputs (VANOS solenoids, fan) are driven elsewhere (TPU/MIOS) and are not covered yet.
The channel is the constant loaded into r3; the value source is the last RAM load
into r5 before the call. `lookups` uses the table catalogue of me9_tables.py.
"""
from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from me9_image import Image, disassemble  # noqa: E402
from me9_tables import catalogue  # noqa: E402
from me9_xref import build, function_end, function_start  # noqa: E402

OUTPUT_DRIVERS = {0xAC00: "dig-out", 0xA418: "dig-out-b", 0xAB88: "dig-in"}  # 0xAB88 reads input bits (port image 0x3FA374)


def outputs(img: Image):
    refs, calls = build(img)
    by_pc = {}
    for pc, ea, k, sz in refs:
        if k == "R":
            by_pc.setdefault(pc, []).append(ea)
    rows = []
    for pc, t, _ in calls:
        if t not in OUTPUT_DRIVERS:
            continue
        ch = src = None
        for k in range(1, 10):
            a = pc - 4 * k
            w = img.u32(a)
            op, rt, ra = w >> 26, (w >> 21) & 31, (w >> 16) & 31
            if ch is None and op == 14 and rt == 3 and ra == 0:
                ch = struct.unpack(">h", img.read(a + 2, 2))[0]
            if src is None and op in (34, 40) and rt == 5 and a in by_pc:
                src = by_pc[a][0]
        rows.append((OUTPUT_DRIVERS[t], ch, src, pc, function_start(img, pc)))
    return rows


def lookups(img: Image, fn: int):
    tabs = catalogue(img)
    site = {s: t for t in tabs.values() for s in t["sites"]}
    end = function_end(img, fn)
    refs, _ = build(img)
    ann = {}
    for pc, ea, k, sz in refs:
        if fn <= pc < end:
            ann.setdefault(pc, []).append(f"{k}{sz} {ea:06X}")
    lines = disassemble(img, fn, (end - fn) // 4)
    for i, line in enumerate(lines):
        pc = int(line[:8], 16)
        if pc in site:
            t = site[pc]
            print(f"--- {pc:06X}: {t['kind']} {t['nx']}x{t['ny']} @CAL 0x{t['addr']:06X} x={t['x'][0]}..{t['x'][-1]}"
                  + (f" y={t['y'][0]}..{t['y'][-1]}" if t["y"] else ""))
            for l in lines[max(0, i - 6):i + 4]:
                p = int(l[:8], 16)
                if p in ann:
                    print(f"    {l[:8]} {' '.join(ann[p])}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--int")
    ap.add_argument("--ext")
    ap.add_argument("cmd", choices=["outputs", "lookups"])
    ap.add_argument("address", nargs="?")
    args = ap.parse_args()
    img = Image.from_args(args)
    if args.cmd == "outputs":
        print("driver     ch   value-src  call-site  function")
        for drv, ch, src, pc, f in sorted(outputs(img), key=lambda r: (r[0], r[1] if r[1] is not None else 999, r[3])):
            print(f"{drv:9s} {ch if ch is not None else '?':>3}   {f'0x{src:06X}' if src else '-':9s}  0x{pc:06X}   0x{f or 0:06X}")
    else:
        lookups(img, int(args.address, 0))


if __name__ == "__main__":
    main()
