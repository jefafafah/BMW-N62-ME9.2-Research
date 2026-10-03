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
          "bank-A lambda modulation flag 0x3FC1E3 requires snapped setpoint 0x5B96AA within 0x0FFF..0x1001 (lambda 1.000)")
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

    # --- round 5: VANOS -------------------------------------------------------
    pwm = {i: img.read(0x156AC + 24 * i, 24) for i in range(10)}
    check([int.from_bytes(pwm[i][4:8], "big") for i in (2, 7, 3, 6)] == [0x0C, 0x0B, 0x1E, 0x1F] and all(pwm[i][0xD] == 0 for i in (2, 3, 6, 7)),
          "PWM logical channels 2/7/3/6 (INT table 0x156AC) map to MIOS hardware channels 0x0C/0x0B/0x1E/0x1F, driver index 0")
    check([dform(img, a)[3] for a in (0x4FAD8, 0x4FAE8, 0x4FAF8, 0x4FB08)] == [2, 7, 3, 6]
          and sum(1 for p, t2, r in calls if 0x4FA8C <= p < 0x4FB24 and t2 == 0x671AC) == 4,
          "INT 0x4FA8C maps actuator index 0/1/2/3 to PWM logical channels 2/7/3/6 via PWM API INT 0x671AC")
    check(any(p == 0x3FC7C and t2 == 0x3F0B4 for p, t2, r in calls) and dform(img, 0x3FC00)[3] == -0x4364 and dform(img, 0x3FC88)[3] == 4,
          "INT 0x3FBAC loops over 4 actuator objects at INT 0x1BC9C (stride 0x78) and drives each through INT 0x3F0B4")
    objs = [0x1BC9C + 0x78 * i for i in range(4)]
    check([img.u32(o + 0x30) for o in objs] == [0x5B8DCC, 0x5B8DA8, 0x5B8DBA, 0x5B8D96]
          and [img.u32(o + 0x2C) for o in objs] == [0x5B8DCA, 0x5B8DA6, 0x5B8DB6, 0x5B8D92]
          and [img.u32(o + 0x10) for o in objs] == [0x5B8DCE, 0x5B8DAA, 0x5B8DBC, 0x5B8D98]
          and [img.u8(o + 0x74) for o in objs] == [0, 1, 2, 3],
          "VANOS-candidate objects: target (+0x30), measured position (+0x2C), duty (+0x10) RAM pointers")
    check(img.u32(objs[0] + 0x44) == img.u32(objs[2] + 0x44) == 0x1D0618 and img.u32(objs[1] + 0x44) == img.u32(objs[3] + 0x44) == 0x1D0613,
          "objects 0/2 share one calibration set, objects 1/3 another (two actuator types x two instances)")
    check(img.u32(0x3F864) == 0x819F0030 and img.u32(0x3F884) == 0x819F0038 and img.u32(0x3F88C) == 0x7FDD6050,
          "controller INT 0x3F848: error = estimated position (+0x38) - target (+0x30)")
    check(touched(0x5B910F, 0x3EF50) and touched(0x5B911A, 0x3EF60) and img.u32(0x3EFEC) == 0x81830030,
          "target writer INT 0x3EF24: odd objects use byte 0x5B910F x8, even objects 0x5B911A x8, stored via +0x30")
    maps = sorted(r.get(3) for p, t2, r in calls if 0x3DA70 <= p < 0x3EF24 and t2 == 0x191B0)
    check(maps == [0x1C9B9C + 0x90 * i for i in range(14)],
          "VANOS target fn INT 0x3DA70 reads fourteen 12x12 byte maps CAL 0x1C9B9C..0x1CA2EC (group axes)")
    check(touched(0x5B9C9A, 0x4F488) and touched(0x5BA058, 0x4F92C) and touched(0x5B9C9A, 0x2F7D4) and touched(0x5BA058, 0x2F810, "W"),
          "cam capture: index-0 angle 0x5B9C9A and timestamp 0x5BA058 written by INT 0x2F7AC, read via INT 0x4F42C/0x4F904")
    check(dform(img, 0xF1206C)[3] == 0x4800 and touched(0x306086, 0xF1207C, "W"),
          "EXT 0xF12018 only switches MIOS register 0x306086 (0x4800/0x4000): not a duty writer (round-5 rejection)")

    # --- round 6: 0x1A2 speed / ratio path -----------------------------------
    check(any(p == 0x39530 and t2 == 0x63660 and r.get(3) == 0x13 for p, t2, r in calls)
          and img.u32(0x39564) == 0x280CFFFF and touched(0x5B9982, 0x39574, "W") and touched(0x5B9982, 0x39580, "W"),
          "0x1A2 (signal 0x13) -> 0x5B9982 unscaled; raw 0xFFFF stored as 0 (INT 0x39564/0x39574)")
    check(dform(img, 0x39594)[3] == 0x32 and touched(0x5B9982, 0x395B0, "W") and touched(0x3FA58C, 0x1D98C, "W"),
          "0x1A2 timeout: >50 decoder calls without RX indication (INT 0x1D974 sets 0x3FA58C) -> 0x5B9982 = 0")
    check(img.u8(0x1C8532) == 0x0E and img.u32(0x46E2C) == 0x558C07BC and touched(0x5B9982, 0x46E3C)
          and img.u32(0x46E40) == 0x559868E4 and touched(0x5B97BA, 0x46E4C),
          "CAL 0x1C8532 = 0x0E: bit 0x02 set selects 0x5B9982 (not model 0x5B97BA) as numerator, shifted <<13")
    check(img.u32(0x4635C) == 0x3B399A26 and img.u32(0x46E54) == 0xA3B90000 and img.u32(0x46E60) == 0x7F18EB96
          and img.u32(0x46E64) == 0x2818FFFF and all(touched(0x5B981E, pc, "W") for pc in (0x46E78, 0x46E84, 0x46EA0, 0x46EB0)),
          "0x5B981E = min((0x5B9982<<13) / 0x5B9A26, 0xFFFF); rpm 0 -> 0xFFFF (or 0 if numerator 0)")
    rx = [img.u16(0x1C84B4 + 2 * i) for i in range(6)]
    gy = [img.u16(0x1C84C0 + 2 * i) for i in range(8)]
    mv = [img.u16(0x1C84D0 + 2 * i) for i in range(48)]
    check(img.u16(0x1C84B0) == 6 and img.u16(0x1C84B2) == 8 and gy == list(range(8))
          and [round(v / 0x4000, 2) for v in rx] == [0.90, 0.96, 0.99, 1.00, 1.04, 1.06],
          "map 0x1C84B0: 6 ratio breakpoints 0.90/0.96/0.99/1.00/1.04/1.06 x 0x4000, gear axis 0..7")
    check(img.u32(0x17CF4) == 0x7CE43B78 and img.u32(0x192D8) == 0x7D8441D6
          and all(mv[x * 8 + g] == 0x8000 for x in range(6) for g in (0, 1, 7)) and mv[2 * 8:3 * 8] == [0x8000] * 8
          and mv[5 * 8:6 * 8] == [0x8000] * 8 and min(mv) == 0x199A and max(mv) == 0xC000,
          "map data ratio-major [x*8+gear]; gears 0/1/7 and ratio 0.99/1.06 = 0x8000; range 0x199A..0xC000")
    check(call_with(0x46EDC, 0x17B64, 0x1C84B0) and touched(0x5B981E, 0x46ED8) and touched(0x5B92CA, 0x46EC8)
          and touched(0x5B97F0, 0x46EE4, "W") and img.u32(0x46EB8) == 0x558C077A and touched(0x5B97F0, 0x46F28, "W"),
          "0x5B97F0 := map 0x1C84B0(0x5B981E, gear 0x5B92CA) when CAL bit 0x04, else curve 0x1CF804")
    check(img.u32(0x46F30) == 0x558C0738 and touched(0x5B9828, 0x46F40) and img.u32(0x46F44) == 0x55997860
          and touched(0x5B97F0, 0x46F4C) and img.u32(0x46F58) == 0x7F39C396 and touched(0x5B982A, 0x46F94, "W"),
          "filter gain 0x5B982A = clamp((0x5B9828<<15) / 0x5B97F0, 1, 0xFFFF) when CAL bit 0x08 (0x8000 = x1)")
    check(touched(0x5B982A, 0x47058) and any(p in (0x47064, 0x470C0) and t2 == 0x16070 for p, t2, r in calls)
          and touched(0x3FB444, 0x47068, "W") and img.u32(0x470C4) == 0x90780000 and touched(0x3FB448, 0x46FB0),
          "0x5B982A is the step gain of the two cascaded integrators 0x3FB444/0x3FB448 (helper INT 0x16070)")
    check(img.u32(0x46AA4) == 0x91410008 and touched(0x5B97F8, 0x46AA0) and touched(0x5B9808, 0x46800)
          and img.u32(0x47700) == 0x81810008 and img.u32(0x47708) == 0xB19C0000 and touched(0x5B9806, 0x46974),
          "filter input 0x5B9808, output 0x5B97F8 (via 8(r1)); output copied to 0x5B9806 while latch 0x3FC18D set")
    check(img.u32(0x475C4) == 0x556B06F6 and img.u32(0xF88860) == 0x556B06F6 and not img.u8(0x1C8532) & 0x10
          and touched(0x5B97F0, 0x475D8) and touched(0x5B97F0, 0xF88874),
          "second 0x5B97F0 divisor (0x5B9824 -> 0x5B9826, INT 0x475D8 / EXT 0xF88874) gated by CAL bit 0x10: inactive")
    check(img.u32(0x5F684) == 0x554A07FE and img.u8(0x1C7AB4) & 1 == 0 and touched(0x5B9982, 0x5F6D0),
          "INT 0x5F52C reads 0x5B9982 only when CAL 0x1C7AB4 bit0 set (=0x00): inactive in this calibration")

    # ===== final pass: 0x0BA / 0x0B5 / 0x5C3 status fields =====
    # --- egs_status: 0x0BA / 0x0B5 status fields and their consumers ----------
    # 0x0BA byte0 bit6 -> 0x3FBEE0, bit7 -> 0x3FBEDF; both forced to 1 on 0x0BA timeout (> 50 calls)
    check(img.u32(0x393C0) == 0x54C9D1BE and img.u32(0x393D0) == 0x54CA07FE and touched(0x3FBEE0, 0x393D4, "W")
          and img.u32(0x393DC) == 0x7CCC0E70 and touched(0x3FBEDF, 0x393E4, "W")
          and dform(img, 0x3947C) == (14, 5, 0, 1) and touched(0x3FBEDF, 0x39484, "W") and touched(0x3FBEE0, 0x3948C, "W"),
          "0x0BA byte0 bit6 -> 0x3FBEE0, bit7 -> 0x3FBEDF (INT 0x393C0..0x393E4); both := 1 on 0x0BA timeout")
    # 0x0B5 bytes 0-3 (signal 0x14) and 0x5C3 bytes 4-7 (signal 0x2D) have no reader; every read-API call has a constant signal
    egs_rd = [r.get(3) for p, t, r in calls if t == 0x63660]
    check(len(egs_rd) >= 37 and None not in egs_rd and 0x14 not in egs_rd and 0x2D not in egs_rd,
          "CAN read API INT 0x63660: all call sites constant; 0x14 (0x0B5 bytes0-3) and 0x2D (0x5C3 bytes4-7) not read via the API")
    # 0x0B5 byte5 bits6-7 != 0 -> 0x3FBEDD
    check(img.u32(0x3975C) == 0x57EC93BE and img.u32(0x39760) == 0x558607BE and touched(0x3FBEDD, 0x39774, "W"),
          "0x0B5 byte5 bits6-7 (word bits 14-15) != 0 -> 0x3FBEDD")
    # 0x3FBEDD gates a slew-rate limiter: 0x3FB460 is the previous output 0x5B981C, step 0x3FB45E = curve 0x1CF412(0x5B9D20)
    check(touched(0x3FBEDD, 0x463B0) and dform(img, 0x4639C) == (14, 18, 18, -0x4BA0) and touched(0x3FB460, 0x463BC)
          and touched(0x3FB45E, 0x463C4) and img.u32(0x46420) == 0xA3F60000 and img.u32(0x46424) == 0xB3F20000
          and touched(0x5B981C, 0x46390) and call_with(0xF889B0, 0x16CD4, 0x1CF412) and touched(0x3FB45E, 0xF889B8, "W")
          and touched(0x5B9D20, 0xF889AC),
          "0x3FBEDD: 0x5B981C = min(KFPED, prev 0x3FB460 + step 0x3FB45E); 0x3FB460 := 0x5B981C every call; step = curve 0x1CF412(0x5B9D20)")
    check(img.u16(0x1CF412) == 2 and [img.u16(0x1CF414 + 2 * i) for i in range(4)] == [1280, 3840, 164, 32735],
          "step curve 0x1CF412: 2 points, x 1280/3840 -> step 164/32735 (limit only at low x)")
    # misfire-type detector INT 0x23338 second threshold: EE0 -> 0x3FA8A0 (map 0x1C1500), EDF -> 0x3FA89C (0x1C1480), else 0x3FA8A8 (0x1C1400)
    check(touched(0x3FBEE0, 0x23668) and touched(0x3FA8A0, 0x23678) and touched(0x3FA89C, 0x2368C) and touched(0x3FA8A8, 0x23698)
          and call_with(0x5C574, 0x192C8, 0x1C1500) and touched(0x3FA8A0, 0x5C598, "W")
          and call_with(0x5C5B0, 0x192C8, 0x1C1480) and touched(0x3FA89C, 0x5C5D4, "W")
          and call_with(0x5C5EC, 0x192C8, 0x1C1400) and touched(0x3FA8A8, 0x5C610, "W"),
          "INT 0x23338 threshold offset: 0x3FBEE0 -> map 0x1C1500, else 0x3FBEDF -> map 0x1C1480, else map 0x1C1400")
    m_ee0 = [img.u16(0x1C1500 + 2 * i) for i in range(64)]
    m_edf = [img.u16(0x1C1480 + 2 * i) for i in range(64)]
    m_def = [img.u16(0x1C1400 + 2 * i) for i in range(64)]
    check(img.u8(0x1C1228) == 8 and m_ee0 != m_def and m_edf != m_def and m_ee0 != m_edf
          and any(a > b for a, b in zip(m_ee0, m_def)) and any(a < b for a, b in zip(m_ee0, m_def))
          and any(a < b for a, b in zip(m_edf, m_def)),
          "maps 0x1C1500/0x1C1480/0x1C1400 (8x8 u16) all differ; EE0/EDF maps are neither uniformly higher nor lower")
    # first stage of 0x23338: EDF/default threshold maps 0xFFFF and the three factor maps identical -> no bit effect
    check(all(img.u16(a + 2 * i) == 0xFFFF for a in (0x1C1680, 0x1C1600) for i in range(64))
          and [img.u8(0x1C1700 + i) for i in range(64)] == [img.u8(0x1C1740 + i) for i in range(64)] == [img.u8(0x1C1780 + i) for i in range(64)]
          and call_with(0x5C788, 0x192C8, 0x1C1680) and call_with(0x5C7D4, 0x192C8, 0x1C1600),
          "INT 0x23338 first stage: EDF/default maps 0x1C1680/0x1C1600 all 0xFFFF; factor maps 0x1C1700/40/80 identical")
    # INT 0x23734: 0x3FC239 -> map 0x1C19B4 (all 0xFFFF), EE0 -> 0x1C1934, EDF -> 0x1C18B4, else 0x1C1834
    check(touched(0x3FC239, 0x23890) and touched(0x3FBEE0, 0x238C8) and touched(0x3FBEDF, 0x23900)
          and call_with(0x5C880, 0x192C8, 0x1C19B4) and call_with(0x5C8D4, 0x192C8, 0x1C1934)
          and call_with(0x5C910, 0x192C8, 0x1C18B4) and call_with(0x5C94C, 0x192C8, 0x1C1834)
          and all(img.u16(0x1C19B4 + 2 * i) == 0xFFFF for i in range(64)),
          "INT 0x23734 threshold: 0x3FC239 -> 0x1C19B4 (all 0xFFFF = blanking), 0x3FBEE0 -> 0x1C1934, 0x3FBEDF -> 0x1C18B4, else 0x1C1834")
    # INT 0x5C99C: EDF/EE0 edge events gated by CAL 0x1C1AC8 bits 0/1, both clear
    check(is_r2_ref(img, 0x5C9D0, 0x1C1AC8) and img.u32(0x5C9D4) == 0x558C07FE and touched(0x3FBEDF, 0x5C9E4)
          and is_r2_ref(img, 0x5CA40, 0x1C1AC8) and img.u32(0x5CA44) == 0x558CFFFE and touched(0x3FBEE0, 0x5CA54)
          and img.u8(0x1C1AC8) & 3 == 0 and touched(0x5B8E8D, 0x5CC64, "W"),
          "INT 0x5C99C: 0x3FBEDF/0x3FBEE0 edge events into 0x5B8E8D enabled by CAL 0x1C1AC8 bit0/bit1 = 0 (inactive)")
    # INT 0x4533C (anti-jerk observer): any change of 0x3FBEE0/0x3FBEDF vs stored copies 0x3FB41F/0x3FB41E -> reset
    check(dform(img, 0x4577C) == (14, 4, 4, -0x4120) and dform(img, 0x45790) == (14, 3, 3, -0x4121)
          and dform(img, 0x45788) == (14, 23, 23, -0x4BE1) and dform(img, 0x4579C) == (14, 26, 26, -0x4BE2)
          and touched(0x3FB41F, 0x457F0) and img.u32(0x4594C) == 0x89980000 and img.u32(0x45950) == 0x999A0000
          and img.u32(0x45954) == 0x89750000 and img.u32(0x45958) == 0x99770000 and touched(0x3FC182, 0x45868, "W"),
          "INT 0x4533C: edge of 0x3FBEE0 or 0x3FBEDF (vs 0x3FB41F/0x3FB41E) -> observer reset 0x3FC182 := 1")
    # EXT 0xFA4628: 0x3FBEDF selects per-gear vs constant parameter tables; output gain 0x5B93CF tables zero with EGS present
    check(touched(0x3FBED1, 0xFA4648) and touched(0x3FBEDF, 0xFA46A4) and touched(0x5B93CF, 0xFA46F4, "W") and touched(0x5B93CF, 0xFA4740, "W")
          and all(img.u8(0x1CF300 + i) == 0 and img.u8(0x1CF308 + i) == 0 for i in range(7))
          and [img.u16(0x1CF34E + 2 * i) for i in range(7)] == [0] + [135] * 6
          and touched(0x5B93CF, 0x317D4) and img.u32(0x317DC) == 0x7FEB51D6 and touched(0x5B97C2, 0x31838, "W"),
          "EXT 0xFA4628: 0x3FBEDF -> gear-independent table 0x1CF34E; gain 0x5B93CF (0x1CF300/0x1CF308) = 0 with EGS -> 0x5B97C2 output 0")
    # 0x0B5 byte4 bits6/7 (exactly one) -> 0x5BBAC7.2 -> coolant target 0x5B91D1 := CAL 0x1D08FB (177)
    check(touched(0x3FBEDB, 0xF9E384) and touched(0x3FBEDC, 0xF9E394) and touched(0x5BBAC7, 0xF9E3F4)
          and touched(0x5B91D1, 0xF9E410, "W") and img.u8(0x1D08FB) == 177 and img.u16(0x1D08FE) & 1 == 1,
          "0x0B5 byte4 bit6 XOR bit7 -> 0x5BBAC7.2 -> coolant target 0x5B91D1 = CAL 0x1D08FB (177); default when invalid = 1")
    # ===== final pass: torque CAN, EGS/DSC decode, arbitration =====
    # --- torque topic (proposed): CAN torque scaling, EGS/DSC decode, arbitration ---------------
    # CAN torque scale: 0x5B922A := CAL 0x1C1150 (stock 0x24); RX factor 0x5B94B6 := 0x800 / CAL 0x1C1150
    check(is_r2_ref(img, 0xF3C578, 0x1C1150) and touched(0x5B922A, 0xF3C57C, "W")
          and dform(img, 0xF3C5A4) == (14, 11, 0, 0x800) and is_r2_ref(img, 0xF3C5A8, 0x1C1150)
          and touched(0x5B94B6, 0xF3C5B0, "W"),
          "torque CAN scale: 0x5B922A = CAL 0x1C1150 (TX); 0x5B94B6 = 0x800 / CAL 0x1C1150 (RX inverse) in EXT fn 0xF3C574")
    # TX converter INT 0x4BCCC: ((T>>1)-(ref>>1)) * 0x5B922A >> 10, clamp to s12
    check(touched(0x5B94BC, 0x4BCD0) and touched(0x5B922A, 0x4BD10) and img.u32(0x4BD18) == 0x7C845670
          and dform(img, 0x4BD1C) == (11, 0, 4, -0x800) and dform(img, 0x4BD2C) == (11, 0, 4, 0x7FF),
          "TX torque converter INT 0x4BCCC: ((T>>1)-(0x5B94BC>>1))*0x5B922A>>10, clamped to -0x800..0x7FF")
    # 0x4BDDC: reference = loss torque 0x5B97AA; conv(0) -> 0x5B94D0 (0x0A9 bits 16-27 = -loss)
    check(touched(0x5B97AA, 0x4BE20) and touched(0x5B94BC, 0x4BE24, "W") and dform(img, 0x4BE78) == (14, 3, 0, 0)
          and any(p == 0x4BE7C and t == 0x4BCCC for p, t, _ in calls) and touched(0x5B94D0, 0x4BE84, "W"),
          "INT 0x4BDDC: reference 0x5B94BC := 0x5B97AA and word 0x5B94D0 = conv(0) = -(loss torque)")
    check(any(p == 0x4BE90 and t == 0x4BD40 for p, t, _ in calls) and touched(0x5B983A, 0x4BE4C)
          and touched(0x5B9784, 0x4BD84),
          "0x5B983A (actual torque) is the only word converted by INT 0x4BD40 (adds signed 0x5B9784)")
    # loss torque producer INT 0x60654
    check(call_with(0x60680, 0x17B64, 0x1C789A) and touched(0x3FC302, 0x60678) and touched(0x5B97AE, 0x607E0)
          and touched(0x5B97AA, 0x607F4, "W"),
          "loss torque 0x5B97AA (INT 0x60654) = map 0x1C789A(rpm, rel. charge 0x3FC302) + further addends incl. 0x5B97AE")
    # actual torque 0x5B983A = 0x5B97E0 * ignition efficiency * firing fraction (INT 0x4790C)
    check(touched(0x5B92EC, 0x47928) and dform(img, 0x4792C) == (7, 11, 11, 200) and touched(0x3FC2EF, 0x47940)
          and touched(0x5B97E0, 0x47A50) and touched(0x5B983A, 0x47A98, "W"),
          "INT 0x4790C: 0x5B983A = 0x5B97E0 x eta(ign. retard 0x5B93DC-0x3FC2EF) x (200-cut*25)/200")
    # 0x0B6 (DSC) raw decode EXT 0xF1241C: RX buffer handle 0x0C, checksum seed 0xB6
    check(msgs.get(0x0C, {}).get("can_id") == 0x0B6 and touched(0x3FAE9C, 0xF1252C)
          and dform(img, 0xF12530) == (34, 12, 28, 0x0C * 0x14) and dform(img, 0xF12770) == (14, 12, 12, 0xB6)
          and touched(0x3FA046, 0xF125D0, "W") and touched(0x3FA044, 0xF12640, "W") and touched(0x3FA042, 0xF12658, "W"),
          "0x0B6 decoded from raw RX buffer (handle 0x0C) in EXT 0xF1241C: s12 bits12-23 -> 0x3FA046, bits24-35 -> 0x3FA044, mode -> 0x3FA042, checksum seed 0xB6")
    # 0x0B5 (EGS) raw decode EXT 0xF15450: handle 0x0B, checksum seed 0xB5
    check(msgs.get(0x0B, {}).get("can_id") == 0x0B5 and dform(img, 0xF15550) == (34, 12, 29, 0x0B * 0x14)
          and dform(img, 0xF15824) == (14, 12, 12, 0xB5) and touched(0x3FA04E, 0xF155F0, "W")
          and touched(0x3FA04C, 0xF15660, "W") and touched(0x3FA048, 0xF1567C, "W"),
          "0x0B5 bytes 0-7 decoded from raw RX buffer (handle 0x0B) in EXT 0xF15450: s12 bits12-23 -> 0x3FA04E, bits24-35 -> 0x3FA04C, mode -> 0x3FA048")
    # EGS mode 2 -> reduction limit 0x5B94A4 = raw*0x5B94B6 + 0x5B94BC; mode 1 -> increase flag 0x3FBEB8
    check(dform(img, 0x4AA34) == (11, 0, 24, 2) and touched(0x3FA04E, 0x4AA40) and touched(0x5B94B6, 0x4A9EC)
          and touched(0x5B94BC, 0x4A9F8) and dform(img, 0x4AB9C) == (11, 0, 24, 1) and touched(0x3FBEB8, 0x4ABA8, "W"),
          "INT 0x4A700: EGS mode 2 -> torque limit 0x5B94A4 = 0x3FA04E*0x5B94B6+0x5B94BC; mode 1 -> 0x3FBEB8")
    check(touched(0x3FBEB8, 0x48670) and touched(0x3FC19F, 0x48634, "addr") and img.u32(0x48698) == 0x98E60000,
          "EGS torque-increase flag 0x3FBEB8 blocks the all-cylinder overrun cut 0x3FC19F (INT 0x484F8)")
    # DSC: mode 1/2 flags, ASC limit 0x5B949A from 0x0B6 via inverse converter
    check(touched(0x3FA042, 0xFB5E68) and touched(0x3FBEB4, 0xFB5E78, "W") and touched(0x3FBEB3, 0xFB5E88, "W")
          and touched(0x5B94B6, 0xFB5EB8) and touched(0x5B94BC, 0xFB5EB0) and touched(0x5B949A, 0xFB609C, "W"),
          "EXT 0xFB5B78: 0x0B6 mode -> 0x3FBEB4 (=1) / 0x3FBEB3 (=2); torque raw*0x5B94B6+0x5B94BC -> 0x5B949A/0x5B949E")
    # fast-path arbitration INT 0x47AB0
    check(touched(0x5B9832, 0x47B98) and touched(0x5B9870, 0x47BB4) and touched(0x5B983E, 0x47C00, "W")
          and touched(0x5B94A0, 0x47C08) and touched(0x5B94A8, 0x47C3C) and touched(0x5B9846, 0x47C60, "W")
          and touched(0x5B949A, 0x47C70) and touched(0x3FC195, 0x47C8C, "W"),
          "INT 0x47AB0: min(request, 0x5B9832, rev limit 0x5B9870, ext. limit) -> 0x5B983E; max(.., 0x5B94A0, 0x5B94A8) -> 0x5B9846; 0x3FC195 from DSC 0x5B949A")
    # rev limiter INT 0x48B04 (6500 rpm normal limit, 0.25 rpm/bit)
    check(is_r2_ref(img, 0x48B6C, 0x1C8B32) and is_r2_ref(img, 0x48BB0, 0x1C8B30) and is_r2_ref(img, 0x48BB8, 0x1C8B2E)
          and img.u16(0x1C8B2E) == 26000 and touched(0x5B9870, 0x48C5C, "W") and touched(0x3FC1A3, 0x48C68, "W"),
          "rev limiter INT 0x48B04: limit CAL 0x1C8B2E (26000 = 6500 rpm) / 0x1C8B30 / 0x1C8B32 -> torque limit 0x5B9870, active flag 0x3FC1A3")
    # ignition intervention INT 0x32EE8
    check(touched(0x3FC32A, 0x32F44) and touched(0x5B985C, 0x33014) and is_r2_ref(img, 0x3327C, 0x1CAB68)
          and touched(0x5B9434, 0x33334, "W"),
          "INT 0x32EE8: ignition reduction from target 0x3FC32A (floored at 0x5B985C) -> torque-based ignition angle 0x5B9434")
    # slow (air) path INT 0x480AC; EGS limit enters via 0x5B9834 (EXT 0xFA488C)
    check(touched(0x5B94A2, 0xFA4938) and touched(0x5B9834, 0xFA493C, "W") and touched(0x5B9834, 0x48424)
          and touched(0x5B949A, 0x4842C) and touched(0x5B9852, 0x484E0, "W"),
          "slow path: EGS 0x5B94A2 -> 0x5B9834 (EXT 0xFA488C); INT 0x480AC 0x5B9852 = min(.., 0x5B9834, DSC 0x5B949A, ..)")
    check(img.u8(0x1C8A18) & 3 == 1 and img.u32(0x48640) == 0x556B07BC,
          "AEVAB enable control word CAL 0x1C8A18 = bit0 set (0x3FC195 enables cut), bit1 clear (0x3FC162 does not)")
    # ===== final pass: Valvetronic / VANOS =====
    # --- valvetronic_vanos final pass ------------------------------------------
    # Valvetronic: CAN frame layout (one u16 request per frame, bytes 2-3 of signal 0x36/0x38)
    check(img.u32(0x4FE10) == 0x57EC801E and img.u32(0x4FE14) == 0x7CCC6378 and img.u32(0x4FF84) == 0x57EB801E
          and any(p == 0x4FE50 and t2 == 0x63C3C and r.get(3) == 0x37 for p, t2, r in calls)
          and any(p == 0x4FFC0 and t2 == 0x63C3C and r.get(3) == 0x39 for p, t2, r in calls),
          "Valvetronic frames 0x105/0x10D: request u16 packed into bits 16-31 of signal 0x36/0x38; 0x37/0x39 carry status byte only")
    check(img.u32(0x500DC) == 0x1F6A06E9 and touched(0x5B8AEA, 0x500E8) and touched(0x5B9D16, 0x50104, "W")
          and img.u32(0x504B4) == 0x1D0A06E9 and touched(0x5B8AEC, 0x504C0) and touched(0x5B9D14, 0x504DC, "W"),
          "Valvetronic feedback: CAN 0x185 raw*0x6E9>>16 - trim 0x5B8AEA -> 0x5B9D16; CAN 0x18D - trim 0x5B8AEC -> 0x5B9D14")
    check(img.u32(0x50274) == 0x392006E9 and touched(0x5B9D16, 0x50278, "W") and img.u32(0x50330) == 0x396006E9
          and touched(0x5B9D16, 0x50334, "W") and img.u32(0x5064C) == 0x392006E9 and touched(0x5B9D14, 0x50650, "W"),
          "Valvetronic feedback substitute on timeout/invalid: actual := 0x6E9 (full-range value) per bank")
    check(any(p == 0x4EC14 and t2 == 0x16CD4 for p, t2, r in calls) and is_r2_ref(img, 0x4EC10, 0x1C50BE)
          and touched(0x5B9BB4, 0x4EC40, "W") and img.u32(0x4ECC0) == 0x2C1F09F6 and img.u32(0x4ECD4) == 0x3980000A,
          "lift target (0x5B9BB0) -> curve CAL 0x1C50BE -> request units 0x5B9BB4; 0x5B9047 = value/10 (0xFF above 2550)")
    check(img.u16(0x1C50BE) == 12 and img.u16(0x1C50BE + 2) == 130 and img.u16(0x1C50BE + 24) == 9600
          and img.u16(0x1C50BE + 26) == 36 and img.u16(0x1C50BE + 48) == 1740,
          "curve CAL 0x1C50BE: x 130..9600 (lift, um) -> y 36..1740 (request units, max 0x6EA=1770)")
    check(touched(0x3FC1BD, 0x4E3F8) and is_r2_ref(img, 0x4E404, 0x1C503A) and touched(0x3FC1C2, 0x4E420)
          and is_r2_ref(img, 0x4E42C, 0x1C51A6) and touched(0x5B8F26, 0x4E438) and is_r2_ref(img, 0x4E454, 0x1C507C),
          "lift target priority in INT 0x4E21C: 0x3FC1BD -> pedal curve 0x1C503A; 0x3FC1C2 -> fixed CAL 0x1C51A6; 0x5B8F26 -> rpm curve 0x1C507C")
    check(is_r2_ref(img, 0x4E4F4, 0x1C4D3C) and is_r2_ref(img, 0x4E50C, 0x1C4C98) and is_r2_ref(img, 0x4E538, 0x1C4A2C)
          and is_r2_ref(img, 0x4E54C, 0x1C4B62) and img.u32(0x4E560) == 0x7D8C59D6 and is_r2_ref(img, 0x4E57C, 0x1C47E8),
          "INT 0x4E21C mode 0x5B8ED6: start maps 0x1C4D3C/0x1C4C98, idle maps 0x1C4A2C/0x1C4B62 blended by 0x5B9048; else main map 0x1C47E8")
    check(is_r2_ref(img, 0xFB5164, 0x1C51A8) and touched(0x5B9BB0, 0xFB516C, "W") and touched(0x3FE954, 0xFB5110)
          and is_r2_ref(img, 0x4EAFC, 0x1C51A8),
          "engine-not-running / rpm=0 lift target = CAL 0x1C51A8 (EXT 0xFB50E4, INT 0x4EAFC)")
    check(touched(0x5B9BB0, 0xF884A4) and img.u32(0xF88710) == 0x2C1F0000 and touched(0x5B8AEA, 0xF8871C, "W")
          and img.u32(0xF88734) == 0x7D7F00D0 and touched(0x5B8AEC, 0xF88738, "W"),
          "bank balance EXT 0xF88494: one signed value per lift range -> positive to trim 0x5B8AEA, negative (negated) to 0x5B8AEC")
    # VANOS
    check(img.u32(0x3F68C) == 0x2C0C1C20 and is_r2_ref(img, 0x3F72C, 0x1CA870) and img.u32(0x3F750) == 0x2C0B0708
          and img.u32(0x3F75C) == 0x6063F8F8 and img.u32(0x3F79C) == 0x2C0B0003,
          "cam angle fetch INT 0x3F60C: raw <= 7200, minus CAL 0x1CA870[i], reduced modulo 1800 (edge index 0..3)")
    check(img.u32(0x3F53C) == 0x546B07FE and is_r2_ref(img, 0x3F548, 0x1CA878) and img.u32(0x3F554) == 0x7C646050
          and img.u32(0x3F56C) == 0x7C646214 and img.u32(0x3F588) == 0x7C0B5000,
          "INT 0x3F3B8: odd objects position = CAL 0x1CA878[i] - delta, even = delta + CAL 0x1CA878[i]; clamped to 0x1CA878[i]")
    check(is_r2_ref(img, 0xF2D27C, 0x1C6DA2) and img.u32(0xF2D284) == 0x1D4A000A and img.u32(0xF2D2BC) == 0x2C091C20
          and [img.u16(0x1C6DA2 + 2 * i) for i in range(4)] == [1320, 720, 1320, 720],
          "cam edge plausibility windows EXT 0xF2D274: CAL 0x1C6DA2[i] -/+ 10*byte, wrap at 7200; nominal 1320/720/1320/720")
    check(touched(0x5B8DA6, 0xFACDE4) and touched(0x5B8DCA, 0xFACE08) and img.u32(0xFACE0C) == 0x7FCADA14 and touched(0x5B9B04, 0xFACE10, "W")
          and touched(0x5B8D92, 0xFACE98) and touched(0x5B8DB6, 0xFACEBC) and img.u32(0xFACEC0) == 0x7F89F214 and touched(0x5B9B02, 0xFACEC4, "W"),
          "air model EXT 0xFACD74 sums measured positions per pair: obj0+obj1 -> 0x5B9B04, obj2+obj3 -> 0x5B9B02")
    check(touched(0x5B8DCA, 0x4E5D4) and touched(0x5B8DCC, 0x4E5E8) and touched(0x5B9BCC, 0x4E5D8, "W")
          and touched(0x5B9E02, 0x3E3A8, "W") and touched(0x5B9E02, 0x4E628) and is_r2_ref(img, 0x4E6D4, 0x1C652E),
          "Valvetronic fn INT 0x4E21C uses only type-A cam position (obj0 measured/target or 0x5B9E02) with lift curve 0x1C652E")
    check(img.u32(0x3E688) == 0x3BA00384 and img.u32(0x3EE4C) == 0x3A600384 and touched(0x3FE954, 0x3E5EC) and touched(0x5B8D7A, 0x3E608),
          "VANOS target composer: default/park request 0x384 for both target bytes when engine not running, before start end, very cold or in start delay")
    # ===== final pass: ignition / knock =====
    # --- ignition / knock structure (CONFIRMED items only) -------------------
    # base/alternate maps in INT fn 0x49600
    check(is_r2_ref(img, 0x49794, 0x1CAD5A) and touched(0x5B9001, 0x4978C) and touched(0x3FC2F5, 0x49790)
          and is_r2_ref(img, 0x4980C, 0x1CB186) and is_r2_ref(img, 0x49834, 0x1CAF04) and touched(0x5B8872, 0x497E8),
          "ign: map A 0x1CAD5A(rpm 0x5B9001, filtered load 0x3FC2F5); B = 0x5B8872 ? 0x1CB186 : 0x1CAF04")
    check(touched(0x5B903C, 0x4984C) and img.u32(0x49850) == 0x7E7351D6 and img.u32(0x49854) == 0x7E7A4670
          and touched(0x5B9453, 0x49874, "W") and touched(0x5B9452, 0x499C0, "W"),
          "ign: 0x5B9453/0x5B9452 = A + (B-A)*0x5B903C>>8 (predicted-load / actual-load variants)")
    check(touched(0x5B8F26, 0x4989C) and is_r2_ref(img, 0x498A8, 0x1CB384) and is_r2_ref(img, 0x49944, 0x1CB414)
          and any(p == 0x498C0 and t == 0x19234 for p, t, r in calls),
          "ign: full-load flag 0x5B8F26 selects 24x6 maps 0x1CB384/0x1CB414 (pre-searched axes, helper 0x19234)")
    check(touched(0x3FC0F4, 0x49BDC) and touched(0x3FC0DC, 0x49BEC) and touched(0x5B9459, 0x49C00)
          and touched(0x5B9454, 0x49C04, "W") and is_r2_ref(img, 0x49F60, 0x1CB644) and is_r2_ref(img, 0x49EF8, 0x1CB4C4),
          "ign: 0x3FC0F4 && 0x3FC0DC -> 0x5B9454 = 0x5B9459 (maps 0x1CB644 + 0x1CB4C4*k/128, fn 0x49E94)")
    check(touched(0x5B93D4, 0x49E24) and touched(0x5B93D5, 0x49E34) and is_r2_ref(img, 0x49DEC, 0x1CB4B9)
          and touched(0x5B9454, 0x49E7C, "W") and img.u32(0x49E1C) == 0x7C723E70,
          "ign: 0x5B9454 = sat(base + 0x5B93D4 + 0x5B93D5 + curve 0x1CB4B9(IAT)*map 0x1D0664>>7)")
    # final per-cylinder sum and output limits
    check(touched(0x5B9454, 0x333DC) and touched(0x5B9462, 0x333E8) and is_r2_ref(img, 0x333F8, 0x1CABAB)
          and touched(0x3FC2D9, 0x33408) and img.u32(0x3340C) == 0x7CAA5850 and touched(0x5B9360, 0x33458, "addr"),
          "ign: INT 0x333CC Z = 0x5B9454 + 0x5B9462 + 0x5B940B + CAL 0x1CABAB - 0x3FC2D9 + 0x5B9360[cyl]")
    check(touched(0x3FC169, 0x33428) and touched(0x5B9461, 0x33438),
          "ign: 0x3FC169 == 0 -> Z = start angle 0x5B9461 + 0x5B940B + CAL 0x1CABAB")
    check(touched(0x5B9460, 0x33924) and touched(0x5B9434, 0x33930) and dform(img, 0x33710)[0] == 11
          and dform(img, 0x33710)[3] == 0x48 and dform(img, 0x33724)[3] == -0x20 and touched(0x5B9438, 0x336DC),
          "ign: applied = min(Z, max(0x5B9434, 0x5B9460)); 0x5B9440[] = clamp(applied + 0x5B9438, -0x20, +0x48)")
    check(touched(0x3FC19F, 0x33688) and touched(0x3FC282, 0x33698, "W") and touched(0x5B9460, 0x336CC)
          and touched(0x3FC282, 0x495F8, "W") and touched(0x5B92EC, 0x495E4),
          "ign: overrun cut 0x3FC19F latches 0x3FC282 -> all angles = 0x5B9460; released when cut ends and 0x5B92EC < 8")
    check(touched(0x5B9440, 0x30CD8) and img.u32(0x30CE4) == 0x1D6B000F and img.u32(0x30CE8) == 0x7D6B0E70,
          "ign: output scheduler converts angle byte x15/2 (0.1 deg units) -> 0.75 deg/bit")
    # torque model: forward efficiency and inverse (intervention) path
    check(touched(0x5B93DC, 0x4A660) and touched(0x5B9460, 0x4A44C, "addr") and is_r2_ref(img, 0x4A6A0, 0x1C7DC4)
          and touched(0x5B8B1C, 0x4A6B4) and img.u32(0x4A6E4) == 0x217B00C8 and touched(0x3FC2F9, 0x4A6E8, "W"),
          "tq: 0x3FC2F9 = 200 - table 0x1C7DC4[0x5B93DC - 0x5B9460] * 0x5B8B1C >> 5 (efficiency at latest angle)")
    check(touched(0x3FC32A, 0x32F44) and touched(0x5B97DA, 0x32F4C) and is_r2_ref(img, 0x3327C, 0x1CAB68)
          and is_r2_ref(img, 0x332E0, 0x1CAA9C) and touched(0x5B93DC, 0x33308) and touched(0x5B9434, 0x33334, "W"),
          "tq: intervention angle 0x5B9434 = 0x5B93DC - inverse-efficiency(0x1CAB68 / 0x1CAA9C) of required ratio")
    # knock control
    check(dform(img, 0x37498) == (14, 11, 11, -0x244C) and img.u32(0x37304) == 0x558C1838 and img.u32(0x37310) == 0x1D6B0028
          and img.u32(0x3732C) == 0x3B2000A0 and touched(0x3FC18B, 0x37320) and dform(img, 0x44E58)[3] == 0xA8,
          "knock: adaptation table 0x3FDBB4[0xA8], cell offset 0x5B936F*8 + 0x5B936E*40 (0xA0 when 0x3FC18B)")
    check(touched(0x3FC101, 0x374C8) and touched(0x5B9369, 0x37740) and touched(0x5B936A, 0x37790)
          and touched(0x3FC0F4, 0x37450) and img.u32(0x37B2C) == 0x7ECC00D0 and touched(0x5B935C, 0x37B34, "W"),
          "knock: retard += step 0x5B9369 on knock 0x3FC101, capped 0x5B936A; 0x5B9360[cyl] = -retard")
    check(touched(0x3FC0ED, 0x36EB0) and is_r2_ref(img, 0x371E8, 0x1C71A5) and is_r2_ref(img, 0x37210, 0x1C71A7)
          and touched(0x3FC2D9, 0x371E0, "W") and touched(0x5B8DE0, 0x37090),
          "knock: dynamic retard 0x3FC2D9 decays by CAL 0x1C71A5 every CAL 0x1C71A7 cycles; phase flag from 0x5B8DE0")
    check(img.u32(0xF31D7C) == 0x39292586 and img.u32(0xF31D78) == 0x54692834 and touched(0x5B9306, 0xF31D5C, "W"),
          "temp: 0x5B96DA = 0x5B9306*32 + 0x2586 (Kelvin*128/3) -> 0x5B9306 is 0.75 degC/bit, -48 degC offset")
    # ===== final pass: lambda architecture =====
    # --- lambda architecture (topic: lambda) ---------------------------------
    # arbitration INT 0x1A5E4 (called from INT 0x5563C / EXT 0xF7E340)
    check(touched(0x5B9C2E, 0x1A5E8) and touched(0x5B891A, 0x1A5F0) and img.u32(0x1A5F4) == 0x7C074000
          and img.u32(0x1A5F8) == 0x4080000C and img.u32(0x1A5FC) == 0x7CE83B78,
          "lambda arbitration INT 0x1A5E4: bank-A rich request = min(full-load 0x5B891A, protection 0x5B9C2E)")
    check(touched(0x5B9C2C, 0x1A778) and img.u32(0x1A77C) == 0x7C074000 and img.u32(0x1A788) == 0x7D074378,
          "bank-B rich request = min(full-load 0x5B891A, protection 0x5B9C2C)")
    check(dform(img, 0x1A6CC) == (11, 0, 4, 0x1000) and img.u32(0x1A6D4) == 0x7C044800
          and touched(0x5B96B4, 0x1A6E0, "W") and touched(0x5B96B4, 0x1A6EC, "W") and touched(0x5B96B4, 0x1A6F8, "W"),
          "0x5B96B4 = base request if rich request == 0x1000, else min(rich request, base request) (richest wins)")
    check(dform(img, 0x1A814) == (11, 0, 8, 0x1000) and touched(0x5B96A2, 0x1A828, "W") and touched(0x5B96A2, 0x1A840, "W"),
          "bank-B 0x5B96A2: same min rule with 0x1000 = 'no request'")
    check(touched(0x5B968C, 0x1A60C) and dform(img, 0x1A610) == (11, 0, 10, 0x1000) and touched(0x3FC03B, 0x1A630, "W")
          and touched(0x5B969C, 0x1A6C8) and touched(0x5B8D1E, 0x1A654) and touched(0x5B96A0, 0x1A688),
          "base request bank A: excitation 0x5B8D1E / purge-bank 0x5B96A0 / warm-up 0x5B968C (if != 1.0) / diagnostic 0x5B969C")
    # coordinator INT 0x5563C
    check(touched(0x3FBFFE, 0x55710) and touched(0x3FBFFF, 0x55718) and touched(0x5B891E, 0x5573C)
          and touched(0x5B891E, 0x55874) and touched(0x5B96B2, 0x55744, "W") and touched(0x5B96B0, 0x5587C, "W"),
          "cut setpoint 0x5B891E replaces the base setpoint of BOTH banks (0x5B96B2/0x5B96B0) if either bank flag is set")
    check(touched(0x5B891C, 0x55760) and touched(0x3FC036, 0x55788, "W") and touched(0x5B891D, 0x55794)
          and touched(0x5B96A6, 0x557B8, "W") and touched(0x5B96A4, 0x558E4, "W"),
          "setpoint clamped to [0x5B891C<<5, 0x5B891D<<5] -> feed-forward setpoints 0x5B96A6 / 0x5B96A4")
    # fuel: per-bank feed-forward divisor and controller factor
    check(touched(0x5B96A6, 0x2EB70) and any(p == 0x2EB74 and t2 == 0x15E58 for p, t2, r in calls) and touched(0x5B98B0, 0x2EB80)
          and touched(0x5B96BE, 0x2EBD4) and touched(0x5B96A4, 0x2ECAC) and touched(0x5B98A0, 0x2ECBC) and touched(0x5B96BA, 0x2ED08),
          "fuel INT 0x2E9E4: path A load/0x5B96A6 x 0x5B98B0 x 0x5B96BE; path B load/0x5B96A4 x 0x5B98A0 x 0x5B96BA")
    # codeword CAL 0x1C947C
    check(is_r2_ref(img, 0x58F78, 0x1C947C) and img.u32(0x58F7C) == 0x558C07FE and touched(0x3FC1EE, 0x58F9C, "W")
          and is_r2_ref(img, 0x58FE0, 0x1C947C) and img.u32(0x58FE4) == 0x558C07BC and touched(0x3FC1EF, 0x5906C, "W"),
          "CAL 0x1C947C bit0 / bit1 are required for lambda release 0x3FC1EE (bank A) / 0x3FC1EF (bank B)")
    check(is_r2_ref(img, 0x570F4, 0x1C947C) and img.u32(0x570F8) == 0x558C077A and img.u32(0x57100) == 0x4082000C
          and dform(img, 0x5710C) == (14, 30, 0, 1) and touched(0x3FC1E3, 0x57118, "W"),
          "CAL 0x1C947C bit2 forces 0x3FC1E3 = 1 regardless of release/setpoint conditions (stock 0x1B: bit2 clear)")
    check(touched(0x3FC1E3, 0x57D88) and touched(0x5B98AA, 0x57D9C) and touched(0x5B98B0, 0x57DD0, "W")
          and touched(0x3FC1E4, 0x57E78, "W") and touched(0x5B9896, 0x57F10) and touched(0x5B98A0, 0x57F4C, "W"),
          "0x3FC1E3/0x3FC1E4 only gate adding the modulation term to the factor (0x5B98AA->0x5B98B0, 0x5B98A2->0x5B98A0)")
    check(is_r2_ref(img, 0x590F8, 0x1C947C) and img.u32(0x590FC) == 0x556B0738 and is_r2_ref(img, 0x59110, 0x1C9986)
          and touched(0x5B96A8, 0x59120) and touched(0x3FC1F2, 0x59138, "W") and touched(0x3FC1F2, 0x57058)
          and img.u32(0x57068) == 0x558C0738 and touched(0x3FC1D7, 0x57088, "W"),
          "CAL 0x1C947C bit3: setpoint < CAL 0x1C9986 (lambda 0.90) -> 0x3FC1F2 -> integrator reset 0x3FC1D7 (edge unless bit6)")
    check(touched(0x5B96AA, 0x590A0) and is_r2_ref(img, 0x590A4, 0x1C9986) and touched(0x3FC1E7, 0x590B8, "W")
          and img.u16(0x1C9986) == 0x0E67,
          "adaptation enable 0x3FC1E7 requires release and setpoint 0x5B96AA >= CAL 0x1C9986 (0x0E67 = lambda 0.90); no upper bound")
    check(touched(0x5B970A, 0x5716C) and touched(0x5B96A6, 0x57280) and any(p == 0x5728C and t2 == 0x16154 for p, t2, r in calls)
          and img.u32(0x57360) == 0x7E7BE850 and any(p == 0x57398 and t2 == 0x1DDE0 for p, t2, r in calls),
          "controller error = (measured' - delayed feed-forward setpoint 0x5B96A6) / setpoint (bank A uses measured 0x5B970A)")
    # requests
    check(call_with(0xF7E26C, 0x16AE4, 0x1CE1D8) and touched(0x5B8F26, 0xF7E244) and call_with(0xF7E298, 0x179E8, 0x1CE1BC)
          and touched(0x5B891A, 0xF7E2F8, "W"),
          "full-load request 0x5B891A = min(curve 0x1CE1D8(rpm) if full-load flag 0x5B8F26, map 0x1CE1BC(rpm, load)) x32")
    check(touched(0x5B891A, 0xF7C75C) and call_with(0xF7C748, 0x16CD4, 0x1C5720) and touched(0x5B9C2E, 0xF7C82C, "W")
          and dform(img, 0xF7C870) == (14, 26, 0, 0x1000),
          "protection request 0x5B9C2E = blend of 0x5B891A toward protection target with weight curve 0x1C5720; 0x1000 when inactive")
    check(touched(0x5B9307, 0xF48E8C) and touched(0x5B9F74, 0xF48EA0, "W") and touched(0x5B9F74, 0xF7E5E8)
          and touched(0x5B891C, 0xF7E61C, "W") and touched(0x5B891D, 0xF7E574, "W"),
          "rich/lean limits 0x5B891C/0x5B891D: curves 0x1CE20C/0x1CE21C on engine-temperature axis index 0x5B9F74")
    # ===== final pass: overrun / generator =====
    # --- DFCO / overrun state machine (topic dfco_generator) -------------------
    check(touched(0x3FC162, 0xFAE51C, "addr") and dform(img, 0xFAE918) == (38, 12, 30, 0)
          and dform(img, 0xFAE928) == (38, 12, 30, 0) and touched(0x3FC060, 0xFAE904, "R"),
          "DFCO request 0x3FC162 written by EXT 0xFAE33C (stb via r30 at 0xFAE918/0xFAE928; bit6/bit7 of 0x3FB351 selected by 0x3FC060)")
    check(call_with(0xF57F98, 0x191B0, 0x1CEFD0) and call_with(0xF57FB8, 0x191B0, 0x1CEFF8)
          and touched(0x3FB355, 0xF57FA0, "W") and touched(0x3FB35B, 0xF57FC0, "W")
          and touched(0x3FB355, 0xFAE8B8, "R") and touched(0x3FB354, 0xFAE8BC, "W"),
          "DFCO entry delays: byte maps 0x1CEFD0/0x1CEFF8 -> reload values 0x3FB355/0x3FB35B of counters 0x3FB354/0x3FB35A")
    check(touched(0x5B9EE8, 0x5C218, "W") and call_with(0x5C214, 0x196C8, 0x1C1240)
          and call_with(0xF48DFC, 0x196C8, 0x1CC458) and touched(0x5B9307, 0xF48DEC, "R"),
          "DFCO delay-map axes: 0x5B9EE8 = rpm byte on axis 0x1C1240, 0x5B9F50 = engine temperature 0x5B9307 on axis 0x1CC458")
    check(is_r2_ref(img, 0xFAE370, 0x1C7434) and touched(0x5B9285, 0xFAE378, "R") and touched(0x5B93B8, 0xFAE38C, "R")
          and touched(0x5B93B6, 0xFAE6A4, "W") and touched(0x5B9001, 0xFAE6AC, "R"),
          "DFCO rpm thresholds: resume 0x5B93B7 = 0x5B93B8 + curve 0x1C7434(0x5B9285); entry 0x5B93B6 compared with rpm byte 0x5B9001")
    check(touched(0x5B93B8, 0xF410CC, "W") and touched(0x1CF020, 0xF41024, "addr") and touched(0x1CF028, 0xF41050, "addr")
          and touched(0x5B903C, 0xF41088, "R") and touched(0x1CF03C, 0xF40FF0, "addr") and touched(0x3FB351, 0xF40FC4, "W"),
          "EXT 0xF40F80: base resume threshold 0x5B93B8 = blend of 0x1CF020/0x1CF028 by 0x5B903C; after-start delay 0x1CF03C sets 0x3FB351 bit0")
    check(touched(0x3FC18B, 0x464B0, "addr") and is_r2_ref(img, 0x46468, 0x1C8910) and is_r2_ref(img, 0x46488, 0x1C890E)
          and touched(0x5B9812, 0x46454, "W") and img.u16(0x1C8910) == 164 and img.u16(0x1C890E) == 328,
          "pedal-released flag 0x3FC18B (INT 0x46348): request 0x5B9812 with hysteresis 0x1C8910/0x1C890E (164/328)")
    check(touched(0x3FC19F, 0x48634, "addr") and touched(0x3FC162, 0x48650, "R") and touched(0x3FC198, 0x48660, "R")
          and touched(0x3FBEB8, 0x48670, "R") and touched(0x3FC19E, 0x48680, "R") and is_r2_ref(img, 0x4863C, 0x1C8A18),
          "full cut 0x3FC19F = 0x3FC162 && !0x3FC198 && !0x3FBEB8 && !0x3FC19E when CAL 0x1C8A18 bit1 = 0")
    check(img.u8(0x1C8A18) & 2 == 0 and is_r2_ref(img, 0x488BC, 0x1C8A18) and touched(0x3FC162, 0x488B0, "R"),
          "staged (AEVAB step) overrun reduction via 0x3FC162 exists but is disabled: CAL 0x1C8A18 bit1 = 0")
    check(touched(0x3FC19F, 0x46C40, "R") and touched(0x1CF3E4, 0x46C58, "addr") and touched(0x3FB451, 0x46C84, "W")
          and touched(0x3FC18E, 0x46D80, "W") and is_r2_ref(img, 0x46DF0, 0x1C8944),
          "post-cut window: 0x3FC19F loads 0x3FB451 from 0x1CF3E4; window flag 0x3FC18E selects filter constants 0x1C8944/0x1C8536")
    check(touched(0x5B90BB, 0x3D2E0, "W") and dform(img, 0x3D2C0) == (14, 10, 0, 0xA0) and touched(0x5B9D1C, 0x3D058, "R")
          and touched(0x5B9D1C, 0x3D014, "W") and touched(0x1C6F18, 0x3D008, "R"),
          "0x5B90BB = processed frequency-input speed 0x5B9D20 / 160 (INT 0x3D03C); raw 0x5B9D1C = K / period (INT 0x3CF9C)")
    check(touched(0x5B9001, 0x59990, "W") and dform(img, 0x59988) == (14, 10, 0, 0xA0)
          and dform(img, 0x59994) == (14, 12, 0, 0x28) and touched(0x5B9002, 0x599B4, "W"),
          "rpm bytes: 0x5B9001 = 0x5B9A26/160 (40 rpm/bit), 0x5B9002 = min(0x5B9A26/40, 255) (10 rpm/bit)")
    # --- generator / BSD ----------------------------------------------------------
    check(call_with(0xF3C258, 0x63660, 0x28) and touched(0x5B8F7B, 0xF3C298, "W") and touched(0x5B8F7B, 0xF8AB10, "R")
          and dform(img, 0xF8AB1C) == (14, 4, 12, 0x1A8) and dform(img, 0xF8ABF0) == (7, 31, 5, 0x19),
          "CAN 0x334 byte0 (signal 0x28) -> 0x5B8F7B; voltage request = max(10600 + 25*0x5B8F7B, base) in EXT 0xF8A9D0")
    check(is_r2_ref(img, 0xF8ABBC, 0x1C9446) and is_r2_ref(img, 0xF8ABC4, 0x1C9444) and touched(0x5B90BB, 0xF8ABB0, "R")
          and img.u16(0x1C9444) == 11200 and img.u16(0x1C9446) == 10600,
          "generator relief request: 0x1C9446 (10600) when 0x5B90BB = 0 else 0x1C9444 (11200)")
    check(touched(0x5B90F8, 0xF8AD9C, "W") and dform(img, 0xF8AD74) == (14, 12, 0, 100)
          and dform(img, 0xF8AD7C) == (14, 6, 12, -0x6A) and is_r2_ref(img, 0xF8AD5C, 0x1C943C),
          "generator setpoint byte 0x5B90F8 = min(request, 0x1C943C)/100 - 106 (0.1 V/bit, 10.6 V offset)")
    check(touched(0x5B90F8, 0xFA4110, "R") and touched(0x5B90ED, 0xFA4118, "R") and img.u32(0xFA41D4) == 0x57EA3632
          and dform(img, 0xFA41F8) == (15, 10, 0, 7) and dform(img, 0xFA41FC) == (14, 10, 10, -0x3204),
          "BSD frame (EXT 0xFA3DB8): 6-bit setpoint from 0x5B90F8 | 2-bit field from 0x5B90ED << 6, sent via INT 0x6CDFC")
    check(img.u32(0x1C3C4) == 0x304000 and img.u8(0x1C3C4 + 0xC) == 14 and img.u8(0x1C3C4 + 0xD) == 13
          and dform(img, 0xFEA3AC) == (15, 11, 0, 2) and dform(img, 0xFEA3B0) == (14, 11, 11, -0x3C3C)
          and dform(img, 0xFEA650) == (34, 4, 30, 0xC) and dform(img, 0xFEA670) == (34, 4, 30, 0xD),
          "BSD service descriptor INT 0x1C3C4: TPU3 A base 0x304000, channels 14 and 13")
    check(dform(img, 0x2061C) == (11, 0, 12, 6) and touched(0x5B89F1, 0x2066C, "W") and touched(0x5B89EA, 0x2073C, "W")
          and is_r2_ref(img, 0x20700, 0x1C6EC3),
          "BSD receive decoder INT 0x205A4 (node 6): msg0 echo -> 0x5B89F1, msg2 bits0-4 x CAL 0x1C6EC3 -> load 0x5B89EA")
    check(call_with(0xF8A52C, 0x179E8, 0x1C8FAC) and call_with(0xF8A4F4, 0x179E8, 0x1C8FF8)
          and call_with(0xF8A510, 0x179E8, 0x1C9044) and touched(0x5B89EA, 0xF8A524, "R") and touched(0x5B8C2A, 0xF8A544, "W"),
          "generator torque maps 0x1C8FAC/0x1C8FF8/0x1C9044 (variant 0x3FE19C) indexed by BSD load 0x5B89EA -> 0x5B8C2A")
    check(touched(0x5B8C4A, 0x5AC74, "W") and touched(0x5B8C4A, 0xF59F08, "R") and touched(0x3FB3BA, 0xF59F4C, "W")
          and touched(0x5B90E3, 0xFB102C, "R") and touched(0x5B97AE, 0xFB1174, "W"),
          "generator torque 0x5B8C4A (INT 0x5A620) -> 0x3FB3BA (EXT 0xF59E80) -> idle torque reserve 0x5B97AE (EXT 0xFB0F10)")
    # ===== final pass: PWM, fan, thermostat, exhaust flap =====
    # --- round 6: PWM channel roles, electric fan, thermostat heater, flap polarity ----------
    # (snippet for main() of tools/verify_770b_findings.py; uses refs/calls/touched/call_with/dform/is_r2_ref)
    pwm_rec = lambda ch: 0x156AC + 24 * ch  # noqa: E731
    check([img.u8(pwm_rec(c) + 7) for c in range(10)] == [0x12, 0x00, 0x0C, 0x1E, 0x13, 0x11, 0x1F, 0x0B, 0x01, 0x03]
          and [img.u8(pwm_rec(c) + 0xD) for c in range(10)] == [1, 1, 0, 0, 1, 1, 0, 0, 1, 1],
          "PWM table INT 0x156AC: hw channel (+4) and driver index (+0xD) of logical channels 0..9")
    check(img.u32(0x671D8) == 0x80670008 and img.u32(0x67268) == 0x7CC361D6 and img.u32(0x672F8) == 0x21842710,
          "PWM API INT 0x671AC: period = rec+8 multiplier x r5; duty inverted (10000-duty) when rec+0x13 set")
    fan_out = (0xF2D78C, 0xF578D8, 0xFB2784)
    check(all(dform(img, f + 0x38) == (14, 3, 0, 9) and any(p == f + 0x3C and t == 0x671AC for p, t, r in calls)
              and touched(0x5B9470, f + 0x10) and touched(0x5B946F, f + 0x28) and img.u32(f + 0x14) == 0x1D8C2710
              for f in fan_out),
          "PWM logical ch 9 (electric fan): duty = 0x5B9470*10000/255, period factor = 10000/0x5B946F (3 copies)")
    check(dform(img, 0xF5A62C) == (14, 11, 0, 10) and dform(img, 0xF5A63C) == (14, 11, 0, 100)
          and touched(0x5B946F, 0xF5A630, "W") and touched(0x5B946F, 0xF5A640, "W"),
          "fan PWM frequency byte 0x5B946F = 10 (after-run flag 0x3FC2A8) else 100 -> 100 ms / 10 ms period")
    check(call_with(0xF5A5DC, 0x16AE4, 0x1D09B8) and touched(0x5B9472, 0xF5A5D8) and touched(0x5BBAC9, 0xF5A5F0)
          and touched(0x5B9470, 0xF5A618, "W"),
          "fan duty 0x5B9470 = curve 0x1D09B8(0x5B9472) clamped to [0x5BBAC9, CAL 0x1D09B6]")
    check(call_with(0xF5A7D0, 0x16AE4, 0x1D09CC) and touched(0x5B9308, 0xF5A7CC)
          and call_with(0xF5A7B8, 0x16AE4, 0x1D0988) and call_with(0xF5A7A0, 0x16AE4, 0x1D09A0) and touched(0x5B854A, 0xF5A74C),
          "fan request: max(curve 0x1D09CC(coolant temp 2 0x5B9308), curves 0x1D0988/0x1D09A0(IHKA request 0x5B854A))")
    check(call_with(0xF5A854, 0x179E8, 0x1D0958) and touched(0x5B9229, 0xF5A82C) and touched(0x5B9477, 0xF5A830, "W")
          and call_with(0xF5A89C, 0x16AE4, 0x1D0940) and touched(0x5B90BB, 0xF5A674),
          "fan request adds map 0x1D0958(transmission oil temp 0x5B9229, 0x5B90BB) and is scaled by curve 0x1D0940(0x5B90BB)")
    check(msgs[3]["can_id"] == 0x1B5 and not msgs[3]["tx"] and dform(img, 0xF3BE98) == (14, 3, 0, 3)
          and touched(0x5B854A, 0xF3BF4C, "W") and img.u32(0xF3BF3C) == 0x5464073E,
          "0x5B854A = low nibble of byte 3 of CAN 0x1B5 (message object 3, read via INT 0x63730)")
    check(touched(0x3FC2A8, 0xFB3898, "W") and touched(0x5B9307, 0xFB3874) and touched(0x1D09E2, 0xFB387C)
          and touched(0x5B9474, 0xFB38D4, "W") and any(p == 0xFB38E8 and t == 0xF5A53C for p, t, r in calls),
          "fan after-run EXT 0xFB37D0: 10 Hz flag 0x3FC2A8 / duty 0x5B9474 from engine temp 0x5B9307 > CAL 0x1D09E2")
    check(dform(img, 0xF2C9E0) == (14, 3, 0, 8) and touched(0x5B9C12, 0xF2C9DC) and touched(0x5B9052, 0xF2C9D0)
          and is_r2_ref(img, 0xF7BE6C, 0x1C5480) and is_r2_ref(img, 0xF7BEB0, 0x1C5484) and is_r2_ref(img, 0xF7BEB8, 0x1C5482)
          and touched(0x5B9C12, 0xF7BEC8, "W"),
          "PWM logical ch 8: duty 0x5B9C12 chosen from fixed CAL duties 0x1C5480/82/84 (EXT 0xF7BDC0), period CAL 0x1C5486")
    check(touched(0x5B9307, 0xF9E5C0) and touched(0x5B91D3, 0xF9E5C8) and touched(0x3FC29B, 0xF9E624, "W")
          and touched(0x1D0938, 0xF9E630) and touched(0x5B8E26, 0xF9E634, "W") and touched(0x1D08A5, 0xF9E608),
          "ch-6 command 0x3FC29B: on when engine temp 0x5B9307 > target 0x5B91D3 (+hyst CAL 0x1D08A5), min-on time CAL 0x1D0938")
    check(img.u32(0xAC1C) == 0x2C040000 and img.u32(0xAC24) == 0x7FEC0034 and dform(img, 0x38C18) == (14, 4, 0, 1),
          "digital output driver INT 0xAC00 inverts the value when r4 != 0; flap channel 12 is called with r4 = 1")
    check(touched(0x5B90BB, 0xF97EAC) and touched(0x1D07EC, 0xF97EB4) and img.u32(0xF97EC4) == 0x558CF6BE
          and touched(0x5B953E, 0xF97E30) and touched(0x1D07E6, 0xF97E38),
          "flap: 0x5B90BB <= CAL 0x1D07EC selects CW bit2; start gate compares 0x5B953E with CAL 0x1D07E6")
    check(dform(img, 0x3D2C0) == (14, 10, 0, 0xA0) and touched(0x5B90BB, 0x3D2E0, "W") and touched(0x5B90BB, 0x3D2A8, "W")
          and any(p == 0x3CFD0 and t == 0x66DD4 for p, t, r in calls) and touched(0x5B9D1C, 0x3D014, "W"),
          "0x5B90BB = filtered 0x5B9D20/160 (0 on timeout); source 0x5B9D1C = K/(10*period) from period capture INT 0x66DD4")
    check(touched(0x3FBFB7, 0x3B934, "W") and call_with(0x3B90C, 0x16AE4, 0x1CCCA0) and touched(0x5B9001, 0x3B914)
          and touched(0x5B953E, 0x3B8CC, "W"),
          "0x3FBFB7 set when rpm byte > curve 0x1CCCA0(engine temp); 0x5B953E counts while 0x3FBFB7 set")

    for ok, text in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {text}")
    failed = sum(1 for ok, _ in results if not ok)
    print(f"\n{len(results) - failed}/{len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
