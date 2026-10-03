# Torque model, driver wish, kickdown and modes (770B) — round 2

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
