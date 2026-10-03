#!/usr/bin/env python3
"""Re-check the round-2 770B findings against user-supplied local dumps.

Every check decodes instructions/data from the local images and compares them
with the claim in research/verified-findings.md. Only expected operands and
addresses are embedded here, never firmware bytes.

Usage:
    python tools/verify_770b_findings.py --int mpc555-6.bin --ext 28f200f3t.bin
Exit status is non-zero if any check fails.
"""
from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from me9_image import R2_BASE, R13_BASE, Image  # noqa: E402
from me9_xref import build  # noqa: E402

# N62 firing order (BMW documentation); bit n of an AEVAB mask = n-th cylinder in this order.
FIRING_ORDER = [1, 5, 4, 8, 6, 3, 7, 2]

results: list[tuple[bool, str]] = []


def check(ok: bool, text: str) -> None:
    results.append((bool(ok), text))


def dform(img: Image, pc: int):
    """Decode a D-form instruction -> (opcode, rt, ra, simm)."""
    w = img.u32(pc)
    d = w & 0xFFFF
    return w >> 26, (w >> 21) & 31, (w >> 16) & 31, d - 0x10000 if d & 0x8000 else d


def is_r2_ref(img: Image, pc: int, target: int, ops=(14, 34, 40, 42, 32)) -> bool:
    op, rt, ra, d = dform(img, pc)
    return op in ops and ra == 2 and R2_BASE + d == target


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--int")
    ap.add_argument("--ext")
    args = ap.parse_args()
    img = Image.from_args(args)
    if not img.is_reference():
        print("WARNING: images differ from the reference dump hashes; addresses below are 1037389760-specific")

    ext = img.ext
    # --- memory architecture -------------------------------------------------
    check(ext[0:4] == b"ZZZZ" and ext[4:8] == b"3333", "ext file 0x00000: program-block header magic 5A5A5A5A/33333333")
    check(ext[0xC0000:0xC0004] == b"ZZZZ" and ext[0xC0004:0xC0008] == b"\xcc" * 4, "ext file 0xC0000: data-block header magic 5A5A5A5A/CCCCCCCC")
    check(struct.unpack(">I", ext[0xC0008:0xC000C])[0] == 0xFC0080, "data-block header self-pointer 0x00FC0080 -> external flash mapped at CPU 0xF00000")
    check(struct.unpack(">I", ext[0xC001C:0xC0020])[0] == 0xFDFF58 and ext[0xDFF58:0xDFF5C] == b"ZZZZ", "data-block end pointer 0xFDFF58 holds end marker")
    check(struct.unpack(">I", ext[0x1C:0x20])[0] == 0xFEFFD0 and ext[0xEFFD0:0xEFFD4] == b"ZZZZ", "program-block end pointer 0xFEFFD0 holds end marker")
    check(b"0087180A770B" in ext and b"1037389760" in ext, "software family 0087180A770B and SW 1037389760 strings present")
    for base_pc in (0x1C828, 0xF0422C):
        hi13, lo13 = dform(img, base_pc), dform(img, base_pc + 4)
        hi2, lo2 = dform(img, base_pc + 8), dform(img, base_pc + 12)
        r13 = (hi13[3] << 16) + lo13[3]
        r2 = (hi2[3] << 16) + lo2[3]
        check(hi13[1] == 13 and r13 == R13_BASE and hi2[1] == 2 and r2 == R2_BASE,
              f"startup at 0x{base_pc:06X} sets r13=0x{r13:06X} r2=0x{r2:06X}")

    refs, calls = build(img)
    by_ea: dict[int, list] = {}
    for pc, ea, k, sz in refs:
        by_ea.setdefault(ea, []).append((pc, k, sz))
    cal_reads = sum(1 for pc, ea, k, sz in refs if 0x1C0000 <= ea < 0x1E0000)
    check(cal_reads > 5000, f"code reads calibration through CPU alias 0x1C0000-0x1DFFFF ({cal_reads} refs)")
    check(any(0x307080 <= ea < 0x307100 for ea in by_ea) and any(0x307480 <= ea < 0x307500 for ea in by_ea),
          "TouCAN A (0x307080) and TouCAN B (0x307480) register blocks are accessed")

    def touched(ea, pc, kind=None):
        return any(p == pc and (kind is None or k == kind) for p, k, _ in by_ea.get(ea, []))

    # --- AEVAB / REDABM ------------------------------------------------------
    red = 0x1C5510
    m = [img.u8(red + i) for i in range(64)]
    check(all(bin(m[r * 8 + c]).count("1") == c + 1 for r in range(8) for c in range(8)), "REDABM (CPU 0x1C5510 = file 0xC5510): column k has exactly k bits set")
    check({m[r * 8 + 3] for r in range(8)} == {0x55, 0xAA}, "REDABM step-4 column only contains 0x55/0xAA")
    check(is_r2_ref(img, 0x2C560, red) and is_r2_ref(img, 0x2C6E4, red), "AEVAB (INT 0x2C060) forms REDABM address r2-0x2AE0 at 0x2C560/0x2C6E4")
    check(touched(0x5B92E4, 0x2C568) and touched(0x5B92E6, 0x2C54C),
          "REDABM row index = phase byte 0x5B92E4, column = step byte 0x5B92E6 - 1")
    check(touched(0x5B907C, 0x2C104) and dform(img, 0x2C108)[3] == 4,
          "phase latched as (segment counter 0x5B907C + 4) mod 8 when a reduction starts")
    check(touched(0x5B92EA, 0x2EF40) and dform(img, 0x2EF5C) == (14, 12, 0, 0x5A),
          "injection-time loop (INT 0x2ED6C) reads final mask 0x5B92EA and uses bank constant 0x5A")
    check(dform(img, 0xFE4BF4) == (14, 11, 0, 0x5A) and touched(0x5B8C82, 0xFE4BF8),
          "bank mask 0x5B8C82 initialised to 0x5A (firing-order positions 1,3,4,6)")
    bank2 = {FIRING_ORDER[i] for i in range(8) if 0x5A >> i & 1}
    check(bank2 == {5, 6, 7, 8}, "0x5A selects exactly cylinders 5-8 when bit n = n-th cylinder in firing order 1-5-4-8-6-3-7-2")
    check(touched(0x1CD9CA, 0xF7BFF8) and touched(0x5B88C5, 0xF7C00C, "W"),
          "CWEVAB candidate 0x1CD9CA (file 0xCD9CA) is OR-ed into cylinder-off mask 0x5B88C5 consumed by AEVAB")
    check(is_r2_ref(img, 0x485DC, 0x1C8A1A), "MDHYEZ candidate 0x1C8A1A used as hysteresis in step request (INT 0x484F8)")
    check(touched(0x5B93E7, 0x48714, "W") and dform(img, 0x48710) == (14, 11, 0, 8),
          "step request writes 8 (all cylinders) to 0x5B93E7 on full-cut request")
    check(touched(0x5B92EA, 0x431A4, "W") and touched(0x5BBBA8, 0x430C4),
          "total-cut word 0x5BBBA8 != 0 forces final mask 0x5B92EA = 0xFF")

    # --- torque / pedal / kickdown -------------------------------------------
    def call_with(pc, target, r3):
        return any(p == pc and t == target and r.get(3) == r3 for p, t, r in calls)

    check(call_with(0x46370, 0x17B64, 0x1C87DA), "KFPED candidate map 0x1C87DA (16x8 u16) looked up at 0x46370")
    check(touched(0x5B96D8, 0x4636C) and touched(0x5B9A26, 0x46360), "KFPED inputs: pedal 0x5B96D8 (x), engine speed 0x5B9A26 (y)")
    check(call_with(0x467B0, 0x17B64, 0x1C85FA) and call_with(0x46680, 0x17B64, 0x1C86EA),
          "KFMIMR/KFMRMI candidates 0x1C85FA / 0x1C86EA looked up in the same driver-wish function")
    check(is_r2_ref(img, 0x3B824, 0x1C1E4C) and is_r2_ref(img, 0x3B838, 0x1C1E4B) and is_r2_ref(img, 0x3B858, 0x1C1E4A),
          "kickdown function 0x3B80C uses 0x1C1E4C (pedal min), 0x1C1E4B (off), 0x1C1E4A (on)")
    check(sum(1 for pc, k, _ in by_ea.get(0x3FBFB3, []) if k == "W" and 0x3B80C <= pc < 0x3B888) == 3, "kickdown state written to 0x3FBFB3")

    # --- lambda / flap / thermal ----------------------------------------------
    check(call_with(0xF7E63C, 0x16AE4, 0x1C6408) and touched(0x5B891E, 0xF7E644, "W"),
          "cylinder-cut lambda setpoint curve 0x1C6408 -> 0x5B891E")
    check(touched(0x5B891E, 0x5573C) and touched(0x5B96AA, 0x55844, "W"),
          "lambda coordinator (INT 0x5563C) substitutes 0x5B891E while a bank has cut cylinders")
    check(call_with(0xF97F0C, 0x179E8, 0x1D077C) and any(k == "W" and 0xF97D8C <= pc < 0xF97F90 for pc, k, _ in by_ea.get(0x3FC286, [])),
          "exhaust-flap map 0x1D077C (7 gears x 12 rpm) drives flap command 0x3FC286")
    check(any(p in (0xF9E484, 0xF9E4D0) and t == 0x179E8 and r.get(3) == 0x1D08A8 for p, t, r in calls),
          "two-level coolant-target map candidate 0x1D08A8 looked up in fn 0xF9E148")

    for ok, text in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {text}")
    failed = sum(1 for ok, _ in results if not ok)
    print(f"\n{len(results) - failed}/{len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
