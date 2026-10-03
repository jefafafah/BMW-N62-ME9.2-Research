#!/usr/bin/env python3
"""Catalogue calibration curves/maps (geometry only) from lookup-helper call sites.

Bosch ME9.2 code calls a small set of interpolation helpers with a pointer to an
inline record:

    curve: [n][x0..xn-1][y0..yn-1]
    map  : [nx][ny][x0..xnx-1][y0..yny-1][values, x-major: v[ix*ny + iy]]

Counts/axes/values share the helper's element width (u8, u16 or s16). Some
helpers take the record pre-split (r3=nx, r4=x-axis, r5=ny / r6=y-axis, r7=data).

This script classifies helpers automatically from their load instructions and
from axis monotonicity across all call sites, then emits one CSV row per
record. It writes geometry and axis ranges only, never table values, so the
output does not reproduce the calibration.

Usage:
    python tools/me9_tables.py [--int ... --ext ...] [--min-sites 3] > tables.csv
"""
from __future__ import annotations

import argparse
import collections
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from me9_image import CAL_ALIAS_TO_FILE, Image, region  # noqa: E402
from me9_xref import build, function_end  # noqa: E402


def _rd(img, a, w, signed):
    v = img.u8(a) if w == 1 else img.u16(a)
    if signed and v >= (0x80 if w == 1 else 0x8000):
        v -= 0x100 if w == 1 else 0x10000
    return v


def _mono(xs):
    return all(xs[i] < xs[i + 1] for i in range(len(xs) - 1))


def helper_width(img: Image, helper: int) -> tuple[int, bool]:
    """Element width/signedness from the helper's own load instructions."""
    end = function_end(img, helper)
    byte = half = sign = 0
    for a in range(helper, end, 4):
        op = img.u32(a) >> 26
        byte += op in (34, 35)
        half += op in (40, 41)
        sign += op in (42, 43)
    if sign and not byte:
        return 2, True
    if half and not byte:
        return 2, False
    return 1, False


def decode(img, a, kind, w, signed):
    try:
        if kind == "curve":
            n = _rd(img, a, w, False)
            if not 2 <= n <= 64:
                return None
            xs = [_rd(img, a + w * (1 + i), w, signed) for i in range(n)]
            return dict(addr=a, kind=kind, nx=n, ny=1, x=xs, y=[], data=a + w * (1 + n), w=w, signed=signed) if _mono(xs) else None
        nx, ny = _rd(img, a, w, False), _rd(img, a + w, w, False)
        if not (2 <= nx <= 64 and 2 <= ny <= 64):
            return None
        xs = [_rd(img, a + w * (2 + i), w, signed) for i in range(nx)]
        ys = [_rd(img, a + w * (2 + nx + i), w, signed) for i in range(ny)]
        if not (_mono(xs) and _mono(ys)):
            return None
        return dict(addr=a, kind=kind, nx=nx, ny=ny, x=xs, y=ys, data=a + w * (2 + nx + ny), w=w, signed=signed)
    except TypeError:  # read outside image
        return None


def decode_split(img, r):
    x = r[4]
    if 6 in r and 7 in r and region(r[7]) == "CAL":
        for cw in (1, 2):
            nx, ny = _rd(img, x - 2 * cw, cw, False), _rd(img, x - cw, cw, False)
            if not (1 <= nx <= 64 and 1 <= ny <= 64) or (r[6] - x) % nx:
                continue
            aw = (r[6] - x) // nx
            if aw in (1, 2) and r[7] - r[6] == ny * aw:
                return dict(addr=x - 2 * cw, kind="map", nx=nx, ny=ny, w=aw, signed=False, data=r[7],
                            x=[_rd(img, x + i * aw, aw, False) for i in range(nx)],
                            y=[_rd(img, r[6] + i * aw, aw, False) for i in range(ny)])
    if 5 in r and region(r[5]) == "CAL":
        for cw in (1, 2):
            n = _rd(img, x - cw, cw, False)
            if not 1 <= n <= 64 or (r[5] - x) % n:
                continue
            aw = (r[5] - x) // n
            if aw in (1, 2):
                return dict(addr=x - cw, kind="curve", nx=n, ny=1, w=aw, signed=False, data=r[5],
                            x=[_rd(img, x + i * aw, aw, False) for i in range(n)], y=[])
    return None


def catalogue(img: Image, min_sites: int = 3):
    _, calls = build(img)
    sites = collections.defaultdict(list)
    for pc, t, r in calls:
        if 3 in r and region(r[3]) == "CAL":
            sites[t].append((pc, r[3]))
    tabs: dict[int, dict] = {}
    for helper, s in sites.items():
        if len(s) < min_sites:
            continue
        w, sg = helper_width(img, helper)
        for kind in ("map", "curve"):
            dec = [(pc, decode(img, a, kind, w, sg)) for pc, a in s]
            if all(d for _, d in dec):
                for pc, d in dec:
                    e = tabs.setdefault(d["addr"], dict(d, helpers=set(), sites=[]))
                    e["helpers"].add(helper)
                    e["sites"].append(pc)
                break
    for pc, t, r in calls:
        if 4 in r and region(r[4]) == "CAL" and not (3 in r and region(r[3]) == "CAL"):
            d = decode_split(img, r)
            if d:
                e = tabs.setdefault(d["addr"], dict(d, helpers=set(), sites=[]))
                e["helpers"].add(t)
                e["sites"].append(pc)
    return tabs


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--int")
    ap.add_argument("--ext")
    ap.add_argument("--min-sites", type=int, default=3)
    args = ap.parse_args()
    img = Image.from_args(args)
    tabs = catalogue(img, args.min_sites)
    wr = csv.writer(sys.stdout)
    wr.writerow(["record_cpu", "record_file_ext", "kind", "nx", "ny", "elem_width", "signed", "data_cpu",
                 "x_first", "x_last", "y_first", "y_last", "helpers", "call_sites"])
    for a, t in sorted(tabs.items()):
        wr.writerow([f"0x{a:06X}", f"0x{a - CAL_ALIAS_TO_FILE:05X}", t["kind"], t["nx"], t["ny"], t["w"], int(t["signed"]),
                     f"0x{t['data']:06X}", t["x"][0], t["x"][-1], t["y"][0] if t["y"] else "", t["y"][-1] if t["y"] else "",
                     " ".join(f"0x{h:06X}" for h in sorted(t["helpers"])),
                     " ".join(f"0x{s:06X}" for s in t["sites"][:4])])
    print(f"# {len(tabs)} records", file=sys.stderr)


if __name__ == "__main__":
    main()
