# Lambda and fuel control (770B) — round 2

Address conventions as in `research/aevab-redabm.md` (CPU addresses; calibration alias
`0x1C0000–0x1DFFFF` = ext file `CPU − 0x100000`; `0x3Fxxxx`/`0x5Bxxxx` are RAM).
Lambda scaling used below: 16-bit lambda with `0x1000 = 4096 = λ 1.000` (**LIKELY**, from the
constant `0x1000` used as neutral value throughout the coordinator). Byte lambda values are
shifted `<<5` into that format, i.e. `1/128` per bit (**CONFIRMED** shift; physical scale LIKELY).

## 1. Setpoint path found so far

```text
lambda requests 0x5B968C, 0x5B969A..0x5B96A0, 0x5B891A, 0x5B9C2C/2E
      │  INT fn 0x1A4F0  (arbitration around 0x1000; per bank)              LIKELY
      ▼
0x5B96B4 (bank path A), 0x5B96A2 (bank path B)  (+ 0x5B96B6/0x5B96B8)
      │  INT fn 0x5563C                                                      CONFIRMED logic
      │   if 0x3FBFFE || 0x3FBFFF (a bank has cylinders cut):
      │        base := 0x5B891E << 5       (cylinder-cut setpoint)
      │   else base := 0x5B96B4 / 0x5B96A2
      │   clamp to [0x5B891C<<5, 0x5B891D<<5]  → 0x5B96A6 / 0x5B96A4 (flag 0x3FC036 = at min)
      │   if 0x3FC23B: × 0x5B8E3A / 4096     → 0x5B96AE / 0x5B96AC
      │   if 0.9985 <= λ <= 1.0012 (CAL 0x1C6418/0x1C6416): λ := 1.000
      ▼
0x5B96AA (bank path A setpoint), 0x5B96A8 (bank path B setpoint)            LIKELY = per-bank λ setpoint
```

* Which physical bank is "A" (`0x5B96AA`) vs "B" (`0x5B96A8`) is **HYPOTHESIS** (A = bank 1 by
  ordering only).
* Limits `0x5B891C/0x5B891D` are written by EXT fn `0xF7E340`. The rich limit uses curve
  `0x1CE20C` (input `0x5B9F74`) or the fallback scalar `0x1CE209` (`0x5A` = λ 0.70) when
  `0x3FC038`/`0x3FC039` are set. **HYPOTHESIS:** component-protection enrichment bounds.

## 2. Cylinder-cut / bank-cut lambda handling — CONFIRMED mechanism

1. INT fn `0x55424` splits the final cut mask `0x5B92EA` with bank mask `0x5B8C82 = 0x5A` into
   per-bank cut counts `0x5B92ED`/`0x5B92EE`, the total `0x5B92EC`, and flags `0x3FBFFE`/`0x3FBFFF`
   ("bank has cut cylinders"). `0x3FC000` = nothing cut. `0x3FC001` = AEVAB idle and mask 0.
2. While either flag is set, the per-bank lambda setpoint is replaced by `0x5B891E << 5`.
3. `0x5B891E` is computed by EXT `0xF7E63C` from curve **`0x1C6408`** (6 points, u8, x input
   `0x3FC2B6` with axis 25…113). It is recomputed only while `0x3FC001 == 0` (cut active).
   Stock values: λ-codes 135,135,135,135,138,154 → λ ≈ 1.055 … 1.20.
4. Name mapping: `LASOABML` (560B `0x6349`, "lambda setpoint during bank shutoff") → `0x1C6408`
   is **LIKELY**. The local delta of +0xBF fits between the anchors REDABM (+0x70) and KFMIMR
   (+0xF4), and the function matches. Counter-evidence: the repo CSV calls LASOABML a scalar,
   whereas `0x1C6408` is a 6-point curve. It must be re-checked against the 560B XDF.

Interpretation (**HYPOTHESIS**): with injection cut, the unfired cylinders pump air, so the sensor
sees a lean mixed exhaust. Setting the setpoint lean keeps the controller from enriching the firing
cylinders. The physical meaning of the x input `0x3FC2B6` (axis 25…113) is open.

`IMLEVABS` (560B `0x98AA`, "integrated air-mass threshold before lambda control after cylinder
blanking") is **not located** yet. Expected near CPU `0x1C99C0` (local delta ≈ +0x118). Look for
an integrator of air mass started on the 1→0 edge of `0x3FC000`.

## 3. Maps vs. correction factors

| Item | Kind | Status |
|---|---|---|
| Cylinder-cut setpoint curve `0x1C6408` | lambda **request** (absolute λ) | LIKELY |
| Snap window `0x1C6416/0x1C6418` | setpoint post-processing | CONFIRMED function |
| Rich limit curve `0x1CE20C` / scalar `0x1CE209` | lambda **limit** | HYPOTHESIS |
| `KFLAMFA` (560B `0xE0AE`, driver-wish lambda map) | lambda request | **not located**; expected ≈ CPU `0x1CE1xx–0x1CE2xx` given the local delta at `0xD8B4` (+0x116). The rich-limit curve above lies in that window, so verify carefully |
| `KFDLASO` (560B `0x12C5`, continuous-control setpoint correction) | correction | not located (delta in this region is negative, cf. kickdown −0x84) |

Rule kept from round 1: the cylinder-cut lambda curve is a setpoint *substitution* during AEVAB
events. It is not a fuel-correction factor and must not be used to implement lean cruise.

## 4. Logging candidates

| Variable | Address | Type | Status |
|---|---|---|---|
| per-bank lambda setpoint A/B | `0x5B96AA` / `0x5B96A8` | u16, 4096 = 1.0 | LIKELY |
| pre-bank-logic setpoint A/B | `0x5B96B4` / `0x5B96A2` | u16 | LIKELY |
| cylinder-cut setpoint | `0x5B891E` | u8, ×1/128 | CONFIRMED function |
| bank-cut flags | `0x3FBFFE` / `0x3FBFFF` | u8 | CONFIRMED |
| cut counts | `0x5B92EC/ED/EE` | u8 | CONFIRMED |
| measured lambda, STFT/LTFT, enrichment factors | — | — | **not located** (next round: follow `0x5B96AA` consumers EXT `0xF6C710`, `0xF68540`, `0xF8B778`, `0xFB13A4`) |

Logging these is read-only. Each address still needs a live sanity check, for example that λ
setpoint ≈ 0x1000 at warm idle.

## 5. Open questions

* Physical bank assignment of the A/B paths.
* Location of the lambda controller (P/I parts), adaptation (`fra`/`rka`-like) and measured λ.
* `IMLEVABS` integrator; `KFLAMFA`; `KFDLASO`.
* Whether `0x3FC2B6` is cut count, load or time since cut.
