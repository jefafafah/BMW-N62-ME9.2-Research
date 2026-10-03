#!/usr/bin/env python3
"""Decode the 770B CAN driver configuration (message objects + signal table).

Structures found in SW 1037389760 (addresses are external-flash CPU addresses):

* message-object index table   0xFDFAC8 : [ptr:u32][count:u8 ...] per entry
* message objects (24 bytes)   0xFDFAF4 : byte0 = handle, +0x0C = 11-bit CAN ID (u32),
                                          +0x11 = controller (0 = TouCAN A, 1 = TouCAN B),
                                          +0x13 bit0 = transmit, +0x14 = DLC
* signal table (5 bytes)       0xFDF967 : [sig][msg handle][byte order][start bit][length]
  read API  INT 0x63660(sig, &out)  /  write API INT 0x63C3C(sig, &in)
  RX copy buffers start at RAM 0x5BB618 (pointer 0x3FAE9C), 0x14 bytes per message handle.

Only structure is decoded here; the semantic meaning of the bits is established
from the consumer functions (see research/can-and-drive-modes.md).

Usage:
    python tools/me9_can.py [--int ... --ext ...] [--users]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from me9_image import Image  # noqa: E402

MSG_INDEX_TABLE = 0xFDFAC8
SIG_TABLE = 0xFDF967
SIG_READ = 0x63660
SIG_WRITE = 0x63C3C


def message_objects(img: Image):
    ptr, count = img.u32(MSG_INDEX_TABLE), img.u8(MSG_INDEX_TABLE + 4)
    out = {}
    for i in range(count):
        d = img.read(ptr + 0x18 * i, 0x18)
        out[d[0]] = dict(handle=d[0], can_id=int.from_bytes(d[12:16], "big"), controller=d[17],
                         tx=bool(d[19] & 1), dlc=d[20], addr=ptr + 0x18 * i)
    return out


def signals(img: Image, msgs: dict):
    """Signal entries whose message handle resolves to a known message object."""
    out = []
    for s in range(0x100):
        e = img.read(SIG_TABLE + 5 * s, 5)
        if e is None or e[0] != s or e[1] not in msgs or e[4] not in (8, 16, 32):
            if s > 0 and out and e is not None and e[0] != s:
                break
            continue
        out.append(dict(sig=s, msg=e[1], order=e[2], start=e[3], length=e[4]))
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--int")
    ap.add_argument("--ext")
    ap.add_argument("--users", action="store_true", help="list functions calling the signal read/write API per signal")
    args = ap.parse_args()
    img = Image.from_args(args)
    msgs = message_objects(img)
    print("handle  CAN-ID  ctrl  dir  dlc")
    for h, m in sorted(msgs.items()):
        print(f"  0x{h:02X}   0x{m['can_id']:03X}   {'A' if m['controller'] == 0 else 'B'}    {'TX' if m['tx'] else 'RX'}   {m['dlc']}")
    users = {}
    if args.users:
        from me9_xref import build, function_start

        _, calls = build(img)
        for pc, t, r in calls:
            if t in (SIG_READ, SIG_WRITE) and 3 in r:
                users.setdefault(r[3], []).append((t, function_start(img, pc), pc))
    print("\nsig  CAN-ID  bytes  order start len  users")
    for s in signals(img, msgs):
        m = msgs[s["msg"]]
        u = " ".join(f"{'R' if t == SIG_READ else 'W'}:fn{f or 0:06X}@{pc:06X}" for t, f, pc in users.get(s["sig"], []))
        print(f"0x{s['sig']:02X}  0x{m['can_id']:03X}  {s['start'] // 8}-{(s['start'] + s['length']) // 8 - 1}    {s['order']}    {s['start']:3d}  {s['length']:2d}  {u}")


if __name__ == "__main__":
    main()
