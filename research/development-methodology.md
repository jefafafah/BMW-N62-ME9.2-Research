# Development methodology (future work) — final static pass

This document defines **how** any future calibration work on the 770B DME must be validated. It is a
process definition, not a calibration. Nothing in this repository is a patch or a flash image, and no
stage below may start before the previous stage has passed its exit criteria.

Guiding rules:

1. **One change at a time.** Each experiment changes one subsystem (one map family or one codeword)
   and is compared against the stock baseline under the same conditions.
2. **OEM protections are never touched.** Total/full fuel cut, diagnostic cylinder cut, knock control,
   component-protection enrichment, thermal protection, misfire response, DSC and EGS interventions
   and the rev/torque limiter stay as calibrated (`protection-priority.md`).
3. **Read-only first.** Every hypothesis in this repository is first checked with logging
   (`in-car-validation-plan.md`) before any calibration experiment depends on it.
4. **No "change everything and see whether it feels better".** A change without a before/after log
   pair on the same route and load is not a result.
5. **Recovery before experiments.** Full ECU backup (internal flash, external flash, EEPROM) stored
   offline, exact HW/SW ID confirmed, checksum handling verified on the bench, stable programming
   supply, and a proven return-to-stock procedure.

## Evidence required for every future change

| Evidence | Minimum |
|---|---|
| Before/after logs | same route, same direction, same ambient band (±5 °C), same fuel, warm engine and gearbox, ≥ 3 repeats each |
| Fuel consumption | injection-time integral (`ti` × rpm) from the log plus tank-to-tank over ≥ 2 fills; the dashboard average alone is not accepted |
| Lambda | target and actual per bank, controller factors, adaptation values: no new drift, no open-loop surprises |
| Temperatures | coolant, oil, transmission oil, intake air, modelled exhaust/catalyst temperature where identified |
| Knock | per-cylinder retard (once its RAM is identified, see `ignition-knock-fuel-quality.md`): no increase in retard activity |
| Torque | driver-request, maximum and delivered torque words (0x0A8/0x0A9/0x0AA) unchanged in meaning; no new torque oscillation |
| Transmission | gear, shift times, 0x1A2 turbine speed, turbine/engine ratio `0x5B981E`, shift quality judged blind if possible |
| Faults | fault memory read before and after; any new fault ends the experiment |

Repeatability tolerance: before comparing variants, the stock baseline itself must repeat within a
stated tolerance (for example fuel per 100 km within ±1.5 % over 3 runs). A change smaller than that
tolerance is reported as "no measurable effect".

## Stages

### Stage 0 — Stock baseline

* Stock calibration and stock hardware state verified (no open faults, injectors, ignition, lambda
  sensors and catalysts healthy, Valvetronic/VANOS adaptations done).
* Logs: the full set in `in-car-validation-plan.md` §A and §B.
* **Exit:** repeatable baseline per route and manoeuvre, with tolerance bands documented.

### Stage 1 — Logging and model validation only (no calibration change)

* Confirm every LIKELY scaling used later: rpm 0.25 rpm/bit, λ 4096 = 1.0, 0x1A2 0.125 rpm/bit,
  Valvetronic lift scaling, VANOS angle scaling and assignment (bank, intake/exhaust), torque word
  scaling, exhaust-flap polarity, thermostat-heater channel.
* Confirm the dynamic behaviour of documented logic: torque-rise filter (round 6), kickdown,
  overrun/DFCO state machine, cylinder-cut lambda substitution during real DSC/EGS interventions.
* **Exit:** every variable a later stage depends on is CONFIRMED by logs (status updated in
  `RESEARCH_STATUS.md`).

### Stage 2 — Single-subsystem calibration experiments

One subsystem per experiment, each with its own before/after pair: Valvetronic/VANOS part-load,
ignition (95 RON minimum, knock activity must not increase), generator load management, thermostat
target, DFCO entry/exit, torque-rise filtering. Each experiment has a written hypothesis, the CAL
addresses involved, the expected log signature and a stop criterion.

* **Exit per experiment:** measured effect larger than the baseline tolerance, no protection activity
  increase, no new faults, reversible.

### Stage 3 — Combined E-mode validation

Only changes that passed Stage 2 individually are combined. Interactions are measured, not assumed:
gains are **not additive** (`efficiency-budget.md`).

* **Exit:** combined result reproducible on the reference route, all protections behave as stock.

### Stage 4 — D-mode validation

D is the daily reference: drivability, smooth torque build-up, conservative thermal targets. It is
validated against stock D for comfort (tip-in, shift quality) and against Stage 3 for consumption.

### Stage 5 — S/M validation

Performance-oriented strategies (`performance-mode.md`), validated with WOT/part-load pulls where
safe and legal, with knock, temperatures and component-protection enrichment logged. Any dyno or
road power claim needs a controlled measurement; no claim is published from feel.

### Stage 6 — Optional ECO-cylinder experiment

Highest risk, last. It needs a dedicated assessment of exhaust lambda, catalyst temperature and NOx,
NVH at the relevant rpm/gear/converter state, and EGS interaction
(`firing-density-feasibility.md`). It is aborted if catalyst temperature, emissions or NVH degrade,
or if the measured benefit is within the baseline tolerance.

## Documentation of each experiment

```
ID / date / car / fuel / ambient
hypothesis
changed CAL addresses (type CAL) and old/new value class (no values published if third-party IP)
route + manoeuvres
baseline log IDs / experiment log IDs
result (numbers with tolerance) / protections observed / faults
decision: keep / reject / repeat
```
