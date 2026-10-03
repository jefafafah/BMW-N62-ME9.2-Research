# Performance architecture (documentation) — existing OEM mechanisms for S / M

This note lists which **existing** OEM mechanisms a future performance-oriented calibration (S/M)
would work through, and which protections must remain untouched and higher priority. It contains no
values, no calibration and no patch. Address types: INT / EXT / CAL / RAM.

## 1. Mechanisms that would carry a performance strategy

| Area | OEM mechanism (located) | What a performance mode would use | Status of the mechanism |
|---|---|---|---|
| Driver wish | KFPED CAL `0x1C87DA` (pedal × rpm, 32768 = 100 %), max with cruise, cap by maximum torque `0x5B9854` | steeper initial response (pedal map or shaping of `0x5B981A`); the cap stays | HIGH CONFIDENCE (name), CONFIRMED (lookup) |
| Torque model | optimum torque KFMIOP CAL `0x1C828E`, loss torque `0x5B97AA`, base torque `0x5B97DA`, maximum torque `0x5B9854` | unchanged model; the EGS must keep receiving consistent torque words (0x0A8/0x0A9/0x0AA) | CONFIRMED formulas; Nm/bit not provable statically |
| Torque-rise filtering | EGS rise limiter (`0x3FBEDD`, step curve CAL `0x1CF412`); tip-in second-order filter (gain `0x5B982A` = base / ratio-map factor, latch `0x3FC18D`) | higher filter gain and earlier latch release in S; minimal shaping in M; EGS limiter left to the EGS | CONFIRMED |
| Valvetronic | full-load curve CAL `0x1C507C` (5.0→9.9 mm), main map CAL `0x1C47E8`, full-load flag `0x5B8F26` | reach maximum lift earlier in the pedal travel | CONFIRMED selection, roles LIKELY |
| VANOS | full-load maps type A (intake) `0x1CA5F0`/`0x1CA658`, type B (exhaust) `0x1CA482`/`0x1CA4EA` | full-load cam timing for volumetric efficiency | structure CONFIRMED, roles LIKELY |
| Ignition | base maps A/B CAL `0x1CAD5A`/`0x1CAF04`, full-load maps `0x1CB384`/`0x1CB414` | only where knock margin exists; knock control decides | CONFIRMED structure |
| Lambda enrichment | full-load curve CAL `0x1CE1D8` (stock λ 0.922), protection request `0x5B9C2E/2C` | full-load λ through the existing request slot; protection stays richer-wins | CONFIRMED |
| Generator unloading | relief voltages 11.2 / 10.6 V; full-load relief chain `0x5B8F26` → timer CAL `0x1C9412` (TGENOFVL, stock 0) → `0x5B90EB` → `0x5B8F2D` | relieve the alternator during full-load demand | HIGH CONFIDENCE (TGENOFVL), CONFIRMED chain |
| Cooling | forced low coolant target CAL `0x1D08FB` (84.75 °C) via IHKA/EGS request; map thermostat heater DIG ch 6; fan PWM ch 9 | earlier low target under high demand | HIGH CONFIDENCE |
| Exhaust flap | pedal-threshold map CAL `0x1D077C` (gear × rpm), command 1 = closed | lower opening thresholds in S/M | CONFIRMED logic, polarity HIGH CONFIDENCE |
| EGS communication | 0x0A8 actual torque, 0x0A9 max/min/loss torque, 0x0AA driver request + kickdown nibble; 0x0B5 EGS torque request (reduce/increase) | keep all torque words physically consistent so the EGS shift pressure and interventions stay correct | CONFIRMED positions/scaling ratio |
| Kickdown | `B_kd` `0x3FBFB3` (100 % pedal + detent voltage) → 0x0AA nibble 0x0B → EGS downshift; flap opens via 100 % pedal | unchanged | CONFIRMED |

## 2. Protections that must stay untouched and higher priority

| Protection | Location | Why it stays |
|---|---|---|
| Total fuel cut, full cut, fault reactions | `0x5BBBA8`, `0x3FBFEC`, `0x3FBF34/38` | fault safety |
| Rev limiter (6500 rpm) and fault rev limits | INT `0x48B04`, CAL `0x1C8B2E` | mechanical protection |
| Maximum torque cap | `0x5B9854` | drivetrain/transmission protection |
| Gear / transmission torque limit | `0x5B9832` (EXT `0xFA488C`) | gearbox protection |
| EGS and DSC interventions | `0x5B94A4/A2/A8/A6`, `0x5B949C/9A/A0` | shift quality, traction, stability |
| Knock control and knock-fault safety map | `0x3FC2E0[8]`, `0x3FDBB4`, `0x5B9459` | engine protection; advance never exceeds the base chain |
| Minimum ignition angle and late-angle monitor | `0x5B9460`, CAL `0x1CB7EC` | exhaust-component protection |
| Component-protection lambda | `0x5B9C2E/2C` (exhaust-temperature model `0x5B86C0`, retard term) | catalyst/exhaust protection; always at least as rich as full-load |
| Lambda temperature limits | `0x5B891C/1D` (rich λ 0.75/0.703, lean 1.203) | combustion/component limits |
| Thermal management fallbacks | fan substitutes, thermostat forced-low path | overheating protection |
| Diagnostic cylinder cut / misfire response | `0x5B88C5`, misfire detector | catalyst protection, legal diagnostics |

A performance mode works **inside** these limits. If a performance change makes any of them
intervene more often in the logs (knock retard, protection enrichment, minimum-angle limiting, gear
limit), the change is rejected (`development-methodology.md`).
