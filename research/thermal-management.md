# Thermal management (770B) — round 2

> **Final-pass status:** electric fan = PWM ch 9 (HIGH CONFIDENCE), thermostat heater DIG ch 6 promoted to HIGH CONFIDENCE, full PWM/digital channel table; 0x5B90BB is vehicle speed. See the *Final static pass* section at the end of this file.


Address conventions as in `research/aevab-redabm.md`.

## 1. Map-controlled thermostat target — candidate found

| Item | Evidence | Status |
|---|---|---|
| Map `0x1D08A8` (8×8 u8), EXT fn `0xF9E148` | values only 177 and 216. With the common Bosch byte temperature scale (0.75 °C/bit, −48 °C offset) these are **84.75 °C** and **114 °C**: the classic BMW two-level target (economy ≈ 110 °C at part load, ≈ 85–90 °C at high load) | **LIKELY** function; scaling HYPOTHESIS |
| x axis | 0, 48, 88, 96, 152, 160, 164, 184 | quantity open; the function reads `0x5B90BB` (temperature-like, see round-3 section) |
| y axis | 77, 84, 97, 111, 117, 131, 137, 144 | quantity open (load ×0.75 % → 58…108 %, or intake-air temperature) |
| Related scalars | `0x1D08FB = 0xB1` (177 → 84.75 °C), `0x1D08FC = 0xE0` (224 → 120 °C), `0x1D08A4…A6`, `0x1D08FA`, `0x1D0938/0x1D093A` | HYPOTHESIS |

Map shape: the low target (177) is used at high x for every y and at increasing x as y rises. In
other words, the low temperature is selected under high load/speed. Writes: `0x3FC29B…0x3FC29D`,
`0x5B8E24/26`, `0x5B91D1/D3`, `0x5BBAC7`.

## 2. Fan strategy, load-dependent cooling

Not located in this round. Approach for next round: E65 N62 drives the electric fan by PWM. Find
MIOS (`0x306000`) PWM channel users and trace the duty-cycle source back to a coolant/AC-pressure
map.

## 3. Interaction with performance vs. efficiency

* Higher target (114 °C) lowers friction and improves part-load BSFC. The 85 °C level supports
  knock margin and volumetric efficiency at high load.
* Mode-dependent targets would need a selector on the map output (code change) or a recalibrated
  map that reacts to load faster. **HYPOTHESIS / UNTESTED.**

## 4. Logging

`0x3FC29B…0x3FC29D`, `0x5B91D1/D3` (outputs of `0xF9E148`, meanings open), coolant temperature (not
located).

---

# Round 3 additions (2026-10-03)

## 5. Coolant-target function EXT `0xF9E148` — partial decode

* Hysteresis flag `0x3FC29D`: `0x5B90BB` vs CAL `0x1D08FC` (0xE0 → 120 °C if 0.75 °C/−48) ± CAL `0x1D08A6`/2.
* Hysteresis flag `0x3FC29C`: `0x5B9306` vs CAL `0x1D08FA` (0x40) ± CAL `0x1D08A4`/2.
* EGS input: when both EGS messages are valid (`0x3FBED2`, `0x3FBED4`), bit `0x5BBAC7.2` = exactly one
  of `0x3FBEDB`/`0x3FBEDC` set (0x0B5 byte4 bits 6/7). Otherwise it is CAL `0x1D08FE` bit0 (= 1). The
  result goes to `0x3FE2EF`. With coding bit `0x3FE313.0` set, `0x3FE2EF` directly sets the bit.
  Meaning: HYPOTHESIS (transmission-side request that influences the coolant target or thermostat).
* Map `0x1D08A8` (two-level ≈ 114/85 °C) as in round 2; its axis inputs are still to be confirmed.
  `0x5B90BB` is a candidate for one axis.

## 6. Fan / thermostat output / high-load protection

Not located in round 3. Output channel functions (like INT `0xAC00` used for the flap) are the
entry point: next round, enumerate all `bl 0xAC00` calls with constant channel numbers to find the
thermostat-heater and fan outputs.

## 7. Low-load vs high-load target

The only distinguishing logic found is the two-level map `0x1D08A8` (high target at low x/y, low
target at high x/y) plus the hysteresis flags above. A mode-dependent target would need a selector
on the map output. Status: HYPOTHESIS.

---

# Round 4 additions (2026-10-03): output stage

Digital output stage INT `0x38A54` (driver INT `0xAC00(channel, invert, value)`; `tools/me9_trace.py outputs`):

| Channel | Command RAM | Writer | Identification | Status |
|---|---|---|---|---|
| 6 | `0x3FC29B` | EXT `0xF9E148` (coolant-target function; actuator-test override `0x3FC13A`/`0x3FC131`) | **map-thermostat heater** | LIKELY |
| 7 | `0x3FC29A` | EXT `0xF9DF20` (inputs `0x5B8A27/28` from private-bus frames 0x184/0x18C) | relay tied to the Valvetronic node | HYPOTHESIS |
| 8 | `0x3FC29F` | EXT `0xF9E6A4` (rpm, full load, temperatures, curve CAL `0x1CBCCC`) | cooling-related relay (fan stage / pump) | HYPOTHESIS |
| 4 | `0x3FC2B5` | EXT `0xF9ED98` / `0xF9EB30` (they also produce lambda multiplier `0x5B8E3A`, gated by `0x3FC23B`) | **canister-purge valve** | LIKELY |
| 12 | `0x3FC286` | EXT `0xF97D8C` | exhaust flap | CONFIRMED |
| 23 / 24 | `0x3FC08D` / `0x3FC08E` | written indirectly; read by lambda functions | lambda-sensor heaters | HYPOTHESIS |
| 2, 5, 9, 10, 18–22, 38–41 | `0x3FC0B7`, `0x5B8ECA`, `0x3FBFC3`, `0x3FC285`, `0x3FBEEE/EF`, `0x3FC200/01/02`, `0x3FC26F`, `0x3FBEED` | various | not identified | open |

Correction: INT `0x388B0` / driver `0xAB88` (channels 0–11) are digital **inputs** (port image
`0x3FA374`), not PWM outputs.

The electric fan (PWM) and any PWM thermostat drive are not on the digital stage. Expected on TPU/MIOS
channels (round 5). Post-run cooling and A/C pressure contribution: not located.

---

# Final static pass (round 7, 2026-10-03)

This section supersedes conflicting statements earlier in this file. CONFIRMED items are re-checked by `tools/verify_770b_findings.py` (final-pass blocks).

### 0. Corrections to earlier rounds

| Item | Earlier | Now | Evidence | Status |
|---|---|---|---|---|
| RAM `0x5B90BB` | round 3: "temperature-like" | **vehicle speed byte**. It is `0x5B9D20`/160, filtered (INT `0x3D2C0…0x3D2E0`), and forced to 0 on signal timeout (counter `0x3FB15C` vs CAL `0x1C6F1E`, INT `0x3D294`). Source `0x5B9D1C` = CAL `0x1C6F18` (0x013F9A2F) / (10·period) from the period-capture driver INT `0x66DD4` (MIOS channel via table INT `0x157BC`), INT `0x3CFD0…0x3D014`; period > 0x1900 → 0. Standstill flag `0x3FC0CE` comes from the same function | K/period from a frequency input with a timeout-to-zero, used as the standstill gate of the flap and as the de-rating input of the fan | **HIGH CONFIDENCE** (identity). Unit HYPOTHESIS: 1.25 km/h/bit if `0x5B9D20` is 1/128 km/h, 0.625 km/h/bit if 1/256 |
| Exhaust-flap gate (round 2 pseudo-code) | `elif (cw.bit4 || 0x3FE954) && gate: out=0` | `if !(cw.bit4 || 0x3FE954) or gate: out=0` (EXT `0xF97DE8`/`0xF97DF8` branch to `0xF97E70`). With stock CW = 0x14, bit4 is set, so there is no behavioural difference | disassembly | CONFIRMED |
| Flap gate inputs | "engine-temperature gate", "0x5B953E further gate" | `0x5B953E` is the **time-since-start counter** (incremented while engine-running flag `0x3FBFB7` is set, INT `0x3B8CC`; zeroed only in init EXT `0xF337EC`) | see §B | CONFIRMED (counter), LIKELY (meaning) |
| RAM `0x3FBFB7` | — | **engine running**: set when rpm byte `0x5B9001` > curve CAL `0x1CCCA0`(engine temperature `0x5B9307`), cleared when below curve CAL `0x1CCC98`(`0x5B9306`) (INT `0x3B888`) | disassembly | HIGH CONFIDENCE |
| PWM table layout (vanos.md) | "+8 period factor" | +0 logical id (u8), +4 hw channel (u32), **+8 period multiplier** (u32: 50 for driver 0, 31 for driver 1), +0xD driver index, +0xE default duty, **+0x10 default period factor**, +0x12 driver polarity arg, +0x13 invert duty (API: `duty := 10000 − duty`, INT `0x672F0…0x672FC`). Period counts = multiplier × r5. r5 is the period in **0.1 ms** (see ch 9: r5 = 10000/f with f = 10 or 100) | INT `0x671D4…0x67298` | CONFIRMED (arithmetic). 0.1 ms unit LIKELY |
| Digital output ch 4 = purge valve (round 4, LIKELY) | | Challenged. PWM logical ch 4 is the variable-duty, variable-period valve with a duty×period flow product (classic TEV). Digital ch 4 `0x3FC2B5` and PWM ch 5 `0x3FC2AF` are written by the same module, which also runs in the after-run task → **DMTL (tank-leak module) valve/pump HYPOTHESIS** | §A.1, §A.5 | downgrade digital-ch-4 "purge" to HYPOTHESIS |

### A. Cooling / thermostat / fan

#### A.1 PWM logical channels (API INT `0x671AC`, copy EXT `0xFD5324`; table INT `0x156AC`)

Driver 0 = MIOS MDASM (hw 11/12/30/31), driver 1 = MIOS MPWMSM (hw 0/1/3/17/18/19); both use IO base `0x306000`. Hardware mapping LIKELY from MPC555 channel numbering.

| Lch | hw | drv | default duty / period (0.1 ms) | inv | Call sites (fn) | r4 duty source | r5 period | Role | Status |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 0x12 | 1 | 0 / 5 | 0 | none (neither API) | — | — | unused, or driven outside the API | NOT COMPLETED |
| 1 | 0x00 | 1 | 500 / 30 | 0 | none | — | — | as ch 0 | NOT COMPLETED |
| 2,7,3,6 | 0x0C,0x0B,0x1E,0x1F | 0 | — | 1 | INT `0x4FAE0/0x4FAF0/0x4FB00/0x4FB10` (INT `0x4FA8C`) | VANOS duty (obj +0x10) | 0x28 = 4 ms (250 Hz) | VANOS | CONFIRMED mapping (vanos.md) |
| 4 | 0x13 | 1 | 10000 / 250 | 1 | INT `0x5F320/0x5F334/0x5F358`, EXT `0xFD5324` @ INT `0x5F36C` (fn INT `0x5F2B8`); EXT `0xFB28A0` (fn `0xFB2860`) | `0x5B9417`·39 (≈ byte→0.01 %, saturating helper INT `0x1DD78`) | `0x5B8D4A`·5 (= byte × 0.5 ms; CAL `0x1C9A5F` = 140 → 70 ms, `0x1C9A60` = 46 → 23 ms, or `0x5B9414`) | **canister-purge valve (TEV)** | LIKELY |
| 5 | 0x11 | 1 | 4000 / 50 | 1 | EXT `0xF2DA2C/40` (`0xF2DA04`), `0xF840A8…F4` (`0xF84070`), `0xFB28E0/F4` (`0xFB28B8`) | on/off only: 10000 if `0x3FC2AF` else 0 | 0x32 = 5 ms (200 Hz) | on/off actuator from module EXT `0xF9ED98`/`0xF9EB30`/after-run `0xFB38FC`: **DMTL pump HYPOTHESIS** | HYPOTHESIS |
| 8 | 0x01 | 1 | 4000 / 60 | 1 | EXT `0xF2C9E4` (`0xF2C9C0`), `0xF82404` (`0xF823E0`) | `0x5B9C12` (0.01 %) | `0x5B9052` = CAL `0x1C5486` = 100 → 10 ms (100 Hz) | fixed-level status/enable line (see A.4) | role HYPOTHESIS |
| 9 | 0x03 | 1 | 10000 / 70 | 1 | EXT `0xF2D7C8` (`0xF2D78C`, init task), `0xF57914` (`0xF578D8`, fan task), `0xFB27C0` (`0xFB2784`, task 0x2B) | `0x5B9470`·10000/255 | 10000/`0x5B946F` (`0x5B946F` = 100 → 10 ms / 100 Hz; 10 → 100 ms / 10 Hz in after-run) | **electric radiator fan** | **HIGH CONFIDENCE** |

Static-level setters EXT `0xFE3AB8/0xFE3D74/0xFE3DD0/0xFE3DFC/0xFE3E5C` call the API with r4 = 10000 and r5 = 0. With r5 = 0 the API takes the static path INT `0x67208…0x6723C` (pin level only). They cover ch 2,3,6,7,8,9,4,5 and are called in pairs from EXT `0xFE3EB8…0xFE3EC8` / `0xFE3F08…0xFE3F18`. Role (init/shutdown or output-stage test): HYPOTHESIS.

Other PWM-like paths, outside the 10-channel table:
* INT `0x6734C`: signed-duty API over output table INT `0x14E48` with 2 bridge channels: ch 0 from INT `0x3464C`, ch 1 from INT `0x4F418` (wrapper INT `0x4F3F4`), plus EXT `0xFB2644` and `0xFE3B90/0xFE3BB8` (−0x8000). H-bridge actuators, throttle-motor candidate. HYPOTHESIS. Not fan/thermostat.
* EXT `0xF12018`: direct on/off of MIOS channel 16 (IO `0x306086`), test sequence EXT `0xF36FE8` (vanos.md).

#### A.2 Electric fan, decoded (EXT `0xF5A65C`, task table EXT `0xFBF2C8` entry 19; output fn `0xF578D8` is the next entry)

```text
## status byte 0x5BBAC8: b0 engine-ran latch, b1 fan on, b2 IHKA hyst, b3 high-speed cut, b4 cut active, b5 on-latch
b3 := hyst(speed 0x5B90BB; set > CAL 0x1D0984=112, clear < CAL 0x1D0983=104)
if b3:            0x5B8E2A := CAL 0x1D09E4 (150); req := 0                     # high-speed fan cut
elif 0x5B8E2A>0:  0x5B8E2A -= 1;  req := 0                                     # hold-off after the cut ends
else:
  b2   := hyst(IHKA 0x5B854A; set > CAL 0x1D0986=10, clear < CAL 0x1D0985=5)
  ac   := b2 ? curve 0x1D09A0(0x5B854A) : curve 0x1D0988(0x5B854A)             # identical curves in stock
  cool := curve 0x1D09CC(coolant temp 2 0x5B9308)
  base := max(ac, cool)
  tot  := (EGS valid 0x3FBED2&&0x3FBED4) ? 0x5B9229 : CAL 0x1D09E1 (216)        # transmission oil temp
  if engine running 0x3FBFB7:  0x5B9476 := map 0x1D0958(tot, speed)           # else the last value is held
  req  := clamp(base + 0x5B9476, 0..255) * curve 0x1D0940(speed) >> 8
0x5B9475 := req
0x5B9473 := rising: immediately; falling: at most CAL 0x1CBCFA (13) per call  # ramp-down limiter
0x5B9471 := CAL 0x1CBCF8 (0) > 0 ? 0x5B9473 : Ubatt-compensated(0x5B9473, 0x5B930C)
            # y = (((x−26)·0xD555>>16)+85)·(0x8200/U)>>8 −85)·0x999A>>15 + 26; factor 1.0 at U = 130 (13.0 V if 0.1 V/bit, LIKELY)
b1 on  if 0x3FBFB7 && req >= CAL 0x1CBCFB (26 = 10 %)  -> 0x5B9472 := 0x5B9471
b1 off if req < CAL 0x1CBCFC (21 = 8 %)                  (0x5B9472 := 0 when not on)
on edge: run-on timer 0x5B8E28 := CAL 0x1D093C (95)
0x3FC2A9 (fan active) := (b1 || run-on>0) && !b4
min duty 0x5BBAC9 := active ? CAL 0x1CBCFB (26 = 10 %) : CAL 0x1D09B5 (18 = 7 %)   # "valid but off" floor
EXT 0xF5A53C (duty):
  if test 0x3FC147:           0x5B9470 := 0x5B8A92
  elif after-run 0x3FC2A8:    0x5B9470 := 0x5B9474
  elif 0x3FC2A7 || engine-standstill 0x3FBEFB:  0x5B9470 := 0
  else 0x5B9470 := clamp(curve 0x1D09B8(0x5B9472), 0x5BBAC9, CAL 0x1D09B6 = 238 = 93 %)
  0x5B946F := 0x3FC2A8 ? 10 : 100            # PWM frequency byte (Hz) -> ch 9 period 10000/f (0.1 ms)
```

Stock data (excerpt):

| Table | Input → output (duty %) |
|---|---|
| curve `0x1D09CC` (coolant temp 2) | 56 °C 10 %, 78 °C 12 %, 85.5 °C 20 %, 90 °C 30 %, 95 °C 47 %, 98 °C 60 %, 101 °C 73 %, 104 °C 91 % |
| curves `0x1D0988`/`0x1D09A0` (IHKA stage 0…15) | 0:0, 1:10, 2:18, 3:27, 5:43, 7:55, 9:65, 11:75, 13:83, 15:90 % |
| map `0x1D0958` (trans oil temp × speed) | ≤ 99.75 °C 0; 105 °C 15 %; 114 °C 25 %; 120 °C 81 %; 123 °C 90 %; 0 at speed byte ≥ 120 |
| curve `0x1D0940` (speed → factor) | 1.0 up to byte 96, linear to 0 at byte 112 |
| curve `0x1D09B8` (output shaping) | near-identity 0…235 |

| Item | RAM / CAL | Behaviour | Status |
|---|---|---|---|
| Fan request (pre-limit) | `0x5B9475` | as above | CONFIRMED |
| Fan duty (byte) / PWM | `0x5B9470` → PWM ch 9 (MPWMSM hw 3), duty·10000/255, invert flag set | 100 Hz normally, 10 Hz in after-run | CONFIRMED path; role HIGH CONFIDENCE |
| Coolant contribution | curve `0x1D09CC` on `0x5B9308` | `0x5B9308` = NTC curve CAL `0x1CE454` of ADC byte `0x5B933B`, substitute CAL `0x1CE47D` = 184 (90 °C) outside CAL `0x1CE47E…7F` or on fault `0x3FE46D` (EXT `0xF320E8`). This is a second coolant sensor, distinct from engine temperature `0x5B9307`: **radiator-outlet temperature LIKELY** (the N62 has one) | CONFIRMED structure, sensor LIKELY |
| A/C contribution | `0x5B854A` = CAN **0x1B5** byte 3 low nibble (message object 3, raw read INT `0x63730`, EXT `0xF3BE98…0xF3BF5C`). 0xF or timeout → 4 | IHKA fan-request stage (the E65 refrigerant-pressure sensor feeds IHKA, not the DME). Missing or invalid frame → stage 4 → 35 % | CONFIRMED decode; meaning LIKELY |
| Transmission-oil contribution | `0x5B9229` (0x0B5 byte 7) via map `0x1D0958`; EGS invalid → 114 °C substitute → +25 % | additive | CONFIRMED |
| Vehicle-speed influence | `0x5B90BB` | de-rating curve plus hard cut with 112/104 hysteresis and a 150-call hold-off; trans-oil term 0 above byte 120 | CONFIRMED logic, speed unit HYPOTHESIS |
| High-load cooling | — | **no load or rpm input to the fan**. High load acts through the thermostat target (A.3) | CONFIRMED (absence within `0xF5A65C`) |
| Emergency / substitute | — | no "100 % on overheat" branch; max 93 %. Substitutes: IHKA missing 35 %, temp-2 fault 30 %, EGS missing +25 %. Duty forced to 0 at engine standstill (`0x3FBEFB`, outside after-run) | CONFIRMED in this fn; external fan-module fail-safe UNTESTED |
| Battery-voltage compensation | `0x5B930C` | factor 0x8200/U | CONFIRMED arithmetic; unit LIKELY |
| Run-on at switch-off | `0x5B8E28`, CAL `0x1D093C` = 95 | holds the 10 % floor for 95 calls | CONFIRMED |
| Fan duty consumers | EXT `0xF892A4` (stores with `0x5B930A` into `0x5B8BEC/F0`, generator/electrical-load area), EXT `0xF7DCF4`, EXT `0xF74BA8` (reads CAL `0x1D09B5/B6`, output diagnosis candidate) | | HYPOTHESIS |

**After-run (EXT `0xFB37D0`, task 0x2B table EXT `0xFBF71C`, scheduled from EXT `0xFB57C8` every 10 slow ticks):**
`0x3FC2A7` = engine-ran latch (`0x5BBAC8`.b0) && `0x3FE198` bit 0x8000 (after-run state, HYPOTHESIS).
If `0x3FC2A7`: `0x3FC2A8` = (`0x3FE19A` < CAL `0x1CF8D2`(50) − 3) && engine temp `0x5B9307` > CAL `0x1D09E2` (222 = 118.5 °C).
`0x5B9474` = CAL `0x1CBCF9` (51 = 20 %) if the latch is set and temp > 118.5 °C, else 0. Then `0xF5A53C` runs.
Result: post-run fan at **20 % duty with a 10 Hz PWM** while the engine is hot and the after-run counter is below its limit; otherwise the signal is 0 (fan off). CONFIRMED logic; "after-run" naming LIKELY. Units of `0x3FE19A` are open.

CAN/LIN check: DME TX frames are only 0x0A8/0x0A9/0x0AA (bus A) and 0x1FF/0x105/0x10D (bus B, Valvetronic). There is no fan-module frame and no LIN driver was seen, so the fan is **PWM only** (HIGH CONFIDENCE).

#### A.3 Map thermostat (EXT `0xF9E148`), full decode. Channel 6 promoted

```text
if test 0x3FC13A:  0x3FC29B := 0x3FC131 ; return
0x3FC29D := hyst(speed 0x5B90BB > CAL 0x1D08FC (224), band CAL 0x1D08A6/2 = 2)         # very high speed
0x3FC29C := hyst(0x5B9306 < CAL 0x1D08FA (64), band CAL 0x1D08A4/2 = 1)                 # cold intake/ambient (64 = 0 °C)
0x5BBAC7.b2 := coding 0x3FE313.0 ? 0x3FE2EF : EGS valid ? (0x3FBEDB xor 0x3FBEDC) : CAL 0x1D08FE.0 (=1)
0x3FE2EF := 0x5BBAC7.b2
if IHKA 0x5B8548 || 0x5BBAC7.b2:  target := CAL 0x1D08FB (177 = 84.75 °C)               # force low target
elif full load 0x5B8F26:          target := map6x6 CAL 0x1D0900 (speed, 0x5B9BA2)
elif 0x3FC29D || 0x3FC29C:        target := map CAL 0x1D08A8 (speed, 0x5B9306)
else:                             target := min(map 0x1D0900(speed, 0x5B9BA2), map 0x1D08A8(speed, 0x5B9306))
0x5B91D1 := target
## decreases of the target are delayed by CAL 0x1D093A (250) calls (timer 0x5B8E24) while the heater is off; increases apply at once
0x5B91D3 := delayed target
diff := 0x5B91D3 − engine temp 0x5B9307
heater 0x3FC29B: ON  when diff < −CAL 0x1D08A5/2 (engine hotter than target); min-on timer 0x5B8E26 := CAL 0x1D0938 (50)
                 OFF when timer expired and diff > +CAL 0x1D08A5/2
0x3FC29B -> digital output channel 6 (INT 0x38B1C..0x38B2C, AC00 invert = 1)
```

* Map `0x1D08A8` axes: x = **vehicle speed** `0x5B90BB` (0…184), y = `0x5B9306` (77…144 → 9.75…60 °C: intake/ambient temperature LIKELY). The low target 177 applies at high speed and/or high intake temperature.
* Map `0x1D0900` (6×6, group helper INT `0x1836C`): x = speed (32…184), y = `0x5B9BA2` (u16 2000…4400, load or rpm; no direct writer found). Values 216/177.
* IHKA flag `0x5B8548` = CAN 0x1B5 byte 3: bits 4–5 ∈ {2,3} or bits 6–7 ∈ {1,3} (3 = invalid → forces low target). `0x3FBEE2` = bits 4–5 == 1. Meaning HYPOTHESIS (IHKA "reduce coolant temperature" request).

**Promotion: digital output ch 6 = map-thermostat heater, now HIGH CONFIDENCE.** Two independent lines:
1. Control law: a two-point controller energises the output when engine temperature exceeds a target of 84.75 or 114 °C chosen from speed, load and intake-air maps. It has a minimum on-time and a delay before the target is lowered. This is the BMW Kennfeld-thermostat heater behaviour (heater on → thermostat opens further → lower coolant temperature).
2. The command byte drives the digital output stage directly (channel 6) and has its own actuator-test override pair `0x3FC13A`/`0x3FC131`, the same pattern as every other actuator.

It is a plain on/off output, not PWM.

#### A.4 PWM ch 8 (EXT `0xF7BDC0`; copies in task tables `0xFBED80`, `0xFBF208`, `0xFBF7B8`)

```text
if 0x5B8EF8: duty := 0
cond := 0x3FE954 && 0x3FDCBD          # 0x3FE954: KL15/power state machine INT 0x3988C; 0x3FDCBD: written with relay outputs 0x3FBEED/0x3FBEEE
deb  := debounce(cond, CAL 0x1C5487 = 100)  (state 0x3FAD62)
if cond:  duty := 0x5B886B ? CAL 0x1C5480 (2000 = 20 %)
                 : test (0x3FC102 && 0x3FC129 && 0x3FC15A) ? CAL 0x1C5484 (5000)
                 : !deb ? CAL 0x1C5484 (50 %) : CAL 0x1C5482 (0)
else:     duty := CAL 0x1C5482 (0)
```

`0x5B886B` is a debounced flag (CAL `0x1C38DF`) from EXT `0xF76E48`, which reads the private-bus data `0x5B8A1D…0x5B8A36` (frames 0x184/0x18C, Valvetronic node). So ch 8 sends 50 % for ~100 calls after power-up, then 0 %, and 20 % when the `0x5B886B` condition holds. That is a fixed-level status/enable signal. Role: **HYPOTHESIS** (Valvetronic-ECU enable/status line, or electronics-box fan). Not the radiator fan, not the thermostat. Live check: scope hw MIOS ch 1 pin / identify the ECU pin.

#### A.5 Digital output stage INT `0x38A54` (driver INT `0xAC00(ch, invert, value)`; invert ≠ 0 → value := !value)

| Ch | Port/bit (INT `0x14E48`) | inv | Command (test override enable/value) | Writer / meaning | Status |
|---|---|---|---|---|---|
| 2 | 6/16 | 0 | `0x3FC0B7`, only when output-test fault `0x3FBE99` = 0 | open | open |
| 3 | 3/11 | 1 | (`0x3FC107`/`0x3FC12D`) else `0x3FE217`.b2 ‖ `0x5B87D5`.b0 | open | open |
| 4 | 3/8 | 1 | `0x3FC2B5` | EXT `0xF9ED98`/`0xF9EB30`/`0xFB38FC` (after-run task) | DMTL valve HYPOTHESIS (was "purge LIKELY") |
| 5 | 3/12 | 1 | `0x5B8ECA` | open | open |
| 6 | 3/9 | 1 | `0x3FC29B` (test `0x3FC13A`/`0x3FC131` in writer) | map-thermostat heater | **HIGH CONFIDENCE** |
| 7 | 3/13 | 1 | (`0x3FC109`/`0x3FC12F`) else `0x3FC29A` | EXT `0xF9DF20` (private-bus inputs) | HYPOTHESIS (round 4) |
| 8 | 3/17 | 1 | `0x3FC29F` | EXT `0xF9E6A4` (rpm, full load, temperatures, curve `0x1CBCCC`) | HYPOTHESIS (cooling-related relay; *not* the fan, which is PWM ch 9) |
| 9 | 3/16 | 1 | `0x3FBFC3` | open | open |
| 10 | 6/2 | 1 | (`0x3FC10C`/`0x3FC130`) else `0x3FC285` && !`0x3FB830`.b5 | open | open |
| 12 | 4/16 | 1 | `0x3FC286` | exhaust flap | CONFIRMED |
| 13–16 | 0/5–8 | 0 | (`0x3FC11A/53`, `0x3FC11B/52`, `0x3FC118/51`, `0x3FC119/50`) else `0x3FBFA4`, `0x3FBFA5`, `0x3FBF9D`, `0x3FBF9E` | open (group of 4) | open |
| 18 / 19 | 8/6, 8/7 | 1 / 0 | `0x3FBEEE` / `0x3FBEEF` | INT `0x3988C`, EXT `0xF2783C` (power state machine) | relay HYPOTHESIS |
| 20, 21, 22 | 9/14, 9/12, 10/26 | 0 | `0x3FC200`, `0x3FC26F`, `0x3FC201` | open | open |
| 23 / 24 | 0/9, 0/10 | 0 | `0x3FC08D` / `0x3FC08E` | lambda heaters | HYPOTHESIS |
| 38 / 39 | 4/6, 4/7 | 1 | `0x3FC202` (driver INT `0xA418`, under interrupt lock) | open | open |
| 40 | 9/13 | 0 | `0x3FBEED` | power state machine (with `0x3FDCBD`) | main-relay HYPOTHESIS |
| 41 | 9/15 | 0 | (`0x3FC121`/`0x3FC158`) else `0x3FBFBE` | open | open |

The invert flag is uniform on ports 3 and 4 (inverted) and on ports 0 and 9 (not inverted), and mixed on ports 6 and 8. It mostly follows the port, which is consistent with "application command 1 = energise" plus per-port hardware polarity compensation. LIKELY, not proven.
Output-stage diagnostic IDs (DTC/fault-path numbers per channel): **NOT COMPLETED**. The fault flags `0x3FBE99/0x3FBE9B` and the pin-readback helper EXT `0xFD52E0` (used for PWM ch 4 → `0x3FC0CD`) are entry points.

#### A.6 Final channel-role table

| Output | Role | Status |
|---|---|---|
| PWM 2/7/3/6 | VANOS solenoids (4 PWM outputs) | CONFIRMED mapping, name HIGH CONFIDENCE |
| PWM 9 (MPWMSM 3) | electric radiator fan (100 Hz, 7–93 %, after-run 10 Hz 20 %) | HIGH CONFIDENCE |
| PWM 4 (MPWMSM 19) | canister-purge valve (variable duty and period, 14–43 Hz) | LIKELY |
| PWM 5 (MPWMSM 17) | on/off 200 Hz actuator from the tank-system module: DMTL pump | HYPOTHESIS |
| PWM 8 (MPWMSM 1) | fixed-level status/enable signal (Valvetronic-related or E-box fan) | HYPOTHESIS |
| PWM 0, 1 | no application call site | NOT COMPLETED |
| DIG 6 | map-thermostat heater | HIGH CONFIDENCE |
| DIG 12 | exhaust-flap solenoid | CONFIRMED |
| DIG 4 | DMTL changeover valve (or purge-related) | HYPOTHESIS |
| DIG 8 | cooling-related relay (`0xF9E6A4`) | HYPOTHESIS |
| Signed API `0x6734C` ch 0/1 | H-bridge (throttle candidate) | HYPOTHESIS |


### C. Unresolved items / what would resolve them

* Vehicle-speed unit (1.25 vs 0.625 km/h per bit): log `0x5B90BB` against the dash speed (one point is enough).
* `0x5B9308` = radiator-outlet sensor: log it against `0x5B9307` during warm-up (the outlet temperature lags until the thermostat opens).
* `0x5B854A` (0x1B5 byte 3 low nibble) meaning: log it while switching A/C on/off and at high refrigerant pressure.
* PWM ch 0/1 use, ch 5 and DIG ch 4 (DMTL?), ch 8 role: scope the ECU pins / actuator tests via `0x3FC11E/0x3FC155` (ch 5), `0x3FC122/0x3FC159` (ch 4), `0x3FC129/0x3FC15A` (ch 8).
* After-run state word `0x3FE198` bit 15 and counter `0x3FE19A` units; task-tick periods (tables EXT `0xFBF2C8` task 0x17, `0xFBF71C` task 0x2B).
* Output-stage diagnostic mapping (NOT COMPLETED).
* Flap physical polarity (bench test above). EGS firmware is not needed for any item here.
