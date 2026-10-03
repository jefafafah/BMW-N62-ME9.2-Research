# Research status — final static pass

Last update: 2026-10-03 (final static-analysis pass, round 7). Target: BMW E65 735i, N62B36, Bosch ME9.2
DME HW 0 261 209 002, SW 1037389760, family 0087180A770B. Read-only analysis; no patches.

Verification: `tools/verify_770b_findings.py` runs **195 checks, all pass** on the reference dumps
(31 round 2 + 16 round 3 + 15 round 4 + 10 round 5 + 12 round 6 + 111 final pass).

Confidence model: **CONFIRMED** (code/data, mostly re-checked by the verifier) · **HIGH CONFIDENCE** (two
independent lines) · **LIKELY** · **HYPOTHESIS** · **REJECTED** · **UNTESTED** · **NOT COMPLETED**.
Address types: INT / EXT / CAL / FILE / RAM / IO (see `docs/FINAL_TECHNICAL_REPORT.md` §2).

Overview: [`docs/SYSTEM_FLOW.md`](docs/SYSTEM_FLOW.md) · Report: [`docs/FINAL_TECHNICAL_REPORT.md`](docs/FINAL_TECHNICAL_REPORT.md)

## CONFIRMED

| Area | Finding | Note |
|---|---|---|
| Identification / memory | HW/SW IDs; internal flash at 0, external flash at `0xF00000`, CAL alias `0x1C0000` = FILE `CPU − 0x100000`; r2 `0x1C7FF0`, r13 `0x401A20` | `verified-findings.md` |
| AEVAB | REDABM `0x1C5510`, bit order = firing order, phase latched per event, priority total > full > diagnostic masks > step | `aevab-redabm.md` |
| Torque | KFPED lookup, torque words in 0x0A8/0x0A9/0x0AA, CAN scaling `(T − loss)·36/2048` (scale CAL `0x1C1150`), full fast/slow arbitration (`min` reductions, `max` increases), ignition first then cut | `torque-and-modes.md` |
| EGS → DME | 0x0B5 torque request decoded from the raw RX buffer (EXT `0xF15450`); EGS path to ignition; EGS never enables cylinder cut; 0x3FBEDD = driver-wish rise limiter; 0x0BA gear, bits 6/7 select misfire-detector maps | `dme-egs-interface.md` |
| DSC path | 0x0B6 raw decode (DSC identity LIKELY), DSC reduction/MSR increase in the arbitration | `torque-and-modes.md` |
| Rev limiter | `0x3FC1A3`, 6500 rpm (CAL `0x1C8B2E`), fault limits 1200 / 1200…3640 rpm | `torque-and-modes.md` |
| Turbine-speed path | `0x5B981E = min((0x5B9982 << 13)/0x5B9A26, 0xFFFF)`; map CAL `0x1C84B0`; tip-in filter gain; no TCC state in the DME | `egs-tcc-shift-state.md` |
| Valvetronic | one request per bank (CAN 0x105/0x10D), no per-cylinder control; target priority; bank-balance split logic; feedback substitute | `valvetronic.md` |
| VANOS | 4 actuators, PWM 2/7/3/6, position loops, 14 target maps in two families | `vanos.md` |
| Ignition | 0.75 °/bit, base/full-load/idle/safety maps, final `min(Z, max(intervention, minimum))`, minimum-angle maps, efficiency table | `ignition-knock-fuel-quality.md` |
| Knock | per-cylinder retard, recovery, adaptation table 21 × 8, floored at 0 (no octane gain beyond the base map) | `ignition-knock-fuel-quality.md` |
| Lambda | arbitration INT `0x1A5E4` (richest wins), protection ≥ full-load richness, cut setpoint on both banks, controller factor 0.75–1.25, codeword `0x1C947C` bits | `lambda-control.md` |
| DFCO | state machine (writer of `0x3FC162` EXT `0xFAE33C`), ramp-out gate, DSC/EGS blocks, no gear dependence in stock data, no generator interaction | `overrun-dfco.md` |
| Generator | voltage-request chain, BSD frame path, generator torque → idle reserve | `generator-control.md` |
| Exhaust flap | logic, map CAL `0x1D077C`, output channel 12, kickdown via pedal not flag | `exhaust-flap.md` |
| Tools | 12 read-only analysis tools + verifier | `tools/README.md` |

## HIGH CONFIDENCE

| Finding | Note |
|---|---|
| D/S/M drive-program state is **not** maintained by the DME | `dme-egs-interface.md` final pass §4 |
| VANOS objects 0/2 = intake, 1/3 = exhaust; pairs {0,1}/{2,3} = banks; 0.1 °CA units | `vanos.md` |
| Valvetronic lift variables in µm | `valvetronic.md` |
| Electric fan = PWM logical channel 9 (no CAN/LIN path) | `thermal-management.md` |
| Thermostat heater = digital output channel 6 (promoted from LIKELY) | `thermal-management.md` |
| Exhaust flap command 1 = closed (logic level) | `exhaust-flap.md` |
| `0x5B90BB` = vehicle speed (frequency input /160); unit open | `thermal-management.md`, `overrun-dfco.md` |
| Generator request in mV; TGENOFVL = CAL `0x1C9412` | `generator-control.md` |
| Transmission oil temperature 0x0B5 byte 7 → `0x5B9229` | `dme-egs-interface.md` |
| λ 4096 = 1.0; KFPED, CWEVAB, MDHYEZ names; relative charge 4267 = 100 % | `torque-and-modes.md`, `lambda-control.md` |

## LIKELY

| Finding | Note |
|---|---|
| 0x1A2 = transmission input / converter turbine speed, 0.125 rpm/bit | `egs-tcc-shift-state.md` |
| Valvetronic request in 0.1° eccentric-shaft angle | `valvetronic.md` |
| 0x0B6 = DSC torque-intervention frame | `torque-and-modes.md` |
| Canister purge = PWM channel 4 | `thermal-management.md` |
| Catalyst-heating / cold-start coordinator EXT `0xF841E4` | `late-ignition-and-catalyst-heating.md` |
| Exhaust-temperature model EXT `0xF4C78C` behind the protection lambda | `full-load-enrichment.md` |
| `0x3FBF34/0x3FBF38` = limp-home / monitoring fault reactions | `torque-and-modes.md` |
| VANOS and Valvetronic map roles (normal / warm-up / idle / full-load) | `vanos.md`, `valvetronic.md` |

## OPEN (needs live data, EGS firmware or more static work)

| Item | Needs |
|---|---|
| Nm per bit of torque words (0.5 Nm/bit HYPOTHESIS) | WOT log, EGS firmware or A2L |
| 0x0BA bits 6/7 meaning and polarity (converter-state HYPOTHESIS) | logs / EGS firmware |
| 0x0B5 bits 24-35 vs 12-23 (slow vs fast request) | shift logs / EGS firmware |
| VANOS bank 1 vs bank 2 | tester values or wiring |
| Vehicle-speed unit (1.25 vs 0.625 km/h per bit) | one log point against GPS |
| Physical bank of lambda paths A/B | live data |
| Role of PWM channels 0/1/5/8 and several digital outputs | pin identification |
| Task rates (counter ticks → seconds) | OS task-table decode |
| Exhaust-temperature model scale | log against EGT |
| Shift schedules, lock-up, D/S/M behaviour | EGS firmware |

## REJECTED

| Assumption | Evidence |
|---|---|
| One global 560B → 770B offset | local deltas −0x84 … +0x118 |
| OEM AEVAB rotates the pattern each cycle | phase latched per event |
| 0x192 / 0x1D2 received by the DME | not in the message table |
| "λ ≠ 1.000 switches the bank to open loop" (round 4) | the window gates only λ modulation; release has no setpoint term |
| 0x0B5 bytes 0-3 unread / no EGS torque value | read from the raw RX buffer by EXT `0xF15450` |
| `0x3FB460`/`0x3FB45E` = EGS torque limit | previous driver wish + DME step size (rise limiter) |
| `0x3FBF34`/`0x3FBF38` = DSC | pure fault-flag logic |
| EXT `0xFAE940` = gear-dependent DFCO thresholds | idle/after-start logic |
| `0x5B90BB` = temperature (round 3) | vehicle speed |
| CAL `0x1CB8AC/0x1CB98A/0x1CBA68` = ignition-efficiency maps | minimum-angle maps |
| 0x1A2 = transmission output speed | single ±6 % ratio axis for all gears |
| `0x1CF610` = sport pedal map (KFPEDS) | shape argues for cruise path |
| EXT `0xF36FE8`/`0xF12018` = VANOS; INT `0xA558` = PWM | output-stage test / discrete port |

## NOT COMPLETED

| Item | What is known | Evidence needed |
|---|---|---|
| Knock signal evaluation internals | acquisition and retard logic CONFIRMED | knock IC identification |
| Lambda adaptation learning internals (EXT `0xF54F18`) | enable conditions CONFIRMED | further static work |
| Valvetronic throttle backup path | fault lift modes known | throttle actuator driver (H-bridge API INT `0x6734C` candidate) |
| Secondary air / exhaust-heating lambda | not found in request paths | further static work |
| Misfire reaction path end-to-end | detector and counters located | trace to fault/diagnostic cut |
| Output-stage diagnostic IDs | fault flag entry points known | further static work |
| EEPROM persistence of adaptation tables | NV-mirror region | further static work |

## Conceptual work (not findings)

[final-mode-architecture](research/final-mode-architecture.md) · [protection-priority](research/protection-priority.md) ·
[efficiency-budget](research/efficiency-budget.md) · [performance-mode](research/performance-mode.md) ·
[late-ignition-and-catalyst-heating](research/late-ignition-and-catalyst-heating.md) ·
[in-car-validation-plan](research/in-car-validation-plan.md) · [development-methodology](research/development-methodology.md)

## Important architectural caution

`REDABM`/AEVAB is an OEM torque-reduction mechanism, not an OEM fuel-economy cylinder-deactivation
feature. The N62 has no valve deactivation: unfired cylinders keep pumping air, and lambda feedback is
suspended on a cut bank. The efficiency concept therefore keeps all 8 cylinders firing; a cylinder-cut
mode remains an optional, last-stage experiment.
