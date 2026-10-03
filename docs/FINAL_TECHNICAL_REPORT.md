# Final technical report — BMW E65 735i (N62B36), Bosch ME9.2 DME, SW 1037389760

Read-only static analysis of the OEM control logic, final pass (2026-10-03). Written for three
readers: an experienced BMW technician (what the engine does), an ECU calibrator (which maps and
switches exist) and an embedded-software engineer (where it is in the code). Every statement carries
a confidence level; hypotheses are labelled as such. Nothing in this repository is a patch, a flash
image or a calibration.

Confidence: **CONFIRMED** (unambiguous code/data, most re-checked by `tools/verify_770b_findings.py`,
195 checks), **HIGH CONFIDENCE** (two independent lines of evidence), **LIKELY**, **HYPOTHESIS**,
**REJECTED**, **UNTESTED**, **NOT COMPLETED**. Address types: INT (internal-flash CPU), EXT
(external-flash CPU), CAL (calibration CPU alias), FILE (external-flash file offset), RAM, IO.

A one-page visual overview is in [`SYSTEM_FLOW.md`](SYSTEM_FLOW.md).

---

## 1. Vehicle and ECU identification

| Item | Value | Status |
|---|---|---|
| Vehicle / engine | BMW E65 735i, N62B36 V8, ZF 6HP automatic | context |
| Hardware | Bosch 0 261 209 002 | CONFIRMED (dump strings) |
| Software | 1037389760, family 0087180A770B ("770B") | CONFIRMED |
| CPU | Motorola MPC555 (PowerPC), internal flash + 1 MiB external flash (28F200) | CONFIRMED |
| Reference dumps | identified by SHA-256 only; never stored in the repository | CONFIRMED |

## 2. Memory architecture

| Region | CPU address | Notes | Status |
|---|---|---|---|
| Internal flash (code) | INT `0x000000–0x070FFF` | most real-time code | CONFIRMED |
| External flash | EXT `0xF00000–0xFFFFFF` | program block + data block, headers `0x5A5A5A5A` | CONFIRMED |
| Calibration alias | CAL `0x1C0000–0x1DFFFF` = FILE `CPU − 0x100000` | code reads calibration through this alias (r2 = `0x1C7FF0`) | CONFIRMED |
| Internal SRAM | RAM `0x3F9800–0x3FFFFF` | flags and states (r13 = `0x401A20`) | CONFIRMED |
| External RAM | RAM `0x5B8000–0x5BFFFF` | most signals | CONFIRMED |
| Peripherals | IO `0x2FC000–0x307FFF` | TouCAN A `0x307080`, TouCAN B `0x307480`, MIOS `0x306000`, TPU | CONFIRMED |

## 3. Torque model

The DME is torque-based: every function asks for torque, and one coordinator decides how to deliver it.

* **Driver wish:** KFPED CAL `0x1C87DA` (pedal × rpm, 32768 = 100 %) → `0x5B981A`; optional EGS rise
  limiter; max with cruise → driver request `0x5B980A` (sent in 0x0AA). CONFIRMED.
* **Models:** optimum torque KFMIOP CAL `0x1C828E` (rpm × relative charge, 4267 = 100 % HIGH
  CONFIDENCE) → base torque `0x5B97DA`; loss torque `0x5B97AA` (friction map + temperature/accessory
  terms); maximum torque `0x5B9854`; minimum torque by ignition alone `0x5B985C`; actual torque
  `0x5B983A` (ignition efficiency × firing fraction). CONFIRMED formulas.
* **Arbitration (fast path):** `min(request, gear limit, rev limit, DSC, EGS)`, then `max` with
  torque-increase requests (DSC drag-torque control, EGS increase) → target `0x3FC32A`. CONFIRMED.
* **Delivery:** slow path (air) via load setpoint → Valvetronic/VANOS; fast path via ignition retard
  down to `0x5B985C`; only the remainder becomes a cylinder cut, and only for rev limiter, DSC and fault
  reactions. CONFIRMED.
* **Physical unit:** the CAN ratio is proven (`CAN = (T − loss)·36/2048`), Nm per bit is **not**
  provable statically; 0.5 Nm per CAN bit gives ≈ 370–410 Nm at full load, consistent with 360 Nm
  (HYPOTHESIS).

Example — **light throttle tip-in:** the request jumps above the filtered value, the tip-in latch
`0x3FC18D` sets, and a second-order filter smooths the rise. Its speed depends on gear and on the
turbine/engine speed ratio (§14). Air path follows, ignition stays near base, no cylinder is cut.

[Read more →](../research/torque-and-modes.md)

## 4. DME / EGS communication

| Frame | Direction | Content (CONFIRMED positions) | Meaning status |
|---|---|---|---|
| 0x0AA | DME → EGS | driver request torque, rpm (0.25 rpm/bit), pedal, kickdown nibble 0x0B | CONFIRMED / HIGH |
| 0x0A8 | DME → EGS | actual torque, torque after intervention | HIGH / HYPOTHESIS |
| 0x0A9 | DME → EGS | loss torque, maximum torque, minimum torque by ignition, torque before intervention | CONFIRMED formula / HIGH |
| 0x0BA | EGS → DME | gear (byte0 low nibble → `0x5B92CA`), bits 6/7 (`0x3FBEE0`/`0x3FBEDF`) | gear CONFIRMED; bits: misfire-detector map selection, converter-state HYPOTHESIS |
| 0x0B5 | EGS → DME | torque request reduce/increase (raw-buffer decode EXT `0xF15450`), rise-limit bit `0x3FBEDD`, cooling request, gearbox oil temperature | CONFIRMED decode; names LIKELY |
| 0x1A2 | EGS → DME | turbine speed `0x5B9982` | LIKELY (output speed REJECTED) |
| 0x5C3 | EGS → DME | identification/handshake | HYPOTHESIS |

The DME has **no D/S/M drive-program state** (HIGH CONFIDENCE): the selector frames are not received
and no decoded EGS field selects alternative maps.

Example — **upshift:** the EGS sends a torque reduction (0x0B5 mode 2) → fast limit `0x5B94A4` →
target `0x3FC32A` drops → ignition retards → no cylinder cut (EGS is not an AEVAB enable) → torque
returns when the EGS request ends.

[Read more →](../research/dme-egs-interface.md)

## 5. Valvetronic

* One lift request per bank on private CAN 0x105/0x10D, actual lift back on 0x185/0x18D; **no
  per-cylinder control** (CONFIRMED).
* Lift values in µm (HIGH CONFIDENCE: maps up to 9900 ≈ 9.9 mm, minimum 180–250); request in 0.1°
  eccentric-shaft angle (LIKELY).
* Target priority: fault modes → full-load curve CAL `0x1C507C` → start maps → idle map CAL
  `0x1C4A2C` → main map CAL `0x1C47E8` (CONFIRMED order).
* Bank balancing: per-lift-range learned value raises the lift of the leaner bank only (CONFIRMED
  logic, driven by lambda imbalance LIKELY).
* Not completed: throttle backup path.

[Read more →](../research/valvetronic.md)

## 6. VANOS

* Four solenoids on PWM logical channels 2/7/3/6, position loops per cam (CONFIRMED).
* Angles in 0.1 °CA; measured spread 120.0 °CA at the park stop (HIGH CONFIDENCE).
* Objects 0/2 = intake, 1/3 = exhaust (HIGH CONFIDENCE, two independent lines); pairs {0,1}/{2,3}
  are banks (HIGH CONFIDENCE); which pair is bank 1 is NOT RESOLVED (live method documented).
* Map families: normal, warm-up (towards park), idle, full-load (structure CONFIRMED, roles LIKELY).

[Read more →](../research/vanos.md)

## 7. Ignition

* Angles: signed byte, 0.75 °/bit; output limits −24°…+54° (CONFIRMED).
* Base maps A/B CAL `0x1CAD5A`/`0x1CAF04` (blended by `0x5B903C`), alternate map `0x1CB186`,
  full-load maps `0x1CB384`/`0x1CB414`, idle maps, IAT retard, warm-up advance (CONFIRMED structure).
* Final angle per cylinder: `min(Z, max(intervention, minimum angle))` (CONFIRMED).
* Torque-model ignition: minimum-angle maps CAL `0x1CB8AC`/`0x1CB98A`/`0x1CBA68` plus a quadratic
  efficiency table CAL `0x1C7DC4` (corrects round 2).
* Knock control: per-cylinder retard, recovery, long-term adaptation (21 cells × 8 cylinders); retard
  and adaptation are floored at 0, so better fuel recovers advance only up to the base map
  (CONFIRMED). Knock signal evaluation internals: NOT COMPLETED.
* Late-ignition mechanisms (interventions, catalyst heating coordinator, post-start minimum angle,
  overrun, tip-in): [late-ignition-and-catalyst-heating](../research/late-ignition-and-catalyst-heating.md).

[Read more →](../research/ignition-knock-fuel-quality.md)

## 8. Lambda

* Format 0x1000 = λ 1.000 (HIGH CONFIDENCE). Arbitration INT `0x1A5E4`: rich request =
  min(full-load, component protection); richest wins; 0x1000 = no request (CONFIRMED).
* Cylinder cut replaces the setpoint of both banks by the cut curve (λ 1.055–1.20); cut bank open
  loop, uncut bank keeps regulating (CONFIRMED code).
* Controller factor 0.75–1.25; release has no setpoint term; the λ = 1 window only switches the
  λ modulation used by diagnostics (corrects round 4).
* Full-load λ 0.922 (curve CAL `0x1CE1D8`); component protection (exhaust-temperature model +
  ignition-retard term) is always at least as rich (CONFIRMED).
* Lean operation: limited to λ 1.203 and in conflict with diagnostics and NOx conversion; not pursued.

[Read more →](../research/lambda-control.md) · [Full-load / protection →](../research/full-load-enrichment.md)

## 9. AEVAB / cylinder cut

* REDABM CAL `0x1C5510` 8×8 patterns (bit order = firing order 1-5-4-8-6-3-7-2), phase latched per
  event, step from the torque ratio with hysteresis (CONFIRMED).
* Priority: total cut > full cut > diagnostic masks (OR-ed after the step) > step (CONFIRMED).
* Enables: rev limiter, DSC, fault reactions; **not** EGS, **not** overrun (overrun uses a direct
  all-cylinder cut) (CONFIRMED).

Example — **cylinder cut during a DSC event:** ignition retards to its limit, the rest becomes N cut
cylinders, both banks switch to the cut lambda target, the cut bank runs open loop; afterwards lambda
release waits for an air-mass integral.

[Read more →](../research/aevab-redabm.md)

## 10. Generator

* Voltage request from the power module (CAN 0x334, 25 mV/bit + 10.6 V) → request in mV (HIGH
  CONFIDENCE) → BSD frame (6-bit setpoint, 2-bit load-response class) on TPU channels (CONFIRMED path).
* Relief levels 11.2 / 10.6 V, start relief after start, full-load relief chain present but disabled
  (TGENOFVL CAL `0x1C9412` = 0, HIGH CONFIDENCE).
* Generator torque model feeds the idle torque reserve, not base torque directly (CONFIRMED path).
* No overrun voltage raise and no low-voltage override in the DME (battery management is external).

[Read more →](../research/generator-control.md)

## 11. Cooling

* Electric fan on PWM channel 9 (HIGH CONFIDENCE): request = max(second coolant sensor term, A/C
  stage term) + gearbox-oil term, reduced with vehicle speed; 7–93 %; after-run 20 % at 10 Hz.
* Map thermostat heater on digital channel 6 (HIGH CONFIDENCE): two-point control against a target
  from speed × intake-temperature and speed × load maps; forced low target 84.75 °C on IHKA or EGS
  request.
* No load input to the fan; high load acts through the thermostat target.

Example — **coolant and load rise:** full-load operation → target from the full-load map → heater
energises above target → fan follows the second coolant sensor and gearbox oil temperature;
protection lambda enriches as the exhaust-temperature model rises.

[Read more →](../research/thermal-management.md)

## 12. Exhaust flap

* Command `0x3FC286` → digital channel 12; **1 = closed** (HIGH CONFIDENCE logic level).
* Opens when the pedal exceeds a gear × rpm threshold (map CAL `0x1D077C`); always open at ≥ 4000 rpm
  in a driving gear; closed at standstill even when revving; kickdown opens it through the 100 % pedal
  value, not through the kickdown flag (CONFIRMED logic).
* Bench check of the physical polarity is still recommended.

[Read more →](../research/exhaust-flap.md)

## 13. DFCO (overrun fuel cut)

* Request `0x3FC162` (EXT `0xFAE33C`), cut `0x3FC19F` → AEVAB step 8 (CONFIRMED).
* Entry: pedal released, after-start delay, rpm above resume + hysteresis, temperature × rpm delay map.
  Exit: immediately when any condition drops; resume rpm ≈ 1800 rpm cold to 800–1000 rpm hot.
* The cut waits until target torque has fallen to the ignition-only minimum (ramp-out). DSC drag-torque
  control and EGS torque increase block the cut. No gear dependence in stock data; no generator
  interaction (CONFIRMED).

[Read more →](../research/overrun-dfco.md)

## 14. Transmission / turbine-speed handling

* 0x1A2 → `0x5B9982` (raw, 0xFFFF → 0, timeout → 0) → ratio `0x5B981E = min((n << 13)/rpm, 0xFFFF)`
  (CONFIRMED); 0x4000 = 1.0 and 0.125 rpm/bit (LIKELY).
* The ratio indexes map CAL `0x1C84B0` (6 ratio points × 8 gears) whose output divides the gain of
  the tip-in filter (CONFIRMED).
* No explicit TCC-lock, slip or shift state exists in the DME (CONFIRMED absence).

Example — **turbine speed approaches engine speed:** in gears 2–6 the factor goes from 0.2 (ratio
0.90, filter 5× faster) through 1.0 (0.99) to 1.25–1.5 (1.00–1.04, filter slower) and back to 1.0 at
1.06. With 0x1A2 missing the ratio reads 0 and the fastest setting applies.

[Read more →](../research/egs-tcc-shift-state.md)

## 15. Confirmed limitations of a DME-only approach

* The DME cannot change shift schedules or converter lock-up (EGS-side).
* No mode/program input exists; a mode signal has to be created.
* Nm per bit, Valvetronic request unit, VANOS bank assignment, vehicle-speed unit and flap polarity
  need live confirmation.
* Unfired cylinders keep pumping air (no valve deactivation); lambda feedback is suspended on a cut
  bank.
* Knock control never advances beyond the base map.

## 16. Proposed future mode architecture (concept, UNTESTED)

E = maximum efficiency with all 8 cylinders; optional manual ECO-cylinder (6/8 or 4/8) only under
validated conditions; D = smooth and thermally conservative; S = direct response, full-load VANOS/
lift earlier, generator relief, performance cooling, flap open earlier; M = as S with minimal
smoothing; kickdown = immediate full 8/8 capability and cancellation of economy requests.
[Read more →](../research/final-mode-architecture.md) · [Performance →](../research/performance-mode.md)
· [Efficiency budget →](../research/efficiency-budget.md)

## 17. Protection hierarchy

Total fuel cut > full cut / fault reactions > diagnostic cut / misfire > knock > thermal/component
protection > DSC > EGS > rev/torque limiter > DFCO > kickdown > drive mode > efficiency request.
The first nine are OEM and remain untouched. [Read more →](../research/protection-priority.md)

## 18. Validation methodology

Stage 0 stock baseline → Stage 1 logging/model validation → Stage 2 single-subsystem experiments →
Stage 3 combined E → Stage 4 D → Stage 5 S/M → Stage 6 optional ECO-cylinder. Every change needs a
before/after log on the same route, fuel, lambda, temperatures, knock, torque and transmission data.
[Methodology →](../research/development-methodology.md) · [Logging plan →](../research/in-car-validation-plan.md)

## 19. Unresolved items

| Item | Needs |
|---|---|
| Nm per bit of the torque words | WOT log vs rated torque, EGS firmware or A2L |
| 0x1A2 unit, 0x0BA bits 6/7 meaning | lock-up/shift logs; EGS firmware |
| 0x0B5 bits 24-35 vs 12-23 (slow vs fast request) | shift logs; EGS firmware |
| VANOS bank 1 vs 2 | tester live values or wiring |
| Valvetronic request unit, throttle backup path | logs, further static work |
| Knock signal evaluation internals, EEPROM persistence of adaptations | IC data, further static work |
| Adaptation learning internals (lambda) | further static work |
| PWM channels 0/1/5/8, several digital outputs, output-stage diagnostic IDs | pin identification, static work |
| Task rates (ticks → seconds) | OS task-table decode |
| Exhaust-temperature model scale | logs vs EGT |
| Shift schedules, lock-up strategy, D/S/M behaviour | **EGS firmware** |

Status overview: [`RESEARCH_STATUS.md`](../RESEARCH_STATUS.md) · Plan: [`ROADMAP.md`](../ROADMAP.md)
