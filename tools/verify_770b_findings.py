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

    # --- round 3: CAN, kickdown propagation, lambda, generator, flap ----------
    from me9_can import message_objects

    msgs = message_objects(img)
    by_id = {(m["can_id"], m["tx"]): m for m in msgs.values()}
    check(len(msgs) == 30, f"CAN message-object table at 0xFDFAF4 holds 30 objects ({len(msgs)})")
    check(all((i, False) in by_id for i in (0x0B5, 0x0BA, 0x1A2, 0x5C3)), "EGS frames 0x0B5/0x0BA/0x1A2/0x5C3 configured as DME receive (TouCAN A)")
    check(all((i, True) in by_id and by_id[(i, True)]["controller"] == 0 for i in (0x0A8, 0x0A9, 0x0AA)), "0x0A8/0x0A9/0x0AA configured as DME transmit on TouCAN A")
    check(not any(m["can_id"] in (0x192, 0x1D2) for m in msgs.values()), "0x192 (selector lever) and 0x1D2 (gear display) are NOT in the DME message table")
    check(img.read(0xFDF967 + 5 * 0x11, 5) == bytes([0x11, 0x0D, 2, 0, 32]) and touched(0x5B8F71, 0x39394, "W"),
          "signal 0x11 = 0x0BA bytes 0-3, decoded in INT fn 0x392C8 into gear 0x5B8F71")
    check(list(img.read(0x15984, 11)) == [0, 0, 7, 0, 0, 1, 2, 3, 4, 5, 6], "0x0BA gear-code table INT 0x15984: codes 5..10 -> gears 1..6, code 2 -> 7")
    check(touched(0x5B8F71, 0x5E358) and touched(0x5B92CA, 0x5E35C, "W"), "current gear 0x5B92CA := 0x5B8F71 when EGS present (0x3FBED1)")
    check(dform(img, 0xFA9070) == (14, 12, 0, 0x0B) and touched(0x5B902B, 0xFA9074, "W") and touched(0x3FBFB3, 0xFA9064),
          "B_kd -> pedal/kickdown state 0x5B902B = 0x0B (EXT fn 0xFA8E70)")
    check(touched(0x5B902B, 0x4BAF0) and any(p == 0x4BB1C and t == 0x63C3C and r.get(3) == 0x33 for p, t, r in calls),
          "0x5B902B packed into 0x0AA byte 6 bits 4-7 (signal 0x33) by TX builder INT 0x4B128")
    check(touched(0x5B9A26, 0x4B950) and touched(0x3F9C24, 0x4B954, "W"), "engine speed 0x5B9A26 (0.25 rpm/bit) is the 0x0AA bytes 4-5 source")
    check(dform(img, 0x397C4) == (14, 11, 11, 8) and dform(img, 0x397CC) == (14, 10, 0, 3) and touched(0x5B9229, 0x397D4, "W"),
          "0x0B5 byte 7 -> transmission temperature 0x5B9229 = (raw+8)*4/3 (raw-40 degC into 0.75 degC/-48 format)")
    t = 0x1C6D0A
    xs = [img.u16(t + 2 + 2 * i) for i in range(22)]
    ys = [img.u16(t + 2 + 44 + 2 * i) for i in range(22)]
    check(img.u16(t) == 22 and ys[xs.index(305)] == 4096 and ys[0] == 3072 and ys[-1] == 16384,
          "broadband-lambda linearisation curve 0x1C6D0A: y = 0x1000 at the stoichiometric point (4096 = lambda 1.0)")
    check(touched(0x5B9708, 0x56310, "W") and touched(0x5B970A, 0x55CFC, "W"), "measured lambda per bank 0x5B9708/0x5B970A written by INT fn 0x55A1C")
    check(touched(0x5B96A4, 0x2ECAC) and any(p == 0x2ECB0 and t2 == 0x15E58 for p, t2, r in calls) and touched(0x5B98A0, 0x2ECBC),
          "fuel calc INT 0x2E9E4 divides by lambda setpoint 0x5B96A4 then applies controller factor 0x5B98A0")
    check(is_r2_ref(img, 0xF47F40, 0x1C9412) and touched(0x5B90EB, 0xF47F68, "W") and touched(0x5B8F26, 0xF47E94),
          "generator timer: 0x1C9412 loaded on full-load (0x5B8F26) edge, running flag 0x5B90EB -> fn 0xF8A648")
    check(touched(0x3FC286, 0x38C10) and dform(img, 0x38C14) == (14, 3, 0, 0xC) and any(p == 0x38C1C and t2 == 0xAC00 for p, t2, r in calls),
          "exhaust-flap command 0x3FC286 drives output channel 12 (INT 0x38C1C, bl 0xAC00)")

    # --- round 4: cylinder-cut lambda, Valvetronic, outputs, torque CAN ------
    check(touched(0x3FBFFE, 0x58C50) and touched(0x3F9D28, 0x58C6C, "W") and touched(0x3FC2FC, 0x58C84),
          "bank-A cut flag 0x3FBFFE resets air-mass integrator 0x3F9D28 (which integrates air-mass flow 0x3FC2FC)")
    check(is_r2_ref(img, 0x58CB4, 0x1C99C2) and touched(0x3FC1F5, 0x58CC8, "W"),
          "IMLEVABS candidate 0x1C99C2: bank-A post-cut threshold -> flag 0x3FC1F5 (blocks lambda release)")
    check(touched(0x3FBFFF, 0x58CDC) and is_r2_ref(img, 0x58D40, 0x1C99C4) and touched(0x3FC1F6, 0x58D54, "W"),
          "bank-B equivalent: 0x3FBFFF / threshold 0x1C99C4 -> flag 0x3FC1F6")
    check(touched(0x3FC19F, 0x58BC0) and is_r2_ref(img, 0x58C24, 0x1C99C6) and touched(0x3FC1F7, 0x58C3C, "W"),
          "after overrun cut (0x3FC19F) a separate air-mass threshold 0x1C99C6 gates lambda release (flag 0x3FC1F7)")
    check(touched(0x3FC2FC, 0xFACDB4, "W") and touched(0x3FC2B6, 0xFACDDC, "W"),
          "0x3FC2FC (air-mass flow) and its byte form 0x3FC2B6 (x input of cut-lambda curve 0x1C6408) written by EXT fn 0xFACD74")
    check(touched(0x5B96AA, 0x5709C) and dform(img, 0x570E8) == (14, 12, 19, -0xFFF) and dform(img, 0x570EC)[3] == 3,
          "bank-A closed loop 0x3FC1E3 requires snapped setpoint 0x5B96AA within 0x0FFF..0x1001 (lambda 1.000)")
    check(touched(0x5B989E, 0x574DC, "W") and touched(0x3FC1EE, 0x570A8),
          "controller states (e.g. 0x5B989E) are reset to 0 when lambda release 0x3FC1EE is off")
    check(img.u32(0x57D00) == 0x618C8000 and touched(0x5B989E, 0x57C9C),
          "bank-A factor 0x5B98AE = 0x8000 + integrator when released, 0x8000 (=1.0) otherwise")
    check(touched(0x5B9B20, 0x4FD14) and dform(img, 0x4FD24) == (10, 0, 31, 0x6EA) and touched(0x5B9D10, 0x4FD58, "W")
          and any(p == 0x4FE24 and t2 == 0x63C3C and r.get(3) == 0x36 for p, t2, r in calls),
          "Valvetronic bank-1 lift request (min(0x5B9B20, 0x5B9BB6+trim), clamp 0x6EA) -> 0x5B9D10 -> CAN 0x105 (signal 0x36)")
    check(touched(0x5B9D12, 0x4FEE4, "W") and any(p == 0x4FF98 and t2 == 0x63C3C and r.get(3) == 0x38 for p, t2, r in calls),
          "Valvetronic bank-2 lift request 0x5B9D12 -> CAN 0x10D (signal 0x38): one request per bank, none per cylinder")
    check(touched(0x3FC29B, 0x38B20) and dform(img, 0x38B24) == (14, 3, 0, 6) and touched(0x3FC29B, 0xF9E624, "W"),
          "output channel 6 driven by 0x3FC29B, written by the coolant-target fn EXT 0xF9E148")
    check(touched(0x5B94BC, 0x4BCD0) and touched(0x5B922A, 0x4BD10) and dform(img, 0x4BD1C)[3] == -0x800,
          "CAN torque converter INT 0x4BCCC: ((T>>1)-(0x5B94BC>>1))*0x5B922A>>10, clamped to signed 12 bit")
    check(touched(0x5B983A, 0x4BE4C) and any(p == 0x4BE90 and t2 == 0x4BD40 for p, t2, r in calls) and img.u32(0x4B550) == 0x554A6226,
          "0x0A8 bits 12-23 carry converted torque 0x5B983A (word 0x5B94CA)")
    check(touched(0x5B9854, 0x4BE6C) and touched(0x5B9854, 0xFA4F30, "W"),
          "0x0A9 torque word 0x5B94CC is converted from 0x5B9854 (written by full-load fn EXT 0xFA4D04)")

    check(touched(0x5B90EB, 0xF8A92C) and is_r2_ref(img, 0xF8A910, 0x1C940A) and touched(0x5B8F2D, 0xF8A950, "W") and touched(0x5B8F2D, 0xF8A9F4),
          "generator chain: timer flag 0x5B90EB -> reduction flag 0x5B8F2D (enable CAL 0x1C940A) -> voltage-request fn EXT 0xF8A9D0")

    for ok, text in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {text}")
    failed = sum(1 for ok, _ in results if not ok)
    print(f"\n{len(results) - failed}/{len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
