# Generator (alternator) control (770B) — round 2

Address conventions as in `research/aevab-redabm.md`.

## 1. Located functions

| Function | Evidence | Status |
|---|---|---|
| EXT `0xF8A9D0` — generator voltage request | reads calibration words `0x1C943A…0x1C9448` with values 40, 16000, 100, 15000, 14300, 11200, 10600, 0. Read as mV these are 16.0 V max, 15.0 V, 14.3 V nominal, 11.2 V, 10.6 V minimum. Uses curve `0x1C942C` (6 points, axis 0…255) and helper `0x173E0`. Writes `0x5B8C7B…0x5B8C80`, `0x5B8F2C/2E`, `0x5B90F8` | **LIKELY** (scaling HYPOTHESIS) |
| EXT `0xF8A648` — generator load / release conditions | chain of threshold comparisons (`0x1C940A…0x1C941A`) against engine speed `0x5B9001`, the byte `0x5B90BB` (round 2: "speed-like"; round 3: more likely a temperature), `0x5B86B4`, `0x5B899E`, `0x3FE159`. Two group maps via `0x1836C` (records at `0x1C9374`, `0x1C939C`, inputs `0x5B8993`, `0x5B853C`), map `0x1C93C4` (6×6) and curve `0x1C93F8`. Writes `0x3FB4BF…0x3FB4C2`, `0x5B8C78`, `0x5B8F2D`, `0x5B90EA/EC/ED` | **LIKELY** generator-related, exact role open |
| EXT `0xF47E48` | small helper writing `0x3FB4C3…0x3FB4C8`, `0x5B90EB`; cal `0x1C9412`, `0x1C9417…0x1C9419` | HYPOTHESIS |

Reproduce: `python tools/me9_xref.py func 0xF8A9D0 0xF8A648`.

## 2. TGENOFVL (full-load generator shutoff time)

560B `TGENOFVL` = `0x92FA`. Using the neighbouring anchor deltas (+0xF4 at `0x8506`, +0x118 at
`0x8902`, +0x116 at `0xD8B4`), the expected 770B window is CPU `0x1C9410–0x1C9420`. The byte there
that is read, `0x1C941A` (`0xF0`), is compared with `0x5B90BB` (a speed/temperature-like byte),
**not** with a timer. **REJECTED:** `0x1C941A` = TGENOFVL. TGENOFVL is **not located**.

Next step: find a timer started on the full-load flag edge whose expiry clears a "generator load
reduction" bit. That bit is probably consumed by `0xF8A9D0`, near the writes to `0x5B8C7x`.

## 3. Torque model and voltage request

* The DME has to account for generator torque in the torque model, and the generator interface on
  N62 is a digital link (BSD). Neither the generator-torque term nor the BSD driver is identified
  yet. **HYPOTHESIS:** the QSMCM (`0x305000`) users at INT `0x12D8C…0x12F88` and EXT `0xF081E4…`
  include the BSD/serial driver.
* Load ramps: not identified.

## 4. Load shifting (acceleration vs. overrun) — design notes, UNTESTED

* Mechanism needed: lower the voltage request (towards ~12.5–13 V within battery-state limits) during
  high driver demand, and raise it (≤ the 15.0 V limit above) during overrun fuel cut (`0x3FC19F`,
  HYPOTHESIS = overrun-cut state).
* The OEM already has a full-load generator cut (TGENOFVL-type) and load-release conditions
  (`0xF8A648`). First reproduce those exactly, then consider changing calibration only.
* Safety: battery state of charge and IBS logic in other ECUs (E65 power management) may override
  the request. Log before changing anything.

## 5. Logging candidates (all unverified scaling)

`0x5B8C7B…0x5B8C80` (voltage request outputs, HYPOTHESIS), `0x5B90F8`, `0x3FB4C0/0x3FB4C1/0x3FB4C2`
(release flags), `0x5B9001` (rpm byte), plus battery voltage (not located).

---

# Round 3 additions (2026-10-03)

## 6. Full-load generator timer — TGENOFVL candidate (LIKELY)

EXT fn `0xF47E48`:

```text
3FB4C4 := debounce(full-load flag 0x5B8F26, CAL 0x1C9417)
3FB4C3 := 1 if 0x5B8F26 && 0x5B90BB < CAL 0x1C9418 ; cleared if 0x5B90BB > CAL 0x1C9419 or not debounced
on rising edge of 3FB4C3:  timer 0x3FB4C6 := CAL 0x1C9412     # counted down by helper 0x1E390
0x5B90EB := (timer running)  ──► read by generator-condition fn EXT 0xF8A648 (INT… 0xF8A92C)
```

* `0x5B8F26` = full-load flag: load compared with an rpm curve and AND-ed with enable flags in EXT
  fn `0xFA4F60` (LIKELY B_vl).
* Stock values: `0x1C9412 = 0`, `0x1C9418 = 0`, `0x1C9419 = 1`, so the function is **disabled** in this
  calibration.
* Name mapping TGENOFVL (560B `0x92FA`) → `0x1C9412`: semantics match (edge-triggered generator-off
  time at full load), and the local delta +0x118 matches the neighbouring anchor (MDHYEZ +0x118).
  **LIKELY.** It cannot be promoted further without the 560B XDF and a live test.
* Correction: round 2 called `0x5B90BB` "speed-like". It is compared against 0xE0/0xF0 with hysteresis
  in several functions, which is more consistent with a **temperature** (HYPOTHESIS). The speed-window
  wording above is therefore tentative.

## 7. Generator torque/load model — LIKELY

Three parallel calibration sets suggest per-alternator-variant models, selected by `0x5B8C3A`
(HYPOTHESIS):
* EXT fn `0xF8A1C8`: maps CAL `0x1C8FAC`, `0x1C8FF8`, `0x1C9044` (7×8 each), scalars `0x1C92FC…0x1C9302`; writes `0x5B8C18…0x5B8C72`, `0x5B9D66`.
* INT fn `0x5A620`: curves CAL `0x1C90D0`, `0x1C9106`, `0x1C913C` (13 points), `0x1C9172…0x1C918E` (3 points); reads the voltage-request outputs `0x5B90F8`, `0x5B8F2C`; writes `0x5B8C1A…0x5B8C71`, `0x5B90E2/E3/E6`.
* EXT fn `0xF47A54`: curve CAL `0x1C934E`; reads `0x5B8C7B` (voltage-request fn output), writes `0x5B8C74`, `0x5B90E8`.

## 8. Load-shifting feasibility (analysis only)

| Phase | Existing hook | Assessment |
|---|---|---|
| Acceleration | full-load timer (`0x1C9412`, currently 0) + release conditions in `0xF8A648` | calibration-only activation looks possible (set the timer and the window); effect on charging balance unknown |
| Steady cruise | stock voltage request EXT `0xF8A9D0` (14.3 V nominal) | unchanged |
| Overrun | no overrun-specific raise of the voltage request found; upper limit 15.0/16.0 V present | would need new logic or recalibration of the request curve `0x1C942C`. HYPOTHESIS |

Low-voltage protection: the 11.2 V / 10.6 V constants in `0xF8A9D0` are the likely lower bounds
(HYPOTHESIS). The physical link to the alternator (BSD) is still not identified.

---

# Round 4 additions (2026-10-03)

## 9. TGENOFVL promoted to HIGH CONFIDENCE

Full chain, CONFIRMED in code (checks in `verify_770b_findings.py`):

```text
full-load flag 0x5B8F26 (EXT 0xFA4F60)
  → EXT 0xF47E48: edge → timer 0x3FB4C6 := CAL 0x1C9412 (stock 0)   → running flag 0x5B90EB
  → EXT 0xF8A648: 0x5B8F2D = (CAL 0x1C940A == 1) && (0x5B90EA || 0x5B90EB)
  → EXT 0xF8A9D0 (voltage request): 0x5B8F2D && 0x3FBEFC gate the request path at 0xF8A9F4
```

The behaviour (timed generator relief triggered by full load) matches the 560B description, and the
local delta (+0x118) matches the neighbouring anchors. **HIGH CONFIDENCE** for TGENOFVL = CAL
`0x1C9412`. With the stock value 0 the timer never runs.

## 10. Overrun link

`0x3FC169` (EXT `0xFAE978`, overrun-related, HYPOTHESIS) is read by EXT `0xF47E48`, which then counts
down the release timers `0x3FB4C0/0x3FB4C1`, and by EXT `0xF8A648`. An overrun-dependent generator
path therefore likely exists already. Its exact effect is open.

## 11. Still open

Battery voltage, generator actual load, the generator torque term in the torque model (the three map
sets in §7 are candidates) and the BSD driver.
