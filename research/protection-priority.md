# Protection priority matrix (770B) — final static pass

This note orders the OEM protection and intervention paths. **Part A** is what the code proves (each
row cites the instruction-level evidence). **Part B** is the conceptual priority that any future mode
architecture must respect; it is a design rule, not a finding. Address types: INT / EXT / CAL / RAM.

## A. CONFIRMED priority from code

### A.1 Fuel / cylinder layer (injector output)

Applied in this order, later stages cannot be undone by earlier ones (AEVAB INT `0x2C060`, injection
INT `0x2ED6C`; `aevab-redabm.md`, `aevab-integration-points.md`, torque final pass §3–4):

| Rank | Mechanism | RAM / trigger | Effect | Evidence | Status |
|---|---|---|---|---|---|
| 1 | **Total fuel cut** | `0x5BBBA8` ≠ 0 (bits from fault reactions `0x3FBFEC`/`0x3FBFEE`, `0x3FBEFF`, `0x3FC247`, `0x3FB830.1`, `0x3FBE99`) | final mask `0x5B92EA` := 0xFF after AEVAB | INT `0x430A4`, `0x2C860` | CONFIRMED |
| 2 | **Full cut via AEVAB** (fault reaction / hard rev cut) | `0x3FBFEC` = (`0x3FBF38` && rpm > 0x23) ‖ (`0x3FC1A4` && `0x3FBF34`) | step N := 8 at AEVAB entry | INT `0x2C064…0x2C08C`, `0x42FC4` | CONFIRMED |
| 3 | **Diagnostic / static cylinder cut** | `0x5B88C5` (diagnosis ‖ CWEVAB), `0x5B8FD1`, `0x5B90D8` | OR-ed into the mask **after** the step; a step-level request cannot remove it | AEVAB states 1/2/5 | CONFIRMED |
| 4 | **Overrun all-cylinder cut** | `0x3FC19F` = `0x3FC162` && !`0x3FC198` (DSC-MSR) && !`0x3FBEB8` (EGS increase) && !`0x3FC19E` | step 8 | INT `0x484F8` | CONFIRMED — torque-increase requests from DSC and EGS **outrank** DFCO |
| 5 | **Torque-reduction step** | `0x5B93E7` = round(8·(1 − `0x3FC32A`/`0x5B97DA`)) with MDHYEZ hysteresis | cylinder count, only if an enable is set: rev limiter `0x3FC1A3`, DSC `0x3FC195`, fault reactions `0x3FBF34`/`0x3FBF38` | INT `0x484F8` | CONFIRMED — EGS reductions and the pedal-rate limit never cut cylinders by themselves |

### A.2 Torque layer (fast path, INT `0x47AB0`)

```
0x5B983E = min( driver request 0x5B97FC, gear limit 0x5B9832, rev limit 0x5B9870, min(DSC 0x5B949C, EGS 0x5B94A4) )
0x5B9846 = max( 0x5B983E, DSC-MSR 0x5B94A0, 0x5B9DD4, EGS increase 0x5B94A8 )      → 0x3FC32A
```

* Every reduction (driver request, EGS, DSC, rev limiter, gear/transmission limit) is a `min`; the
  smallest torque wins. CONFIRMED.
* Torque **increase** requests (DSC drag-torque control, EGS increase) are applied **after** the
  reductions with `max`, so they win over reductions. CONFIRMED.
* The driver request is already capped by the maximum available torque `0x5B9854` before the
  tip-in filter (`0x5B9808 = min(0x5B980A, 0x5B9854)`). CONFIRMED.
* Reduction is realised by ignition first, down to the ignition-only minimum `0x5B985C`; only the
  remainder becomes a cylinder count (A.1 rank 5). CONFIRMED.

### A.3 Ignition layer (INT `0x333CC`, `0x33650`)

```
Z       = base chain + warm-up − tip-in knock retard 0x3FC2D9 − per-cylinder knock retard (0x5B9360[cyl])
applied = min( Z, max(intervention 0x5B9434, minimum angle 0x5B9460) )
final   = clamp(applied + 0x5B9438, −24°, +54°)
```

* Knock retard is inside `Z`, and `applied = min(Z, …)`: no intervention can advance a cylinder
  beyond its knock-retarded angle. **Knock protection outranks every torque request.** CONFIRMED.
* Interventions may retard only down to the minimum angle `0x5B9460`; the late-angle duration
  monitor (map CAL `0x1CB7EC`, flag `0x3FC284`) limits persistent very late ignition. CONFIRMED logic.
* Knock-system fault replaces the base angle by a safety map (`0x5B9459`). CONFIRMED arithmetic.
* Knock retard and adaptation are floored at 0: advance never exceeds the base chain. CONFIRMED.

### A.4 Lambda layer (INT `0x1A5E4`, `0x5563C`)

```
R      = min(full-load 0x5B891A, protection 0x5B9C2E/2C)          (richest wins; 0x1000 = no request)
target = (R == 0x1000) ? base request : min(R, base request)
then:  cylinder-cut substitution (both banks) → clamp to temperature limits (rich λ 0.75 / 0.703, lean λ 1.203) → purge factor → snap
```

* Component protection (exhaust-temperature model + ignition-retard term) is always at least as rich
  as the full-load request. CONFIRMED.
* A lean request can only pass when no rich request is active, and is clipped at λ 1.203. CONFIRMED.

### A.5 Other confirmed relations

| Relation | Evidence | Status |
|---|---|---|
| Kickdown has **no** torque path in the DME; it only reaches the EGS (0x0AA byte 6 nibble 0x0B) and opens the exhaust flap through the 100 % pedal value | `kickdown-path.md`, flap final pass | CONFIRMED |
| EGS driver-wish rise limiter `0x3FBEDD` acts on the pedal wish before arbitration | INT `0x46384` | CONFIRMED |
| Rev limiter: normal limit CAL `0x1C8B2E` = 6500 rpm; fault limits 1200 rpm / 1200…3640 rpm | INT `0x48B04` | CONFIRMED |
| Thermostat low target forced by IHKA request or EGS cooling request | EXT `0xF9E148` | CONFIRMED |
| Fan: no overheat-100 % branch; max 93 %; substitute values on missing inputs | EXT `0xF5A65C` | CONFIRMED |

### A.6 Not ranked from code

| Mechanism | Why not ranked | Status |
|---|---|---|
| Misfire response | the detector (INT `0x22110…0x24798`) and its per-cylinder counters are located; the reaction path (fault entry, diagnostic cut via `0x5B88C5`) is not traced end-to-end | LIKELY via rank 3 |
| Thermal protection beyond lambda/ignition | exhaust-temperature model EXT `0xF4C78C` feeds the protection lambda; no separate torque derate was found | partial |
| Generator | no voltage-request derate from the thermal model; battery management is external (CAN 0x334) | CONFIRMED absence in the request fn |

## B. Conceptual priority for any future architecture (design rule, UNTESTED)

Highest first. Rows 1–9 are OEM and must stay **untouched and above** every mode or efficiency request.

| Rank | Layer | Source | Rule for future work |
|---|---|---|---|
| 1 | Total fuel cut | OEM (A.1 r1) | never overridden |
| 2 | Full cut / hard rev cut / fault reactions | OEM (A.1 r2, A.5) | never overridden |
| 3 | Diagnostic cylinder cut, misfire response | OEM (A.1 r3) | never overridden; any custom cut request is combined with `max`, so it can never remove a diagnostic cut |
| 4 | Knock protection | OEM (A.3) | never weakened; no mode may raise the knock limit or remove retard |
| 5 | Thermal / component protection (protection lambda, minimum ignition angle, late-angle monitor, fan, thermostat) | OEM (A.3, A.4, A.5) | never weakened; performance modes run *inside* these limits |
| 6 | DSC torque reduction / increase | OEM (A.2) | never overridden |
| 7 | EGS torque intervention (shift reduction, increase, gear limit, rise limiter) | OEM (A.2) | never overridden |
| 8 | Rev / torque limiter, maximum torque | OEM (A.2) | never raised by a mode |
| 9 | Overrun cut logic (DFCO) | OEM (A.1 r4) | may be tuned only within OEM structure, keeps its DSC/EGS blocks |
| 10 | Kickdown | driver | cancels any economy request immediately and restores normal 8/8 capability |
| 11 | Drive-mode request (E/D/S/M) | future | only shapes the driver request and comfort filters; enters before the OEM arbitration |
| 12 | Efficiency request (e.g. ECO-cylinder) | future | lowest; forced to zero whenever any rank 1–10 element is active (`aevab-integration-points.md` gate list) |

Rule of combination: future requests enter where OEM requests enter (driver request, `max` at the
AEVAB step), never after the OEM final mask, and never by editing a protection path.
