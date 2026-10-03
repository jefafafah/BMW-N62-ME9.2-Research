# Roadmap — after the final static pass

The DME binary alone answers *how the OEM logic works*. It cannot answer physical units that are only
defined outside the binary, what the EGS does, or whether a change is beneficial. This roadmap separates
those four kinds of work. Status per item: [`RESEARCH_STATUS.md`](RESEARCH_STATUS.md).

## 1. STATIC ANALYSIS — COMPLETE / MOSTLY COMPLETE

- [x] Evidence discipline: hashes, confidence model, no firmware in the repository.
- [x] Memory map, calibration alias, startup registers (CONFIRMED).
- [x] AEVAB / REDABM chain and priority (CONFIRMED).
- [x] Torque structure: driver wish, models, arbitration, ignition-vs-cut split, CAN torque words and scaling ratio (CONFIRMED).
- [x] DME ↔ EGS CAN: 0x0A8/0x0A9/0x0AA, 0x0BA, 0x0B5 (incl. raw-buffer torque request), 0x1A2, 0x5C3 (CONFIRMED decode).
- [x] Turbine-speed ratio path and tip-in filter (CONFIRMED).
- [x] D/S/M absence in the DME (HIGH CONFIDENCE).
- [x] Valvetronic protocol, target chain, bank balancing (CONFIRMED / HIGH CONFIDENCE units).
- [x] VANOS structure, units, intake/exhaust and bank pairing (CONFIRMED / HIGH CONFIDENCE).
- [x] Ignition map structure, final angle, knock control structure (CONFIRMED).
- [x] Lambda architecture, arbitration, protection lambda, lean-feasibility constraints (CONFIRMED).
- [x] DFCO state machine (CONFIRMED).
- [x] Generator request chain and torque model (CONFIRMED / HIGH CONFIDENCE).
- [x] Fan, thermostat heater, PWM/digital channel roles (HIGH CONFIDENCE where stated).
- [x] Exhaust flap logic and polarity (CONFIRMED / HIGH CONFIDENCE).
- [x] Verifier: 195 reproducible checks; tools for xref, CAN, call graph, tables, PWM, dependencies.
- [~] Remaining static work (not blocking validation): knock-signal internals, lambda adaptation learning,
      throttle backup path, misfire reaction path, output-stage diagnostic IDs, OS task rates, unknown
      PWM/digital channels, EEPROM persistence.
- [ ] Minimal 770B definition containing only CONFIRMED / HIGH CONFIDENCE symbols (from `research/symbol-map-770B.csv`).

## 2. REQUIRES LIVE VEHICLE DATA (read-only logging, `research/in-car-validation-plan.md`)

- [ ] Torque Nm per bit (WOT log vs 360 Nm rating).
- [ ] 0x1A2 unit (ratio ≈ 0x4000 with converter locked) and 0x0BA bits 6/7 behaviour.
- [ ] Vehicle-speed unit of `0x5B90BB`/`0x5B9D20`.
- [ ] VANOS bank 1 vs bank 2 (tester values or wiring); confirm intake/exhaust assignment.
- [ ] Valvetronic request unit and lift scaling vs tester values.
- [ ] Exhaust-flap physical polarity (bench check at idle).
- [ ] DFCO thresholds, resume behaviour and timing in seconds.
- [ ] Catalyst-heating coordinator behaviour after a cold start.
- [ ] Knock activity on 95 vs 98 RON.
- [ ] Physical bank of lambda paths A/B; exhaust-temperature model scale.
- [ ] Whether any EGS field changes with the D/S/M selector.
- [ ] Stock baseline consumption with repeatability tolerance (Stage 0).

## 3. REQUIRES EGS FIRMWARE (ZF 6HP / EGS software dump)

- [ ] Identify the exact EGS software.
- [ ] Meaning of 0x0BA bits 6/7, 0x0B5 bits 24-35 vs 12-23, byte4/byte5 status bits.
- [ ] Shift schedules, converter lock-up strategy, D/S/M programs.
- [ ] EGS interpretation of the DME torque words (confirms Nm/bit).
- [ ] Any E-mode shift programme or earlier lock-up (largest transmission efficiency lever).

## 4. FUTURE CALIBRATION DEVELOPMENT (only after sections 2–3; `research/development-methodology.md`)

- [ ] Stage 0 stock baseline → Stage 1 model validation (no changes).
- [ ] Stage 2 single-subsystem experiments: Valvetronic/VANOS part load, ignition (95 RON minimum, knock
      activity must not rise), generator load management, thermostat target, DFCO, torque-rise filtering.
- [ ] Stage 3 combined E (all 8 cylinders) — gains are not additive (`research/efficiency-budget.md`).
- [ ] Stage 4 D validation; Stage 5 S/M validation (`research/performance-mode.md`).
- [ ] Mode-signal source design (none exists in the DME; `research/final-mode-architecture.md`).
- [ ] Stage 6 optional ECO-cylinder experiment (`research/firing-density-feasibility.md`) — last, abort on
      emissions/catalyst/NVH degradation.
- Rule for every stage: OEM protections stay untouched and higher priority (`research/protection-priority.md`).

## What cannot be proven from the DME binary alone

Physical torque units, the meaning of EGS-side bits, EGS shift/lock-up behaviour, the physical
polarity of actuators, bank labels that depend on wiring, and any fuel-economy or power benefit. These
need logs, EGS firmware or controlled measurements.
