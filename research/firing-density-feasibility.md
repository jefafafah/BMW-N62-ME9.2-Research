# Firing-density feasibility review (770B, N62) — round 4

> **Final-pass status:** consolidated matrix and the corrected lambda behaviour are in the *Final static pass* section at the end of this file. The intended concept is now: E = all 8 cylinders; ECO-cylinder only as an optional manual experiment; kickdown always returns to 8/8.

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

---

# Final static pass (round 7, 2026-10-03) — consolidated feasibility

Inputs: AEVAB/REDABM (rounds 2–3), lambda final pass (`lambda-control.md`), Valvetronic final pass
(`valvetronic.md`), torque final pass (`torque-and-modes.md`). Correction to §1 above: during a cut the
lambda setpoint of **both** banks switches to the cut curve CAL `0x1C6408` (λ 1.055–1.20); the cut bank
loses release (open loop), the uncut bank keeps regulating around that lean target (CONFIRMED code,
LIKELY effect). The torque structure realises reductions by ignition first and only cuts cylinders
for rev limiter, DSC and fault reactions (CONFIRMED).

| Variant | OEM support | Airflow consequence | Lambda consequence | Torque consequence | NVH consequence | Thermal consequence | Likely efficiency benefit | Confidence |
|---|---|---|---|---|---|---|---|---|
| 6/8 sustained | AEVAB step 2 exists (REDABM), only as torque intervention; no efficiency request input | 2 of 8 cylinders pump fresh air (no valve deactivation; Valvetronic is per bank, not per cylinder) | exhaust ≈ λ 1.33 overall; cut bank open loop, other bank regulates to lean cut target; adaptation inhibited on the cut bank; λ=1 diagnostics not ready | needs more lift on all cylinders of the bank to hold torque; torque words to EGS must reflect firing fraction (they do: `0x5B983A` × (8−n)/8) | uneven firing on the affected bank; low-rpm/locked-converter shudder risk | cut cylinders cool, active ones hotter; catalyst oxygen loading | small at best, possibly negative | HYPOTHESIS |
| 4/8 sustained (0x55/0xAA) | AEVAB step 4 exists, balanced pattern | half the cylinders pump fresh air | exhaust ≈ λ 2; three-way catalyst cannot reduce NOx; both banks affected | large lift increase needed; may hit full-load lift at moderate load | strong at low rpm | catalyst temperature/oxygen issues | uncertain, likely marginal or negative | HYPOTHESIS |
| Rotating patterns | phase is latched per event (CONFIRMED); rotation needs event restarts | as the chosen density | every restart re-enters lambda release logic (air-mass integral thresholds) | transition errors | spreads NVH | spreads thermal load | none by itself | HYPOTHESIS |
| Fixed pattern | possible with a constant step (same row) | as the chosen density | as above | as above | as above | uneven cylinder/plug temperatures, plug fouling on unfired cylinders | as 4/8 or 6/8 | HYPOTHESIS |
| Bank cut | bank masks exist (0x5A/0xA5 static path); Valvetronic per bank | only variant where the cut bank could reduce air with minimum lift | one bank open loop and full of air unless lift is minimised; that bank's catalyst cools | other bank carries all torque | uneven firing intervals (V8 bank firing), likely unacceptable | one catalyst cold | the only variant that reduces pumped air; NVH and emissions dominate | HYPOTHESIS |

Conclusion for the concept (normal E = 8/8; optional manual ECO-cylinder; kickdown = immediate 8/8):

* E-mode efficiency should come from mechanisms that keep all 8 cylinders firing (`efficiency-budget.md`).
* An ECO-cylinder experiment, if ever attempted, is Stage 6 of `development-methodology.md`, only under
  validated conditions (warm catalyst, stable low load, no OEM intervention, validated NVH), and must be
  cancelled by kickdown, any OEM intervention flag, faults or knock activity
  (`final-mode-architecture.md` §3, `protection-priority.md` part B).
* Exhaust lambda, catalyst temperature and NOx must be measured before any benefit is claimed.

