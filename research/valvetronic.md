# Valvetronic (770B) — round 4

> **Final-pass status:** lift in µm (HIGH CONFIDENCE), request in 0.1° eccentric angle (LIKELY), target priority CONFIRMED, bank-balance logic CONFIRMED; no per-cylinder control (CONFIRMED). See the *Final static pass* section at the end of this file.


Address kinds: INT = internal-flash CPU, EXT = external-flash CPU, CAL = calibration alias, RAM = runtime.

## 1. Architecture — CONFIRMED (DME side)

The DME does not drive the eccentric-shaft motors itself. It sends one **lift request per bank**
over the private TouCAN-B bus and receives status back:

| Direction | CAN ID (TouCAN B) | DME variable | Function |
|---|---|---|---|
| DME → | 0x105 (signals 0x36/0x37) | bank-1 request `0x5B9D10` | INT `0x4FB78` |
| DME → | 0x10D (signals 0x38/0x39) | bank-2 request `0x5B9D12` | INT `0x4FB78` |
| DME → | 0x1FF (signals 0x34/0x35) | rpm `0x5B9A26`, status bytes | INT `0x4FB78` |
| → DME | 0x185 / 0x18D | `0x5B9D14…0x5B9D1A`, status `0x5B90A4…0x5B90B9`, `0x5B8F20…25` | INT `0x50008` |
| → DME | 0x184 / 0x18C | status/fault bytes `0x5B8A1D…0x5B8A36`, `0x5B8F1C…1F` | EXT `0xF83C8C` |

**HYPOTHESIS:** the separate node is the Valvetronic control unit. This is consistent with the N62
system layout; the node name is not proven from code.

## 2. Request calculation — CONFIRMED arithmetic

```text
bank 1:  req = min( 0x5B9B20 , 0x5B9BB6 + CAL 0x1C6F14 + 0x5B8AEA )      INT 0x4FCF8–0x4FD20
         req = min(req, 0x6EA);  0x5B9D10 = req·65536/0x6EA (≤ 0xFFFE)    → CAN 0x105
bank 2:  same with 0x5B9B22, CAL 0x1C6F12, 0x5B8AEC → 0x5B9D12          → CAN 0x10D
```

* `0x5B9BB6`: common lift target from INT fn `0x4E21C` (below).
* `0x5B8AEA` / `0x5B8AEC`: per-bank trims (written by EXT `0xF88494`, `0xF410DC`, init `0xF2E66C`). **HYPOTHESIS:** bank balancing.
* `0x5B9B20` / `0x5B9B22`: per-bank upper limits from EXT fn `0xFAD4B8` (map CAL `0x1C37DE` 4×4, scalars `0x1C38B4…0x1C38D0`; uses the fed-back values `0x5B9D14/16`). LIKELY fault/limit handling.
* `0x6EA` = 1770 = maximum request unit. Physical unit open (eccentric angle in 0.1° or lift in 1/180 mm are both plausible). HYPOTHESIS.

## 3. Target maps in INT fn `0x4E21C` (geometry CONFIRMED, roles HYPOTHESIS)

| CAL address | Geometry | Axes (inputs) | Output | Role (HYPOTHESIS) |
|---|---|---|---|---|
| `0x1C47E8` | 16×16 u16 | x engine speed 2200…24800 (0.25 rpm/bit: 550…6200 rpm), y `0x5B9B62` 427…4267 | `0x5B9BAC` | main part-load lift map (lift vs rpm × load demand) |
| `0x1C4C98` | 8×8 u16 | x 800…3600, y `0x5B9B64` 1280…4267 | `0x5B9BAC` | alternative/limit region |
| `0x1C4D3C` | 8×8 u16 | x 800…3600, y 24…184 (temperature-like) | `0x5B9BAC` | warm-up lift |
| `0x1C4A2C` / `0x1C4B62` | 21×6 u16 | x `0x5B9B4A` 200…6000 / 400…6000, y rpm 550…1200 | `0x5B9BAC` | idle / low-speed lift |
| `0x1C4DE0` | 16×16 u16 | x `0x5B9BAE` 0…10200, y `0x5B9BCC` or `0x5B9E02` 500…1300 | `0x5B9BBE` / `0x5B9BC0` | lift ↔ air-flow conversion (y possibly pressure 500…1300 mbar) |
| `0x1C503A` | 16 u16 | pedal `0x5B96D8` | — | pedal-based limit/feed-forward |
| `0x1C516C` | 6 u8 | `0x5B9307` (engine temperature) | `0x5B9048` | temperature factor |
| `0x1C50BE` | 12 u16 | 130…9600 | `0x5B9B9C` | rate/limit |

Min/max lift, full-load map, throttle backup interaction and fault fallback are not yet isolated.
Fn `0xFAD4B8` and the status decoding in INT `0x50008` are the next places to look.

## 4. Key question: can airflow through unfuelled cylinders be reduced?

* **Per cylinder: no.** The DME produces exactly two lift requests (bank 1, bank 2) and no
  per-cylinder value exists in the protocol. The N62 mechanism is one eccentric shaft per bank.
  CONFIRMED for the DME side.
* **Per bank: only by cutting a whole bank.** Lowering one bank's lift reduces airflow for all four
  cylinders of that bank, including fired ones. A meaningful reduction of pumped air therefore needs
  a bank-wise cut (mask `0x5A` or `0xA5`) plus minimum lift on that bank.
  * REDABM's balanced patterns are never bank-wise (2 per bank).
  * A single-bank firing order on the N62 cross-plane crank gives uneven intervals (positions 0,2,5,7
    → 180/270/180/90°), so NVH would be poor.
  * Minimum lift still flows air.
  Status: HYPOTHESIS (engineering inference).

---

# Final static pass (round 7, 2026-10-03)

This section supersedes conflicting statements earlier in this file. CONFIRMED items are re-checked by `tools/verify_770b_findings.py` (final-pass blocks).

### A. Valvetronic

#### A1. Protocol: no per-cylinder control (CONFIRMED)

| Frame (TouCAN B) | DLC | Signal / bytes | Content (writer INT `0x4FB78`, init EXT `0xF2D910`) |
|---|---|---|---|
| 0x105 TX | 8 | 0x36 = bytes 0-3 | low byte: checksum `0x5B90A0` (sum of the packed bytes + 0x402); byte 1: alive counter `0x5B90A2` (0..14) + 2-bit fields `0x5B9038` (<<4) and `0x5B8886` (<<6); bits 16-31: **bank-1 request `0x5B9D10`** (u16, 0..0xFFFE = 0..0x6EA) |
| 0x105 TX | 8 | 0x37 = bytes 4-7 | status byte `0x5B904D` + `0x5B9050`<<3 + flag `0x5B8ED9`<<6; other bytes 0xFF |
| 0x10D TX | 8 | 0x38 / 0x39 | the same layout for **bank 2 `0x5B9D12`**, with counter `0x5B90A3`, checksum `0x5B90A1` (+0x40A) and status `0x5B9051` |
| 0x1FF TX | 8 | 0x34 / 0x35 | rpm `0x5B9A26`, mux counter `0x3F9BC0` (0..2): mux 0 = coolant `0x5B9307`·3/4, mux 1 = `0x3F9BC1`, mux 2 = `0x3F9BC2` / `0x5B8F77`+0x28 |
| 0x185 / 0x18D RX | 8 | 0x18/0x19 and 0x1C/0x1D | bytes 2-3: raw actual `0x5B9D18` / `0x5B9D1A` (0xFFFF = invalid); bytes 0-1 and 4-7: status bit-fields `0x5B90A4…0x5B90B9`, with a checksum/counter test |

The checksum constants differ by 8 (0x402 / 0x40A), which matches the 8-ID difference between 0x105 and 0x10D (LIKELY: the CAN ID is folded into the checksum).
Each frame carries exactly **one** 16-bit lift request, and only two request frames exist. The
only application writer of signals 0x36…0x39 is INT `0x4FB78`, apart from the zero-initialisation
in EXT `0xF2D910`. The DME has no per-cylinder Valvetronic value. CONFIRMED (verifier: frame packing, signals 0x36…0x39).

#### A2. Units and scaling

| Quantity | Evidence | Status |
|---|---|---|
| Lift-domain variables (`0x5B9BAC`, `0x5B9BA4`, `0x5B9BA6`, `0x5B9BB0`, actual `0x5B9BA2`/`0x5B9B9C`) are **lift in µm** | main map tops at 9900 and full-load curve at 9900 (N62 max ≈ 9.85 mm); idle and minimum values 180–250 (≈0.2–0.25 mm); conversion curve x 130…9600; model maps use x 250…9600 | HIGH CONFIDENCE |
| Request domain (`0x5B9BB4`, `0x5B9BB6`, clamp 0x6EA, feedback `0x5B9D14/16`) is **0.1° eccentric-shaft angle** | curve CAL `0x1C50BE` maps lift 130…9600 µm to 36…1740 with an S-shaped, non-linear profile. `0x5B9047` = value/10 saturated at 255, i.e. whole units. Max 0x6EA = 177.0 matches the Valvetronic eccentric range (~0–180°) | LIKELY (unit name not in code) |
| CAN scaling | request = units·65536/0x6EA (≤0xFFFE); actual = raw·0x6E9>>16 − bank trim | CONFIRMED |

Conversion curve CAL `0x1C50BE` (12 points): 130→36, 180→94, 320→195, 540→293, 860→395,
1300→495, 2860→745, 4070→896, 7340→1296, 8540→1494, 8970→1595, 9600→1740.
Actual lift `0x5B9BA2` (= `0x5B9B9C`, same value) is the inverse lookup (INT `0x16508`) of the
**bank-1** actual `0x5B9D16` minus the correction `0x5B9DBA`>>8. Only bank 1 feeds the lift actual
used by the air models. CONFIRMED (INT `0x4ECE0…0x4ED80`).

#### A3. Lift target chain (INT `0x4E21C`; priority CONFIRMED, roles as stated)

```
lift(µm) =
  0x3FC1BD ? curve 0x1C503A(pedal 0x5B96D8)                [0…9000]   pedal-direct emergency mode   HYPOTHESIS role
: 0x3FC1C2 ? CAL 0x1C51A6 = 9500                            fixed lift (fault fallback)           HYPOTHESIS role
: 0x5B8F26 && 0x3FBFB7 ? curve 0x1C507C(rpm), factor 1.0   full-load curve                       LIKELY
: 0x5B8ED6 ? ( 0x5B8ED5 ? (0x5B8993>144 ? map 0x1C4D3C : map 0x1C4C98)   start lift
                        : 0x1C4A2C + (0x1C4B62-0x1C4A2C)*0x5B9048/256 )   idle lift
           : map 0x1C47E8(rpm, 0x5B9B62)                     normal (part-load) map
then  0x5B9BAE = max(0x5B9C08, lift)                         0x5B9C08 = minimum-lift request (EXT 0xF7AB04)
      0x5B9BA4 = 0x5B9BAE · 0x5B9BBA/0x8000                  0x5B9BBA = 0x8000 when CAL 0x1C51B0≠0 (stock 1) → correction off
      ramp term 0x5B9B94 (CAL 0x1C5196…0x1C519E, max 0x1C5198) → 0x5B9BB2 ≤ 0x5B9BC2 (curve 0x1C50F0 = 10000, or 9500 if 0x5B886F)
      target = max(0x5B9BA4, 0x5B9BB2);  rpm==0 → CAL 0x1C51A8 = 2000
      0x5B9BA6 = target + 0x5B9DB8 ; 0x5B9BB0 = filter(0x5B9BA6, τ from curve 0x1C514A/0x1C5128 of 0x5B9876)
      0x5B9BB4 = curve 0x1C50BE(0x5B9BB0) + 0x5B9DBA>>8 ; 0x5B9BB6 = 0x5B9BB4 delayed via ring buffer 0x3FACE8 (CAL 0x1C51B2 = 0)
```

Mode flags:

| RAM | Meaning (evidence) | Status |
|---|---|---|
| `0x3FBFB7` | start-end flag: set when rpm byte `0x5B9001` > curve CAL `0x1CCCA0`(coolant), cleared below curve `0x1CCC98` (INT `0x3B888`). Gates the time-after-start counter `0x5B953E` | HIGH CONFIDENCE |
| `0x5B8ED7` | near-idle flag: rpm byte `0x5B9001` vs `0x5B93B7` + 3, hysteresis 3 (CAL `0x1C51AD/AE`) | LIKELY |
| `0x5B8ED6` | = (`0x3FC18B` && `0x5B8ED7`) ‖ !`0x3FBFB7` → selects start/idle maps | CONFIRMED logic |
| `0x5B8ED5` | = CAL `0x1C51AF` (1) && !`0x3FBFB7` → start maps | CONFIRMED logic |
| `0x5B8F26` | full-load flag: EXT `0xFA4F60`, ratio `0x5B9874` = (`0x5B9852`<<15)/`0x5B9854` vs rpm curve CAL `0x1C8B48`, hysteresis CAL `0x1C8B42`, AND !`0x3FC197`, !`0x5B8846`. Also selects VANOS full-load maps and is read by ignition INT `0x49600` | LIKELY |
| `0x3FC18B` | torque/idle-type mode flag set through a pointer in INT `0x46348` (torque structure). Selects idle lift and the VANOS alternative family | LIKELY (exact name open) |
| `0x3FC1BD`, `0x3FC1C2` | the only static writer is init EXT `0xFE4BF0` (cleared); the runtime writer goes through a pointer or a diagnostic routine and is not located | NOT COMPLETED |
| `0x3FE954` | engine running / synchronised (writer INT `0x3988C`); also gates the VANOS default | LIKELY |

Override EXT `0xFB50E4` (called from EXT `0xFB5690`):
* !`0x3FE954` → 0x5B9BB0 = CAL `0x1C51A8` (2000 µm), converted → `0x5B9BB6`.
* Else, if `0x5B8ED8` (latched once start-end is reached) → `0x5B9BB6` ≤ curve CAL `0x1C5112`(rpm) = 400 flat (≈0.9 mm).

The calling context is not traced, so the role of this override is a HYPOTHESIS (stop / after-run positioning).

#### A4. Min / max / fault / full-load / idle / warm-up lift (stock values)

| Item | Value | Source | Status |
|---|---|---|---|
| Minimum lift in maps | 180 µm (idle map 0x1C4A2C, low torque, 550 rpm); 250 µm main map | CAL data | CONFIRMED data, µm HIGH CONFIDENCE |
| Minimum-lift floor | `0x5B9C08` (EXT `0xF7AB04`, three writes; also a VANOS correction-map axis) | — | LIKELY role |
| Maximum lift (request) | 9900 µm (main map corner and full-load curve ≥ 4000 rpm); request clamp 0x6EA = 177.0 units | CAL / INT `0x4FD24` | CONFIRMED values |
| Full-load lift | curve CAL `0x1C507C`: 1000 rpm 5000, 1250 → 5200, 1750 → 6000, 2508 → 7700, 2752 → 8100, 3505 → 8500, ≥3999 rpm 9900 µm | — | LIKELY role |
| Idle lift | map CAL `0x1C4A2C` 21×6 (x `0x5B9B4A` torque/air demand 200…6000, y 550…1200 rpm): 180…1940 µm. Blend partner `0x1C4B62` has weight `0x5B9048` = curve CAL `0x1C516C`(coolant), all 0 in stock → **unused** | — | LIKELY |
| Start / warm-up lift | maps CAL `0x1C4C98` (x 200…900 rpm, y `0x5B9B64`) and `0x1C4D3C` (y `0x5B8993` 24…184, used when > 144): 2000…4000 µm, active before start-end | — | LIKELY (start). No separate warm-up map exists after start; temperature only enters through the start-map selector and the idle blend (0 in stock) |
| Engine-off / rpm 0 lift | 2000 µm (CAL `0x1C51A8`) | INT `0x4EAFC`, EXT `0xFB516C` | CONFIRMED value |
| Fault/fixed lift | 9500 µm (CAL `0x1C51A6`, mode `0x3FC1C2`); upper cap 9500 µm (CAL `0x1C51A0`) when `0x5B886F` (EXT `0xF76E48`, Valvetronic diagnosis area) | — | CONFIRMED value, HYPOTHESIS role |
| Feedback loss | per bank: after > 50 cycles without a valid frame, or with the plausibility counter `0x5B90A8/A9` ≥ 16, actual := 0x6E9 (full range), raw := 0xFFFF, status bytes = defaults, flag `0x5B8F1A`/`0x5B8F1B` = 1 | INT `0x50008` | CONFIRMED |
| Model substitute when feedback is invalid | INT `0x54A5C`: if `0x5B8F1A` ‖ `0x5B8F1B`, the model lift `0x5B95EA` = 1000 (instead of actual `0x5B9BA2`) | INT `0x54C1C…0x54C5C` | CONFIRMED code, role LIKELY (air/throttle model) |

#### A5. Per-bank limits and bank balancing

* **Limits** (EXT `0xFAD4B8`):
  * Common limit `0x5B8884`. In the normal branch it is CAL `0x1C38C6` = 1800 (no limit). In the follow-up branch it is min(`0x5B8878`, max(CAL `0x1C38C8` = 50, filt(min(`0x5B9D16`, `0x5B9D14`)) + map CAL `0x1C37DE`(filt, rpm) = 5…10 units)), i.e. the request may lead the slower bank's actual by only 5–10 units.
  * Per bank: `0x5B9B20` = `0x5B8884` + `0x5B8AEA` and `0x5B9B22` = `0x5B8884` + `0x5B8AEC`. Each is capped at CAL `0x1C38B4` = 1600 when `0x5B8EF5` && `0x3FBEFC`.
  * Status: LIKELY (structure read; condition names open).
* **Balance trim generation** (EXT `0xF88494`; CONFIRMED logic):
  * The filtered lift `0x5B9BB0` is classified into 7 ranges: thresholds CAL `0x1C744E…0x1C7458` = 350/550/1000/1500/2000/2500 µm, hysteresis CAL `0x1C7440` = 20.
  * A learned signed value per range, RAM `0x3FE17A[range]`, is approached by `0x5B8AE8` with step CAL `0x1C7464` = 110. Range 6 (> 2500 µm) gives no offset.
  * If the value is ≥ 0: bank-1 trim `0x5B8AEA` = value, bank 2 = 0. If < 0: bank-2 trim `0x5B8AEC` = −value, bank 1 = 0. Only the bank that needs more lift is raised.
  * A global offset `0x3FE178` is added the same way. It is CAL `0x1C745C` (0) if CAL `0x1C7485` is set, else `0x5B8A9A`.
  * The trims are subtracted again from the decoded actuals (INT `0x50008`), so the models see untrimmed lift.
* **What drives the learning** (EXT `0xF410DC`; LIKELY):
  * It compares the measured λ per bank, `0x5B970A` − `0x5B9708` (INT `0x55A1C`), against CAL `0x1C7462`.
  * It compares the λ-controller outputs, |`0x5B98AA` − `0x5B98A2`| (INT `0x56DD0`), against CAL `0x1C7460`.
  * It also uses `0x5B8948` − `0x5B8942` and the 32-bit values `0x5BA03C`/`0x5BA010` from the injection-time fn INT `0x2ED6C`.
  * Result: a **bank-to-bank air (λ) imbalance adaptation per lift range**. The write path to `0x3FE17A[]` is not fully traced.

#### A6. Throttle / backup interaction

* No direct link from the Valvetronic chain to an identified throttle-position request was found.
  The throttle actuator path itself is not identified in this repo. NOT COMPLETED.
* Evidence that is available:
  * Fault mode `0x3FC1C2` uses fixed 9.5 mm lift. Feedback loss sets the actual to the full-range value and switches the air model to a 1.0 mm substitute.
  * Both fit "Valvetronic to high/fixed lift, load by throttle", but the throttle side is not traced.
  * The VANOS composer blends two map families with weight `0x5B903C` (see B5). The same weight blends the load signal `0x5B9B60` in INT `0x41600` (`0x5B9B60` = old·(256−w) + new·w), so `0x5B903C` is a global operating-mode weight. HYPOTHESIS: throttled vs unthrottled operation. The writer of `0x5B903C` was not found (pointer-indirect; raw scan shows only reads).
* Next step: trace the readers of `0x5B95EA…0x5B9616` (INT `0x54A5C` outputs) and of `0x5B903C`, and look for the throttle H-bridge driver (PWM logical channels 4/5/8/9 are still unidentified).

#### A7. Valvetronic map summary

| CAL | Geometry | Axes (RAM inputs) | Output | Consumer | Probable role | Confidence |
|---|---|---|---|---|---|---|
| `0x1C47E8` | 16×16 u16 | x rpm `0x5B9A26` 550…6200; y `0x5B9B62` 427…4267 (INT `0x41600`) | `0x5B9BAC` 250…9900 µm | INT `0x4E21C` → `0x5B9BB6` | main lift map (normal mode) | selection CONFIRMED, role LIKELY |
| `0x1C507C` | curve 16 u16 | rpm 1000…6300 | lift 5000…9900 µm | `0x4E21C` (`0x5B8F26`) | full-load lift | LIKELY |
| `0x1C4A2C` | 21×6 u16 | x `0x5B9B4A` 200…6000; y rpm 550…1200 | 180…1940 µm | `0x4E21C` (`0x5B8ED6`, after start) | idle lift | LIKELY |
| `0x1C4B62` | 21×6 u16 | x `0x5B9B4A` 400…6000; y rpm 400…1200 | 200…2311 µm | blend weight `0x5B9048` = 0 | second idle map (cold), unused in stock | LIKELY / inactive |
| `0x1C4C98` | 8×8 u16 | x rpm 200…900; y `0x5B9B64` | 2000…4000 µm | `0x4E21C` (start, `0x5B8993` ≤ 144) | start lift | LIKELY |
| `0x1C4D3C` | 8×8 u16 | x rpm 200…900; y `0x5B8993` 24…184 | 2000…4000 µm | `0x4E21C` (start, `0x5B8993` > 144) | start lift (temperature branch) | LIKELY |
| `0x1C503A` | curve 16 u16 | pedal `0x5B96D8` | 0…9000 µm | `0x4E21C` (`0x3FC1BD`) | pedal-direct emergency lift | HYPOTHESIS |
| `0x1C50BE` | curve 12 u16 | lift `0x5B9BB0` 130…9600 µm | 36…1740 (0.1° eccentric) | `0x4E21C`, EXT `0xFB50E4`; inverse at `0x4ED24/0x4ED70` | lift ↔ eccentric angle | CONFIRMED use, unit LIKELY |
| `0x1C5112` | curve 5 u16 | rpm | 400 flat | EXT `0xFB50E4` | request cap after start (override) | HYPOTHESIS role |
| `0x1C50F0` | curve 8 u16 | rpm | 10000 flat | `0x4E21C` → `0x5B9BC2` | ramp upper limit (inactive) | CONFIRMED data |
| `0x1C514A` / `0x1C5128` | curve 8 u16 | `0x5B9876` (EXT `0xFA4F60`) | 65535…3277 | filter `0x5B9BB0` | target filter time constant | LIKELY |
| `0x1C4DE0` | 16×16 u16 | x lift `0x5B9BAE` 0…10200; y type-A cam pos (`0x5B8DCA` / `0x5B8DCC` by CAL `0x1C51B4`) or `0x5B9E02` 500…1300 | 0 / 62500 step | ratio → `0x5B9BB8` → `0x5B9BBA` | lift/cam-dependent correction; **forced 1.0 in stock** (CAL `0x1C51B0` = 1) | CONFIRMED inactive |
| `0x1C652E` | curve 8 u16 | lift 250…9000 | 13…43 (×30) | `0x5B9BC6/C8` = cam pos + 30·f | lift-dependent intake event offset (0.1°CA) | LIKELY |
| `0x1C2AC0` | curve 10 | 0…1800 (0.1°CA) | 0…255 | `0x4E21C`, INT `0x4DF50` | valve-event weighting | HYPOTHESIS |
| `0x1C5024` / `0x1C5030` | 2×2 u8 | `0x5B9001`, `0x5B903F` | factors | `0x4E21C` | correction factors (feed `0x5B9BB8`) | HYPOTHESIS |
| `0x1C516C` | curve 6 u8 | coolant `0x5B9307` | 0 (all) | `0x5B9048` | idle-map blend (off) | CONFIRMED data |
| `0x1C37DE` | 4×4 u16 | x filtered actual 100…600; y rpm 550…3000 | 50…100 | EXT `0xFAD4B8` | allowed lead of request over actual | LIKELY |
| `0x1C744E…58` | 6 u16 | lift `0x5B9BB0` | range index | EXT `0xF88494` | balance lift ranges | CONFIRMED use |
| scalars `0x1C51A6` 9500, `0x1C51A8` 2000, `0x1C51A0` 9500, `0x1C38B4` 1600, `0x1C38C6` 1800, `0x1C6F14`/`0x1C6F12` 0 | — | — | — | see A3–A5 | fixed lift, engine-off lift, cap, per-bank cap, common limit, static bank offsets (0) | CONFIRMED values |

---------------------------------------------------------------------------------------------------

### Unresolved / next evidence

* Bank 1 vs 2 for VANOS pairs: tester correlation or wiring (B7).
* Writers of `0x5B903C`, `0x3FC1BD`, `0x3FC1C2`, `0x5B9DB8` / `0x5B9DBA` (pointer-indirect or diagnostic). A pointer-tracking pass over INT `0x406B0` / `0x41600` and the diagnostic job table would resolve them.
* Throttle actuator path and its coupling to Valvetronic fault modes.
* Learning path into `0x3FE17A[]` (balance table) inside EXT `0xF410DC`.
* Calling context of EXT `0xFB50E4` (stop/after-run override).
* VANOS +0x08 per-object scalar (1270 type A / 710 type B): not used in INT `0x3EF24…0x3FBAC`, so another reader holds it.
