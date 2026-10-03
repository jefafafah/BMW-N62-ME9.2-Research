# Final mode architecture (conceptual) — E / D / S / M / Kickdown / optional ECO-cylinder

**Status: concept only (UNTESTED).** Nothing here exists in the stock DME and nothing here is a
calibration or patch. The purpose is to map each intended mode behaviour onto the OEM mechanisms that
the static analysis has located, so that later work changes as little as possible and never touches a
protection path. Address types: INT / EXT / CAL / RAM.

Hard rule: **OEM protections always override mode requests** (`protection-priority.md`, part B ranks
1–10). Kickdown always cancels economy requests.

## 1. Starting point: what the DME has and does not have

| Fact | Status | Consequence |
|---|---|---|
| No D/S/M program state in the DME (no 0x192/0x1D2 RX, no consumer of a program field) | HIGH CONFIDENCE | a mode signal must be created: from an existing input (kickdown, pedal, cruise, gear), a coding/calibration switch, a new RX object, or a field the EGS sends but the DME ignores |
| Shift schedules and converter lock-up live in the EGS | CONFIRMED (DME side) | DME modes cannot change shifting; the EGS needs its own work (requires EGS firmware) |
| One driver-wish map (KFPED CAL `0x1C87DA`), no sport map | HIGH CONFIDENCE / LIKELY absent | mode-specific pedal feel needs either map switching or shaping of `0x5B981A` |
| Torque-rise shaping exists: EGS rise limiter (`0x3FBEDD`, step `0x3FB45E`) and the tip-in second-order filter (gain `0x5B982A`, ratio map CAL `0x1C84B0`) | CONFIRMED | natural handles for D (smooth) vs S/M (direct) |
| Valvetronic: one lift request per bank, main/idle/full-load maps; VANOS: two map families blended by `0x5B903C` | CONFIRMED / LIKELY roles | E/D part-load optimisation vs S/M full-load optimisation are separate regions |
| Ignition: base maps A/B, full-load maps, knock control floored at the base map | CONFIRMED | no mode can gain advance beyond the base map without changing the map; knock control stays |
| Lambda: richest request wins; component protection ≥ full-load richness; lean clipped at λ 1.203 | CONFIRMED | performance enrichment is allowed only through the existing request slots; protection stays on top |
| Generator: voltage request with relief levels 11.2 / 10.6 V and start relief; full-load relief chain exists but is disabled (TGENOFVL = 0) | CONFIRMED / HIGH CONFIDENCE | S/M generator relief under high demand uses an existing OEM mechanism |
| Cooling: map thermostat (DIG 6), fan PWM ch 9, low target forced by IHKA/EGS | HIGH CONFIDENCE | "performance cooling" = earlier low coolant target, using the existing forced-low path |
| Exhaust flap: pedal-threshold map per gear × rpm (CAL `0x1D077C`), command 1 = closed | CONFIRMED / HIGH CONFIDENCE | S/M flap behaviour = different thresholds, same logic |
| AEVAB: cylinder patterns exist only as torque intervention; lambda feedback suspended on the cut bank; unfired cylinders pump air | CONFIRMED | ECO-cylinder is high-risk and last (`firing-density-feasibility.md`) |

## 2. Mode definitions (conceptual)

| Aspect | **E** (efficiency, 8/8) | **E + ECO-cylinder** (manual, experimental) | **D** (daily) | **S** (sport) | **M** (manual gears) | **Kickdown** |
|---|---|---|---|---|---|---|
| Intent | maximum efficiency with all 8 cylinders | optional 6/8 or 4/8 only under validated conditions | smooth, responsive, thermally conservative | direct torque response | as S, minimal smoothing that fights manual control | full normal capability now |
| Driver wish | progressive pedal near zero; reuse KFPED shape or a scaled `0x5B981A`; cruise unchanged | as E | stock KFPED | steeper initial pedal (shaping of `0x5B981A`) | as S | 100 % pedal + detent → `B_kd` `0x3FBFB3` |
| Torque filtering | stock or slightly softer tip-in filter (gain `0x5B982A`) | as E | stock filter (reference) | higher filter gain, earlier exit of latch `0x3FC18D` | lowest smoothing compatible with driveline; stock EGS rise limiter stays | stock filter; no extra smoothing |
| Valvetronic | part-load main map CAL `0x1C47E8` optimised for low pumping loss | compensate lost torque by more lift on fired cylinders (per bank only) | stock | full-load curve CAL `0x1C507C` reached earlier | as S | full-load curve |
| VANOS | part-load families (A `0x1CA2EC`/`0x1CA25C`, B `0x1C9DDC`/`0x1CA13C`) for efficiency (overlap/internal EGR) | as E | stock | full-load maps (A `0x1CA5F0`/`0x1CA658`, B `0x1CA482`/`0x1CA4EA`) | as S | full-load maps |
| Ignition | base maps; no change to knock control | as E | stock | stock base maps; benefit from better fuel only through knock-retard recovery up to the base map | as S | stock |
| Lambda | λ 1.000 closed loop (diagnostics need the λ=1 window) | cut bank open loop, uncut bank around lean cut target (OEM behaviour) — main risk | stock | stock full-load λ (0.922) with protection on top | as S | stock |
| Generator | load shifting: higher setpoint in overrun / lower under acceleration (within OEM request range 10.6–16 V) | as E | stock | relief under high demand via the existing full-load relief chain (`0x5B8F26` → `0x5B90EB` → `0x5B8F2D`) | as S | relief allowed |
| Cooling | higher coolant target at part load (map thermostat) | as E | stock targets | earlier low target (existing forced-low path, CAL `0x1D08FB`) | as S | stock |
| Exhaust flap | stock (closed at low load) | as E | stock | lower opening thresholds (map CAL `0x1D077C`) | as S | opens via 100 % pedal (stock) |
| EGS interaction | early upshift / early lock-up need EGS changes; DME keeps 0x0A8/0x0A9/0x0AA meaning unchanged | EGS must see correct reduced torque words; avoid cut with locked converter at low rpm (NVH) | stock | sport schedule is EGS-side | manual gear control is EGS-side | 0x0AA kickdown nibble → EGS downshift (stock) |
| Cylinder state | 8/8 always | 6/8 or 4/8 only when all gates are true | 8/8 | 8/8 | 8/8 | **8/8 immediately**, ECO request cancelled and latched off until re-armed |
| Protections | all OEM, unchanged and higher priority | all OEM; ECO request forced to 0 when any OEM intervention/protection/fault is active | all OEM | all OEM; performance runs inside limits | all OEM | all OEM |

## 3. Transitions and gating (conceptual)

```text
            ┌──────────── mode selector (source to be created: coding, kickdown/pedal gesture, new RX object) ────────────┐
            ▼                                                                                                             ▼
   E ◄──────► D ◄──────► S ◄──────► M            (driver choice; D is the default after every start)
   │
   └─ ECO-cylinder request (manual button) ─► ECO-ARMED ─(all gates true for T_stable)─► ECO-ACTIVE (6/8 or 4/8)
                                                 ▲                                              │
                                                 └────── any gate false / kickdown / fault ◄────┘  → immediate 8/8
gates (all required): warm engine, oil and catalyst; λ control released on both banks; no OEM intervention flag
(0x3FBF34, 0x3FBF38, 0x3FC1A3, 0x3FC195, 0x3FC19F, 0x3FBFEC, 0x5BBBA8 ≠ 0, static masks); no knock activity above
baseline; no misfire counts; stable low load and rpm band; gear and converter state validated for NVH; battery stable;
B_kd 0x3FBFB3 = 0; kickdown re-arm requires driver action.
```

## 4. Why E is 8/8

The static analysis shows that an injector-cut mode on the N62 keeps the unfired cylinders pumping
fresh air (no valve deactivation), suspends lambda feedback on the cut bank, and pushes the exhaust
far lean of λ 1 (`firing-density-feasibility.md`). Therefore the efficiency mode is built from
mechanisms that keep all cylinders firing (Valvetronic/VANOS part load, generator, thermal strategy,
DFCO, transmission strategy). ECO-cylinder stays an optional, manually requested experiment, last in
the development sequence (`development-methodology.md` Stage 6).

## 5. Open prerequisites

* A mode-signal source (none exists in the DME; see §1).
* EGS firmware for shift/lock-up changes in E and S/M.
* Live validation of every LIKELY scaling (Valvetronic units, VANOS assignment, torque Nm/bit,
  flap polarity, speed unit) before any mode experiment (`in-car-validation-plan.md`).
