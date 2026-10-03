# AEVAB integration points for a future efficiency request — round 3 analysis

> **Final-pass status:** round-3 analysis. Final-pass correction: `0x3FBF34/38` are fault reactions (not DSC/ASC), `0x3FC1A3` is the rev limiter, `0x3FC195` is DSC-dominant; the overrun request `0x3FC162` does not enable the step (CAL `0x1C8A18` bit1 = 0). See `torque-and-modes.md` final pass and `protection-priority.md`.


No code is changed or proposed as a patch. Addresses: INT = internal-flash CPU, RAM = runtime.
Details of the stock chain: `aevab-redabm.md`.

## 1. Where requests enter, and their priority (CONFIRMED from code)

```text
priority (highest first)
1  total cut         0x5BBBA8 != 0  ──► final mask 0x5B92EA := 0xFF          INT 0x430A4 / 0x2C860 (after AEVAB)
2  full cut via AEVAB 0x3FBFEC       ──► step N := 8                          INT 0x2C064-0x2C08C (AEVAB entry)
3  step request      0x5B93E7        ──► N (torque ratio; 8 on 0x3FC19F)       written only by INT 0x484F8 (0x48714 / 0x48938 / 0x48944)
4  static masks      0x5B88C5 (diag|CWEVAB), 0x5B8FD1, 0x5B90D8&0x3FC13B ──► OR-ed into mask in AEVAB states 1/2
   AEVAB state machine 0x5B92E8 / phase 0x5B92E4 / pattern REDABM[P][N-1]
5  per-cylinder ti   INT 0x2ED6C: bit set → injection time 0
```

* The step request is the **only** place where torque-reduction sources (DSC/ASC `0x3FBF34/38`, EGS/limiter
  `0x3FC1A3`, `0x3FC195`, `0x3FC162`) turn into a cylinder count. The enable OR and the hysteresis are in
  INT `0x484F8`.
* Diagnostics and CWEVAB never pass through the step. They are OR-ed later, so a step-level request
  cannot remove them.
* Total cut is applied after AEVAB and overrides everything.

## 2. Candidate insertion points

| Location | Mechanism | Can it suppress OEM protection/interventions? | Notes |
|---|---|---|---|
| **A. AEVAB entry, INT `0x2C088`** (where `N := 0x5B93E7` unless full cut) | `N := max(0x5B93E7, N_eff)` | No for total cut (applied later), full cut (8 is max), static masks (OR-ed later). Yes, it can **add** cut during an OEM intervention → must be gated off when any OEM enable flag is set | single, well-defined point; OEM step and phase logic untouched |
| B. In step request INT `0x484F8` | extra enable source + own ratio | risk of interacting with MDHYEZ hysteresis and `0x3FC19E` blocking | more invasive |
| C. Static-mask path (like CWEVAB) | OR a rotating mask into `0x5B88C5` | puts AEVAB into "static" states 1/2/5 and is treated like a diagnostic cut | **not recommended** |
| D. Final mask after INT `0x2C860` | OR into `0x5B92EA` | bypasses state machine, bank accounting order and lambda handling | **not recommended** |

**Least invasive:** A, with the efficiency request computed by a new function and combined by
`max`. The request is forced to 0 whenever any of these hold: `0x3FBFEC`, `0x3FC19F`, `0x5BBBA8 ≠ 0`,
any AEVAB enable flag (`0x3FBF34`, `0x3FBF38`, `0x3FC1A3`, `0x3FC195`, `0x3FC162`), a static mask ≠ 0,
B_kd `0x3FBFB3`, or a diagnostic fault. Combining by `max` means an efficiency request can never
lower an OEM count, and the gate means it never adds to an OEM intervention.

## 3. Problems the stock logic does not solve (design constraints)

1. **Phase latching:** with a constant N the same cylinders stay cut (`aevab-redabm.md` §3). A
   continuous 4/8 mode needs periodic re-latching (e.g. forcing an event end/start every *k* cycles)
   or its own phase rotation. Otherwise cylinders 1,4,6,7 (or 5,8,3,2) stay unfired.
2. **Air through unfired cylinders:** the N62 has no per-cylinder valve deactivation. Cut cylinders
   pump fresh air into the exhaust. With 4 of 8 cut, the exhaust is far lean of λ = 1, so a
   three-way catalyst cannot reduce NOx, and oxygen loading of the catalyst affects its
   temperature. This is the dominant technical and legal risk of injector-cut efficiency modes.
   It must be evaluated (exhaust λ, cat temperature, NOx) before any efficiency benefit is claimed.
3. **Lambda substitution:** any cut sets `0x3FBFFE/0x3FBFFF`, and the lambda setpoint switches to the
   cut curve CAL `0x1C6408` (λ ≈ 1.05–1.20). That curve is calibrated for short torque-reduction
   events, not for a steady 4/8 or 6/8 operation (mixed exhaust λ ≈ 2.0 or 1.33).
4. **Torque compensation:** to keep wheel torque, the remaining cylinders need more air
   (Valvetronic lift/throttle). The AEVAB step itself only removes torque.

Status of this section: engineering HYPOTHESIS; items 1 and 3 are CONFIRMED properties of the stock code.
