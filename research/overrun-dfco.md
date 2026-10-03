# Overrun / decel fuel cut (770B) — round 4 (partial)

> **Final-pass status:** overrun state machine CONFIRMED (writer of 0x3FC162 found); EXT 0xFAE940 is idle/after-start logic (REJECTED as gear-dependent DFCO); no gear dependence in stock data; no generator interaction. See the *Final static pass* section at the end of this file.


Address kinds: INT = internal-flash CPU, EXT = external-flash CPU, CAL = calibration alias, RAM = runtime.
Research only; no calibration for late combustion or "pops" is proposed.

## 1. Full-cut chain — CONFIRMED (from rounds 2–3)

```text
0x3FC162 (overrun cut request) && !0x3FC198 && !0x3FBEB8 && (blank-block / cut-count condition)
   → 0x3FC19F (all-cylinder cut state)                        INT 0x484F8
   → AEVAB step 8 → all injectors off                         INT 0x2C060
0x3FC19F consumers: > 40 functions, including
   - 0x0A9/0x0AA torque word forced to 0                     INT 0x4BDDC
   - post-overrun lambda-release delay, threshold CAL 0x1C99C6 = 0x62   INT 0x58AE8 (round 4)
   - lambda/catalyst functions EXT 0xF5199C, 0xF68540
```

## 2. Request and resume logic — candidates

| Item | Address | Evidence | Status |
|---|---|---|---|
| Overrun request producer | written through a pointer (`0x3FC162` taken as address in EXT `0xFAE33C`); readers INT `0x46348`, INT `0x484F8`, EXT `0xFAE940` | exact store site not resolved by the xref scanner | open |
| Overrun-related state machine | EXT `0xFAE33C` (CAL `0x1C7426…0x1C7434`, curve `0x1C7434`, `0x1CF030`; reads gear `0x5B92CA`, rpm `0x5B9001`, `0x5B90BB` with hysteresis CAL `0x1C742E`/`0x1C742B`) | uses `0x3FC162` and `0x3FC169`; ramp helper `0x15F28` | LIKELY DFCO entry/exit and ramp |
| Gear-dependent resume/thresholds | EXT `0xFAE940`: four 6-point curves CAL `0x1C748C`, `0x1C749C`, `0x1C74AC`, `0x1C74BC`; reads gear `0x5B92CA`, `0x3FC19F`, `0x3FC162`; writes `0x3FC168…0x3FC16C` | gear-indexed curve selection | LIKELY |
| `0x3FC169` | written EXT `0xFAE978` (forced 0 when `0x3FBEFC` = 0) | read by generator fns EXT `0xF47E48` / `0xF8A648` and by EXT `0xFAE33C` | links an overrun-related state to the generator logic — HYPOTHESIS |
| Torque-reduction ignition retard / catalyst-heating retard | not isolated | — | open |

## 3. Existing OEM mechanisms relevant later

* Smooth DFCO: gear-dependent curves and a ramp helper exist (LIKELY).
* Torque intervention: AEVAB plus the ignition path (torque-model maps around INT `0x4A014`).
* Catalyst heating / late ignition: not located yet.
* Generator: `0x3FC169` reaches the generator functions (see `generator-control.md`).

---

# Final static pass (round 7, 2026-10-03)

This section supersedes conflicting statements earlier in this file. CONFIRMED items are re-checked by `tools/verify_770b_findings.py` (final-pass blocks).

### Corrections to earlier notes

| Earlier claim | Now | Evidence |
|---|---|---|
| `0x3FC162` producer "not resolved" | **CONFIRMED**: EXT `0xFAE33C` writes it via r30 (`stb` at EXT `0xFAE918`/`0xFAE928`) | `addi r30,…,0x3FC162` at EXT `0xFAE51C` |
| EXT `0xFAE940` = "gear-dependent resume/thresholds" | **REJECTED**. It is the idle/after-start state logic next to DFCO. Its 4 curves CAL `0x1C748C/9C/AC/BC` are **engine-temperature** (`0x5B9307`) indexed delay curves (flat 25/25/10/10), selected by `0x5B888B`. Its only gear use: `0x5B92CA > 0` for `0x3FC16C` | disassembly EXT `0xFAE940-0xFAEDB4` |
| `0x3FC169` = overrun-related state | **REJECTED** as overrun. It is a latch in EXT `0xFAE940`: set once `0x5B9784 + 0x5B979A/2 >= 0x5B93CE<<7`, cleared only when `0x3FBEFC` = 0. HYPOTHESIS: "post-start / drive-off torque condition reached". It gates the start-up generator relief (§B4) and the DFCO hysteresis ramp | EXT `0xFAE980-0xFAE9D8` |
| `0x5B90BB` = temperature (round 3) | **REJECTED**. `0x5B90BB` = `0x5B9D20 / 160` (sat. 255), `0x5B90BA` = clamped delta; `0x5B9D1C` = `CAL 0x1C6F18 / (period·10)` from a timer-capture input (INT `0x3CF9C`, API INT `0x66DD4`), slew-limited by CAL `0x1C6F20`. **LIKELY vehicle speed** (frequency input). Unit (km/h?) HYPOTHESIS. CONFIRMED arithmetic | INT `0x3CF9C`, INT `0x3D03C` (`li r10,0xA0; divwu` at `0x3D2C0`) |
| `0x5B9001` 40 rpm/bit LIKELY | **CONFIRMED** `0x5B9001 = 0x5B9A26/160` (0.25 rpm/bit source → 40 rpm/bit); new: `0x5B9002 = min(0x5B9A26/40,255)` (10 rpm/bit, ≤ 2550 rpm) | INT `0x59988-0x599B4` |
| Voltage-request constants "LIKELY mV" | **HIGH CONFIDENCE mV**: request = `10600 + 25·(CAN 0x334 byte0)` and output byte = mV/100 − 106; mismatch flag compares CAN byte with 4×output byte (25 mV vs 100 mV) | EXT `0xF8AB10-0xF8AC10`, `0xF8AD74-0xF8ADC0` |

### A. Overrun / DFCO

#### A1. OEM state machine (CONFIRMED structure; names/units as marked)

```text
Inputs per cycle (EXT 0xFAE33C, status byte 0x3FB351 bits b0..b7, control byte 0x5B93B4):

 b0 "enable after start"   (EXT 0xF40F80) = 0x3FBFB7 (engine running after start, INT 0x3B888)
                            && countdown 0x3FB356 expired; 0x3FB356 reloaded from array CAL 0x1CF03C[T]
 b1 = previous 0x3FC18B (pedal released), b5 = previous 0x3FC162
 b2 "gear allowed"          = 0x3FC20F ? 0x3FC238 : (CAL 0x1C742C >> gear 0x5B92CA) & 1
 b3 "rpm window"            set   if 0x5B9001 >= 0x5B93B6 (entry)
                            clear if 0x5B9001 <= 0x5B93B7 (resume)      (hysteresis, else hold)
 b4 "speed high"            set if 0x5B90BB >= CAL 0x1C742B+0x1C742E (37), clear if <= 0x1C742E (33)

 CONDITION (0x5B93B4.bit1) = b0 && 0x5B86B4 <= curve 0x1CF030(0x5B9001)
                             && !0x3FC28E && !0x3FBFD6 && !0x3FC0D4 && !0x3FC184 && !0x3FC140
                             && b2 && b3 && 0x3FC18B
 CONDITION true : counters 0x3FB354 / 0x3FB35A count down; at 0 set b6 / b7
 CONDITION false: b6 = b7 = 0; reload 0x3FB354 := 0x3FB355, 0x3FB35A := 0x3FB35B   (immediate exit)
 0x3FC162 (DFCO request) := 0x3FC060 ? b7 : b6
       0x3FC060 = 0 whenever EGS present (0x3FBED1) -> automatic E65 always uses b6 / map 0x1CEFD0

INT 0x484F8 (cut execution, stock CAL 0x1C8A18 = 0x01, bit1 = 0):
 0x3FC19F (all-cylinder cut) := 0x3FC162 && !0x3FC198 && !0x3FBEB8 && !0x3FC19E
 0x3FC19E := 0 if minimum torque 0x5B985C >= target 0x3FC32A; := 1 if 0x5B985C + MDHYEZ<<8 <= target
 0x3FC19F -> AEVAB step 0x5B93E7 := 8 -> all injectors off (INT 0x2C060)
```

States (derived): IDLE-NOT-ARMED (b0=0) → ARMED (b0) → CONDITION/DELAY (0x5B93B4.b1, counter
running) → REQUEST (0x3FC162=1) → CUT (0x3FC19F=1, after torque target ≤ ignition-limited minimum)
→ RESUME (any condition lost → 0x3FC162=0 next cycle → 0x3FC19F=0) → POST-CUT window (0x3FB451).

#### A2. Thresholds and CAL (stock values)

| Item | Address | Stock / meaning | Conf. |
|---|---|---|---|
| after-start delay | CAL `0x1CF03C` (5 B, no header, idx = `0x5B9F50`) | 8,6,4,3,3 ticks over T | CONFIRMED (code), unit ticks |
| T axis `0x5B9F50` | CAL `0x1CC458` (5 pts) on `0x5B9307` | 31,51,107,124,184 (= −24.75…90 °C if 0.75 °C/−48) | CONFIRMED axis, unit LIKELY |
| rpm axis `0x5B9EE8` | CAL `0x1C1240` (8 pts) on `0x5B9001` | 5,13,20,30,50,65,75,150 (200…6000 rpm) | CONFIRMED |
| resume base `0x5B93B8` | `CAL 0x1CF020[T] + (CAL 0x1CF028[T] − 0x1CF020[T])·0x5B903C/255` (EXT `0xF41020-0xF410CC`) | 0x1CF020: 45,45,35,20,20; 0x1CF028: 45,45,45,25,25 → 1800…800 / 1800…1000 rpm | CONFIRMED formula; `0x5B903C` meaning HYPOTHESIS (0..255 weight; refs only via pointer in air-charge fns INT `0x406B0`/`0x41600`/`0x45C3C`/`0x49600`) |
| resume `0x5B93B7` | `= sat(0x5B93B8 + curve 0x1C7434(0x5B9285 signed) [+ CAL 0x1C742A (=2) if 0x3FC29F])`; min CAL `0x1C742D` (=28 → 1120 rpm) when `0x5B8512 >= CAL 0x1C7430` (=1311) | curve x −20,−15,−10,−4,0 → +25,+25,+12,+5,0 (≤ +1000 rpm) | CONFIRMED formula; `0x5B9285` (INT `0x3A4A4`, signed, ×16000 path) HYPOTHESIS rpm gradient; `0x3FC29F`, `0x5B8512` meaning open |
| entry `0x5B93B6` | `= sat(0x5B93B7 + 0x5B93B5)` | — | CONFIRMED |
| hysteresis `0x5B93B5` | b4 (speed ≥ 37): `0x5B93B4.b0 ? CAL 0x1C7428 (13) : hi(0x3FB358)`; b4=0: same `+ CAL 0x1C7429 (10)` | 520/200…480 rpm, +400 rpm at low speed | CONFIRMED |
| hysteresis ramp `0x3FB358` | on pedal press (falling edge of `0x3FC18B`): `:= CAL 0x1C7426 (12)<<8`, `0x5B93B4.b0 := 0`; then while `0x3FC169`: ramp helper INT `0x15F28` toward `CAL 0x1C7427 (5)<<8`, step param `CAL 0x1C7432` (−256) | 480 → 200 rpm | CONFIRMED |
| re-entry lockout `0x5B93B4.b0` | set when `0x3FC162` falls while pedal still released (rpm resume) → fixed hysteresis 13 (520 rpm) | anti-hunting | CONFIRMED |
| gear mask | CAL `0x1C742C` = 0xFF | all gears 0..7 allowed (no gear dependence in stock data) | CONFIRMED |
| EGS gear-allow override | `0x3FC20F` → `0x3FC238` (both written EXT `0xFE52BC`) | source open | CONFIRMED path, meaning HYPOTHESIS |
| load ceiling | curve CAL `0x1CF030` (x rpm 0,10,20,30) vs `0x5B86B4` | all 255 → inactive | CONFIRMED |
| entry delay (EGS) | map CAL `0x1CEFD0` 5 T × 8 rpm, u8 (EXT `0xF57F60` → `0x3FB355`) | T0-T2: 25; T3: 18 (≤2600 rpm), 3 (≥3000); T4 hot: 14,14,14,14,12,10,3,3 ticks | CONFIRMED |
| entry delay (`0x3FC060`=1) | map CAL `0x1CEFF8` → `0x3FB35B` | 25…18, 1 at ≥3000 rpm | CONFIRMED; only used without EGS |
| pedal released `0x3FC18B` | INT `0x46348`: 0 if `0x5B9812` (= max(pedal request `0x5B981C`, cruise `0x5B954E`)) > CAL `0x1C890E` (328) (clears below `0x1C8910` = 164) or (`0x3FBFD6` && CAL `0x1C8530` bit5 (set)) | 0.5 %/0.25 % of 65535 | CONFIRMED |
| DFCO inhibits | `0x3FC28E` (EXT `0xF988A0`), `0x3FBFD6` (EXT `0xFAC420`, cruise area), `0x3FC0D4` (EXT `0xF36190`), `0x3FC184` (via ptr in INT `0x46348`), `0x3FC140` (EXT `0xF1DF64/0xF1F2EC/0xF2E2C8`); cut-stage inhibits `0x3FC198` (INT `0x47AB0`), `0x3FBEB8` (INT `0x4A700`) | — | CONFIRMED as gates, meanings HYPOTHESIS (`0x3FBFD6` LIKELY cruise active) |

#### A3. Subtasks

| Subtask | Result | Conf. |
|---|---|---|
| fuel-cut request | `0x3FC162` (EXT `0xFAE33C`) → `0x3FC19F` (INT `0x484F8`) → AEVAB step 8 | CONFIRMED |
| entry (pedal, rpm, delay) | pedal < 0.5 % (hyst.), rpm ≥ resume+hysteresis, temp×rpm delay map, after-start delay | CONFIRMED |
| exit / resume | any condition false → immediate; rpm ≤ resume curve (temp blend + `0x5B9285` term + min 1120 rpm option) | CONFIRMED |
| gear dependence | only CAL bitmask `0x1C742C` (all set) or external flags `0x3FC20F/0x3FC238`; no gear-indexed curve. `0x5B92CA` axis not used for thresholds | CONFIRMED (stock: none) |
| rpm dependence | entry delay map rpm axis; rpm hysteresis | CONFIRMED |
| temperature dependence | resume curves, after-start delay, entry delay map (all on `0x5B9307`) | CONFIRMED (unit LIKELY) |
| ramp-out before cut | cut only when target torque `0x3FC32A` ≤ ignition-limited minimum `0x5B985C` (= `0x5B97E0·0x3FC2F9/200`, MDHYEZ hysteresis) → the torque path must first reduce torque via ignition; the target falls through the pedal map (0 at pedal 0) and the torque filter `0x5B97F8` | CONFIRMED gate; shaping filter for tip-out LIKELY |
| ramp-in after resume | INT `0x46348`: while `0x3FC19F`, `0x3FB451 := array CAL 0x1CF3E4[idx 0x5B9EC0 (rpm, axis CAL 0x1CC4F2)]` (stock 20); counts down after cut; `0x3FB452` likewise from `0x1CF3EC` on pedal-released (stock 0). `0x3FC18E` = window active; if also `0x5B980E < curve 0x1CF810` → torque-filter constants `0x5B9828 := CAL 0x1C8944 (2617)`, `0x5B97E4 := CAL 0x1C8536 (13108)` instead of `0x3FB458/0x3FB45A` | CONFIRMED mechanism; curve `0x1CF810` mostly −32768/0 → effect likely small (HYPOTHESIS) |
| fuel resume | `0x3FC19F` = 0 → AEVAB step recomputed from torque ratio (no separate per-cylinder re-entry sequence found in DFCO code) | LIKELY |
| lambda recovery | INT `0x58AE8`: `0x3FC19F` resets integral `0x3F9D30`; closed loop held off (`0x3FC1F7`) until integrated air mass ≥ CAL `0x1C99C6` (98) | CONFIRMED (round 4) |
| loss/reserve torque | `0x5B979C := 0` while `0x3FC162` (INT `0x3D4B8`); `0x5B97F4 = 0x5B979E (+0x5B97AE/2 unless CAL 0x1C7898 ≠ 0 or 0x3FC162)`; stock `0x1C7898` = 1 → reserve never added | CONFIRMED |
| CAN | `0x3FC19F` forces 0x0AA driver-request torque `0x5B94C2` to 0 (INT `0x4BDDC`) | CONFIRMED (earlier) |
| generator interaction | **none**: no generator function (EXT `0xF8A9D0`, `0xF8A648`, `0xF47E48`, `0xF8A1C8`, INT `0x5A620`, BSD EXT `0xFA3DB8`) reads `0x3FC162`/`0x3FC19F`; no overrun voltage raise | CONFIRMED absence in these fns |
| cylinder-wise staged cut | exists as calibration option: CAL `0x1C8A18` bit1 = 1 would (a) let `0x3FC162` request AEVAB step reduction (INT `0x488B0`) and (b) allow full cut only when `0x5B92EC >= CAL 0x1C8A1D` (=2). Stock bit1 = 0 → direct full cut | CONFIRMED |
| ignition during cut | INT `0x4A014` and INT `0x495D0` branch on `0x3FC19F` (resets `0x3FB8A6` / `0x3FC282`); exact ignition angle in cut NOT COMPLETED | — |

#### A4. EXT 0xFAE940 (idle/after-start logic, for completeness)

`0x3FC168` = pedal released && !`0x3FC19F` && !`0x3FC162` && !`0x3FC184` && !`0x3FC189` && (delay
`0x5B820C` (CAL `0x1C748A`) expired or `0x5B93C3` ≥ 0); `0x3FC16B`/`0x3FC16A` = temperature-curve delays
(`0x1C74AC/BC`, `0x1C748C/9C`) after `0x3FC169`; `0x3FC16A` also needs `0x5B9002 < 0x5B93C2 + CAL 0x1C7489`
(100 → +1000 rpm); `0x3FC16C` = (gear > 0 …) && `0x5B90BB` > CAL `0x1C74C9` (4). Consumers: INT `0x310B0`,
EXT `0xFAFCE0`, `0xF593DC`, INT `0x55A1C`. LIKELY idle-control activation; DFCO and idle are mutually exclusive
through `0x3FC162`/`0x3FC19F`.


### Unresolved / NOT COMPLETED

* Task periods for DFCO counters and generator ramps (needed to convert ticks to s and 100 mV/step to V/s).
* Meanings of DFCO inhibits `0x3FC28E`, `0x3FC0D4`, `0x3FC184`, `0x3FC140`, `0x3FC198`, `0x3FBEB8`; of `0x5B903C`, `0x5B9285`, `0x5B8512`, `0x3FC29F`, `0x5B86B4`.
* Exact ignition angle / torque ramp shape during ramp-out (INT `0x4A014`, `0x495D0` branches on `0x3FC19F`): NOT COMPLETED.
* CAN-ID of TX handle 0x75 (EXT `0xF5EAF0`, API INT `0x63DCC`) carrying generator load/torque: NOT COMPLETED.
* Battery-voltage scale; which TPU channel (13/14) is TX vs RX; BSD bit timing (TPU function code in CFSR) NOT COMPLETED.
* CAN 0x334 DLC 2 vs. byte2 decode (temperature `0x5B8551`).
* Live data that resolves most items: log `0x3FB351`, `0x5B93B4..B8`, `0x3FC162`, `0x3FC19F`, `0x5B9001`, `0x5B9307`,
  `0x5B90BB` (compare with dash speed) during coast-downs; `0x5B8F7B`, `0x5B8C7E`, `0x5B90F8`, `0x5B89EA`, `0x5B89F1`,
  `0x5B930A` (compare with a multimeter), `0x5B8C4A`, `0x5B97AE` with headlights/rear-window heater switching.
  A PT-CAN capture identifies the 0x334 sender and the handle-0x75 frame.
