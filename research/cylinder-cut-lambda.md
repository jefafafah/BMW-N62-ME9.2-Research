# Cylinder cut and lambda control (770B) — round 4

Address kinds: **INT** = internal-flash CPU, **EXT** = external-flash CPU, **CAL** = calibration alias
(file = CPU − 0x100000), **RAM** = runtime. All CONFIRMED rows are re-checked by
`tools/verify_770b_findings.py` (round-4 section).

## 1. End-to-end chain

```text
final cut mask 0x5B92EA ──► INT 0x55424: per-bank counts 0x5B92ED / 0x5B92EE (bank mask 0x5B8C82 = 0x5A)
                                          flags 0x3FBFFE (bank A cut) / 0x3FBFFF (bank B cut)        CONFIRMED (round 2)
   │
   ├─► setpoint path INT 0x5563C: while 0x3FBFFE||0x3FBFFF, base setpoint := 0x5B891E << 5
   │       0x5B891E = curve CAL 0x1C6408 (λ-codes 135…154 → λ 1.055…1.20) over air-mass flow byte 0x3FC2B6   CONFIRMED
   │       → clamp → 0x5B96A6/0x5B96A4 (feed-forward divisor) → snap → 0x5B96AA/0x5B96A8 (controller target)
   │
   ├─► release logic INT 0x58AE8:
   │       bank A: 0x3FBFFE → integrator 0x3F9D28 := 0;  else 0x3F9D28 += air-mass flow 0x3FC2FC
   │               0x5B98EC = 0x3F9D28 >> 8;  0x3FC1F5 = (0x5B98EC < CAL 0x1C99C2)          CONFIRMED
   │       bank B: same with 0x3FBFFF / 0x3F9D2C / 0x5B98EA / CAL 0x1C99C4 → 0x3FC1F6            CONFIRMED
   │       after overrun cut 0x3FC19F: 0x3F9D30 / 0x5B98EE vs CAL 0x1C99C6 (0x62) → 0x3FC1F7      CONFIRMED
   │       release 0x3FC1EE (A) / 0x3FC1EF (B) = AND of ~14 conditions incl. !0x3FC1F5(F6), !0x3FC1F7   CONFIRMED
   │
   └─► controller INT 0x56DD0:
           active 0x3FC1E3 (A) = 0x3FC1EE && !0x3FC1E9 && … && |0x5B96AA − 0x1000| ≤ 1
                                 (bypass only if CAL 0x1C947C bit2; stock 0x1B → bit2 = 0)         CONFIRMED
           if release off: integrator/state words 0x5B989E, 0x5B98CE…0x5B98DE, 0x5B98E2/E6,
                           0x3F9CDC…0x3F9CE8 := 0                                                 CONFIRMED
           bank factor 0x5B98AE = 0x8000 + 0x5B989E (released) | 0x8000 or hold 0x5B98F2 (not released)   CONFIRMED
           upper limit CAL 0x1C95A2 = 0xA000 (factor 1.25)
           → 0x5B98A2 / 0x5B98A0 → fuel calc INT 0x2E9E4
adaptation EXT 0xF54F18 (writes 0x5B8920…0x5B8952, read by INT 0x5EB7C → factor 0x5B96BA)
           enable flags 0x3FC1E7/0x3FC1E8 (INT 0x58AE8) require the bank release and setpoint ≥ CAL 0x1C9986 (λ 0.90)   LIKELY
adaptation diagnosis EXT 0xF5199C (limits 0x6666/0x999A, 0x628F/0x9D71 of 0x8000 → ±20 %/±23 %)   LIKELY
```

`IMLEVABS` (560B `0x98AA`, "integrated air mass before lambda control after cylinder blanking") →
CAL `0x1C99C2` (+ bank-B twin `0x1C99C4`): semantics (air-mass integral restarted at each cut,
threshold before release) and local delta (+0x118, same as MDHYEZ/TGENOFVL) agree. **HIGH CONFIDENCE.**
Stock values: `0x1C99C2 = 1`, `0x1C99C4 = 1` (one integration unit after `>>8`), `0x1C99C6 = 0x62`.

## 2. Answers to the round-4 questions

| Q | Answer | Status |
|---|---|---|
| A. Closed-loop lambda during AEVAB cuts? | **No** for the affected bank. The cut flag resets the post-cut air-mass integrator, so the release is blocked; in addition the cut setpoint (λ ≥ 1.055) fails the "setpoint ≈ 1.000" condition. The other bank keeps closed loop if it has no cut cylinders. | CONFIRMED |
| B. Target during cut | No feedback target. The **feed-forward** uses the cut setpoint (λ 1.055…1.20 vs. air-mass flow), so fuel mass per active cylinder = load / λ_cut (open loop). | CONFIRMED structure |
| C. Integrators frozen or modified? | **Reset to 0** (factor 1.0, or hold value `0x5B98F2` if `0x3FC1FE`), not frozen. | CONFIRMED |
| D. Adaptation during cut? | Learning enable depends on the bank release, so it is **inhibited** during cuts and until IMLEVABS is reached. | LIKELY |
| E. Compensation of pumped oxygen? | **None in the controller.** Bosch suspends feedback and runs a lean-ish feed-forward target. Interpretation (HYPOTHESIS): the lean target limits the CO/HC the catalyst must oxidise with the oxygen from unfired cylinders (exotherm/catalyst protection). | CONFIRMED (no compensation path) / HYPOTHESIS (purpose) |
| F. When the cut ends | Bank flag clears → setpoint returns to the normal path → air-mass integral accumulates → after CAL `0x1C99C2` the bank is released → controller restarts from **zero integrator** (factor 1.0). After an overrun cut the longer threshold `0x1C99C6` applies (oxygen-storage purge time, HYPOTHESIS). | CONFIRMED |

## 3. Sustained 4/8 or 6/8: would active cylinders be enriched by feedback?

* **Stock code: no.** As long as any cylinder on a bank is cut, that bank stays open loop at the cut
  feed-forward target. Active cylinders run at about λ 1.05–1.2 relative to their own charge, with
  no feedback and no adaptation.
* **If closed loop were forced on** (e.g. by changing the release or CAL `0x1C947C` bit2), the sensor
  would see mixed exhaust. Mixed λ ≠ active-cylinder λ: with 4 of 8 unfired, half the gas is fresh
  air. The controller would drive the factor towards its limit (+25 %, CAL `0x1C95A2`) and enrich the
  active cylinders strongly. This would be a protection and emissions hazard.
* Long open-loop operation also means no correction for fuel or air-model errors and no adaptation.
  It probably also affects catalyst and lambda monitors (`0x3FC001` is read by several diagnostic
  functions; not analysed).

Conclusion: the OEM design tolerates cuts as **short torque interventions**. It does not support
sustained skip-fire with closed-loop lambda.
