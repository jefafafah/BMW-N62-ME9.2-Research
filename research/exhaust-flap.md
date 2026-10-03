# Exhaust flap (770B) — round 2

> **Final-pass status:** command 1 = flap closed (HIGH CONFIDENCE logic level); opens via pedal threshold map, not via the kickdown flag. See the *Final static pass* section at the end of this file.


Address conventions as in `research/aevab-redabm.md`.

## 1. Control path — CONFIRMED from disassembly (EXT fn `0xF97D8C`)

```text
cw := CWAKR candidate @ 0x1D07E8   (stock 0x14 = bits 2 and 4)

if 0x3FC102 && 0x3FC103:              out := 0x3FC104        # override/actuator test (HYPOTHESIS)
elif (cw.bit4 || 0x3FE954) &&
     hyst(0x5B9307; on 0x1D07E9=13, off 0x1D07EB=11) ? (0x5B953E < 0x1D07E6) : (0x5B90BB < 0x1D07ED):
                                       out := 0
elif cw.bit0 && 0x3FC0D4:             out := cw.bit3
elif 0x5B90BB <= 0x1D07EC (=0):       out := cw.bit2         # low-value branch (round 2 said "standstill"; 0x5B90BB is now thought to be a temperature)
else:
    pedal := 0x3FC188 ? 0x5B9822 : 0x5B96D8                    # cruise-equivalent vs. real pedal
    thr   := KFAKR_GANG[gear 0x5B92CA][rpm byte 0x5B9001]      # map 0x1D077C, 7×12 u8
    out   := NOT hyst(pedal>>8 >= thr, hysteresis 0x1D07EA=12)
if cw.bit5: out := !out
0x3FC286 := out                                                  # flap command
```

* Map `0x1D077C`: x = gear 0…6, y = rpm byte 10…163 (×40 rpm ≈ 400…6520 rpm, LIKELY). Values are
  pedal thresholds (0 = always, 254 = practically never):

  rpm breakpoints: 400, 720, 1000, 1320, 1520, 2000, 2200, 2320, 2520, 3000, 4000, 6520.

  | gear | ≤1000 | 1320–1520 | 2000 | 2200 | 2320 | 2520 | 3000 | ≥4000 |
  |---|---|---|---|---|---|---|---|---|
  | 0 | 254 | 254 | 254 | 254 | 254 | 254 | 254 | 254 |
  | 1 | 254 | 129 | 129 | 129 | 129 | 0 | 0 | 0 |
  | 2 | 254 | 129 | 129 | 129 | 0 | 0 | 0 | 0 |
  | 3 | 254 | 254 | 232 | 232 | 232 | 13 | 13 | 0 |
  | 4 | 254 | 254 | 254 | 232 | 232 | 13 | 13 | 0 |
  | 5–6 | 254 | 254 | 254 | 232 | 232 | 205 | 13/12 | 0 |

  (pedal>>8 scale: 129 ≈ 50 %, 232 ≈ 91 %, 13 ≈ 5 %)

* `out = 1` while pedal < threshold. Whether `1` means "flap closed" or "open" depends on the output
  stage. Consumers: INT `0x38A54`, EXT `0xF1BCC8`, EXT `0xF72F40`. **HYPOTHESIS:** 1 = flap closed
  (quiet) at low load. Verify on the car.
* Name mapping: `KFAKR_GANG` → `0x1D077C` and `CWAKR` → `0x1D07E8` are **LIKELY**: function and
  description match. The 560B offsets recorded in `research/reference-symbols.csv` (`0x10655`,
  `0xD2827`) cannot be offsets into the same 128 KiB calibration image as REDABM (`0x54A0`), so
  those two CSV rows need re-checking against the 560B XDF.

## 2. Mode-dependent flap behaviour with existing logic

| Option | Uses existing logic? | Notes |
|---|---|---|
| Recalibrate `0x1D077C` | yes | affects all modes |
| `cw.bit5` invert / `cw.bit0+bit3` force | yes | static, not mode-dependent |
| Select pedal source via `0x3FC188` | partly | only switches to the cruise-equivalent pedal |
| Second map selected by a sport flag | **no** | needs a code hook and a located sport-mode flag (not yet found) |

Conclusion (**LIKELY**): a true D/S-dependent flap needs a small code change, either a second
threshold map or an offset on `thr` gated by a sport flag. That is out of scope for this round, and
no flash image is produced.

## 3. Logging

`0x3FC286` (command), `0x5B92CA` (gear), `0x5B9001` (rpm byte), `0x5B96D8` (pedal), `0x3FC188`.

---

# Round 3 additions (2026-10-03)

## 4. Output path and polarity

* `0x3FC286` drives **digital output channel 12** directly: INT `0x38C0C…0x38C1C`
  (`r3 = 0xC, r4 = 1, r5 = 0x3FC286`, `bl 0xAC00`). CONFIRMED.
* It is also packed into a diagnostic status byte (EXT `0xF1BDFC`) and monitored by EXT `0xF72F40`.
* Polarity: `out = 1` at standstill (CW bit2), at low pedal and at low rpm in high gears, and `0` at
  high pedal/high rpm. With a vacuum-actuated flap, the likely reading is **output on = flap closed**.
  Status: LIKELY (needs a bench/car check).

## 5. Exact inputs (complete list from the function)

| Input | Role |
|---|---|
| `0x3FC102`, `0x3FC103`, `0x3FC104` | override/actuator-test path |
| CAL `0x1D07E8` (CW = 0x14) | bit0: forced-value enable with `0x3FC0D4`; bit2: standstill value; bit3: forced value; bit4: enable temperature-gated branch; bit5: invert |
| `0x3FE954` | alternative enable of the gated branch |
| `0x5B9307` with hysteresis CAL `0x1D07E9`/`0x1D07EB` (13/11) | engine-temperature gate (`0x5B9307` is the engine temperature that also serves as fallback for transmission temperature) — LIKELY cold-engine condition |
| `0x5B953E` vs CAL `0x1D07E6`; `0x5B90BB` vs CAL `0x1D07ED`/`0x1D07EC` | further gates (`0x5B90BB` temperature-like, see generator note) |
| `0x3FC188` | pedal source: cruise-equivalent `0x5B9822` vs pedal `0x5B96D8` |
| gear `0x5B92CA` (from CAN 0x0BA), rpm byte `0x5B9001` | map `0x1D077C` axes |
| CAL `0x1D07EA` (12) | pedal hysteresis |

No sport/program input exists (none is received; see `sport-mode.md`). Gear dependence comes only
through `0x5B92CA`.

## 6. Mode concept mapping (analysis only)

| Desired | Existing means | Needed |
|---|---|---|
| E: quiet / OEM | stock map | nothing |
| D: OEM or slightly earlier | recalibrate `0x1D077C` | affects all modes |
| S/M: open in normal running | no mode input | new mode variable selecting a second threshold map (or forcing `out=0`), inserted at EXT `0xF97F0C` |
| E + kickdown: power behaviour | B_kd `0x3FBFB3` is not used by the flap. At kickdown the pedal is 100 % (pedal>>8 = 255), which is ≥ every map entry (max 254) | the flap should already open at full pedal in every gear, subject to the hysteresis helper `0x1E74C` semantics. LIKELY no change needed |

---

# Final static pass (round 7, 2026-10-03)

This section supersedes conflicting statements earlier in this file. CONFIRMED items are re-checked by `tools/verify_770b_findings.py` (final-pass blocks).

### B. Exhaust flap, final pass (EXT `0xF97D8C`; task tables `0xFBF1E8` and `0xFBF804`)

```text
cw = CAL 0x1D07E8 (0x14: bit2, bit4)
if test 0x3FC102 && 0x3FC103:            out := 0x3FC104
elif !(cw.b4 || 0x3FE954):               out := 0
elif ( hyst(engine temp 0x5B9307 > CAL 0x1D07EB=11, band CAL 0x1D07E9=13)
         ? time-since-start 0x5B953E < CAL 0x1D07E6 (=1)
         : speed 0x5B90BB < CAL 0x1D07ED (=0) ):  out := 0
elif cw.b0 && 0x3FC0D4:                  out := cw.b3
elif speed 0x5B90BB <= CAL 0x1D07EC (=0): out := cw.b2  (stock 1)
else:
    pedal := 0x3FC188 ? 0x5B9822 : 0x5B96D8           # cruise-equivalent vs pedal (0xFFFF = 100 %)
    thr   := map 0x1D077C[gear 0x5B92CA][rpm byte 0x5B9001]
    st    := hyst helper INT 0x1E74C(state 0x3FB8B9, pedal>>8, band CAL 0x1D07EA=12, thr)   # st=1 if pedal>>8 > thr; st=0 if thr − pedal>>8 > 12
    out   := !st
if cw.b5: out := !out
0x3FC286 := out  -> DIG ch 12 with AC00 invert = 1
```

Hysteresis helper INT `0x1E74C(state, x, band, thr)`: x > thr → 1; (thr − x) > band → 0; otherwise hold. CONFIRMED.

| Input | Identity | Status |
|---|---|---|
| gear `0x5B92CA` | 0x0BA, 1…6, 7 = R, 0 = P/N/other. R (7) is beyond the map x range 0…6 → treated as gear 6 if the map helper clamps (helper clamp behaviour not re-verified) | CONFIRMED source; R handling LIKELY |
| rpm `0x5B9001` | rpm byte, map y = 10…163 (× 40 rpm → 400…6520 rpm) | LIKELY scale |
| pedal `0x5B96D8` / cruise `0x5B9822` | u16, 0xFFFF = 100 % (WPKDMN = 0xFFFF) | LIKELY |
| speed `0x5B90BB` | standstill gate (≤ 0) | HIGH CONFIDENCE (§0) |
| temperature gate | engine temp `0x5B9307` > 11 (≈ −40 °C): effectively always true → the start gate applies | CONFIRMED values |
| start gate | `0x5B953E` < 1 → out 0. The counter is 0 from init until the engine runs (it is not reset after a stall) | CONFIRMED |
| B_kd `0x3FBFB3` | not read | CONFIRMED |

Map `0x1D077C` (pedal>>8 thresholds; flap requests "open", out = 0, when pedal > threshold. Linear interpolation between rpm breakpoints, LIKELY):

| gear | ≤1000 | 1320 | 1520–2000 | 2200 | 2320 | 2520 | 3000 | ≥4000 |
|---|---|---|---|---|---|---|---|---|
| 0 | 254 | 254 | 254 | 254 | 254 | 254 | 254 | 254 |
| 1 | 254 | 129 | 129 | 129 | 129 | 0 | 0 | 0 |
| 2 | 254 | 129 | 129 | 129 | 0 | 0 | 0 | 0 |
| 3 | 254 | 254 | 254/232 | 232 | 232 | 13 | 13 | 0 |
| 4 | 254 | 254 | 254 | 232 | 232 | 13 | 13 | 0 |
| 5 | 254 | 254 | 254 | 232 | 232 | 205 | 13 | 0 |
| 6 | 254 | 254 | 254 | 232 | 232 | 205 | 12 | 0 |

(Gear 3 reaches 232 at the 2000 rpm breakpoint; gears 4–6 only at 2200 rpm.)

**Polarity: command `0x3FC286` = 1 means "flap closed" (quiet).** Logic level HIGH CONFIDENCE; electrically "solenoid energised = vacuum = closed" LIKELY.
1. Load/rpm semantics: at ≥ 4000 rpm in every driving gear, and at ≥ 2320–2520 rpm in gears 1–2, the threshold is 0, so out = 0 with any pedal. Full pedal (255 > 254) gives out = 0 in every gear. OEM flaps open at high load/rpm for flow, so 0 = open.
2. Default states: standstill → CW bit2 = 1 even when revving (stationary-noise behaviour). Ignition on before the first start (start counter 0) → 0. A de-energised vacuum valve (no vacuum with the engine off anyway) is the natural "0" state, and spring-open is the usual BMW fail-safe.
3. AC00 is called with invert = 1 on port 4, whose channels are all inverted. This is consistent with an active-low port where command 1 = driver on.

Remaining doubt: the physical actuator construction. Confirm by bench: with the engine idling at standstill, unplug the solenoid. The flap should move to its open (spring) position.

OEM behaviour (stock CAL):

| Situation | out | Flap |
|---|---|---|
| Ignition on, engine not yet started | 0 | open / de-energised |
| Idle at standstill, also when revving at standstill | 1 (CW bit2) | closed |
| Moving, low load (pedal below threshold), < ~2000 rpm | 1 | closed |
| Gear 1–2, 1320–2320 rpm, pedal > ~51 % (129) | 0 | open |
| Gear 3–6, 2200–2320 rpm (gear 3 from 2000 rpm), pedal > ~91 % (232) | 0 | open |
| Gear 3–6, 2520–3000 rpm, pedal > ~5 % (13); gear 5–6 at 2520 rpm > ~80 % (205) | 0 | open |
| ≥ 4000 rpm in a driving gear, any pedal > 0 | 0 | open |
| Overrun (pedal 0) at a 0 threshold | hold | stays in its previous state (hysteresis hold, since 0 − 0 is not > 12) |
| Kickdown (pedal = 100 %, plus detent) | 0 in every gear when moving | open (via pedal 255 > 254, not via B_kd) |
| Gear 0 (N/P/other) while moving | 1 unless pedal 100 % | closed |
| Cruise control active (`0x3FC188`) | uses the cruise-equivalent pedal `0x5B9822` | as above |


### C. Unresolved items / what would resolve them

* Vehicle-speed unit (1.25 vs 0.625 km/h per bit): log `0x5B90BB` against the dash speed (one point is enough).
* `0x5B9308` = radiator-outlet sensor: log it against `0x5B9307` during warm-up (the outlet temperature lags until the thermostat opens).
* `0x5B854A` (0x1B5 byte 3 low nibble) meaning: log it while switching A/C on/off and at high refrigerant pressure.
* PWM ch 0/1 use, ch 5 and DIG ch 4 (DMTL?), ch 8 role: scope the ECU pins / actuator tests via `0x3FC11E/0x3FC155` (ch 5), `0x3FC122/0x3FC159` (ch 4), `0x3FC129/0x3FC15A` (ch 8).
* After-run state word `0x3FE198` bit 15 and counter `0x3FE19A` units; task-tick periods (tables EXT `0xFBF2C8` task 0x17, `0xFBF71C` task 0x2B).
* Output-stage diagnostic mapping (NOT COMPLETED).
* Flap physical polarity (bench test above). EGS firmware is not needed for any item here.
