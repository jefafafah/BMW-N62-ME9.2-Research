# BMW N62 / Bosch ME9.2 Research

Open, read-only research into the Bosch ME9.2 engine computer (DME) of the **BMW E65 735i (N62B36 V8)**:
how the OEM software controls torque, air, fuel, ignition, cooling and the gearbox interface. Reference
unit: Bosch HW `0 261 209 002`, SW `1037389760`, software family `0087180A770B` ("770B").

> **This is documentation, not a tune.** No firmware, no patches, no flash images. Everything here is
> derived from static analysis and is labelled with a confidence level.

**Start here:** 🗺️ [System flow — how everything works and depends on each other](docs/SYSTEM_FLOW.md) ·
📘 [Final technical report](docs/FINAL_TECHNICAL_REPORT.md) · 📊 [Research status](RESEARCH_STATUS.md) ·
🧭 [Roadmap](ROADMAP.md)

---

## How the system works (short version)

The DME is **torque-based**. The pedal is turned into a torque request; the DME limits and smooths it,
merges it with requests from the gearbox (EGS), stability control (DSC) and the rev limiter, and then
delivers it: slowly through **air** (Valvetronic valve lift, VANOS cam timing) and quickly through
**ignition angle**; only in rare interventions by **cutting injectors**. Lambda control meters fuel to
the air. Cooling, alternator and exhaust flap run alongside. Protections (fuel cut, knock control,
component protection) always win. [Read more →](docs/SYSTEM_FLOW.md)

| Subsystem | What it does (proven) | Status | Read more |
|---|---|---|---|
| Driver wish & torque-rise filter | pedal map KFPED, cruise, EGS rise limiter, tip-in filter whose speed depends on gear and turbine/engine speed ratio | CONFIRMED | [→](research/egs-tcc-shift-state.md) |
| Torque structure | torque models, `min`/`max` arbitration of driver, EGS, DSC, rev limiter; ignition first, cylinder cut only for limiter/DSC/faults | CONFIRMED | [→](research/torque-and-modes.md) |
| DME ↔ gearbox (EGS) CAN | torque words 0x0A8/0x0A9/0x0AA; gear, torque request, cooling request and turbine speed from the EGS; no D/S/M state in the DME | CONFIRMED / HIGH CONFIDENCE | [→](research/dme-egs-interface.md) |
| Valvetronic | one lift request per bank (no per-cylinder control), lift maps, bank balancing | CONFIRMED / HIGH CONFIDENCE | [→](research/valvetronic.md) |
| VANOS | 4 cams, intake = objects 0/2, exhaust = 1/3, map families normal/warm-up/idle/full load | CONFIRMED / HIGH CONFIDENCE | [→](research/vanos.md) |
| Ignition & knock | base/full-load/idle maps, per-cylinder knock retard and adaptation (never above the base map) | CONFIRMED | [→](research/ignition-knock-fuel-quality.md) |
| Late ignition & catalyst heating | how interventions, cold start and overrun move the ignition angle later | CONFIRMED / LIKELY | [→](research/late-ignition-and-catalyst-heating.md) |
| Lambda | richest request wins, component protection always at least as rich as full load, cut-lambda on both banks | CONFIRMED | [→](research/lambda-control.md) |
| Full-load & protection lambda | full-load λ 0.922, exhaust-temperature/retard protection enrichment | CONFIRMED | [→](research/full-load-enrichment.md) |
| Cylinder cut (AEVAB) | REDABM patterns in firing order, priority layers | CONFIRMED | [→](research/aevab-redabm.md) |
| Overrun fuel cut (DFCO) | complete state machine, resume by temperature, blocked by DSC/EGS torque increase | CONFIRMED | [→](research/overrun-dfco.md) |
| Generator | voltage request (mV), BSD interface, generator torque model | CONFIRMED / HIGH CONFIDENCE | [→](research/generator-control.md) |
| Cooling | electric fan PWM ch 9, map-thermostat heater, coolant targets | HIGH CONFIDENCE | [→](research/thermal-management.md) |
| Exhaust flap | gear × rpm pedal thresholds; command 1 = closed | CONFIRMED / HIGH CONFIDENCE | [→](research/exhaust-flap.md) |

## What has been proven

* Memory layout, calibration alias and the full AEVAB chain. [→](research/verified-findings.md)
* The complete torque arbitration and the meaning/scaling ratio of every DME→EGS torque word. [→](research/torque-and-modes.md)
* The EGS torque-intervention path (0x0B5 → ignition retard; EGS never cuts cylinders on its own). [→](research/dme-egs-interface.md)
* Lambda arbitration and the priority of component protection. [→](research/protection-priority.md)
* **195 automated checks** reproduce these claims from your own dump. [→](tools/README.md)

## What is still research

* Physical units that the binary does not define (torque Nm/bit, 0x1A2 rpm/bit, vehicle speed unit). [→](research/in-car-validation-plan.md)
* Which VANOS pair is bank 1, flap polarity on the car, meaning of some EGS status bits. [→](RESEARCH_STATUS.md)
* Everything inside the EGS (shift maps, converter lock-up, D/S/M programs) needs the EGS firmware. [→](ROADMAP.md)

## Future concept (not implemented)

E = maximum efficiency **with all 8 cylinders**; an optional manual ECO-cylinder mode only as a late,
validated experiment; D = smooth and conservative; S/M = direct and performance-oriented; kickdown =
immediate full 8-cylinder capability. OEM protections always override modes.
[Mode architecture →](research/final-mode-architecture.md) · [Protection priority →](research/protection-priority.md) ·
[Efficiency budget →](research/efficiency-budget.md) · [Performance →](research/performance-mode.md) ·
[Firing-density feasibility →](research/firing-density-feasibility.md)

## What to do next

1. Read-only logging on the car (stationary and driving tests). [Validation plan →](research/in-car-validation-plan.md)
2. Follow the staged method: baseline → model validation → one change at a time. [Methodology →](research/development-methodology.md)

## Reproduce the verification

```sh
pip install capstone                       # only needed for disassembly listings
export ME9_INT=/path/outside/repo/mpc555-6.bin ME9_EXT=/path/outside/repo/28f200f3t.bin
python tools/me9_image.py hash             # must report "reference" for both files
python tools/verify_770b_findings.py       # expected: 195/195 checks passed
```

The dumps are **your own** reads of the ECU; they are never part of this repository. Tools:
[tools/README.md](tools/README.md).

## Explicitly not provided

* BMW/Bosch firmware images, EEPROM contents, VIN/ISN/immobiliser data
* WinOLS projects, DAMOS/A2L files or other commercial material without redistribution rights
* Flash-ready calibrations, patches or instructions to bypass protections, diagnostics or emissions systems

## Safety

No calibration should ever be flashed without a full backup, verified IDs and checksums, a stable power
supply, a proven return-to-stock path, and one-change-at-a-time validation with lambda, knock, temperature,
misfire and transmission monitoring. OEM protections remain the default fallback.

## Document index

| Area | Documents |
|---|---|
| Overview | [System flow](docs/SYSTEM_FLOW.md) · [Final report](docs/FINAL_TECHNICAL_REPORT.md) · [Status](RESEARCH_STATUS.md) · [Roadmap](ROADMAP.md) |
| Evidence | [Verified findings](research/verified-findings.md) · [Symbol map (CSV)](research/symbol-map-770B.csv) · [560B→770B mapping](research/560B-to-770B-mapping.md) · [Sources](references/SOURCES.md) |
| Engine control | [Torque](research/torque-and-modes.md) · [Valvetronic](research/valvetronic.md) · [VANOS](research/vanos.md) · [Ignition & knock](research/ignition-knock-fuel-quality.md) · [Lambda](research/lambda-control.md) · [Full load](research/full-load-enrichment.md) · [Cylinder-cut lambda](research/cylinder-cut-lambda.md) · [AEVAB](research/aevab-redabm.md) · [DFCO](research/overrun-dfco.md) · [Kickdown](research/kickdown-path.md) |
| Vehicle interfaces | [DME↔EGS](research/dme-egs-interface.md) · [Turbine speed](research/egs-tcc-shift-state.md) · [CAN & drive modes](research/can-and-drive-modes.md) · [Generator](research/generator-control.md) · [Thermal](research/thermal-management.md) · [Exhaust flap](research/exhaust-flap.md) |
| Concept & method | [Mode architecture](research/final-mode-architecture.md) · [Protection priority](research/protection-priority.md) · [Efficiency budget](research/efficiency-budget.md) · [Performance](research/performance-mode.md) · [Late ignition](research/late-ignition-and-catalyst-heating.md) · [Firing density](research/firing-density-feasibility.md) · [Validation plan](research/in-car-validation-plan.md) · [Methodology](research/development-methodology.md) |
| Early concept notes (superseded where they conflict) | [docs/](docs/) |

Last structured update: 2026-10-03 (final static pass).
