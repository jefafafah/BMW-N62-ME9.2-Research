#!/usr/bin/env python3
"""PWM channel enumerator for the 770B image (round 7).

    python tools/me9_pwm.py            # logical channel table + every PWM API call site
    python tools/me9_pwm.py --ch 8     # only one logical channel

Decodes the logical-channel table INT 0x156AC (10 x 24-byte records) used by the PWM API
INT 0x671AC(r3=logical ch, r4=duty 0..10000, r5=period factor), then lists each `bl 0x671AC`
with the constant/RAM source of r3, r4, r5 found by a short backward scan (register moves,
li/lis/addi, lbz/lhz/lha from known RAM). Wrappers (functions that forward r3 to the API) are
followed one level: their callers are listed with the logical channel they pass.
"""
from __future__ import annotations
import argparse, struct, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from me9_image import Image  # noqa: E402
from me9_xref import build, function_start  # noqa: E402

API, TABLE, NCH, DRIVERS = 0x671AC, 0x156AC, 10, 0x1579C
APIS = {0x671AC: "api", 0xFD5324: "api-copy"}   # EXT 0xFD5324 is a byte-identical copy used by INT 0x5F2B8
DEST_RA = {28, 60, 124, 284, 316, 412, 444, 476, 24, 536, 792, 824, 954, 922, 26}   # logical/shift XOs: dest = rA
STORE_XO = {151, 183, 215, 247, 407, 439, 662, 918, 150, 727, 759, 983}
DRV_NAME = {0: "MIOS MDASM (drv0)", 1: "MIOS MPWMSM (drv1)"}


def table(img):
    rows = []
    for i in range(NCH):
        b = TABLE + 24 * i
        rows.append(dict(ch=img.u8(b), hw=img.u32(b + 4), mult=img.u32(b + 8), drv=img.u8(b + 0xD),
                         dflt_duty=img.u16(b + 0xE), dflt_per=img.u16(b + 0x10),
                         f12=img.u8(b + 0x12), inv=img.u8(b + 0x13), rec=b))
    return rows


def sources(img, pc, rdmap, want=(3, 4, 5), depth=40):
    """Backward scan from a call: for each wanted register return 'const 0x..', 'RAM 0x..' or 'reg rN'."""
    out, track = {}, {r: r for r in want}       # wanted reg -> current reg holding it
    a = pc
    for _ in range(depth):
        a -= 4
        w = img.u32(a)
        op, rt, ra, imm = w >> 26, (w >> 21) & 31, (w >> 16) & 31, w & 0xFFFF
        if w == 0x4E800020 or (op == 18 and not (w & 1)) or (op == 18 and (w & 1)):
            break
        for want_r, cur in list(track.items()):
            if want_r in out:
                continue
            if op == 14 and rt == cur and ra == 0:
                out[want_r] = f"const 0x{struct.unpack('>h', struct.pack('>H', imm))[0] & 0xFFFF:X}"
            elif op in (34, 40, 42, 32) and rt == cur:
                out[want_r] = ("RAM 0x%06X" % rdmap[a]) if a in rdmap else f"load via r{ra}"
            elif op == 31 and ((w >> 1) & 0x3FF) == 444 and ra == cur:   # mr ra,rs
                rs = rt
                if rs == (w >> 11) & 31:
                    track[want_r] = rs
            elif op == 31 and ((w >> 1) & 0x3FF) == 922 and ra == cur:   # extsh ra,rs
                track[want_r] = rt
            elif op == 21 and ra == cur:                                     # rlwinm ra,rs,...
                track[want_r] = rt
            elif op == 31 and ((w >> 1) & 0x3FF) not in STORE_XO and \
                    (ra if ((w >> 1) & 0x3FF) in DEST_RA else rt) == cur:
                out[want_r] = f"computed @{a:06X}"
            elif op == 7 and rt == cur:                                      # mulli
                out[want_r] = f"r{ra}*{struct.unpack('>h', struct.pack('>H', imm))[0]}"
            elif rt == cur and op not in (36, 37, 38, 39, 44, 45, 10, 11, 16, 31):
                out[want_r] = f"computed @{a:06X}"
    for r in want:
        out.setdefault(r, f"arg r{track[r]}")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--int"); ap.add_argument("--ext"); ap.add_argument("--ch", type=int)
    args = ap.parse_args()
    img = Image.from_args(args)
    refs, calls = build(img)
    rdmap = {pc: ea for pc, ea, k, sz in refs if k == "R"}
    tab = table(img)
    print("lch hw    drv                 mult dflt_duty dflt_per(0.1ms) inv  record")
    for r in tab:
        if args.ch is None or args.ch == r["ch"]:
            print(f"{r['ch']:>3} 0x{r['hw']:02X}  {DRV_NAME.get(r['drv'], r['drv']):19s} {r['mult']:>4} {r['dflt_duty']:>9} "
                  f"{r['dflt_per']:>8} {r['inv']:>3}  INT 0x{r['rec']:05X}")
    sites = [(pc, regs) for pc, t, regs in calls if t in APIS]
    # one-level wrapper resolution: call sites whose r3 is an incoming argument
    wrappers = {}
    rows = []
    for pc, regs in sites:
        s = sources(img, pc, rdmap)
        if 3 in regs:
            s[3] = f"const 0x{regs[3]:X}"
        fn = function_start(img, pc) or 0
        rows.append((pc, fn, s))
        if s[3].startswith("arg"):
            wrappers[fn] = s
    for fn in list(wrappers):
        for pc, t, regs in calls:
            if t == fn:
                s = sources(img, pc, rdmap)
                if 3 in regs:
                    s[3] = f"const 0x{regs[3]:X}"
                rows.append((pc, function_start(img, pc) or 0, dict(s, via=f"wrapper 0x{fn:06X}")))
    ram_reads = sorted((pc, ea) for pc, ea, k, sz in refs if k == "R" and (0x3F9800 <= ea < 0x400000 or 0x5B8000 <= ea < 0x5C0000))
    def reads_before(fn, pc):
        return sorted({ea for p, ea in ram_reads if fn <= p < pc})
    print("\ncall-site  function   r3 (logical ch)      r4 (duty)               r5 (period)          via / RAM read in fn before call")
    for pc, fn, s in sorted(rows, key=lambda x: (x[2][3], x[0])):
        if args.ch is not None and s[3] != f"const 0x{args.ch:X}":
            continue
        rr = " ".join(f"{a:06X}" for a in reads_before(fn, pc)[:8])
        print(f"0x{pc:06X}  0x{fn:06X}  {s[3]:20s} {s[4]:23s} {s[5]:20s} {s.get('via', '')} {rr}")
    used = {int(s[3].split()[1], 16) for _, _, s in rows if s[3].startswith("const")}
    unused = [r["ch"] for r in tab if r["ch"] not in used]
    if args.ch is None:
        print("\nlogical channels without any API call site:", unused or "none")


if __name__ == "__main__":
    main()
