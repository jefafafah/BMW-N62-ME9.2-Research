# Thermal management (770B) — round 2

Address conventions as in `research/aevab-redabm.md`.

## 1. Map-controlled thermostat target — candidate found

| Item | Evidence | Status |
|---|---|---|
| Map `0x1D08A8` (8×8 u8), EXT fn `0xF9E148` | values only 177 and 216. With the common Bosch byte temperature scale (0.75 °C/bit, −48 °C offset) these are **84.75 °C** and **114 °C**: the classic BMW two-level target (economy ≈ 110 °C at part load, ≈ 85–90 °C at high load) | **LIKELY** function; scaling HYPOTHESIS |
| x axis | 0, 48, 88, 96, 152, 160, 164, 184 | quantity open; the function reads `0x5B90BB` (speed-like) |
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
