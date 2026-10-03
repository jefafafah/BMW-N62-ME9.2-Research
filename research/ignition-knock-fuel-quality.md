# Ignition, knock and fuel quality (770B) — round 4

> **Final-pass status:** ignition 0.75°/bit, base/full-load/idle/safety maps and the final per-cylinder sum CONFIRMED; 0x1CB8AC/98A/A68 are minimum-angle maps (corrects round 2); knock retard/adaptation structure CONFIRMED; no octane factor. See the *Final static pass* section at the end of this file.


Address kinds: INT = internal-flash CPU, EXT = external-flash CPU, CAL = calibration alias, RAM = runtime.

## 1. Ignition path — candidates (from round 2, extended)

| Item | Address | Evidence | Status |
|---|---|---|---|
| Ignition-angle function | INT `0x49600` | uses three 24×16 signed-byte maps on rpm/40 × load×0.75 axes, plus 8×8/12×5/8×5/6×6 corrections; writes `0x5B9451…0x5B9457` | LIKELY |
| Base/alternate/optimal maps | CAL `0x1CAD5A`, `0x1CAF04`, `0x1CB186` | values rise with rpm and fall with load (spark-advance shape) | LIKELY maps, roles HYPOTHESIS |
| Torque-model ignition efficiency | INT `0x4A014`, CAL `0x1CB8AC`/`0x1CB98A`/`0x1CBA68` (16×12 s8) | writes `0x3FC2F9`, which scales the "torque without cut" used by AEVAB (`0x5B985C`, also sent on 0x0A9) | LIKELY torque-model part |

## 2. Knock control and adaptation — not located

* No per-cylinder knock-retard array was identified this round. The only 8-byte per-cylinder array
  found (`0x5B9467…0x5B946E`, EXT `0xF986FC`) is fed by catalyst-diagnosis variables. REJECTED as knock.
* Method for round 5: find the knock-sensor acquisition (QADC A/B fast conversions in a crank-angle
  window, TPU-scheduled). Follow the per-cylinder integrator values into a comparator with a
  reference level. The retard array is the object that is decremented quickly and recovered slowly;
  its long-term part is stored in EEPROM-backed RAM.

## 3. Fuel-quality question (95 RON baseline with automatic gain on better fuel)

* No fuel-quality detector or octane switch was found.
* Whether the stock knock control has a **long-term adaptive** component that would retain more
  advance on 98 RON cannot be answered until the knock adaptation is located. Status: open.
* Working rule (unchanged): calibrate hard limits for 95 RON and rely only on mechanisms that are
  proven to exist.

---

# Final static pass (round 7, 2026-10-03)

This section supersedes conflicting statements earlier in this file. CONFIRMED items are re-checked by `tools/verify_770b_findings.py` (final-pass blocks).

Angle unit everywhere below: **signed byte, 0.75 deg/bit (crank, + = advance)** — CONFIRMED (see A.6).
Load byte = u16 relative load >> 5 (`0x3FC2B7` = `0x3FC302`>>5, INT `0x2BE8C`; `0x3FC2F3` = `0x5B9626`>>5, INT `0x4962C`).
With Bosch rl scaling (0.0234375 %/bit u16) the byte is 0.75 %/bit (axis 14…134 = 10.5…100.5 %): LIKELY.

Task tree (all called from scheduler list INT `0x3D8xx`): `0x45C3C` torque model (call 0x3D848), `0x49504` multi-spark (0x3D84C),
`0x4A014` min angle / efficiency (0x3D850), `0x49E94` safety map (0x3D888), `0x49600` base angle (0x3D88C), `0x495D0` overrun latch
release (0x3D8A4), `0x44E08`/`0x44A6C` knock enable/range (0x3D8AC/0x3D8B0), `0x5132C` warm-up corr (0x3D8E8), `0x5123C` start angle (0x3D8EC).
Segment-synchronous (no static caller, via pointer table): knock task INT `0x35888` / `0x3602C` (two copies), ignition output
`0x31B9C` → `0x333CC` (final sum) → `0x33650` (limits/intervention) → `0x30A2C` (scheduling).

### A. Ignition map structure

#### A.1 Base angle function INT `0x49600` (writes `0x5B9451…0x5B9457`, `0x3FC2F2…F8`, `0x5B8DDE…E0`) — CONFIRMED arithmetic

```text
ldsp   = 0x3FC2F3 = min(0x5B9626>>5,255)          # load SETPOINT byte (0x5B9626 = rl setpoint from torque, INT 0x42DC8)
liftb  = 0x5B91D0 = min(0x5B9C08*256/1000,255)
ring1[16] 0x3FB86C ← ldsp ; 0x3FC2F4 = ring1[idx - map 0x1CAD28(liftb,0x3FC2B8)]   # variable delay 2…12 samples
ring2[16] 0x3FB884 ← ldsp ; 0x3FC2F7 = ring2[idx - CAL 0x1CB4A5(=2)]               # fixed delay
0x3FC2F5 = PT1(0x3FB880, 0x3FC2F4, k = u16 map 0x1CACAC(0x5B9C08,0x5B9B34))         # helper INT 0x1EBE4
0x3FC2F6 = PT1(0x3FB898, 0x3FC2F7, k = CAL 0x1CB4C0)
corrA  = 0x5B9457 = map 0x1CB330(liftb, 0x3FC2B8)                 # 8x8, all 0 in stock
-- "predicted-load" variant (delayed/filtered setpoint):
A1 = map 0x1CAD5A(rpm, 0x3FC2F5) + corrA
B1 = (0x5B8872 ? map 0x1CB186 : map 0x1CAF04)(rpm, 0x3FC2F6)
0x5B9453 = sat8(A1 + (B1-A1)*0x5B903C>>8)
-- "actual-load" variant (load 0x3FC2B7):
A2 = 0x5B8F26 ? map 0x1CB384(24x6, pre-searched axes 0x5B9F04/0x5B9F10) : map 0x1CAD5A(rpm,0x3FC2B7) + corrA
B2 = 0x5B8872 ? map 0x1CB186(rpm,0x3FC2B7) : (0x5B8F26 ? map 0x1CB414(24x6) : map 0x1CAF04(rpm,0x3FC2B7))
0x5B9452 = sat8(A2 + (B2-A2)*0x5B903C>>8)
0x5B9451 = sat8((0x5B9453-0x5B9452) * map 0x1CAD10(rpm, IAT 0x5B9306) >> 8)        # 4x3, all 0 in stock
dyn      = min(sat8(0x5B9451+0x5B9453), 0x5B9452)                                   # never earlier than actual-load angle
0x5B8DDE = (0x5B961A >= curve u16 0x1D0696(rpm 0x5B9A26))                          # setpoint-step detector
if 0x5B8DDE: 0x3FC2F8 = curve 0x1CB4A8(rpm)  ; 0x3FC2F8 counts down; 0x5B8DDF = (0x3FC2F8 > 0)
0x5B8DE0 = 0x5B8DDF && CW 0x1CED35.bit1 && (CW.bit0 || !0x5B8F26)                 # transient phase flag (CW = 0x07)
0x5B9455 = 0x5B8DE0 ? dyn : 0x5B9452
if 0x3FC0F4 && 0x3FC0DC: 0x5B9454 = 0x5B9459 ; return                               # knock-fault safety map (A.4)
idle  = sat8(map 0x1CB134(liftb,0x3FC2B8) + map 0x1CB0AE(rpm,0x3FC2B7)) ; I2 = map 0x1CB0FD(rpm,0x3FC2B7)
0x5B9456 = sat8(idle + (I2-idle)*0x5B903C>>8)
base = CW.bit2 ? (0x3FC18B ? 0x5B9456 : 0x5B9455) : 0x5B9455 + (0x5B9456-0x5B9455)*0x5B90DC>>8
0x3FC2F2 = 0x5B8DE0 ? (0x5B8872 ? 0x3FC2F6 : 0x3FC2F5) : 0x3FC2B7
iatc = curve s8 0x1CB4B9(IAT 0x5B9306) * map u8 0x1D0664(rpm, 0x3FC2F2) >> 7       # 0 … -7 bit, weight 0…1.0 (128)
0x5B9454 = sat8(base + 0x5B93D4 + 0x5B93D5 + iatc)
```

#### A.2 Map inventory

| CAL | Geometry | Axes (RAM) | Role | Confidence |
|---|---|---|---|---|
| `0x1CAD5A` | 24×16 s8 | x rpm `0x5B9001` 10…163; y load `0x3FC2F5` / `0x3FC2B7` 14…134 | **base ignition map, mode A** (blend factor `0x5B903C` = 0). Irregular, hand-calibrated; −20…+69 bit (−15…+51.75°) | role LIKELY (lookup CONFIRMED) |
| `0x1CAF04` | 24×16 s8 | same axes | **base ignition map, mode B** (`0x5B903C` = 255). Smoother; −5…+66 | LIKELY |
| `0x1CB186` | 24×16 s8 | same axes | **alternate map replacing B** when flag `0x5B8872` set. Very regular (linear 3-bit steps) | role HYPOTHESIS: Valvetronic-fault/throttle limp map (`0x5B8872` written by EXT `0xF76E48`, which reads Valvetronic status bytes `0x5B8A1D…36`) |
| `0x1CB384` / `0x1CB414` | 24×6 s8 | x rpm (axis CAL `0x1C128C`), y load (axis `0x1C12B0`: 74,94,114) on `0x3FC2B7` | **full-load maps** A/B, used when full-load flag `0x5B8F26` (actual-load variant only) | CONFIRMED selection; "full-load" LIKELY |
| `0x1CB0AE` (12×5) + `0x1CB134` (8×8) / `0x1CB0FD` (8×5) | s8 | x rpm 9…50 (360…2000 rpm), y load 14…67; `0x1CB134`: x `0x5B91D0`, y `0x3FC2B8` | **idle / low-load ignition** `0x5B9456`, A/B blend by `0x5B903C`; faded in by `0x5B90DC` (ramped to 255 when idle flag `0x3FC18B`, INT `0x45F00…0x45F58`) | LIKELY (idle = `0x3FC18B`, written INT `0x464E8/0x464F8` in driver-wish fn) |
| `0x1CB644` + `0x1CB4C4`·k/128 | 24×16 s8 each | rpm (`0x5B9F04`), load (`0x5B9F2C`, axis `0x1C12F0` on `0x5B9037` or `0x3FC2B7` per CW `0x1CB4A4`) | **knock-control-fault safety ignition** `0x5B9459` (INT `0x49E94`); k = `0x3FB89C` = map `0x1CB7D2`(engine temp `0x5B9307`, IAT `0x5B9306`), or CAL `0x1CB7D1` when sensor-fault bits `0x3FE46F.0`/`0x3FE465.0`; + curve `0x1CB7C4`(rpm) if CW `0x3FE37B.0` | CONFIRMED arithmetic; "knock-fault" LIKELY |
| `0x1CAD28` | 6×6 u8 | `0x5B91D0`, `0x3FC2B8` | delay (samples) of setpoint load ring buffer | CONFIRMED |
| `0x1CACAC` | 6×6 u16 | `0x5B9C08` 200…1000, `0x5B9B34` 0…12800 | PT1 constant of predicted load | CONFIRMED |
| `0x1CB330` | 8×8 | `0x5B91D0`, `0x3FC2B8` | additive correction to map A | stock all 0 |
| `0x1CAD10` | 4×3 | rpm, IAT | dynamic overshoot gain | stock all 0 |
| `0x1CB4B9` + `0x1D0664` | curve 3 s8 / 6×6 u8 | IAT 97…171 (24.75…80.25 °C); weight rpm × `0x3FC2F2` | **IAT retard** 0 / −4 / −7 bit (0 / −3 / −5.25°) × weight | CONFIRMED arithmetic, IAT meaning LIKELY |
| `0x1D0696` | u16 curve 8 | rpm 600…4000 | setpoint-gradient threshold for transient flag | CONFIRMED |
| `0x1CB4A8` | curve 8 | rpm byte | transient phase duration (30…35 task cycles) | CONFIRMED |

RAM inputs: `0x5B9306` = intake-air temperature, 0.75 °C/bit −48 °C (CONFIRMED scaling: `0x5B96DA = 0x5B9306·32 + 0x2586` = Kelvin·128/3,
EXT `0xF31D7C`; substitute CAL `0x1CE318` on fault). `0x5B8993` = coolant-sensor temperature (written by the next linearisation fn EXT `0xF31D94`; LIKELY).
`0x5B9C08` (EXT `0xF7AB04`) and `0x5B9B34`/`0x3FC2B8` (= `0x5B9B34`>>8, EXT `0xF31994`, filtered INT `0x42574`) are air-path quantities
shared with the air-charge model (INT `0x41600`) and Valvetronic target fn (INT `0x4E21C`); physical meaning HYPOTHESIS (valve lift / manifold pressure).
`0x5B903C` = curve CAL `0x1C3E68`(`0x5B903D`) written through a pointer at INT `0x424B8` (air-charge model); `0x5B903D` = ratio ×256 (INT `0x42490`).
It selects map set A↔B everywhere (ignition, torque-model efficiency, min-load `0x5B9622`, warm-up corr). Meaning of A/B (e.g. unthrottled
Valvetronic vs. throttled operation): HYPOTHESIS.

#### A.3 Additive corrections

| RAM | Writer | Source | Meaning | Confidence |
|---|---|---|---|---|
| `0x5B93D4` | INT `0x46168` (copy of `0x5B93D2`) | map CAL `0x1CF36A` (load `0x3FC2B7` × `0x5B92DC`), EXT `0xFA47B8` | load-dependent ignition correction (input `0x5B92DC` from load fn INT `0x2B68C`) | CONFIRMED path, meaning HYPOTHESIS |
| `0x5B93D5` | INT `0x46154` | curve s8 CAL `0x1C806E`(`0x5B92FF`) | lambda-dependent ignition correction (pairs with lambda efficiency curve `0x1C7E48` → `0x5B93D8`) | stock all 0 / efficiency flat 200 → inactive. Meaning LIKELY |
| `0x5B9462` | INT `0x5132C` | `0x5B9463 + s8(0x3FB8B2)·map u8 0x1CBB8C(rpm,load)/256` blended with `s8(0x3FB8B3)·map u8 0x1CBBE0/256` by `0x5B903C`; `0x3FB8B2/B3` = maps CAL `0x1D0717`/`0x1D0749`(engine temp `0x5B9307`, coolant `0x5B8993`) EXT `0xF97C94` | **warm-up (cold-engine) advance**: +16…0 bit at −20…+60 °C, weighted by rpm/load | CONFIRMED arithmetic, LIKELY meaning |
| `0x5B9463` | INT `0x5132C` | 2×2 maps `0x1D070D` (idle) / `0x1D0703` (rpm×load) × `0x5B9464` = map u16 `0x1CBB78`(engine temp, time-after-start `0x5B953E`) | time/temperature-weighted offset; forced 0 when `0x5B8ED1` | **stock maps all 0 → inactive**. Catalyst-heating-offset candidate: HYPOTHESIS |
| `0x5B940B`, `0x5B940C[8]` | only init writer EXT `0xFE5858/0xFE586C` (value 0) | — | global / per-cylinder offsets; HYPOTHESIS: tester/diagnostic adjustment | open |
| CAL `0x1CABAB` | — | = 0 | global offset | CONFIRMED read |
| `0x5B9461` | INT `0x5123C` | curve `0x1CBB64` / `0x1CBB6D` (rpm, selected by `0x5B888E`) + `0x3FB8B0` (curve of IAT, EXT `0xF97B4C`) | **start (cranking) angle**, used while `0x3FC169` = 0 | CONFIRMED path; stock curves 0 |
| `0x5B9438` | EXT `0xF97B44` | curve `0x1D065C` on pre-searched rpm `0x5B9EE8` | rpm offset added after all limits | CONFIRMED; meaning HYPOTHESIS (timing/latency compensation) |

#### A.4 Final command (CONFIRMED)

```text
INT 0x333CC (next 4 cylinders in firing order, queue 0x5B943C[4], start index 0x5B9343):
  Z = 0x3FC169 ? 0x5B9454 + 0x5B9462 + 0x5B940B + CAL0x1CABAB − 0x3FC2D9 + 0x5B9360[cyl]
               : 0x5B9461 + 0x5B940B + CAL0x1CABAB                       (start)
INT 0x33650:
  if overrun latch 0x3FC282 (set by 0x3FC19F; cleared INT 0x495F8 when !0x3FC19F && 0x5B92EC < 8): applied = 0x5B9460 (all)
  elif 0x3FC1D6 (coding CAL 0x1C945C.0) or 0x3FC27E (no reduction): applied = Z
  else applied = min(Z, max(0x5B9434, 0x5B9460))             # intervention angle, never later than min angle
  0x5B9440[i] = clamp(applied + 0x5B9438, −0x20, +0x48)      # hard limits −24° … +54°
  0x3FC2EF = applied, 0x3FC2F1 = final; 0x3FC2F0.bit[cyl] = (applied == Z)  → knock recovery only counts unretarded cylinders
INT 0x30A2C: angle·15>>1 (0.1° units) → driver INT 0x6B168 (with 0x5B9972) ; INT 0x6B1CC (multi-spark, see C)
```

#### A.5 Torque-model ignition (INT `0x45C3C`, `0x4A014`, `0x32EE8`) — CONFIRMED arithmetic, names LIKELY

```text
reference angle (model):  ZWref 0x5B93DC = sat8( 0x5B93DD + (CAL0x1C7DC2.0 ? 0x5B93D6 : 0x5B9462) + 0x5B93D4 + 0x5B93D5 )
   0x5B93DD = Bm + (Opt−Bm)·0x5B90DC>>8, Bm = blend(map 0x1C7F60, map 0x1C7E60 by 0x5B903C)  (16x16 s8, pre-searched rpm 0x5B9EFC / load 0x5BA098)
                                         Opt = blend(map 0x1C7D54, 0x1C7D8B by 0x5B903C)    (8x5 s8, rpm × load byte 0x3FC2EB)
   → mirrors the ECU base/idle angle chain on model axes (base-angle reference for the torque model).
optimum torque 0x5B97DE = u16 map 0x1C828E(rpm,load); eff A/B 0x5B97DC; × lambda eff 0x5B93D8 → 0x5B97E0; × mean per-cyl eff 0x5B93DB → base torque 0x5B97DA
minimum angle (INT 0x4A014):
   0x5B945C = map 0x1CB8AC(rpm,load)   (16x12 s8, −31…+11)
   0x5B945F = map 0x1CB98A·w/255 + map 0x1CBA68·(255−w)/255,  w = 0x3FB8AB = min(0x5B9348·256/CAL0x1CB7E8,255)   (post-start variant)
   0x5B945D = 0x5B945C + (0x5B945F−0x5B945C)·0x3FB8A2/256 + 0x3FB89E ;  0x3FB8A0 = 0xFFFF at start, ramps to 0 (rate curve 0x1CBB46(coolant 0x5B8993))
   0x5B9460 = 0x5B945D with rate limiting (0x3FB8A8/A9, step 0x5B945A, ≤ 0x3C) when torque target changes; direct when 0x3FC0D4/0x3FC0D9
   late-angle duration monitor: applied 0x3FC2EF ≤ map 0x1CB7EC(16x12) for > CAL 0x1CBB62 → 0x3FC284 → 0x3FB8AA.0 (HYPOTHESIS: exhaust/component protection)
forward efficiency:  Δ = ZWref − 0x5B9460 ;  0x3FC2F9 = 200 − table 0x1C7DC4[Δ]·0x5B8B1C>>5   (200 = 100 %; table 0,0,1,2,4,…,91: quadratic loss vs retard)
   → "torque reachable without cut" = 0x5B97E0·0x3FC2F9/200 (AEVAB, existing note)
inverse (intervention, INT 0x32EE8):
   dM 0x5B9970 = 0x5B97DA − 0x3FC32A (or vs. 0x5B985C), ramped out by 0x3FB868; zeroed by 0x3FC19C
   η_req 0x5B9432 = min(200, (0x5B984A − dM)·200 / (0x5B92EC ? 0x3FB864 : 0x3FB866))
   idx = (200−η_req)·256/0x5B8B1C ;  ΔZW 0x5B9431 = idx<0x40 ? table 0x1CAB68[idx] : table 0x1CAA9C[idx>>3] (≥200 → CAL 0x1CAB64)
   0x5B9434 = ZWref − ΔZW ;  0x3FC27E = (dM ≤ 0 && !0x3FC19B)   (no reduction → Z used unchanged)
0x5B8B1C = blend(map u8 0x1C7C54(rpm,load), CAL 0x1C7E44 by 0x5B903C): efficiency-curve gain (INT 0x462CC–0x46330)
```

Distinction: base = `0x1CAD5A`/`0x1CAF04`; alternate = `0x1CB186` (flag), full-load = `0x1CB384/0x1CB414`; idle = `0x1CB0AE/0x1CB0FD`(+`0x1CB134`);
warm-up = `0x5B9462` chain; temperature = IAT `0x1CB4B9`; optimal/MBT-style **reference** for the torque model = `0x5B93DC` chain (maps `0x1C7E60/0x1C7F60/0x1C7D54/0x1C7D8B`)
— note it is the model's *base-angle* reference, not proven to be MBT (HYPOTHESIS that `0x1C7Dxx`/`0x1C7Exx`/`0x1C7Fxx` are KFZWOP-type);
efficiency-vs-Δ curve = `0x1C7DC4` (forward) and `0x1CAB68`/`0x1CAA9C` (inverse); latest angle = `0x1CB8AC` (+ post-start `0x1CB98A/0x1CBA68`).
Round-2 hypothesis "0x1CB8AC/98A/A68 = efficiency/delta maps" is **corrected**: they are **minimum (latest) ignition angle maps**; the
efficiency comes from `0x1C7DC4` applied to (reference − minimum).

#### A.6 Scaling evidence
0.75 °/bit CONFIRMED: INT `0x30CE4/0x30CE8` (`mulli ×15`, `srawi 1`) converts `0x5B9440` to 0.1° units for the output driver. Limits
−0x20/+0x48 → −24°/+54°.

### B. Knock control and fuel quality (documentation level)

| Item | Address | Behaviour | Confidence |
|---|---|---|---|
| Acquisition | knock task INT `0x35888` (copy `0x3602C`), cylinder index `0x3FC2D4` = (`0x5B907C`−1) mod 8 | reads two analog channels via INT `0x8B34` (logical ch 0x15/0x1B, >>2 → `0x3FAFEC/ED`, `0x5B89B6/B8`); per cylinder writes 3 discrete selector lines via INT `0xA558`(0/1/2) built from per-cylinder table `0x3FB1B8[cyl]` and gain code `0x5B89BC[cyl]`→`0x5B9314`→table INT `0x1AA44`; schedules the next measurement window via INT `0x6C89C` with angle args derived from `0x5B932A/0x5B932C` (×7.5 + 540) | LIKELY: external knock evaluation IC with integrator read by QADC; IC type not identified |
| Signal evaluation / detection | INT `0x351EC`, `0x37B48` (CAL `0x1C741F…25`, `0x1C6C87…89`), `0x367F0`, `0x36C80` | reference level and comparison; produce knock flag `0x3FC101` for current cylinder | structure LIKELY, internals NOT COMPLETED |
| Enable / ranges | INT `0x44E08` | knock control active `0x3FC0F4` = (dynamic `0x3FC0ED` or load above threshold `0x3FB1B4`) && engine running `0x3FBFB7` && `0x3FC0FA` && rpm > CAL `0x1C71D4`; rpm range `0x5B936F` 0…4 (CAL `0x1CEE5A…5D`, hyst `0x1CEE5E`); load range `0x5B936E` (RAM thresholds `0x5B8A8C…8F`; full-load forces a value) | CONFIRMED compares, axis identity LIKELY |
| Per-cylinder working retard | `0x3FC2E0[8]` (current cell), current-cyl copy `0x3FB19C` | on knock (`0x3FC101`): retard += step `0x5B9369`, recovery counter `0x5B9374[cyl]` reloaded with `0x5B936D`; cap `0x5B936A`; spread limit ±`0x5B935D` around the 8-cyl mean `0x3FC2E8` | CONFIRMED |
| Recovery | INT `0x377E4…0x3785C` | counter `0x5B9374[cyl]` decremented per unretarded combustion (`0x3FC0FC` = `0x3FC2F0.bit[cyl]`); at 0: retard −= 1 bit (0.75°) if > 0; counter reloaded with `0x5B936C` (dynamic `0x3FC0FD`) or `0x5B936D` | CONFIRMED |
| Output | `0x5B9360[cyl]` = −(retard + `0x5B940C[cyl]` + CAL `0x1C71C0[cyl]`) ; 0 when `0x3FC0F4` = 0 ; fixed `0x5B9368` (with safety map) when `0x3FC0DC` | CONFIRMED |
| Long-term adaptation | `0x3FDBB4[0xA8]` = 21 cells × 8 cyl, cell offset `0x5B936F·8 + 0x5B936E·40`, idle cell `0xA0` (`0x3FC18B`); copied to `0x3FC2E0` on cell change (`0x3FB193`); reset loop INT `0x44E48` when `0x3FC209` | when adaptation enabled (`0x3FC0F5`, not dynamic `0x3FB191`, rpm > CAL `0x1C71D3`): knock → adapt = max(adapt, retard + CAL `0x1C71CF`) (≤ `0x5B936A`); otherwise when retard ≤ adapt − CAL `0x1C71CE`: adapt −= CAL `0x1C71D0`, floor 0. Area `0x3FDBB4` lies in the non-volatile-mirror region (EEPROM backing not traced) | CONFIRMED logic; persistence LIKELY |
| Dynamic (tip-in) knock retard | INT `0x36E98`, `0x44A6C`: global `0x3FC2D9`, subtracted in final sum | phase flag `0x3FC0ED` ← transient flag `0x5B8DE0` (CW `0x1CED35.1`); learned per range `0x3FE16C[0x3FB180]` (+`0x5B9369` on knock, cap CAL `0x1C71A4`; −1 when knock-free ratio `0x3FB182` ≥ CAL `0x1C71A9`, floor CAL `0x1C71A6`); after phase: `0x3FC2D9` −= CAL `0x1C71A5` every CAL `0x1C71A7` cycles | CONFIRMED decay; init value from `0x3FE16C` in `0x44A6C` LIKELY |
| Knock-system fault | `0x3FC0DC` (EXT `0xF85BCC`) | base angle replaced by safety map `0x5B9459`, retard fixed `0x5B9368` | LIKELY (diagnosis identity) |

**Fuel quality / 98 RON question:**
* No octane / fuel-quality factor that raises advance was found. The only interpolation factor between two ignition maps besides `0x5B903C`
  is `0x3FB89C` (safety maps), and it is a temperature map, used only in the knock-fault path. CONFIRMED (static).
* Knock retard and adaptation are both **non-negative and floored at 0** (INT `0x3781C`, `0x37970`). The angle can therefore never exceed the
  base chain (base map + corrections + static per-cylinder offset `0x1C71C0`). CONFIRMED.
* Consequence: better fuel lets the per-cylinder/per-range retard and adaptation decay toward 0, recovering advance **up to the base map**, not
  beyond. Whether the stock base map lies above the 95 RON knock limit (so that 98 RON gains anything) is UNTESTED; it needs live logging of
  `0x3FC2E0[8]`, `0x3FDBB4` cells and `0x3FC2D9` on 95 vs 98 RON at the same operating points.
