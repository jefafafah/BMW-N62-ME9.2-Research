# Exhaust flap (770B) — round 2

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
