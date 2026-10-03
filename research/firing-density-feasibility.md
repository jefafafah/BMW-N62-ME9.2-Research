# Firing-density feasibility review (770B, N62) — round 4

This combines the AEVAB (rounds 2–3), cylinder-cut lambda (round 4) and Valvetronic (round 4)
findings. It analyses only; nothing here is a calibration or code proposal. "Expected benefit" is a
qualitative engineering judgement (HYPOTHESIS) unless stated otherwise.

## 1. What each OEM layer supports

| Layer | What exists | Evidence |
|---|---|---|
| AEVAB | 1…8-cylinder cut patterns (REDABM), latched phase per event, step from the torque ratio, priority below full/total cut and above nothing | CONFIRMED |
| Lambda | feedback **suspended** on a bank with any cut; integrators reset; feed-forward λ 1.055…1.20; adaptation inhibited; release after air-mass integral (IMLEVABS) | CONFIRMED / LIKELY |
| Valvetronic | one lift request per bank (CAN 0x105 / 0x10D); no per-cylinder lift | CONFIRMED (DME side) |
| Torque model / CAN | cut count and torque words reach 0x0A8/0x0A9 (EGS sees the reduced torque) | CONFIRMED (structure) |

## 2. Feasibility matrix

| Feature | OEM support | Required modification | Main risk | Expected benefit | Confidence |
|---|---|---|---|---|---|
| Short torque-reduction cuts (stock) | full | none | — | — (intervention, not efficiency) | CONFIRMED |
| Sustained 6/8 (2 cut) | AEVAB can hold step 2; lambda goes open loop for the whole time | efficiency request at AEVAB entry + torque compensation (more lift on all cylinders) + a new lambda strategy | lean exhaust (25 % fresh air), no NOx conversion, catalyst oxygen loading, open-loop fuelling error, no adaptation, NVH | small at best: active cylinders gain load, but pumping and friction of the 2 unfired cylinders remain (valves active) | HYPOTHESIS |
| Sustained 4/8 (balanced 0x55/0xAA) | AEVAB step 4 exists; same lambda behaviour | as above, plus a large torque compensation | exhaust ~50 % fresh air, catalyst cannot reduce NOx, possible cat temperature issues, strong NVH at low rpm, EGS torque handling | uncertain; likely negative or marginal because unfired cylinders still pump air through open valves | HYPOTHESIS |
| Rotating patterns (alternating rows) | phase is only re-latched per event | new phase rotation or forced event restarts | each restart re-enters the lambda-release logic; transition fuelling errors | spreads thermal load; no efficiency gain by itself | HYPOTHESIS |
| Fixed REDABM pattern for long periods | possible (constant step keeps the row) | efficiency request only | uneven cylinder/catalyst temperatures, plug fouling on unfired cylinders | as 4/8 | HYPOTHESIS |
| Bank cut + minimum lift on that bank | bank mask exists (0x5A/0xA5 via static path), lift is per bank | new bank-wise cut request + per-bank lift override | uneven firing (180/270/180/90°), one catalyst bank cold and filled with air, Valvetronic min-lift limits | the only variant that reduces pumped air; NVH likely unacceptable | HYPOTHESIS |
| Closed-loop λ during cuts | not supported (blocked by release logic and the setpoint ≈ 1.000 condition) | would require a mixed-exhaust model | forced feedback would **enrich active cylinders up to +25 %** | none | CONFIRMED (blocking) / HYPOTHESIS (consequence) |

## 3. Conclusion (round 4)

* OEM AEVAB plus OEM lambda handling are built for **seconds-long torque interventions**, not for
  sustained firing-density operation.
* Without per-cylinder valve deactivation, unfired N62 cylinders keep pumping air. That removes most
  of the efficiency rationale and creates the main emissions and catalyst risk.
* Before any firing-density work, the efficiency budget should first be explored with mechanisms that
  keep all cylinders fired: Valvetronic/VANOS part-load optimisation, ignition, generator load
  shifting, thermostat targets, DFCO and transmission/TCC strategy. That is a recommendation, not a
  measured result.
