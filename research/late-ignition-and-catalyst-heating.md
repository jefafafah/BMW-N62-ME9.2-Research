# Late ignition and catalyst heating — existing OEM mechanisms (770B)

Documentation only. This note identifies and separates the **existing** OEM mechanisms that move the
ignition angle later than the base chain, or that heat the exhaust. It is not a calibration and does
not describe how to create one; in particular it is not a "pops and bangs" design. Address types:
INT / EXT / CAL / RAM as in the other notes. Ignition angles are signed bytes, 0.75 °/bit, + = advance
(CONFIRMED, see `ignition-knock-fuel-quality.md` final pass).

## 1. How late ignition is produced in this DME

There is **one** common way to retard: the per-cylinder command is
`applied = min(Z, max(intervention angle 0x5B9434, minimum angle 0x5B9460))` (INT `0x33650`,
CONFIRMED), where `Z` is the normal base chain. Every OEM late-ignition strategy therefore works
through one of three handles:

| Handle | RAM | What moves it | Status |
|---|---|---|---|
| intervention angle | `0x5B9434` (INT `0x32EE8`) | a torque target `0x3FC32A` below base torque `0x5B97DA`, converted into retard through the inverse efficiency tables CAL `0x1CAB68`/`0x1CAA9C` | CONFIRMED |
| minimum (latest permitted) angle | `0x5B9460` (INT `0x4A014`) | maps CAL `0x1CB8AC` (normal) and `0x1CB98A`/`0x1CBA68` (post-start), ramps and rate limits | CONFIRMED arithmetic |
| additive terms in `Z` | `0x5B9454`, `0x5B9462`, `0x3FC2D9`, `0x5B9360[cyl]` | IAT retard, warm-up advance, tip-in knock retard, per-cylinder knock retard | CONFIRMED |

The torque structure decides how much retard is needed; the minimum-angle maps decide how late it
may go. Below the ignition-only minimum torque `0x5B985C`, the remainder goes to cylinder cut (AEVAB)
only for the rev limiter, DSC and fault reactions (`torque-and-modes.md` final pass §4).

## 2. Distinguishing the strategies

| Strategy | Trigger (code) | Handle | Distinguishing feature | Status |
|---|---|---|---|---|
| Torque-intervention retard (DSC, EGS shift reduction, rev limiter, fault limits) | `0x3FC32A` < `0x5B97DA` | intervention angle | follows an external or limiter torque request; ends when the request ends (ramp-out step `0x3FB868`) | CONFIRMED; EGS path to `0x3FC32A` CONFIRMED (torque final pass §3a) |
| Shift-related retard | EGS 0x0B5 mode 2 → `0x5B94A4` → `0x3FC32A` | intervention angle | identical to the above; the EGS decides timing and depth; EGS reductions never cut cylinders on their own | CONFIRMED (DME side); shift timing needs logs/EGS firmware |
| Catalyst-heating / cold-start coordinator | EXT `0xF841E4`: time after start `0x5B953E`, coolant `0x5B8993`, IAT, idle `0x3FC18B` → flags `0x3FC0D4`/`0x3FC0D9`, weight `0x5B9348` | minimum angle (post-start blend), torque target fn | active only after a start, exits on time/temperature thresholds CAL `0x1CE735…0x1CE7D8` | coordinator LIKELY; retard realised via torque reserve/intervention = HYPOTHESIS |
| Post-start minimum-angle extension | start flag `0x3FBFB6` | minimum angle | allows a later latest angle right after start, ramped out by coolant-dependent rate | CONFIRMED arithmetic; "cold-start retard window" LIKELY |
| Time/temperature ignition offset | map CAL `0x1CBB78` (engine temp × time after start) | additive `0x5B9463` | maps CAL `0x1D0703`/`0x1D070D` are **all 0 in stock** → inactive | CONFIRMED inactive; catalyst-heating candidate HYPOTHESIS |
| Overrun ignition | full cut `0x3FC19F` (latch `0x3FC282`) | all cylinders at the minimum angle | no combustion (injectors off), so no exhaust heating effect intended | CONFIRMED |
| Tip-in retard | setpoint step `0x5B961A` ≥ curve CAL `0x1D0696` | min(predicted, actual-load angle) + global knock retard `0x3FC2D9` | short (CAL `0x1CB4A8` cycles), drivability/knock protection | CONFIRMED |
| Knock retard | knock flag `0x3FC101` | per-cylinder `0x5B9360[cyl]` | protection, recovers 0.75° per counter expiry | CONFIRMED |
| IAT retard | intake temperature `0x5B9306` | additive in `0x5B9454` | 0 / −3 / −5.25° × rpm/load weight | CONFIRMED arithmetic |
| Late-angle duration monitor | applied ≤ map CAL `0x1CB7EC` longer than CAL `0x1CBB62` | flag `0x3FC284` → minimum-angle handling | limits how long very late ignition may persist | CONFIRMED logic; component-protection purpose HYPOTHESIS |
| Multi-spark (cold, low rpm) | map CAL `0x1CAA38` (engine temp × rpm) | spark count, not angle | up to 10 sparks below ~2100 rpm | arithmetic CONFIRMED; meaning LIKELY |
| Secondary air / exhaust-heating lambda | — | — | not found in the ignition or lambda request paths (post-start/warm-up λ `0x5B968C` is enrichment, not cat heating) | NOT COMPLETED / not found |

## 3. What this means for later work (documentation, not design)

* Catalyst heating and torque interventions share the same ignition handles; any future strategy has
  to coexist with them and must not weaken the minimum-angle maps or the late-angle duration monitor,
  which protect exhaust components.
* Extended late ignition raises exhaust temperature; the protection-lambda path (`0x5B9C2E/2C`,
  `full-load-enrichment.md`) reacts to ignition retard per bank by enriching. Late ignition is
  therefore never "free" and is self-limited by OEM protection.
* Cold-start behaviour must be validated with a cold-start log of `0x3FC0D4`, `0x3FC0D9`, `0x5B9348`,
  `0x3FC32A` vs `0x5B97DA`, `0x5B9434`, `0x5B9460`, applied angle `0x3FC2EF` and final angle `0x3FC2F1`
  (`in-car-validation-plan.md`).

## 4. Source table from the final static pass (ignition analysis §C)

| Strategy | Trigger | Magnitude source | Duration / exit | Consumers | Status |
|---|---|---|---|---|---|
| Torque-intervention retard (fast path) | any torque target `0x3FC32A` below base `0x5B97DA` (sources: ASC/DSC/EGS/limiters feeding `0x3FC32A`, INT `0x47AB0`, EXT `0xF2EBD8`) | inverse efficiency tables `0x1CAB68/0x1CAA9C` on required ratio; limited by min angle `0x5B9460` | as long as dM > 0; ramp-out step `0x3FB868`; beyond ignition range AEVAB cylinder cut takes over (existing note) | `0x5B9434` → INT `0x33650` | CONFIRMED mechanism; individual sources (EGS shift reduction) CONFIRMED for the EGS DME-side path (torque final pass §3a); timing needs logs |
| EGS shift torque reduction | via the same `0x3FC32A` path | as above | EGS request duration | — | CONFIRMED on the DME side (0x0B5 → 0x5B94A4 → 0x3FC32A, torque final pass §3a) |
| Catalyst-heating / cold-start coordinator | EXT fn `0xF841E4`: reads time-after-start `0x5B953E` (INT `0x3B8CC`, +1/task while running), coolant `0x5B8993`, IAT, idle `0x3FC18B`; exit-reason bits incl. `0x5B953E > CAL 0x1CE7D2` | writes flags `0x3FC0D4` (read by torque target fn `0x47AB0`, min-angle fn `0x4A014`, lambda/idle fns), `0x3FC0D9`, `0x3FC0DA`, weight `0x5B9348` | time/temperature thresholds `0x1CE735…0x1CE7D8` | `0x47AB0`: gates intervention flag `0x3FC194` (coding CAL `0x1C8964`); `0x4A014`: post-start min-angle blend | coordinator LIKELY; retard realised through torque reserve/intervention path = HYPOTHESIS |
| Post-start minimum-angle extension | start (`0x3FBFB6`) | maps `0x1CBA68`/`0x1CB98A` blended by `0x5B9348`; −49…+37 bit | ramp `0x3FB8A0` 0xFFFF→0 at rate curve `0x1CBB46`(coolant) | `0x5B9460` (latest permitted angle) | CONFIRMED arithmetic; "allows later ignition after cold start" LIKELY |
| Time/temp-weighted ignition offset | `0x5B9464` = map `0x1CBB78`(engine temp, `0x5B953E`) | 2×2 maps `0x1D0703/0x1D070D` | — | `0x5B9462` | **inactive (maps 0)**; catalyst-heating candidate HYPOTHESIS |
| Cold-start / warm-up advance | engine temp, coolant | `0x1D0717/0x1D0749` × `0x1CBB8C/0x1CBBE0` | until warm | `0x5B9462` | LIKELY (advance, not retard) |
| Idle ignition (reserve) | idle `0x3FC18B` | `0x1CB0AE/0x1CB0FD/0x1CB134`; fade `0x5B90DC` (ramp CAL `0x1C806D`, curve `0x1C8060`) | idle | `0x5B9454` and model ref `0x5B93DC` | LIKELY |
| Transient (tip-in) retard | setpoint step `0x5B961A` ≥ curve `0x1D0696` | delayed/filtered setpoint maps (min with actual-load angle) + dynamic knock retard `0x3FC2D9` | `0x1CB4A8` cycles; `0x3FC2D9` decays | `0x5B9455`, final sum | CONFIRMED |
| Overrun ignition | full cut `0x3FC19F` | `0x5B9460` (min angle) for all cylinders | until cut ends and cut count `0x5B92EC` < 8 | INT `0x33650` | CONFIRMED |
| Late-angle duration monitor | applied ≤ map `0x1CB7EC` | timers `0x3FB8A4/A6` vs CAL `0x1CBB62/0x1CBB60` | — | `0x3FC284` → `0x3FB8AA.0` → `0x5B9460` handling | CONFIRMED logic, purpose HYPOTHESIS (component protection) |
| Multi-spark (cold/low rpm) | INT `0x49504`: count `0x5B9430` = map `0x1CAA38`(engine temp, rpm byte; 0…10, 0 above ~2100 rpm), CAL `0x1CAA34`, final angle ≥ −0x1B | `0x5B996C` = curve `0x1CAA78`(`0x5B96E0`) ≤ 25000, `0x5B996E` = CAL `0x1CAA9A` | — | INT `0x30A2C` → INT `0x6B1CC` | arithmetic CONFIRMED; multi-spark meaning LIKELY |
| Secondary air / exhaust-heating lambda | — | — | — | — | NOT COMPLETED (not found in the ignition path; lambda functions not examined) |

