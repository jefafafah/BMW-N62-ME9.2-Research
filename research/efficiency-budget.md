# Efficiency budget (planning document) — final static pass

**No savings in this document are measured.** Every benefit below is a qualitative engineering
judgement (HYPOTHESIS) until it has passed a before/after test (`development-methodology.md`).
Percentages are **not additive**: the mechanisms act on the same losses (pumping, combustion phasing,
idle/overrun share, converter slip), so combining them gives less than the sum.

Supersedes the older estimate in `docs/efficiency-estimate.md` (12–20 % whole-trip), which predates
the static analysis and assumed a firing-density mode that this analysis does not support.

## 1. Mechanism table

| Mechanism | OEM support (located) | Required future change | Operating region | Qualitative expected benefit | Interaction | Technical risk | Confidence |
|---|---|---|---|---|---|---|---|
| Valvetronic part-load lift | main map CAL `0x1C47E8`, idle map `0x1C4A2C`, per-bank balance (EXT `0xF88494`) | part-load lift/target optimisation (air path only) | 1000–3000 rpm, low/medium load | small: the N62 is already largely unthrottled at part load; gain comes mainly from mixture motion vs pumping trade-off | strongly coupled with VANOS overlap and ignition | idle quality, combustion stability at very low lift, bank imbalance | HYPOTHESIS |
| VANOS part load (overlap / internal EGR) | two map families per cam type, blended by `0x5B903C`; intake/exhaust assignment HIGH CONFIDENCE | part-load target optimisation | cruise, low/medium load | small to moderate at cruise (internal EGR lowers pumping and heat loss) | changes residual gas → ignition demand → knock | combustion stability, emissions (NOx/HC), knock | HYPOTHESIS |
| Ignition at part load | base maps A/B, knock control floored at the base map (no octane gain beyond it) | closer to best-efficiency angle where the stock map is retarded for reasons other than knock | part load | small; possibly zero if the stock map is already near optimum | depends on VANOS/residual gas; higher octane only recovers knock retard | knock, exhaust temperature, NOx | HYPOTHESIS |
| Generator load shifting | voltage request 10.6–16 V (mV, HIGH CONFIDENCE), relief levels, start relief, disabled full-load relief | raise setpoint in overrun, lower under acceleration, within battery-management limits | transient driving | small (alternator load is a few hundred watts) | coupled with DFCO (overrun share) and battery state (CAN 0x334 is external) | battery state of charge, voltage-sensitive consumers | HYPOTHESIS |
| Thermal strategy | map thermostat with high/low targets (DIG ch 6), fan PWM ch 9 | higher coolant target over more of the part-load area | part load, warm engine | small; the OEM already uses a high target at part load | knock (hot charge), fan energy | knock, component temperatures | HYPOTHESIS |
| DFCO | complete state machine (entry delay map, resume curves by temperature, no gear dependence) | earlier entry / lower resume within drivability | urban, downhill | small to moderate in urban driving | interacts with converter state (EGS) and generator | drivability (shunt), catalyst oxygen loading, lambda recovery | HYPOTHESIS |
| TCC / transmission | EGS-side; the DME only sees gear, 0x1A2 turbine speed and status bits | earlier lock-up and upshift (requires EGS firmware) | 40–120 km/h | moderate: converter slip and gear choice are the largest remaining part-load loss on a 6HP automatic | NVH with locked converter at low rpm; interacts with the tip-in filter (ratio map) | NVH, shift quality, EGS adaptation | HYPOTHESIS |
| Lambda / lean | lean clipped at λ 1.203; feedback possible at λ ≠ 1 in principle; diagnostics need the λ = 1 window; three-way catalyst needs λ ≈ 1 for NOx | would require a new request source and a solution for catalyst/diagnostic preconditions | cruise | not pursued: emissions/diagnostic conflict | — | NOx, catalyst diagnostics not ready | LIKELY (constraint) |
| Firing-density (ECO-cylinder) | AEVAB patterns as torque intervention only | efficiency request, torque compensation, lambda strategy for mixed exhaust | very low load only | uncertain, possibly negative: unfired cylinders keep pumping air | conflicts with lambda feedback, catalyst, NVH, EGS torque handling | high (emissions, catalyst, NVH) | HYPOTHESIS |

## 2. Planning estimate (NOT a measured result)

Clearly labelled planning ranges for discussion only, assuming each mechanism is validated
individually and combined carefully:

| Package | Planning range (whole-trip fuel use) | Basis |
|---|---|---|
| DME-only, all cylinders firing (Valvetronic/VANOS, ignition, generator, thermal, DFCO) | roughly **2–6 %** | small individual effects with overlap; N62 already unthrottled |
| Plus EGS changes (earlier lock-up/upshift) | roughly **4–10 %** in total | converter slip and gear choice dominate at part load |
| Firing density | **not included**: sign of the effect unknown | `firing-density-feasibility.md` |

These ranges must be replaced by measured numbers after Stage 2–3 of the development sequence.
They are deliberately conservative compared with the earlier project estimate.

## 3. How to measure

Same route, same ambient band, warm engine, ≥ 3 runs per variant, fuel from injection-time integral
plus tank-to-tank (`development-methodology.md`). Report the baseline repeatability tolerance with
every result.
