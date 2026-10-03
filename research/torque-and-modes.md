# Torque model, driver wish, kickdown and modes (770B) — round 2

> **Final-pass status:** torque words, CAN scaling (36/2048) and the full arbitration chain are CONFIRMED; 0x3FBF34/38 are fault reactions (REJECTED as DSC); Nm/bit not provable statically. See the *Final static pass* section at the end of this file.


Address conventions as in `research/aevab-redabm.md`.

## 1. Driver wish — KFPED found

| Item | Address | Status | Evidence |
|---|---|---|---|
| `KFPED` | CPU `0x1C87DA` (file `0xC87DA`), map 16×8 u16 | **HIGH CONFIDENCE** | INT `0x46370`: `bl 0x17B64` (u16 map helper) with r3 = record, r4 = `0x5B96D8`, r5 = `0x5B9A26`; output stored to `0x5B981A` |
| x axis | 16 points 0…65535 | CONFIRMED | pedal 0…100% (u16, 65535 = 100%) **LIKELY** |
| y axis | 8 points 1280…24000 | CONFIRMED | engine speed at 0.25 rpm/bit → 320…6000 rpm **LIKELY** |
| values | 0…32768, x-major order `v[ix*8+iy]` | CONFIRMED | pedal 0% → 0 at all speeds; pedal 100% → 32768. Read as relative torque with 32768 = 100% (**LIKELY**) |
| `KFMRMI` | CPU `0x1C86EA`, 16×6 u16 | LIKELY (name) | INT `0x46680`, x = rpm, y = `0x5B97EE` → `0x5B980C` |
| `KFMIMR` | CPU `0x1C85FA`, 16×6 u16 | LIKELY (name) | INT `0x467B0`, x = rpm, y = `0x3FB460`, result into helper `0x1DEEC` |

Name evidence: in 560B the three records start at `0x8506`, `0x85F6`, `0x86E6`, exactly 0xF0 apart.
A 16×6 u16 record is 4 + 2·(16+6) + 2·96 = 240 = 0xF0 bytes. In 770B the three records start at
`0x1C85FA`, `0x1C86EA`, `0x1C87DA`: the same order and spacing, at local delta +0xF4. The third
record is the only 16×8 pedal × rpm map and behaves as a driver-wish map. Counter-evidence: the
560B record sizes were not re-measured from the 560B XDF in this round.

Full-pedal driver wish: EXT fn `0xF887A0` evaluates KFPED at pedal = 0xFFFF → `0x5B9810`, takes the
max with curve `0x1C8912` (rpm) → `0x5B9816`. **HYPOTHESIS:** this is the maximum available wish used
for EGS/kickdown or a torque limit.

### Sport map (`KFPEDS`) — not found

* There is exactly one other 16×8 u16 map on the same rpm axis: `0x1CF610` (EXT `0xFA483C`). Its
  x axis spans 0…31785 and its values are linear (≈2×x, rpm-independent). Input `0x5B954E` is written
  by EXT fns `0xFAA0F8/0xFAA384`, a large state machine reading gear, speed and several curves.
  Output `0x5B9820` is rate-limited into `0x5B9822`. **HYPOTHESIS:** this is the cruise-control
  pedal-equivalent path, **not** KFPEDS. **REJECTED:** "0x1CF610 is the sport pedal map" as a working
  assumption, because the shape argues against it.
* `0x3FC188` (set in the driver-wish fn when the KFPED value exceeds a competing request) switches
  the exhaust-flap pedal source to `0x5B9822`. **HYPOTHESIS:** "cruise request dominant".
* `B_sptvar`/sport-button flags from the 725D A2L have no 770B equivalent identified yet. Next step:
  find the CAN input bit for the sport button (E65 has DSC/sport via CAN) and trace consumers.

## 2. Kickdown — function CONFIRMED, names HIGH CONFIDENCE

INT fn `0x3B80C` (writes `0x3FBFB3` only):

```text
if pedal_fault(0x3FC068):            B_kd := 0
elif wped(0x5B96D8) < WPKDMN(0x1C1E4C = 0xFFFF):  B_kd := 0
elif upwg(0x5B96D0) <= 4*UPWGKDU(0x1C1E4B = 0xCE): B_kd := 0
elif upwg(0x5B96D0) >= 4*UPWGKDO(0x1C1E4A = 0xD2): B_kd := 1
(else hold)
```

* The 560B XDF order (`UPWGKDO 0x1ECE`, `UPWGKDU 0x1ECF`, `WPKDMN 0x1ED0`) is reproduced exactly at
  `0x1C1E4A/4B/4C`, but with a **negative** local delta (−0x84).
* Stock calibration requires **pedal = 100%** plus pedal-pot voltage beyond the detent threshold.
  So kickdown is the pedal overtravel/detent, not a percentage threshold.
* Consumers of `B_kd`: EXT `0xF1BCC8` and EXT `0xFA8E70`. **HYPOTHESIS:** `0xFA8E70` packs
  pedal/kickdown/intervention status for CAN, since it reads `0x3FBFB3`, `0x5B96D8`, `0x5B9822` and
  `0x3FBF34/35/3A` and writes `0x5B92C9`, `0x5B902B/2C`.
* For an E-mode override (round-1 H3): `B_kd` exists, but on this calibration it only fires at
  full pedal. A softer override would need either `WPKDMN` < 100% (changes what EGS sees as
  kickdown) or a separate threshold. Status: HYPOTHESIS / UNTESTED.

## 3. Torque request and intervention path (partial)

| Signal | Address | Evidence | Status |
|---|---|---|---|
| base torque (no intervention) | `0x5B97DA` | divisor in AEVAB step ratio; written INT `0x461AC` (fn `0x45C3C`) | LIKELY |
| target torque after intervention | `0x3FC32A` | numerator in AEVAB ratio; written INT `0x47E2C/0x47E38` (fn `0x47AB0`) and EXT `0xF2EBD8` | LIKELY |
| torque reachable without cut | `0x5B97E0` × `0x3FC2F9`/200 | compared with target using MDHYEZ hysteresis | LIKELY |
| intervention-source flags | `0x3FBF34`, `0x3FBF38` (fn `0x404D4`), `0x3FC1A3` (fn `0x48B04`), `0x3FC195`/`0x3FC198` (fn `0x47AB0`), `0x3FC162` | enable AEVAB | sources HYPOTHESIS |
| full cut (overrun / all-cylinder) | `0x3FC19F` | read by >40 functions | HYPOTHESIS: overrun fuel cut-off state |

The precise split into fast path (ignition) and slow path (air) is not yet traced. Fn `0x4A014`
(three 16×12 signed byte maps `0x1CB8AC/0x1CB98A/0x1CBA68`, writes `0x3FC2F9`) is the best candidate
for the ignition-efficiency part of the torque model (HYPOTHESIS).

## 4. DME ↔ EGS torque exchange

The CAN controllers are TouCAN A (`0x307080`) and TouCAN B (`0x307480`). They are accessed from
INT `0x62704/0x62768` and EXT `0xF09D0C/0xF09D50`; message buffers are reached through pointers.
Mapping these to the E65 PT-CAN identifiers is **not done**: a direct search for TouCAN-encoded
IDs (`id<<5`) found no clean ID table. Gear input to engine functions: `0x5B92CA` (0…6, gear axis of
the exhaust-flap map; LIKELY). See `research/egs-integration-plan.md` for the capture plan.

## 5. Safe logging variables

`0x5B96D8` pedal, `0x5B96D0` pedal-pot voltage, `0x3FBFB3` B_kd, `0x5B9A26` rpm, `0x5B981A` driver
wish, `0x5B9816` full-pedal wish, `0x5B97DA` base torque, `0x3FC32A` target torque, `0x5B93E7` AEVAB
step, `0x5B92CA` gear. All are read-only RAM. Scale factors are LIKELY at best; verify live.

## 6. Cruise control (FGR) speed handling — added on request

Question: does the DME hold fixed cruise-control speed presets (e.g. 60/70 and 100–110 km/h)?

Answer: **no preset/set-speed table was found** in the DME cruise code (EXT fns `0xFA93F8`,
`0xFAA0F8`, `0xFAA384`). Speed calibrations use 1/128 km/h per bit. This scale is **LIKELY**
because every constant comes out as a round value: 1, 2, 4, 5, 10, 12, 16, 20, 40, 150 and 250 km/h.

| Calibration (CPU) | Value | Use in code | Status |
|---|---|---|---|
| `0x1C2002` | 128 = **1 km/h** | added to / subtracted from the set speed per lever step (`0xFABA90…0xFABB60`); option bit `0x1C1FB5`.4 selects base = current set speed vs. actual speed | CONFIRMED arithmetic, meaning LIKELY |
| `0x1C2006` | 1280 = 10 km/h | deviation threshold (actual − set) that switches cruise state (`0xFAAC74`) | LIKELY |
| `0x1C1FFC`/`0x1C2004` | 1536 = 12 km/h | thresholds in the state machine | HYPOTHESIS |
| `0x1C1FFE`/`0x1C2000` | 4 / 2 km/h | thresholds near `0xFAC2B4/0xFAC2E8` | HYPOTHESIS |
| `0x1C2008/0x1C200A/0x1C200C` | 40 / 20 / 5 km/h | thresholds near `0xFAB800…0xFAB840` | HYPOTHESIS |
| `0x1C1F92/0x1C1F94` | 16 / 40 km/h | plausibility differences with debounce counters (limit 5000 at `0x1C1F96/98`) | LIKELY |
| `0x1C1FA0`, `0x1C1F8A/8C`, `0x1C1FA2` | 150 / 250 / 250 km/h | upper limits | HYPOTHESIS |
| curves `0x1C1FB8` / `0x1C1FDA` | axis 30,60,90…210,250 km/h; flat values 9 / 14 | speed-dependent parameters (gain-like) | HYPOTHESIS |
| map `0x1C200E` | x = **30, 50, 70, 100, 130, 200 km/h**, y = gear 0…7 | speed × gear-dependent parameter, values 0…282 | HYPOTHESIS: controller gain/acceleration limit |

So the "≈60/70 and 100–110" speeds the user noticed are most likely these **breakpoints** (70 and
100 km/h in `0x1C200E`), not selectable presets. A "jump to the next 10 km/h" lever behaviour, if
the car shows it, is not implemented in these DME functions: no 10 km/h rounding or division was
found in `0xFA93F8–0xFAC420`. It is probably done in the steering-column/cruise-stalk electronics
before the request reaches the DME over CAN (HYPOTHESIS; check with a CAN capture of lever presses).

Other 1/128-km/h-looking axes containing 50/60/70/80/100/110 exist (e.g. map `0x1C5B70`, y-axis
16…110, used in INT fn `0x2D234`). They belong to non-cruise functions, and their physical unit is
unverified.

---

# Final static pass (round 7, 2026-10-03)

This section supersedes conflicting statements earlier in this file. CONFIRMED items are re-checked by `tools/verify_770b_findings.py` (final-pass blocks).

Address types: INT / EXT / CAL / RAM / IO as in BRIEF. "T-units" = internal torque LSB (physical unit unproven, §2).
Helpers used below: INT 0x1DED0 = (a·b)>>15 sat; INT 0x1DEEC = (a·b)>>14 sat; INT 0x1DEC4 = (a·b)>>16;
INT 0x15E58 = 32/16 divide; efficiency bytes use **200 = 100 %** (CONFIRMED: 0x5B93E1 = 200·(8−n)/8).

### 0. Corrections / new facts vs. earlier rounds

| Item | Old | New | Status |
|---|---|---|---|
| 0x0B5 bytes 0-3 | "no reader" (round 3, signal API only) | read from the **raw RX buffer** (handle 0x0B, `0x3FAE9C`+0xDC) by EXT 0xF15450: torque request s12 bits 12-23 → `0x3FA04E`, s12 bits 24-35 → `0x3FA04C`, mode byte4 bits4-5 → `0x3FA048`, checksum byte0 = Σbytes1-7 + 0xB5, counter byte1 low nibble | CONFIRMED |
| 0x0B6 | "only freshness" (signal API) | raw-buffer decode (handle 0x0C, +0xF0) by EXT 0xF1241C: s12 bits 12-23 → `0x3FA046`, s12 bits 24-35 → `0x3FA044`, mode byte4 bits4-5 → `0x3FA042` (0/3 invalid), checksum = Σbytes1-4 + 0xB6, counter | CONFIRMED (DSC origin LIKELY) |
| 0x0CE, 0x19E, 0x1A0 (INT 0x5B988) | DSC torque candidates | not torque: 0x0CE = four u16 (→ `0x5B94AE/B2/AC/B0`, 0x8000 on timeout; wheel speeds LIKELY); 0x1A0 bits0-11 ×12.8 → `0x5B9980` (1/128 km/h ⇒ vehicle speed LIKELY), s12 → `0x5B8536`/abs → `0x5B8538`; 0x19E status bits | CONFIRMED decode, meanings LIKELY |
| `0x3FBF34/0x3FBF38` | "DSC/ASC" (round 2/3 HYPOTHESIS) | pure flag logic (INT 0x404D4) over fault flags written by pedal/E-gas monitoring fns (INT 0x3A984, 0x44198, 0x1A0E0, 0x1A9F0, EXT 0xFADF90, 0xF3E458); they select reduced rev limits 1200 rpm / curve 1200…3640 rpm | **REJECTED as DSC**; limp-home/monitoring fault reaction LIKELY |
| `0x3FC1A3` | "EGS/limiter" | rev-limiter active flag (INT 0x48B04) | CONFIRMED |
| `0x3FC195` | open | DSC/ASC-dominant flag (INT 0x47AB0) | CONFIRMED logic, DSC origin LIKELY |
| Round-6 "second request word via r19" in `0x5B9808 = min(0x5B980A, ·)` | unknown | r19 = &`0x5B9854` → `0x5B9808 = min(driver request, max torque)` | CONFIRMED |
| `0x5B9800/02/04, 0x5B97EE, 0x5B980C, 0x5B9818` (limit chain inside INT 0x46348) | — | computed but **no consumer** (KFMRMI CAL 0x1C86EA is an identity map) | CONFIRMED dead for the request |

### 1. Torque words in 0x0A8 / 0x0A9 / 0x0AA (positions from round 4, CONFIRMED)

Converter (INT 0x4BCCC): `CAN = clamp_s12( sat_s16((T>>1) − (L>>1)) · S >> 10 )`, L = `0x5B94BC` (= copy of loss
torque `0x5B97AA`, written INT 0x4BE24), S = `0x5B922A` = CAL 0x1C1150 = **0x24 (36)**. Variant INT 0x4BD40 adds signed
`0x5B9784` (half T-units) before scaling. So every field is **effective torque = indicated − loss**, in CAN units of
**2048/36 = 56.9 T-units**; signed 12-bit two's complement, 0x800 reserved (TX sends 0x801). CONFIRMED.

| Frame bits | RAM word → src | Producer | Upstream (traced) | Meaning | Conf. |
|---|---|---|---|---|---|
| 0x0A8 12-23 | `0x5B94CA` ← conv2(`0x5B983A`) | INT 0x4790C | `0x5B983A = 0x5B9838·(200−25·n_cut[0x5B92EC])/200`; `0x5B9838 = 0x5B97E0·η_zw/200`; η_zw = 200 − curve CAL 0x1C7DC4[Δ]·`0x5B8B1C`/32, Δ = max(0, `0x5B93DC`(optimum ign.) − `0x3FC2EF`(actual ign.)) | **actual (delivered) torque after ignition + cut interventions**, effective, incl. `0x5B9784` offset | CONFIRMED formula; name HIGH (Bosch mi_ist structure) |
| 0x0A8 28-39 | `0x5B94C6` ← `0x5B9878` | INT 0x48F68 | steady state = `0x5B983A`; = `0x5B983E` (fast-path target) when torque-increase request `0x3FC19A`; during an external limit (`0x5B9842` ≤ `0x5B9884`, flag `0x3FC1A6`) = `0x5B9882` = min(`0x5B9886`, max(DSC `0x5B949C`, `0x5B985C`)) | torque after intervention / target as seen by EGS | formula CONFIRMED; name HYPOTHESIS |
| 0x0A9 16-27 | `0x5B94D0` ← conv(0) | INT 0x4BDDC | = −`0x5B97AA`·36/2048 | **loss / drag torque** (effective torque at zero indicated) | CONFIRMED formula; name LIKELY→HIGH |
| 0x0A9 28-39 | `0x5B94CC` ← `0x5B9854` | EXT 0xFA4D04 | KFMIOP CAL 0x1C828E (rpm 0x5B9EFC × rel. charge) at rl_max `0x5B985A`=min(`0x5B9858`,`0x5B8850`), × KFPED(100 %)`0x5B9810`/32768 × CAL 0x1C89CC/128 (=1) | **maximum available torque** (optimum ignition, max charge) | CONFIRMED formula; name HIGH |
| 0x0A9 40-51 | `0x5B94D2` ← `0x5B985C` | INT 0x484F8 | `0x5B97E0·0x3FC2F9/200`; `0x3FC2F9` = 200 − 0x1C7DC4[Δmax]·`0x5B8B1C`/32, Δmax = `0x5B93DC` − latest ign. `0x5B9460` (INT 0x4A014) | **minimum torque reachable by ignition alone** (ignition-limited minimum, no cut) | CONFIRMED formula; name HIGH |
| 0x0A9 52-63 | `0x5B94C8` ← `0x5B987A` | INT 0x48F68 | steady = `0x5B983A`; in limit state = `0x5B9886` = `0x5B9880`·(200−25·`0x5B92EB`)/200 with `0x5B9880` = max(min(max(`0x5B987C`,`0x5B985C`),`0x5B97DA`),`0x5B9860`); with MSR (`0x3FC198`) = min(`0x5B97DA`,`0x5B984A`) | torque **before fast intervention** (air-path achievable) | formula CONFIRMED; name HYPOTHESIS |
| 0x0AA 12-23 | `0x5B94CE` ← `0x5B980A` (0 if `0x3FC19F`) | INT 0x46348 | §1a | **driver-request torque** (pedal/cruise, before limits) | CONFIRMED formula; name HIGH |

Not present on CAN (resolved by absence): friction-only torque (only total loss sent), cylinder-cut-limited torque,
explicit "before/after intervention" pair other than the 0x0A8/0x0A9 word pair above.

#### 1a. Driver-request chain (INT 0x46348, CONFIRMED arithmetic)
```
0x5B981A = KFPED(pedal 0x5B96D8, rpm)            (32768 = 1.0 relative)
0x5B981C = (0x3FBEDD [0x0B5 byte5 b6-7] || 0x3FE313.0) ? min(0x5B981A, 0x3FB460 + 0x3FB45E) : 0x5B981A
0x3FB460 = 0x5B981C                               -> EGS flag = rise-rate limit of the pedal wish (step 0x3FB45E from EXT 0xF887A0)
0x5B9812 = max(0x5B981C, cruise 0x5B954E);  0x3FC188 = cruise dominant
0x5B9814 = max(0x5B9812, 0x5B97BE [INT 0x3D530])
rel      = min(0x5B9814, 0x8000)
mi       = 0x5B979C + rel·(0x5B9856 − 0x5B979C)>>15          0x5B979C = loss-based zero-pedal torque, 0 in overrun 0x3FC162 (INT 0x3D4B8)
0x5B980A = min( ((mi>>1) + 0x5B9784) · KFMIMR(rpm,0x5B9814)>>14 , CAL 0x1C8AF4·256 = 0xFF00 )   KFMIMR = 32768 at rel ≤ 1.0
0x5B9808 = min(0x5B980A, 0x5B9854 max)  -> tip-in filter (round 6) -> 0x5B9806
0x5B97F4 = 0x5B979E (CAL 0x1C7898 = 1, else + 0x5B97AE/2);  0x5B97FC = 0x5B9806 + 2·0x5B97F4   (fast request)
0x5B97FA = 0x3FB462 (gear-dependent filtered copy, CAL 0x1CF516/0x1CF47C) + 2·0x5B97F4            (slow request)
```

### 2. Reference / scaling chain

| Item | Finding | Status |
|---|---|---|
| `0x5B97AA` | **total loss torque** (INT 0x60654): `0x5B97A4` = map CAL 0x1C789A(rpm 550…6000, rl 10…100 %) + curve 0x1C7854(`0x5B9BA2`) [+ curve 0x1C7876(rpm) if `0x5B888B`]; `0x5B97A6` = +adaptive offsets `0x3FB3A8` + s`0x3FB3AA` (EXT 0xF591E0); `0x5B97A2` = + map 0x1C7A16(rl, rpm)·s`0x5B8B06`>>15; `0x5B97AA` = + `0x5B97AE` (EXT 0xFB0F10, accessory torque); all sat. u16 | sum CONFIRMED; friction map LIKELY; addend identities HYPOTHESIS (`0x5B888B`/`0x5B97AE` accessory/AC candidates) |
| `0x5B94BC` | copy of `0x5B97AA` for TX/RX converters | CONFIRMED |
| `0x5B922A` | = CAL 0x1C1150 byte (0x24), written EXT 0xF3C574 (an init-type fn, no CAN input; not from 0x5C3) | CONFIRMED |
| `0x5B94B6` | = 0x800 / CAL 0x1C1150 = 56 (if CAL = 0 → 0xFFFF); RX inverse `T = raw_s12·0x5B94B6 + 0x5B94BC` used for 0x0B5 (INT 0x4A700) and 0x0B6 (EXT 0xFB5B78) | CONFIRMED |
| rel. charge `0x3FC302` | axis breakpoints 427/853/2133/4267 = 10/20/50/100 % → **0.0234375 %/bit (4267 = 100 %)** | HIGH (round numbers in 3 tables) |
| KFMIOP | CAL 0x1C828E, 16 rpm (axis CAL 0x1C1360: 550…6500 rpm) × 16 rl (axis CAL 0x1C848E: 0…110 %) u16, data only; ≈ 53 300 T at 3700 rpm/100 % | CONFIRMED geometry/values |
| Internal torque unit | **Not provable statically.** Only the ratio CAN:internal = 36/2048 (TX) / 56 (RX) is code-proven. Plausibility: if 1 CAN bit = 0.5 Nm (common E-series assumption, not verified here) → 1 T ≈ 0.00879 Nm; then 100 % rl at 3700 rpm → (53 300 − 6 540 loss)·36/2048·0.5 ≈ 410 Nm, ≈ 370 Nm at 90 % rl (N62B36 rated 360 Nm) — physically consistent; 1.0 or 0.25 Nm/bit give 820 / 205 Nm (implausible) | HYPOTHESIS (0.5 Nm/CAN bit) |
| What would prove it | (a) EGS firmware decode of 0x0A8/0x0A9 scaling; (b) live log at WOT 3700 rpm: 0x0A9 bits 28-39 vs rated 360 Nm, and `0x5B9854`, `0x5B97AA`, `0x3FC302`; (c) a 770B A2L/DAMOS (normalisation/reference-torque constant); (d) idle with known accessory steps (AC on/off → change in 0x0A9 bits 16-27) | — |

### 3. Intervention variables

| Var | Writer (fn) | Source | Consumers | Class | Conf. |
|---|---|---|---|---|---|
| `0x3FBF34` | INT 0x404D4 = 3FBF11‖3FBF0B‖3FBF02‖3FC0CC‖3FC0BE | fault flags of pedal/E-gas monitoring (INT 0x3A984, 0x44198, EXT 0xFADF90, 0xF3E458, INT 0x1A9F0) | 0x484F8 (AEVAB enable), 0x42FC4 (full cut with `0x3FC1A4`), 0x48B04 (rev limit = curve 0x1C8B00(`0x5B9305`)·160 → 1200…3640 rpm) | other: limp-home fault reaction | LIKELY |
| `0x3FBF38` | INT 0x404D4 = 3F98C0 ‖ 3FBF36 ‖ 3FBF37; 3FBF36 = 3FBF1E ‖ (3FBF1F && 3FBF24); 3FBF37 = 3FC0C6‖3FC0BA‖3FC0C8 | same family + `0x3F98C0` (EXT CAN/monitoring fns 0xF128A0…0xF1605C, 0xF36FE8) | 0x484F8, 0x42FC4 (full cut if rpm byte > CAL 0x1C5550), 0x48B04 (rev limit CAL 0x1C8B32 = 1200 rpm) | other: severe fault reaction | LIKELY |
| `0x3FC1A3` | INT 0x48B04 | rpm vs limit (CAL 0x1C8B2E 6500 / 0x1C8B30 2000 if `0x3FC22A` / fault limits) | AEVAB enable (0x484F8); `0x5B9870` limit used in 0x47AB0, 0x480AC, 0x48F68 | rev limiter | CONFIRMED |
| `0x3FC1A4` | INT 0x48B04 (via ptr) | rpm > limit + `0x3FB474` (hard) | `0x5B9870` := 0; 0x42FC4 full cut **only with `0x3FBF34`** | rev limiter hard stage | CONFIRMED |
| `0x3FC195` | INT 0x47AB0 | `(0x5B949A < min(0x5B9854,0x5B97FC)) ‖ (0x5B9846 == 0x5B949C)` | AEVAB enable (CAL 0x1C8A18 bit0 = 1 ⇒ active), `0x5B985C` − CAL 0x1C8A19·256 (=0) | DSC/ASC reduction dominant | CONFIRMED logic, DSC LIKELY |
| `0x3FC198` | INT 0x47AB0 | `0x5B94A0 > 0x5B983E` (DSC mode-1 torque increase) | blocks full cut `0x3FC19F`; 0x48F68 branch | DSC MSR (drag-torque control) increase | CONFIRMED logic, MSR LIKELY |
| `0x3FC19A` | INT 0x47AB0 | `0x5B94A8 > 0x5B983E` ‖ `0x5B9DD4 > 0x5B983E` | 0x48F68, 0x4A700 plausibility | EGS increase (or `0x5B9DD4`) active | CONFIRMED logic |
| `0x3FC19F` | INT 0x484F8 | `0x3FC162` && !`0x3FC198` && !`0x3FBEB8` && !blank-block `0x3FC19E` (CAL 0x1C8A18 bit1 = 0) | AEVAB step 8; 0x0AA request := 0; > 40 fns | overrun all-cylinder cut | CONFIRMED |
| `0x3FC162` | via pointer in EXT 0xFAE33C (round 4) | overrun state machine | 0x484F8 (cut, **not** AEVAB enable: CAL bit1 = 0), `0x5B979C` := 0, `0x5B97F4` | overrun | LIKELY (writer site unresolved) |
| `0x3FBEB8` | INT 0x4A700 | 0x0B5 mode = 1 | blocks `0x3FC19F` | **EGS torque-increase request** | CONFIRMED |
| `0x5BBBA8` | INT 0x430A4 (bits 0x02 ← `0x3FBFED` = `0x3FBFEC`‖`0x3FBFEE`; 0x04 ← 3FBEFF; 0x08 ← 3FC247; 0x80 ← 3FB830.1; 0x100 ← 3FBE99/0x431EC) | `0x3FBFEC` = (3FBF38 && rpm > 0x23) ‖ (3FC1A4 && 3FBF34); `0x3FBFEE` = 3F98C0 && rpm > 0x23 | final mask 0xFF | total fuel cut (fault reactions + others) | CONFIRMED logic |
| `0x3FC32A` | INT 0x47AB0 | `0x3FC197 ? 0x5B9860 : 0x5B9846` | 0x484F8 (step), 0x32EE8 (ignition), 0x4A014 | final fast-path target | CONFIRMED |

#### 3a. EGS path — CONFIRMED end-to-end (code), names of endpoints LIKELY
```
CAN 0x0B5 (raw RX buffer handle 0x0B) ─ EXT 0xF15450 ─► 0x3FA04E (s12 b12-23), 0x3FA04C (s12 b24-35), 0x3FA048 (mode b36-37)
  INT 0x4A700 (valid: 0x3FBEF0, EGS present 0x3FBED1, freshness, !0x3F98AD, !0x3FE313.0, raw ≠ −0x800):
    mode 2 (reduce):  0x5B94A4 = 0x3FA04E·56 + loss          (fast limit; else 0xFFFF)
                      0x5B94A2 = max(0x3FA04C·56 + loss, 0x5B94A4)   (slow limit)
    mode 1 (increase): 0x5B94A8 = 0x5B94A6 = 0x3FA04E·56 + loss; 0x3FBEB8 = 1   (plausibility 0x3FBEB5..BC → 0x3F9925 disables)
  fast path INT 0x47AB0: 0x5B9840 = min(DSC 0x5B949C, EGS 0x5B94A4, 0x5B9DD6); 0x5B9842 = 0x5B9840 (0xFF00-floored if rpm byte < CAL 0x1C8968 = 11)
                         0x5B983E = min(0x5B97FC, 0x5B9832, 0x5B9870, 0x5B9842)        [0x5B8B38 off: CAL 0x1C8965 bit0 = 0]
                         0x5B9846 = max(0x5B983E, DSC 0x5B94A0, 0x5B9DD4, EGS 0x5B94A8) → 0x3FC32A
  ignition INT 0x32EE8:  0x5B9970 = 0x5B97DA − max(0x3FC32A, 0x5B985C); η = (0x5B984A − 0x5B9970)·200/0x3FB864
                         → inverse η-curve CAL 0x1CAB68 / 0x1CAA9C → retard → 0x5B9434 = 0x5B93DC − retard → INT 0x33650 (→ 0x3FC2EF)
                         EGS-active (0x5B94A4 == 0x3FC32A / 0x5B9846) switches latest-ignition limit to 0x5B945D (INT 0x4A014)
  AEVAB: NOT enabled by EGS (enable = 0x3FBF38‖0x3FC1A3‖0x3FBF34‖0x3FC195; EGS sets none) → EGS cut only if another enable is set
  slow path: 0x5B94A2 → 0x5B9834 (EXT 0xFA488C; CAL 0x1C8948·256 if 0x3FE313.0; 0xFF00 without EGS) → INT 0x480AC
             0x5B9852 = min(max(slow req, 0x5B94A0, 0x5B94A6), min(0x5B9834, 0x5B949A), 0x5B8B38, 0x5B9870, 0x5B9832)
  feedback to EGS: actual 0x5B983A → 0x0A8 b12-23; 0x5B9878/0x5B987A → 0x0A8 b28-39 / 0x0A9 b52-63
```
The EGS byte5 limit flag `0x3FBEDD` acts separately on the pedal wish (rise-rate limit, §1a). Also EGS-related:
gear torque limit `0x5B9832` (EXT 0xFA488C) = 2·min(curve CAL 0x1C894C[gear]·curve CAL 0x1CF820[rpm byte], 0x7FFF),
only with EGS present; enters fast, slow and EGS-word chains (transmission protection LIKELY).

#### 3b. DSC path (0x0B6) — CONFIRMED code, DSC identity LIKELY (ID not in DME/EGS reference filter sets)
`0x3FA042` mode: 2 → `0x3FBEB3` → `0x5B949E` = `0x3FA046`·56+loss (else 0xFFFF) → `0x5B949C` (= 949E, or ramp +CAL 0x1C10C8
per call after loss of request); `0x5B949A` = max(`0x3FA044`·56+loss, `0x5B949C`). Mode 1 → `0x3FBEB4` → `0x5B94A0` =
`0x3FA046`·56+loss (MSR increase, else 0). Fast path uses `0x5B949C`; slow path and `0x3FC195` use `0x5B949A`.

### 4. Arbitration — CONFIRMED order (code)

```
DRIVER   0x5B981A KFPED ─[EGS 0x3FBEDD: rise-rate limit]─ max(cruise 0x5B954E) ─ max(0x5B97BE)
         → interp(0x5B979C..0x5B9856) + idle/loss offset → 0x5B980A  (CAN 0x0AA)
         → min(max torque 0x5B9854) → 0x5B9808 → tip-in filter → 0x5B9806 → +reserve → 0x5B97FC (fast) / 0x5B97FA (slow)
FAST     0x5B983E = min(0x5B97FC, gear limit 0x5B9832, REV LIMIT 0x5B9870, min(DSC 0x5B949C, EGS 0x5B94A4, 0x5B9DD6))
         0x5B9846 = max(0x5B983E, DSC-MSR 0x5B94A0, 0x5B9DD4, EGS-increase 0x5B94A8)      ← increases win over reductions
         0x3FC32A = 0x3FC197 ? 0x5B9860 : 0x5B9846
SLOW     0x5B9852 = min( max(f(0x5B97FA, reserve 0x5B984C, η-scaling), DSC-MSR 0x5B94A0, EGS-inc 0x5B94A6) [+anti-jerk 0x5B978E],
                         min(EGS 0x5B9834, DSC 0x5B949A), 0x5B8B38, REV 0x5B9870, 0x5B9832 [, 0x5B9860 if 0x3FC197] )
IGNITION reduction = 0x5B97DA − max(0x3FC32A, 0x5B985C)      (fast path; floor = ignition-only minimum)
AEVAB    step = round(8·(1 − 0x3FC32A/0x5B97DA)) only if (0x5B985C ≥ … blank-block hysteresis MDHYEZ) and
         enable ∈ {0x3FBF38 fault, 0x3FC1A3 rev limiter, 0x3FBF34 fault, 0x3FC195 DSC (CAL bit0)}; overrun 0x3FC162 NOT (CAL bit1 = 0)
FULL CUT 0x3FC19F (overrun; blocked by DSC-MSR 0x3FC198 and EGS-increase 0x3FBEB8) → step 8
         0x3FBFEC (fault 0x3FBF38 & rpm>0x23, or hard rev cut 0x3FC1A4 & fault 0x3FBF34) → AEVAB step 8 and 0x5BBBA8 bit 0x02
TOTAL    0x5BBBA8 ≠ 0 → mask 0xFF after AEVAB (highest priority, round 2)
```
Ignition vs. AEVAB split (CONFIRMED): every fast reduction (EGS, DSC, rev limiter, faults) goes first to ignition down to
`0x5B985C`; the remainder goes to AEVAB **only** for rev limiter, DSC (`0x3FC195`) and fault reactions. EGS reductions
and the pedal-rate limit never cut cylinders by themselves. Overrun cut is all-or-nothing (`0x3FC19F`).

Conceptual (not code-proven here): kickdown has no torque path (only CAN 0x0AA nibble, round 3); knock, thermal
(component enrichment `0x5B9C2E`), misfire response and diagnostic cylinder cut act outside this coordinator (ignition
angle / λ / static AEVAB masks `0x5B88C5`), so their priority vs. the chain above is set by the AEVAB/total-cut layering
from round 2/3, not by min/max here. `0x5B9DD4/0x5B9DD6` (EXT 0xFE52BC, same fn as `0x3FC234`/`0x5B90F9` static-cut
path) and `0x5B9860` (byte maps CAL 0x1C8A20/0x1C8A60 + 0x1C8AA0, INT 0x4895C) — role HYPOTHESIS.

### 5. Dependency graph (key RAM words)
```
pedal 0x5B96D8, rpm 0x5B9A26 → KFPED → 0x5B981A ─(0x3FBEDD EGS)→ 0x5B981C ─max cruise 0x5B954E→ 0x5B9812 ─max 0x5B97BE→ 0x5B9814
rl 0x3FC302 → 0x5B97E2 → KFMIOP 0x1C828E → 0x5B97DE ─×blend(0x5B93D7, map 0x1C808E)·41>>13→ 0x5B97DC ─×η(0x5B93D8)→ 0x5B97E0 ─×mean 0x5B93DB→ 0x5B97DA (base)
rl_max 0x5B985A → KFMIOP → 0x5B9856 ─×KFPED100%·CAL→ 0x5B9854 (max)              loss: 0x1C789A+… → 0x5B97AA → 0x5B94BC
0x5B979C(loss·k) , 0x5B9856, 0x5B9814 → 0x5B980A (driver req) → min 0x5B9854 → 0x5B9808 → filter → 0x5B9806 → 0x5B97FC / 0x5B97FA
0x5B97E0 × η_zw(0x5B93DC−0x3FC2EF) × firing → 0x5B983A (actual)      0x5B97E0 × η_min(0x3FC2F9) → 0x5B985C (min by ignition)
0x0B5 → 0x3FA04E/4C/48 → 0x5B94A4 / 0x5B94A2 / 0x5B94A8,0x5B94A6, 0x3FBEB8
0x0B6 → 0x3FA046/44/42 → 0x5B949C / 0x5B949A / 0x5B94A0, 0x3FBEB3/B4
rpm, limit CALs → 0x5B9870, 0x3FC1A3, 0x3FC1A4            gear, rpm → 0x5B9832 ; 0x5B94A2 → 0x5B9834
0x5B97FC,0x5B9832,0x5B9870,0x5B949C,0x5B94A4 → 0x5B983E ; +0x5B94A0,0x5B94A8 → 0x5B9846 → 0x3FC32A
0x3FC32A,0x5B97DA,0x5B985C → 0x5B9970 → 0x5B9432/33 → 0x5B9434 (ign.)    0x3FC32A/0x5B97DA → 0x5B93E7 (AEVAB) ; 0x3FC19F → step 8
0x5B97FA,0x5B94A0,0x5B94A6,0x5B9834,0x5B949A,0x5B9870,0x5B9832 → 0x5B9852 (air path)
TX: 0x5B983A,0x5B9878,0x5B987A,0x5B9854,0x5B985C,0x5B980A,0 → INT 0x4BDDC → 0x5B94C6…D2 → INT 0x4B128 → 0x0A8/0x0A9/0x0AA
```

### 6. Open items / what resolves them
| Item | Evidence needed |
|---|---|
| Nm per bit | §2 (EGS firmware, WOT log vs 360 Nm, A2L) |
| `0x5B9784` (idle-control or loss-adaptation torque, half T-units; EXT 0xFAFCE0) | trace EXT 0xFAFCE0; live log at idle |
| `0x5B97AE`, `0x5B888B`, `0x5B8B06` addends of loss torque | log with AC / generator load steps |
| `0x3FC162` exact writer | resolve pointer store in EXT 0xFAE33C |
| `0x5B9DD4/0x5B9DD6`, `0x5B9860`, `0x5B98FC` roles | trace EXT 0xFE52BC and INT 0x4895C inputs |
| 0x0B6 = DSC | CAN capture with DSC intervention (ASC on low µ) |
| 0x0B5 bits 24-35 vs 12-23 semantics (slow vs fast) | EGS firmware or shift log: compare `0x5B94A4` vs `0x5B94A2`, `0x3FC32A`, `0x5B9852` |
| Names of `0x5B9878`/`0x5B987A` | shift log with interventions (`0x3FC1A6`, `0x3F9C05/06/07`) |
