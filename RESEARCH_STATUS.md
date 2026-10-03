# Research status

Last update: 2026-10-03 (static-analysis round 3).

## Confidence model

- **CONFIRMED** — reproduced directly from the provided binary/reference files or unambiguous code/data; round-2 items are re-checked by `tools/verify_770b_findings.py`.
- **HIGH CONFIDENCE** — two independent lines of evidence (e.g. 770B code semantics + 560B XDF description/order), where one line depends on a reference not re-verified in the current round.
- **LIKELY** — strongly supported by code structure, table geometry or local alignment, but not proven end-to-end.
- **HYPOTHESIS** — plausible interpretation awaiting validation.
- **REJECTED** — tested and contradicted by evidence.
- **UNTESTED** — proposed calibration/behaviour not yet run on a vehicle.

## Current status summary

| Item | Status | Notes |
|---|---|---|
| Target external flash is 1 MiB | CONFIRMED | `28f200f3t.bin` is 1,048,576 bytes |
| Bosch HW `0261209002` | CONFIRMED | dump metadata/string data and source label |
| Bosch SW `1037389760` / 770B family | CONFIRMED | present in external flash |
| Reference listing vs physical DME part-number mismatch | CONFIRMED | archive title and label differ |
| MPC555 memory map (internal flash at 0, ext flash at `0xF00000`, SRAM `0x3F9800`, ext RAM `0x5B8000`, peripherals) | CONFIRMED | `research/verified-findings.md` § Memory architecture |
| Calibration read via CPU alias `0x1C0000–0x1DFFFF` (= ext file `CPU − 0x100000`) | CONFIRMED | e.g. REDABM `r2 − 0x2AE0` |
| Application r13 = `0x401A20`, r2 = `0x1C7FF0` | CONFIRMED | two identical startup sequences |
| 770B `REDABM` at ext `0xC5510` / CPU `0x1C5510`, used by AEVAB | CONFIRMED | int `0x2C560`, `0x2C6E4` |
| Four-of-eight patterns `0x55`/`0xAA`; bits = firing-order positions | CONFIRMED | `0x55` = cyl 1,4,6,7; `0xAA` = cyl 5,8,3,2 |
| Runtime mask selection `REDABM[(segment+4) mod 8][step−1]`, phase latched per event | CONFIRMED | `research/aevab-redabm.md` |
| Step from torque ratio round(8·(1−target/base)) with hysteresis | CONFIRMED logic | torque signal names LIKELY |
| 770B `CWEVAB` at ext `0xCD9CA` / CPU `0x1CD9CA` | HIGH CONFIDENCE (function CONFIRMED) | upgraded from LIKELY |
| `MDHYEZ` at CPU `0x1C8A1A` | HIGH CONFIDENCE | |
| `KFPED` at CPU `0x1C87DA` | HIGH CONFIDENCE | KFMIMR/KFMRMI LIKELY |
| Kickdown `B_kd` (`0x3FBFB3`) computed in 770B fn int `0x3B80C`; thresholds `0x1C1E4A/4B/4C` | CONFIRMED fn / HIGH CONFIDENCE names | requires 100 % pedal + detent voltage |
| Cylinder-cut lambda substitution | CONFIRMED mechanism | LASOABML → `0x1C6408` LIKELY |
| Exhaust-flap logic and gear×rpm map | CONFIRMED fn | names LIKELY |
| Two-level coolant target map | LIKELY | scaling HYPOTHESIS |
| Generator voltage request function | LIKELY | TGENOFVL not located |
| Ignition maps (24×16 ×3) | LIKELY | roles HYPOTHESIS |
| VANOS/Valvetronic, knock adaptation, fan/thermostat outputs, full-load/protection enrichment sources | not located | ROADMAP round 4 |
| Cruise-control set-speed presets in DME | none found | 1 km/h step; breakpoints 30/50/70/100/130/200 km/h |
| One global 560B → 770B offset | REJECTED | local deltas −0x84 … +0x118 |
| OEM AEVAB rotates the pattern each cycle | REJECTED | phase latched per event |
| E-mode can use native kickdown as override trigger | HYPOTHESIS | exists, but stock fires only at full pedal |
| 4/6 firing can be used for efficiency | HYPOTHESIS | OEM path is torque reduction; triggers cut-lambda substitution |
| Lean cruise can be implemented cleanly | HYPOTHESIS | setpoint path partly traced (`research/lambda-control.md`) |
| EGS efficiency gain | HYPOTHESIS | no EGS binary |

## What was verified in round 2

All CONFIRMED rows above (31 automated checks, `tools/verify_770b_findings.py`, 31/31 PASS on the
reference dump).

## What remains speculative

Names of RAM variables (Bosch labels), physical scalings, the identity of the intervention sources,
everything under "not located", and all efficiency/mode proposals.


## Round 3 status (CAN, modes, kickdown, lambda, generator, flap, thermal, AEVAB integration)

| Item | Status | Notes |
|---|---|---|
| TouCAN driver: message-object table EXT `0xFDFAF4` (30 IDs), signal table EXT `0xFDF967`, read/write API INT `0x63660`/`0x63C3C` | CONFIRMED | `research/can-and-drive-modes.md`, `tools/me9_can.py` |
| DME TX 0x0A8/0x0A9/0x0AA; RX EGS 0x0B5/0x0BA/0x1A2/0x5C3 (+ 16 other RX IDs, private TouCAN-B bus) | CONFIRMED | matches the E65 reference filter sets |
| 0x192 (selector) and 0x1D2 received by the DME | REJECTED | not in the message table |
| Current gear `0x5B92CA` from 0x0BA byte0 nibble via table INT `0x15984` | CONFIRMED | upgraded from LIKELY |
| D/S/M program state inside the DME | LIKELY absent | no input, no consumer |
| Sport driver-wish behaviour (KFPEDS-type) in 770B | LIKELY absent | `research/sport-mode.md` |
| B_kd consumers: only CAN coder (→ 0x0AA byte6 high nibble = 0x0B) and diagnostics | CONFIRMED | `research/kickdown-path.md` |
| 0x0AA content: rpm (bytes4-5, 0.25 rpm/bit), pedal byte3, kickdown state byte6 | CONFIRMED | |
| Transmission oil temperature from 0x0B5 byte7 → `0x5B9229` | HIGH CONFIDENCE | exact unit conversion |
| EGS driver-wish limit `0x3FBEDD` (0x0B5 byte5 bits6-7) | LIKELY | |
| Turbine-speed candidate 0x1A2 → `0x5B9982` | LIKELY | |
| λ scale 4096 = 1.0 (sensor curve `0x1C6D0A`) | HIGH CONFIDENCE | upgraded |
| Fuel feed-forward divides by λ setpoint; controller factor `0x5B98A0` | CONFIRMED structure | lean target via setpoint is structurally clean |
| TGENOFVL → `0x1C9412` (full-load-edge generator timer, stock 0) | LIKELY | |
| Flap command `0x3FC286` → output channel 12 | CONFIRMED | polarity LIKELY "on = closed" |
| `0x5B90BB` = vehicle speed (round 2) | REJECTED as stated; now HYPOTHESIS temperature | |
| Least-invasive efficiency-request point: `max()` at AEVAB entry INT `0x2C088`, gated off during any OEM intervention | analysis (HYPOTHESIS) | `research/aevab-integration-points.md` |
| Continuous 4/8 via injector cut keeps unfired cylinders pumping air (lean exhaust, NOx/cat risk) | engineering constraint | must be evaluated before any efficiency claim |

Verification: `tools/verify_770b_findings.py` now runs 47 checks (31 round-2 + 16 round-3); all pass on the reference dump.

## Round-2 input limitation

The third-party 560B bin/XDF and 725D A2L were not re-opened in round 2. 560B-based names rely on
the offsets/descriptions recorded in round 1 (`research/reference-symbols.csv`).

## Important architectural caution

`REDABM`/AEVAB is an OEM torque-reduction mechanism, not an OEM fuel-economy cylinder-deactivation feature. Reusing it for efficiency requires preserving demanded wheel torque by changing load/torque control on the firing events that remain active. Simply forcing a reduction step is not the same thing as an efficient V4/V6 mode. Round 2 adds two facts: the OEM pattern does not rotate during a steady event, and any cut switches the lambda setpoint to the cylinder-cut curve.

## Research notes index

`research/verified-findings.md`, `research/symbol-map-770B.csv`, `research/560B-to-770B-mapping.md`,
`research/aevab-redabm.md`, `research/lambda-control.md`, `research/torque-and-modes.md`,
`research/generator-control.md`, `research/exhaust-flap.md`, `research/thermal-management.md`,
`research/ignition-vanos-valvetronic.md`, `research/egs-integration-plan.md`, `research/can-and-drive-modes.md`, `research/sport-mode.md`, `research/kickdown-path.md`, `research/dme-egs-interface.md`, `research/aevab-integration-points.md`.
