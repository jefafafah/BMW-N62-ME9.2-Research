# Generator (alternator) control (770B) — round 2

> **Final-pass status:** voltage request in mV (HIGH CONFIDENCE), BSD frame and TPU channels, generator torque model and its path to the idle reserve CONFIRMED. See the *Final static pass* section at the end of this file.


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

---

# Final static pass (round 7, 2026-10-03)

This section supersedes conflicting statements earlier in this file. CONFIRMED items are re-checked by `tools/verify_770b_findings.py` (final-pass blocks).

### B. Generator / alternator

#### B1. Signal chain (CONFIRMED unless noted)

```text
CAN 0x334 (handle 0x06, signal 0x28, EXT 0xF3C228; LIKELY from the E65 power module)
  byte0 -> 0x5B8F7B voltage request (0xFF -> CAL 0x1C114F; timeout >5 cycles -> CAL 0x1C114F)
  byte1 b0-1 -> 0x5B8F7C status (3 -> 1)
  byte2 -> 0x5B8551 = raw*4/3 (temperature format; 0xFF -> 0x5B899C)  [DLC in table = 2: byte2 HYPOTHESIS]
EXT 0xF8A9D0:
  base 0x5B8C7C = CW 0x1C944B ? min(curve 0x1C941C(0x5B8551), 0x1C9448*curve 0x1C942C(0x5B9349)) : CAL 0x1C9444
  relief (0x1C943A != 0 and 0x5B8F2E, or 0x5B8F2D && !0x3FBEFC):
       request = 0x5B90BB==0 ? CAL 0x1C9446 (10600) : CAL 0x1C9444 (11200)
  init (0x5B8C7A && 0x5B8F7B==0)   : request = CAL 0x1C9442 (14300)
  normal                           : request = max(10600 + 25*0x5B8F7B, max(0x5B8C7C, 11200))
  0x5B8C7E = request (mV); 0x5B8C80 = ramped: step CAL 0x1C943E (100 mV) up/down,
       CAL 0x1C9440 (15000 = immediate) when request <= 11200; clamp 30000
  CW 0x1C944A==1 -> fixed 14300; limit CAL 0x1C943C (16000)
  0x5B90F8 = max(min(..,16000)/100 - 106, 0)       # 0.1 V/bit, 10.6 V offset
  0x5B8C7B = (0x5B8F7B != 4*0x5B90F8)             # CAN request vs. sent mismatch
  0x5B8F2C = (0x5B90F8*100 >= 600)                # generator active (setpoint >= 11.2 V)
EXT 0xFA3DB8 (BSD master client, state 0x5BBAB3):
  frame = (clamp(0x5B90F8, CAL 0x1C6EC7=1, 0x1C6EC8=54) & 0x3F)   # 54 -> 16.0 V
          | (min(0x5B90ED / CAL 0x1C6EC4 (30), 3) << 6)
          (0x5B90F8 < 1 -> substitute CAL 0x1C6EC2 = 0)
  write INT 0x6CDFC(handle 0x5BBAB2, node 0x5B90F2, msg 0, frame) -> INT 0x6AD68
  request INT 0x6CDBC(handle, node, msg 0/2/6)                   -> INT 0x6AC44
INT 0x205A4 (BSD receive callback, node 6):
  msg0: b0-5 -> 0x5B89F1 (setpoint echo), b6-7 -> 0x5B89ED, 0x5B89EF = 0x5B89ED*30;
        0x5BBAB7 = echo > CAL 0x1C6EC2
  msg2: b0-4 -> 0x5B89F0, load 0x5B89EA = 0x5B89F0 * CAL 0x1C6EC3 (8), sat 255;
        b5 -> 0x5B89E6, b6 -> 0x5B89E8, b7 -> 0x5B89E7 (fault bits)
  msg6: b5-6 -> 0x5B89EB, b2-4 -> 0x5B89EC (type / manufacturer code)
```

| Item | Address | Result | Conf. |
|---|---|---|---|
| requested voltage | RAM `0x5B8C7E` (mV, unramped), `0x5B8C80` (mV, ramped), `0x5B90F8` (0.1 V/bit + 10.6 V) | as above | CONFIRMED arithmetic; mV scale HIGH CONFIDENCE |
| external request | RAM `0x5B8F7B` from CAN 0x334 byte0, 25 mV/bit + 10.6 V | — | CONFIRMED decode; sender (power module) LIKELY |
| BSD physical layer | INT descriptor `0x1C3C4`: `{0x304000, 0x3041E0, 0x3041D0, ch 14, ch 13}` → **TPU3 A channels 14 and 13** (param RAM `0x3041E0`/`0x3041D0`); EXT `0xFEA5EC` disables both via channel-priority helper EXT `0xFE8AF4` before setup; registration EXT `0xFEDA6C` (8 client slots at RAM `0x3FC934`, start EXT `0xFEA5EC`) | client: protocol fn INT `0x205A4`, event fn EXT `0xFE3BCC` | CONFIRMED descriptor & code path; "BSD" name LIKELY (generator setpoint is its client, single-wire 2-TPU-channel service) |
| BSD node | RAM `0x5B90F2` (written EXT `0xFE52BC`); receive accepts node 6 only (`cmpwi r12,6` INT `0x2061C`) | — | CONFIRMED |
| frame | 6-bit setpoint + 2-bit LRF class | — | CONFIRMED layout; meaning of 2-bit field LIKELY (load-response) |
| generator load / DF | RAM `0x5B89EA` = 5-bit BSD value × 8 (0…248) | used by torque maps, CAN TX `0x63DCC` handle 0x75 byte6 = `0x5B89EA·100>>8` (%) | CONFIRMED decode; % scale LIKELY |
| generator status/faults | `0x5B89E6/E7/E8` (bits), `0x5BBAB7`, comm counters `0x5BBBD2-0x5BBBDA`; diagnosis EXT `0xF8953C`, `0xF89CE0` (→ fault flags `0x5B8C0C-0x5B8C14`, calls INT `0x4C600`) | — | CONFIRMED wiring, fault meanings HYPOTHESIS |
| load-response (LRF) | `0x5B90EC = sat(map CAL 0x1C93C4(0x5B9001, 0x3FC2B7) · curve CAL 0x1C93F8(0x5B9307) >> 6)`; `0x5B90ED = CW 0x1C940B==1 ? CAL 0x1C940D (90) : (0x3FB4BF ? 0x5B90EC : CAL 0x1C9413 (200))`; `0x3FB4BF` = timer/debounce of `0x3FC169` (helper INT `0x1E548`, CAL `0x1C9413`) | sent as min(`0x5B90ED`/30, 3) | CONFIRMED formula; LRF name LIKELY |
| alternator torque model | EXT `0xF8A1C8`: variant `0x3FE19C = CAL 0x1C92D4[0x5B89EC + INT 0x1B4B8[0x5B89EB]]` (on new ID `0x5B90E4`); generator speed `0x5B9D66 = 0x5B9A26 · ratio >> 7` (ratio CAL `0x1C933D/3E/3F` = 187/173/187 per variant); torque `0x5B8C2A = map(0x1C8FAC / 0x1C8FF8 / 0x1C9044 by variant; x = load 0x5B89EA, y = 0x5B8C6A) << 5`, 0 when `0x5B8C0F‖0x5B90E2‖0x5B90F8=0‖!0x3FBFB7‖0x5B8C0D`; PT1 (CAL `0x1C9302`) → `0x5B8C28`; `0x5B8C68` = (`0x5B8C2A`+CAL `0x1C92FE`)>>5, or substitute `0x5B8BF8` on BSD fault; `0x5B8C72` = min(`0x5B8C68`, 0xFE) (0xFF = invalid) | — | CONFIRMED structure |
| electrical-power torque | INT `0x5A620`: `T = P_el / (eff × ω)` style: `0x5B8C42` (map×temp curve) × `0x5B8C71` (rpm/240) → `0x5B8C58`; `0x5B8C64` (from `0x5B90F8` and current maps `0x1C8CC8/0x1C8D22/0x1C8D7C`) / `0x5B8C58` → `0x5B8C48` (scaled with CAL `0x1C1150` = 36, the same scale byte as the CAN torque words); `0x5B8C46 = CW 0x1C932F (1) ? 0x5B8C48 : 0`; `0x5B8C4A = 0x5B8C46 + CAL 0x1C92F4 (0)`; `0x5B90E3 = (0x5B8C4A != 0)` | — | CONFIRMED data flow; physical reading LIKELY |
| torque contribution | `0x5B8C4A` → EXT `0xF59E80`: `0x3FB3BA = map CAL 0x1C7A4A(0x5B9A26, 0x5B8C4A) · 0x5B8C4A >> 15` → EXT `0xFB0F10`: idle torque reserve `0x5B97AE` (when `0x3FC1C0 && 0x5B90E3`) → INT `0x46348` (`0x5B97F4 = 0x5B979E + 0x5B97AE/2`, disabled by CAL `0x1C7898`=1) and INT `0x60654` (loss/reference torque) | generator load enters the torque structure as idle-control reserve/pre-control, **not** as a direct term of 0x5B97DA | CONFIRMED path to `0x5B97AE`; how much reaches the engine torque request with stock CAL: LIKELY via `0x60654` only |
| BSD-fault fallback | INT `0x5A620`: `0x3FB4B2` = fault (`0x5B8C0C‖0x5B8C10‖0x5B89E4`) → debounce `0x3FB4B0` (CAL `0x1C9347`) → factor `0x3FB4AC` = 1.0 decaying (PT1 CAL `0x1C932A`) → `0x5B8C70 = 0x5B8C68 + headroom·factor` (headroom `0x5B8C1A = 0x5B8C6E − 0x5B8C68`, max `0x5B8C6E = CAL 0x1C9342/43 (40) + 0x5B8BEA>>4`); used only if CW `0x1C9346` (=0) | — | CONFIRMED |
| substitute model | EXT `0xF892A4` (`0x5B8BF8`) from `0x5B930A` (battery voltage candidate), `0x5B9470`, temps | — | LIKELY |
| generator temperature model / protection | INT `0x5A620` + EXT `0xF47200`: temperatures relative to engine temp (`0x5B9307`/`0x5B9306` by CW `0x1C9340`), NV state `0x3FE19C/0x3FE19E`, writes `0x5B8C3A` (model temperature, also selectable as torque-model input via CAL `0x1C9337`), `0x5B90E5/E7`. No explicit derating of the voltage request from this model was found | — | LIKELY (thermal model); derating NOT FOUND |
| load statistics | EXT `0xF47A54`: load `0x5B89EA` classes → `0x5B90E8` (2 bits, CAN TX byte5) and NV counters `0x3FE1A0/0x3FE1A8` | — | HYPOTHESIS |
| full-load relief (TGENOFVL) | chain `0x5B8F26 → 0x3FB4C6 (CAL 0x1C9412=0) → 0x5B90EB → 0x5B8F2D → relief request` | stock disabled | HIGH CONFIDENCE (round 4) |
| low-voltage override | relief voltages are the **lowest** requests (11.2/10.6 V); setpoint floor `0x5B90F8 ≥ 0` (10.6 V); BSD code floor CAL `0x1C6EC7` = 1. No battery-voltage-based raise found in `0xF8A9D0` (battery management is external: CAN 0x334) | — | CONFIRMED (absence in fn) |
| battery voltage | RAM `0x5B930A` = validated ADC logical ch 0 (INT `0x565FC`: `0x5B89DA = ADC(0)>>2` via INT `0x8B34`; INT `0x1F960`: < CAL `0x1C6C01` (27) → substitute CAL `0x1C6BFF` (149) + error bit `0x3F9BBC.0`); `0x5B96DE = 0x5B930A·0x3C5/4`, filtered `0x5B96DC` (PT1 0x3333); 48 readers incl. generator substitute model | — | LIKELY (battery voltage); scale HYPOTHESIS (~0.094 V/bit if 149 = 14 V) |

#### B2. Start-up / release logic (EXT 0xF8A648), CONFIRMED

```text
0x3FB4C2 := 0 if !0x3FC169; latched 1 if any of: 0x5B90BB > CAL 0x1C941A (240), 0x5B9001 > 0x1C940E (250),
            0x3FC2B7 > 0x1C940F (200), 0x5B86B4 > 0x1C9411 (255), 0x5B899E < 0x1C940C (0), 0x3FE159 < 0x1C9414 (0),
            0x5B899C outside (0x1C9415, 0x1C9416) = (0,255), 0x5B88E0 outside (0x1C9406, 0x1C9408) = (0,0xFFFF)
on rising edge of 0x3FC169: timers 0x3FB4C1 := group map CAL 0x1C939C, 0x3FB4C0 := group map CAL 0x1C9374
            (inputs 0x5B8993, 0x5B853C; counted down in EXT 0xF47E48)
0x5B90EA := 0 if 0x3FB4C2; 1 if !0x3FC169;
            else CW 0x1C9410 (0) ? (pedal released or !0x3FBFB7 ? 0x3FB4C0 : 0x3FB4C1) running
                                 : (0x5B90BB > 0 ? 0x3FB4C1 : 0x3FB4C0) running
0x5B8F2D := CAL 0x1C940A (1) == 1 && (0x5B90EA || 0x5B90EB)   -> relief request in EXT 0xF8A9D0
```
Meaning: generator relief (low setpoint) until `0x3FC169` latches after start, then for a
map-defined time (separate standstill/driving timers). LIKELY "start / drive-off generator relief".


### Unresolved / NOT COMPLETED

* Task periods for DFCO counters and generator ramps (needed to convert ticks to s and 100 mV/step to V/s).
* Meanings of DFCO inhibits `0x3FC28E`, `0x3FC0D4`, `0x3FC184`, `0x3FC140`, `0x3FC198`, `0x3FBEB8`; of `0x5B903C`, `0x5B9285`, `0x5B8512`, `0x3FC29F`, `0x5B86B4`.
* Exact ignition angle / torque ramp shape during ramp-out (INT `0x4A014`, `0x495D0` branches on `0x3FC19F`): NOT COMPLETED.
* CAN-ID of TX handle 0x75 (EXT `0xF5EAF0`, API INT `0x63DCC`) carrying generator load/torque: NOT COMPLETED.
* Battery-voltage scale; which TPU channel (13/14) is TX vs RX; BSD bit timing (TPU function code in CFSR) NOT COMPLETED.
* CAN 0x334 DLC 2 vs. byte2 decode (temperature `0x5B8551`).
* Live data that resolves most items: log `0x3FB351`, `0x5B93B4..B8`, `0x3FC162`, `0x3FC19F`, `0x5B9001`, `0x5B9307`,
  `0x5B90BB` (compare with dash speed) during coast-downs; `0x5B8F7B`, `0x5B8C7E`, `0x5B90F8`, `0x5B89EA`, `0x5B89F1`,
  `0x5B930A` (compare with a multimeter), `0x5B8C4A`, `0x5B97AE` with headlights/rear-window heater switching.
  A PT-CAN capture identifies the 0x334 sender and the handle-0x75 frame.
