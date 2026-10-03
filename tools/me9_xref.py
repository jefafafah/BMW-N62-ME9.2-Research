#!/usr/bin/env python3
"""Cross-reference builder for ME9.2 (MPC555 / PowerPC) images.

A deliberately simple linear scanner: it tracks `lis/addi/ori/mr` constants per
register inside straight-line code (state is reset at `blr` and unconditional
branches) and records every load/store/address formation whose effective
address falls in a known region (calibration alias, internal SRAM, external
RAM, I/O, flash). r2/r13-relative accesses use the application bases
R2=0x1C7FF0 and R13=0x401A20.

This is evidence-gathering tooling, not a decompiler: indirect accesses
(pointer arithmetic, indexed stores) are not resolved, so "no writer found"
does not prove a variable is read-only.

Usage (images via --int/--ext or ME9_INT/ME9_EXT):
    python tools/me9_xref.py build                 # writes cache (default ~/.cache/me9_770b_xref.pkl)
    python tools/me9_xref.py refs 0x5B92EA         # who reads/writes an address
    python tools/me9_xref.py func 0x484F8          # summary of reads/writes/cal/calls
    python tools/me9_xref.py dis 0x2C060 0x2C860   # annotated disassembly (needs capstone)
    python tools/me9_xref.py callers 0x2C060
"""
from __future__ import annotations

import argparse
import os
import pickle
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from me9_image import R2_BASE, R13_BASE, Image, region  # noqa: E402

LOADS = {32: 4, 33: 4, 34: 1, 35: 1, 40: 2, 41: 2, 42: 2, 43: 2, 48: 4, 50: 8}
STORES = {36: 4, 37: 4, 38: 1, 39: 1, 44: 2, 45: 2, 52: 4, 54: 8}
UPDATE_FORMS = {33, 35, 41, 43, 37, 39, 45}
DEFAULT_CACHE = Path(os.environ.get("ME9_XREF_CACHE", Path.home() / ".cache" / "me9_770b_xref.pkl"))


def _sx(x: int) -> int:
    return x - 0x10000 if x & 0x8000 else x


def build(img: Image):
    refs: list[tuple[int, int, str, int]] = []  # (pc, ea, kind R/W/addr, size)
    calls: list[tuple[int, int, dict[int, int]]] = []  # (pc, target, known arg regs)
    for base, data in img.segments():
        regs: dict[int, int] = {}
        for o in range(0, len(data) - 4, 4):
            pc = base + o
            w = struct.unpack(">I", data[o:o + 4])[0]
            op, rt, ra, imm = w >> 26, (w >> 21) & 31, (w >> 16) & 31, w & 0xFFFF
            if w == 0x4E800020 or (op == 18 and (w & 1) == 0):
                regs = {}
                continue
            if op == 15:  # addis / lis
                if ra == 0:
                    regs[rt] = (imm << 16) & 0xFFFFFFFF
                elif ra in regs:
                    regs[rt] = (regs[ra] + (imm << 16)) & 0xFFFFFFFF
                else:
                    regs.pop(rt, None)
                continue
            if op == 14:  # addi / li
                if ra == 0:
                    regs[rt] = _sx(imm) & 0xFFFFFFFF
                    continue
                b = regs.get(ra, R2_BASE if ra == 2 else R13_BASE if ra == 13 else None)
                if b is None:
                    regs.pop(rt, None)
                    continue
                v = (b + _sx(imm)) & 0xFFFFFFFF
                regs[rt] = v
                if region(v):
                    refs.append((pc, v, "addr", 0))
                continue
            if op == 24:  # ori rA,rS,imm
                if rt in regs:
                    regs[ra] = regs[rt] | imm
                else:
                    regs.pop(ra, None)
                continue
            if op in LOADS or op in STORES:
                b = 0 if ra == 0 else regs.get(ra, R2_BASE if ra == 2 else R13_BASE if ra == 13 else None)
                if b is not None and ra != 1:
                    v = (b + _sx(imm)) & 0xFFFFFFFF
                    if region(v):
                        refs.append((pc, v, "R" if op in LOADS else "W", LOADS.get(op) or STORES.get(op)))
                    if op in UPDATE_FORMS and ra in regs:
                        regs[ra] = v
                if op in LOADS and op not in (48, 50):
                    regs.pop(rt, None)
                continue
            if op == 18 and (w & 1):  # bl
                li = w & 0x03FFFFFC
                if li & 0x02000000:
                    li -= 0x04000000
                t = (li if w & 2 else pc + li) & 0xFFFFFFFF
                calls.append((pc, t, {r: regs[r] for r in (3, 4, 5, 6, 7, 8, 9) if r in regs}))
                for r in (0, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12):
                    regs.pop(r, None)
                continue
            if op == 31:
                xo = (w >> 1) & 0x3FF
                if xo == 444 and rt == ((w >> 11) & 31):  # mr
                    if rt in regs:
                        regs[ra] = regs[rt]
                    else:
                        regs.pop(ra, None)
                elif xo in (444, 28, 60, 124, 284, 316, 412, 476, 24, 536, 792, 824, 954, 922, 986, 26):
                    regs.pop(ra, None)
                else:
                    regs.pop(rt, None)
                continue
            if op in (20, 21, 23, 25, 26, 27, 28, 29):
                regs.pop(ra, None)
                continue
            if op in (16, 19, 10, 11):  # branches / compares
                continue
            regs.pop(rt, None)
    return refs, calls


def function_start(img: Image, pc: int) -> int | None:
    """Nearest preceding prologue (stwu r1,-X(r1)) or instruction after a blr."""
    a = pc
    while a > pc - 0x3000 and img.read(a - 4, 4):
        a -= 4
        w = img.u32(a)
        if w == 0x4E800020:
            return a + 4
        if (w & 0xFFFF8000) == 0x94218000:
            return a
    return None


def function_end(img: Image, start: int) -> int:
    a = start
    while img.read(a, 4) and img.u32(a) != 0x4E800020 and a < start + 0x4000:
        a += 4
    return a + 4


def load_cache(path: Path):
    if not path.exists():
        raise SystemExit(f"no xref cache at {path}; run `build` first")
    return pickle.loads(path.read_bytes())


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--int")
    ap.add_argument("--ext")
    ap.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build")
    for name in ("refs", "callers"):
        p = sub.add_parser(name)
        p.add_argument("address", nargs="+")
    p = sub.add_parser("func")
    p.add_argument("address", nargs="+")
    p = sub.add_parser("dis")
    p.add_argument("start")
    p.add_argument("end", nargs="?")
    args = ap.parse_args()
    img = Image.from_args(args)

    if args.cmd == "build":
        refs, calls = build(img)
        args.cache.parent.mkdir(parents=True, exist_ok=True)
        args.cache.write_bytes(pickle.dumps({"hashes": img.hashes(), "refs": refs, "calls": calls}))
        print(f"{len(refs)} refs, {len(calls)} calls -> {args.cache}")
        return

    db = load_cache(args.cache)
    if db["hashes"] != img.hashes():
        raise SystemExit("cache was built from different images; rebuild")
    refs, calls = db["refs"], db["calls"]

    if args.cmd == "refs":
        for s in args.address:
            ea = int(s, 0)
            hits = [(pc, k, sz) for pc, e, k, sz in refs if e == ea]
            print(f"{ea:06X} [{region(ea)}]")
            for pc, k, sz in hits:
                print(f"   {k}{sz} @ {pc:06X}  fn {function_start(img, pc) or 0:06X}")
    elif args.cmd == "callers":
        for s in args.address:
            t = int(s, 0)
            print(f"{t:06X}: " + " ".join(f"{pc:06X}" for pc, tt, _ in calls if tt == t))
    elif args.cmd == "func":
        for s in args.address:
            st = int(s, 0)
            en = function_end(img, st)
            sel = [(pc, e, k, sz) for pc, e, k, sz in refs if st <= pc < en]
            rd = sorted({e for pc, e, k, sz in sel if k == "R" and region(e) != "CAL"})
            wr = sorted({e for pc, e, k, sz in sel if k == "W"})
            cal = sorted({(e, sz) for pc, e, k, sz in sel if region(e) == "CAL" and k == "R"})
            cl = sorted({t for pc, t, _ in calls if st <= pc < en})
            print(f"== {st:06X}-{en:06X}")
            print(" reads :", " ".join(f"{a:06X}" for a in rd))
            print(" writes:", " ".join(f"{a:06X}" for a in wr))
            print(" cal   :", " ".join(f"{a:06X}/{sz}" for a, sz in cal))
            print(" calls :", " ".join(f"{a:06X}" for a in cl))
    elif args.cmd == "dis":
        from me9_image import disassemble

        st = int(args.start, 0)
        en = int(args.end, 0) if args.end else function_end(img, st)
        by_pc: dict[int, list] = {}
        for pc, e, k, sz in refs:
            if st <= pc < en:
                by_pc.setdefault(pc, []).append((e, k, sz))
        for line in disassemble(img, st, (en - st) // 4):
            pc = int(line[:8], 16)
            ann = "".join(f"  ;{k}{sz} {e:06X}" for e, k, sz in by_pc.get(pc, []))
            print(line + ann)


if __name__ == "__main__":
    main()
