# Generator (alternator) control (770B) — round 2

Address conventions as in `research/aevab-redabm.md`.

## 1. Located functions

| Function | Evidence | Status |
|---|---|---|
| EXT `0xF8A9D0` — generator voltage request | reads calibration words `0x1C943A…0x1C9448` with values 40, 16000, 100, 15000, 14300, 11200, 10600, 0. Read as mV these are 16.0 V max, 15.0 V, 14.3 V nominal, 11.2 V, 10.6 V minimum. Uses curve `0x1C942C` (6 points, axis 0…255) and helper `0x173E0`. Writes `0x5B8C7B…0x5B8C80`, `0x5B8F2C/2E`, `0x5B90F8` | **LIKELY** (scaling HYPOTHESIS) |
| EXT `0xF8A648` — generator load / release conditions | chain of threshold comparisons (`0x1C940A…0x1C941A`) against engine speed `0x5B9001`, the speed-like byte `0x5B90BB`, `0x5B86B4`, `0x5B899E`, `0x3FE159`. Two group maps via `0x1836C` (records at `0x1C9374`, `0x1C939C`, inputs `0x5B8993`, `0x5B853C`), map `0x1C93C4` (6×6) and curve `0x1C93F8`. Writes `0x3FB4BF…0x3FB4C2`, `0x5B8C78`, `0x5B8F2D`, `0x5B90EA/EC/ED` | **LIKELY** generator-related, exact role open |
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
