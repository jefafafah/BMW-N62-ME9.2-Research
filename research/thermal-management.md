# Thermal management (770B) — round 2

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
