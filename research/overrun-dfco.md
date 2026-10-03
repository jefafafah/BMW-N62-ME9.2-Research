# Overrun / decel fuel cut (770B) — round 4 (partial)

Address kinds: INT = internal-flash CPU, EXT = external-flash CPU, CAL = calibration alias, RAM = runtime.
Research only; no calibration for late combustion or "pops" is proposed.

## 1. Full-cut chain — CONFIRMED (from rounds 2–3)

```text
0x3FC162 (overrun cut request) && !0x3FC198 && !0x3FBEB8 && (blank-block / cut-count condition)
   → 0x3FC19F (all-cylinder cut state)                        INT 0x484F8
   → AEVAB step 8 → all injectors off                         INT 0x2C060
0x3FC19F consumers: > 40 functions, including
   - 0x0A9/0x0AA torque word forced to 0                     INT 0x4BDDC
   - post-overrun lambda-release delay, threshold CAL 0x1C99C6 = 0x62   INT 0x58AE8 (round 4)
   - lambda/catalyst functions EXT 0xF5199C, 0xF68540
```

## 2. Request and resume logic — candidates

| Item | Address | Evidence | Status |
|---|---|---|---|
| Overrun request producer | written through a pointer (`0x3FC162` taken as address in EXT `0xFAE33C`); readers INT `0x46348`, INT `0x484F8`, EXT `0xFAE940` | exact store site not resolved by the xref scanner | open |
| Overrun-related state machine | EXT `0xFAE33C` (CAL `0x1C7426…0x1C7434`, curve `0x1C7434`, `0x1CF030`; reads gear `0x5B92CA`, rpm `0x5B9001`, `0x5B90BB` with hysteresis CAL `0x1C742E`/`0x1C742B`) | uses `0x3FC162` and `0x3FC169`; ramp helper `0x15F28` | LIKELY DFCO entry/exit and ramp |
| Gear-dependent resume/thresholds | EXT `0xFAE940`: four 6-point curves CAL `0x1C748C`, `0x1C749C`, `0x1C74AC`, `0x1C74BC`; reads gear `0x5B92CA`, `0x3FC19F`, `0x3FC162`; writes `0x3FC168…0x3FC16C` | gear-indexed curve selection | LIKELY |
| `0x3FC169` | written EXT `0xFAE978` (forced 0 when `0x3FBEFC` = 0) | read by generator fns EXT `0xF47E48` / `0xF8A648` and by EXT `0xFAE33C` | links an overrun-related state to the generator logic — HYPOTHESIS |
| Torque-reduction ignition retard / catalyst-heating retard | not isolated | — | open |

## 3. Existing OEM mechanisms relevant later

* Smooth DFCO: gear-dependent curves and a ramp helper exist (LIKELY).
* Torque intervention: AEVAB plus the ignition path (torque-model maps around INT `0x4A014`).
* Catalyst heating / late ignition: not located yet.
* Generator: `0x3FC169` reaches the generator functions (see `generator-control.md`).
