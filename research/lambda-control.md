# Lambda and fuel control (770B) — round 2

> **Final-pass status:** arbitration INT 0x1A5E4 CONFIRMED (richest wins); round-4 'lambda != 1 = open loop' CORRECTED (the window gates only modulation); per-bank paths and codeword 0x1C947C decoded. See the *Final static pass* section at the end of this file.


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

---

# Round 3 additions (2026-10-03)

## 6. Measured lambda — CONFIRMED structure

| Item | Address | Evidence | Status |
|---|---|---|---|
| Broadband sensor linearisation | CAL curve `0x1C6D0A` (22 points, u16) | x 55…708 (sensor signal) → y 3072…16384, with y = 4096 at x = 305: λ 0.75…4.0 | **CONFIRMED** curve; proves the 4096 = λ 1.000 scale (round-2 LIKELY → **HIGH CONFIDENCE**) |
| Measured λ per bank | RAM `0x5B9708`, `0x5B970A` (+ `0x5B9700…0x5B9712`) | written only by INT fn `0x55A1C` (uses the curve above and inputs `0x3FE15C…0x3FE166`) | LIKELY (bank assignment open) |
| Consumers of measured + target λ | INT `0x56DD0` (controller), `0x53C40`, EXT `0xF6C710`, `0xF8B778`, `0xFA2898`, `0xFB13A4`, `0xF6041C` (diagnostics/catalyst monitoring) | read both `0x5B96A8/AA` and `0x5B9708/0A` | LIKELY |

## 7. Feedback controller — LIKELY

INT fn `0x56DD0` reads setpoints `0x5B96A4/A6/A8/AA` and measured `0x5B9708/0A`. It writes the block
`0x5B988C…0x5B98E6`, uses limits CAL `0x1C9986…0x1C9994` (0x1E00, 0x4000, 0xC000, 0x7FFF, 0x8000,
0x199A) and map CAL `0x1C95A6` (5×4, x 64…184, y 1000…10000). Output factor `0x5B98A0` (and `0x5B98A2`)
is consumed by the fuel calculation (below) and by catalyst/diagnostic functions. Separate P/I terms
and the adaptation store are not yet split out.

## 8. How the setpoint enters fueling — CONFIRMED

INT fn `0x2E9E4` (fuel mass / injection-time base, same task as AEVAB):

```text
q   = (load << 12) / λ_setpoint(0x5B96A4)      # INT 0x2ECAC-0x2ECB0, divide helper 0x15E58
q  *= controller factor 0x5B98A0               # INT 0x2ECBC (multiply helper 0x1DED0)
q  += additive term (lha)                      # adaptation-like offset
q  *= 0x5B96BA                                 # further multiplicative factor
→ 0x5B9694 / 0x5B9690…0x5B9698
```

So the lambda **setpoint** is a true feed-forward divisor of fuel mass, and the closed-loop controller
works around the snapped setpoint `0x5B96AA/A8`. The bank path B uses `0x5B96A6` the same way.

## 9. Lean-cruise implication

A mild lean target set at the setpoint level (`0x5B96B4/A2` before limits) would reduce fuel
feed-forward **and** move the controller target together, so it would not fight the closed loop.
Constraints found:
* the min/max clamps `0x5B891C/0x5B891D` (×32) bound the setpoint;
* the snap window (0.9985…1.0012) only affects targets near 1.0;
* catalyst/diagnostic monitors (EXT `0xF6C710`, `0xF8B778`, `0xFB13A4`) read the setpoint and may
  flag or suspend monitoring when λ ≠ 1 (not analysed).

Status: mechanism CONFIRMED; suitability for lean cruise HYPOTHESIS (emissions/NOx and monitor
behaviour unknown).

## 10. Still open

Full-load enrichment and protection enrichment sources inside the arbitration (INT `0x1A4F0` inputs
`0x5B968C`, `0x5B969A…0x5B96A0`), the IMLEVABS integrator, and the adaptation memory.

---

# Round 4 additions (2026-10-03)

The full cylinder-cut / lambda analysis is in `cylinder-cut-lambda.md`. Key facts for this file:

* **Closed-loop condition** (INT `0x570E8`): bank A only regulates when the snapped setpoint `0x5B96AA`
  is within ±1 of 0x1000, unless CAL `0x1C947C` bit2 is set (stock 0x1B: not set). **CONFIRMED.**
  Correction to round 3 §9: a lean setpoint does *not* move the controller target along with it.
  It switches the bank to **open loop**. Lean cruise via the setpoint therefore means open-loop
  lean operation unless that calibration bit (or the code) is changed.
* Release flags `0x3FC1EE` (A) / `0x3FC1EF` (B) from INT `0x58AE8`: AND of ~14 conditions, including
  the post-cut and post-overrun air-mass integrals (IMLEVABS = CAL `0x1C99C2`/`0x1C99C4`, overrun CAL
  `0x1C99C6`).
* Controller INT `0x56DD0`: when not released, the state words are **reset** to 0 and the factor is 1.0
  (or a hold value). Upper factor limit CAL `0x1C95A2` = 0xA000 (1.25). The setpoint passes through a
  transport-delay buffer (helper INT `0x16154`).
* Adaptation: learning EXT `0xF54F18` (block `0x5B8920…0x5B8952`), applied by INT `0x5EB7C` as factor
  `0x5B96BA`, checked by EXT `0xF5199C` (±20/23 % limits). Enables `0x3FC1E7/0x3FC1E8` depend on the
  release and on setpoint ≥ CAL `0x1C9986` (λ 0.90). LIKELY.
* Additive fuel term in the fuel calc: `0x5B9654` (writer not resolved).
* Full-load and protection inputs of the arbitration: see `full-load-enrichment.md`.

---

# Final static pass (round 7, 2026-10-03)

This section supersedes conflicting statements earlier in this file. CONFIRMED items are re-checked by `tools/verify_770b_findings.py` (final-pass blocks).

### 0. Corrections to earlier notes (important)

| Earlier claim | Correction | Status | Evidence |
|---|---|---|---|
| Round 4: "a setpoint ≠ 1.000 disables closed loop" (3FC1E3 = "controller active") | The ±1 window on snapped setpoint RAM 0x5B96AA gates **RAM 0x3FC1E3 / 0x3FC1E4 = λ-modulation (forced excitation) active**, not the integrator. 3FC1E3 is only used (a) to subtract the delayed modulation from measured λ (INT 0x571E0) and (b) to add the square-wave term to the factor (INT 0x57D88 → 0x5B98B0; bank B INT 0x57F00 → 0x5B98A0), plus by diagnostic EXT 0xF6C710. The integrator runs whenever release 0x3FC1EE && !0x3FC1F0 && !0x3FC1D7 (INT 0x574AC). The release (INT 0x58AE8) has **no setpoint condition**. | CONFIRMED (code paths); vehicle behaviour LIKELY | INT 0x570A8–0x57118, 0x574AC–0x574D0, 0x57C80–0x57F60, 0x58F78–0x5906C |
| Round 4 cut analysis: "the other bank keeps closed loop" | Cut substitution applies to **both** banks if either bank flag is set (INT 0x55728 and 0x55860 test 0x3FBFFE‖0x3FBFFF for each path). The uncut bank stays released and its integrator regulates toward the **lean cut target** (λ 1.055–1.20); only the cut bank is blocked (0x3FC1F5/F6). Modulation off on both. | CONFIRMED (code); LIKELY (effect) | INT 0x5570C–0x55758, 0x55854–0x55890 |
| Round 3: "bank path B uses 0x5B96A6" / adaptation factor 0x5B96BA only | Path A = 0x5B96B4→B2→**A6**→AE→**AA**, factor 0x5B98AE→AA→**B0**, adaptation **0x5B96BE**, measured **0x5B970A**, fuel 0x5B9696. Path B = 0x5B96A2→B0→**A4**→AC→**A8**, factor 0x5B98AC→A2→**A0**, adaptation **0x5B96BA**, measured **0x5B9708**, fuel 0x5B9694. | CONFIRMED | fuel INT 0x2EB70/0x2EB80/0x2EBD4 vs 0x2ECAC/0x2ECBC/0x2ED08; measured pairing INT 0x5716C, EXT 0xF8B9E4/0xF8BAB4 |
| Full-load note: rich limit 0x5B891C = "component-protection bound" | 0x5B891C/0x5B891D are **engine-temperature** limit curves (CAL 0x1CE20C / 0x1CE21C over engine-temp axis CAL 0x1CC49C) with diagnostic and special-mode overrides. Stock rich limit λ 0.75 (λ 0.703 at ≥ 90 °C), lean limit λ 1.203. | CONFIRMED | EXT 0xF7E53C–0xF7E61C, axis index RAM 0x5B9F74 written EXT 0xF48EA0 |
| 0x5B968C = "warm-up / catalyst-heating λ" | 0x5B968C = **post-start / warm-up λ** (maps CAL 0x1C5906, 0x1CE0F0); no catalyst-heating λ found. | CONFIRMED structure, names LIKELY | INT 0x4329C, 0x433C8, EXT 0xF54CAC |
| 0x5B98A6 not described | Lower factor limit: map CAL 0x1C95A6 (engine temp × 0x5B953E, stock all 0x6000 = 0.75) or CAL 0x1C95A4 (0x7333 = 0.90) when 0x3FC2B2 && 0x3FC0D4. Factor range 0.75 … 1.25 (CAL 0x1C95A2 = 0xA000). | CONFIRMED | INT 0x57448–0x57494, 0x57D08–0x57D80 |

### A. Final lambda architecture

#### A.1 Block diagram (task INT 0x3D764 order: 0x55A1C measured λ → 0x58AE8 release → 0x50A38 trims → 0x56DD0 controller → … → 0x5080C/0x56908 purge-bank requests → 0x5563C coordinator; the controller uses the previous cycle's setpoints)

```text
REQUEST SOURCES (RAM u16, 0x1000 = no request)
 full-load      0x5B891A  EXT 0xF7E200  min(curve CAL 0x1CE1D8(rpm 0x5B9001) if full-load flag 0x5B8F26 && temp-latch 0x3FAE0B,
                                          map CAL 0x1CE1BC(rpm 0x5B9001, load byte 0x3FC2B7)) ×32, entry delay CAL 0x1CE1F9
 protection A/B 0x5B9C2E / 0x5B9C2C  EXT 0xF7C014  λFL + w·(λprot_bank − λFL), w = curve CAL 0x1C5720(model temp 0x5B86C0); 0x1000 if inactive
 warm-up/start  0x5B968C  INT 0x433C8   rate-limited 0x5B968E (map CAL 0x1CE0F0, EXT 0xF54CAC) while 0x3FC034, else post-start map
                                          0x5B9634 (CAL 0x1C5906, INT 0x4329C); deadband CAL 0x1C60EC around 1.0
 purge/bank A/B 0x5B96A0 / 0x5B969E  INT 0x1A8C0  0x5B968C + (0x5B976C/0x5B9766 − 0x5B968C)·0x5B9347/256   (used while 0x3FC03A)
 diag A/B       0x5B969C / 0x5B969A  EXT 0xF7E340  0x5B86F8/86F6 (if 0x5B873B/3C bit0) | 0x5B9532/9530 (if 0x3FC143/44) | 0x5B876E/876C (if 0x3FBF54/55) | 0x1000
 excitation A/B 0x5B8D1E / 0x5B8D1C  EXT 0xFB13A4  0x1000 ± curve CAL 0x1CFB60(airflow)·ramp, while 0x5B8D28 bit0 (copied to bit1/bit3)
        │
ARBITRATION INT 0x1A5E4 (code; INT 0x1A4F0 is its data/pointer area). Called from INT 0x5563C when !(0x5B8EFB && 0x3FC0DB) or
        0x5B8D28 & 0x0A, otherwise from EXT 0xF7E340 (exactly complementary conditions)      → 0x5B96B4 (A) / 0x5B96A2 (B)
        │
COORDINATOR INT 0x5563C
   base_X := 0x5B891E<<5 if (0x3FBFFE || 0x3FBFFF) else 0x5B96B4 / 0x5B96A2           → 0x5B96B2 / 0x5B96B0
   clamp [0x5B891C<<5 , 0x5B891D<<5] (flags 0x3FC036/0x3FC037 = at rich limit)          → 0x5B96A6 / 0x5B96A4   = FEED-FORWARD setpoint
   ×0x5B8E3A/4096 (A) | ×0x5B8E38/4096 (B) if 0x3FC23B (purge factors, EXT 0xF9ED98)   → 0x5B96AE / 0x5B96AC
   snap to 0x1000 if CAL 0x1C6416 (0x0FFA) ≤ x ≤ CAL 0x1C6418 (0x1005)                  → 0x5B96AA / 0x5B96A8   = SNAPPED setpoint
   0x5B92FF = ((A6+A4)/2)>>5 (avg byte);  0x3FC03C = 0x3FC03D || 0x3FC03E (non-base request active)
        │
FEED-FORWARD FUEL INT 0x2E9E4
   A: q = (load<<12)/0x5B96A6 × 0x5B98B0 + 0x5B9654 → × adaptation 0x5B96BE → 0x5B9696 (−0x5B9966 → 0x5B9698)
   B: q = (load<<12)/0x5B96A4 × 0x5B98A0 + 0x5B9654 → × adaptation 0x5B96BA → 0x5B9694 (−0x5B9966 → 0x5B9692)
        │
RELEASE INT 0x58AE8 (no setpoint term)
   0x3FC1EE = 0x3FC1ED && 0x3FC1FC && 0x3FC1F9 && 0x3FBFB7 && !0x3FC1F7(post-overrun air integral < CAL 0x1C99C6) && !0x3FC20D
              && !0x3FC1F8 && !0x3FC1E5 && 0x3FC1F3 && !0x3FC1F5(post-cut, CAL 0x1C99C2) && 0x3FC08F && !0x5B8F03 && CAL 0x1C947C bit0
   0x3FC1EF = same with 0x3FC1F4, !0x3FC1F6 (CAL 0x1C99C4), 0x3FC090, !0x5B8F04, CAL 0x1C947C bit1
   (0x3FC1F3/F4, EXT 0xF8B778: |measured − snapped setpoint| ≤ CAL 0x1C99C0 → "sensor has reached target" start condition)
        │
CONTROLLER INT 0x56DD0 (bank A shown; bank B symmetric)
   setpoint' = delay(0x5B96A6, 0x5B98E8, helper INT 0x16154) + (0x5B9DA0 + 0x5B93F2·8)/8, ≥ CAL 0x1C9986 when setpoint ≤ 0.90 → 0x5B98B8
   measured' = 0x5B970A / purge corr − 0x5B9D9C/8 − (0x3FC1E3 ? delayed modulation 0x5B989A/8 : 0)                       → 0x5B98BC
   e = ((measured' − setpoint')<<15)/setpoint' (INT 0x1DDE0) × ramp 0x3F9C4A (0→0xFFFF after release)                  → 0x5B98B4
   integrator 0x5B989E (+ states 0x5B98CE…0x5B98E6, 0x3F9CDC…0x3F9CE8) reset when !0x3FC1EE || 0x3FC1F0 || 0x3FC1D7
   0x5B98AE = released ? 0x8000+0x5B989E : (0x3FC1FE ? 0x5B98F2 : 0x8000)
   0x5B98AA = clamp(0x5B98AE, 0x5B98A6 (0.75), CAL 0x1C95A2 (1.25)); flags 0x3FC1D8 (upper), 0x3FC1DA (lower)
   0x5B98B0 = 0x3FC1E3 ? 0x5B98AA + square wave 0x5B989C (±0x5B8CCD<<5, period CAL 0x1C9988) : 0x5B98AA
   bank B: 0x5B988C → 0x5B98AC → 0x5B98A2 → 0x5B98A0 (adds 0x5B9896 = 0x5B989C × CAL 0x1C947E(−16)/16 when 0x3FC1E4)
        │
ADAPTATION EXT 0xF54F18 (block 0x5B8920…0x5B8952) → INT 0x5EB7C → 0x5B96BE (A), 0x5B96BA (B) [+0x5B96C0/C2 additive]
   enable 0x3FC1E7 = 0x3FC1EE && !0x3FC1E9 && !0x3FC214 && 0x5B96AA ≥ CAL 0x1C9986 (λ 0.90);  0x3FC1E8 analogous (0x5B96A8)
   diagnosis EXT 0xF5199C (±20/23 % limits)
        │
INJECTOR TIME INT 0x2ED6C (AEVAB mask 0x5B92EA zeroes cut cylinders)
```

#### A.2 Arbitration order inside INT 0x1A5E4 (CONFIRMED, instruction-level)

All compares are signed 32-bit on zero-extended u16 values → numeric min = **richest wins**.

Bank A (0x5B96B4):
1. `R = min(0x5B891A, 0x5B9C2E)` (INT 0x1A5E4–0x1A604).
2. Base request `B`:
   - if 0x5B8D28 bit1 (excitation A): `B = min(0x5B8D1E, 0x5B968C)` (0x1A63C–0x1A668)
   - elif 0x3FC03A (= 0x3FC0D4 ‖ 0x3FC28C ‖ 0x3FC2AA, set in INT 0x5563C): `B = CAL 0x1C6415 bit0 ? min(0x5B96A0, 0x5B968C) : 0x5B96A0` (stock bit0 = 0)
   - elif 0x5B968C ≠ 0x1000 (0x3FC03B): `B = 0x5B968C`
   - else `B = 0x5B969C` (diagnostic request).
3. `0x5B96B4 = (R == 0x1000) ? B : min(R, B)` (0x1A6CC–0x1A6F8). R == 0x1000 is treated as "no request", so a lean B passes only when there is no rich request.
4. `0x5B96B8 = min(B, R)` (unconditional); `0x3FC03D = 0x3FC03A ‖ 0x3FC03B ‖ bit1 ‖ 0x3FC038 ‖ 0x3FC229`.
Bank B identical with 0x5B9C2C, 0x5B8D28 bit3/0x5B8D1C, 0x5B969E, 0x5B969A, 0x3FC039 → 0x5B96A2, 0x5B96B6, 0x3FC03E.
0x5B96B6/0x5B96B8: no reader found by xref (only init EXT 0xF2C2F0) — possibly read indirectly.

Then INT 0x5563C applies, in this order: cylinder-cut substitution (overrides everything, both banks) → clamp to temperature limits (rich limit can override a richer protection request) → purge multiplier → snap.

#### A.3 Separate paths

| Path | Source → consumer | Behaviour | Status |
|---|---|---|---|
| Normal | B = 0x1000 (after warm-up), snapped to exactly 0x1000; modulation active (3FC1E3/E4) | closed loop with ±amplitude excitation | CONFIRMED |
| Full-load | 0x5B891A → R → min | stock λ 0.922 (CAL 0x1CE1D8 all 118); map 0x1CE1BC all 128 = no part-load enrichment; > 0.90 ⇒ integrator keeps running, adaptation enable still true, modulation off | CONFIRMED (stock values); closed loop at full load LIKELY |
| Cylinder cut | curve CAL 0x1C6408 (x = air-mass flow byte 0x3FC2B6) → 0x5B891E, recomputed only while 0x3FC001 == 0; replaces base of both banks | open loop on cut bank (release blocked), uncut bank regulates around the lean target | CONFIRMED |
| Protection | 0x5B9C2E / 0x5B9C2C (see C) | min with full-load | CONFIRMED structure |
| Overrun | no setpoint change; 0x3FC19F resets post-overrun air integral 0x3F9D30 → release blocked until CAL 0x1C99C6 (0x62) | integrator reset, factor 1.0 | CONFIRMED (round 4) |
| Adaptation | enable needs release && setpoint ≥ λ 0.90 | no upper bound on setpoint in the enable | CONFIRMED (enable); learning internals not decoded |

### B. Lean-operation feasibility (research only; diagnostics must stay intact)

#### B.1 Codeword CAL 0x1C947C (stock 0x1B = bits 0,1,3,4) — all 10 read sites decoded

| Bit | Mask | Read at | Effect | Stock |
|---|---|---|---|---|
| 0 | 0x01 | INT 0x58F78 | required for release 0x3FC1EE (bank A closed loop) | set |
| 1 | 0x02 | INT 0x58FE0 | required for release 0x3FC1EF (bank B) | set |
| 2 | 0x04 | INT 0x570F4 / 0x57E54 | **forces 0x3FC1E3 / 0x3FC1E4 = 1** regardless of release, 3FC1E9, excitation bit, sensor-ready 0x5B86D2/D0 ≥ CAL 0x1C998A and setpoint window → modulation added and diagnostics see "active" | clear |
| 3 | 0x08 | INT 0x590F8 | 0x3FC1F2 = (0x5B96AA < λ0.90 ‖ 0x5B96A8 < λ0.90) → integrator reset 0x3FC1D7 | set |
| 4 | 0x10 | INT 0x590CC / 0x591A0 | 0x3FC1F0/F1 = 0x3FC1E9/EA (timers after events 0x3FC02E/0x3FC025, or rich setpoint < 1.0 with 0x3FE0AC bits) → integrator reset | set |
| 5 | 0x20 | — | no reader found | clear |
| 6 | 0x40 | INT 0x5702C / 0x57048 | 3FC1D7 = 3FC1F2 continuously (bit6) vs. only on the first cycle of 3FC1F2 (bit6 clear, edge via 0x3F9C08 bit3 = last 3FC1F2) | clear |
| 7 | 0x80 | INT 0x58B6C | adds 0x5B8E7E to the release-blocking flag 0x3FC1E5 | clear |

Sibling bytes: CAL 0x1C947D (0xE0 → hold value −0x2000 for 0x5B9890/0x5B988E), CAL 0x1C947E (0xF0 = −16, modulation gain bank B). CAL 0x1C9478/0x1C9479/0x1C947A are read by purge / catalyst functions (not lambda-control bits).

#### B.2 Findings per question

| Question | Finding | Status |
|---|---|---|
| Alternate enable logic | No setpoint term in release; λ ≠ 1 only removes modulation (3FC1E3/E4) and the 3FC1F3 start test is generic (|meas−set|). Rich side: integrator reset only at the transition below λ 0.90 (bit3, bit6 clear). | CONFIRMED |
| Wideband capability | CAL 0x1C6D0A, 22 pts: x 55…708 → λ 0.75, 0.84, 0.88, 0.92, 0.95, 0.97, 0.98, 0.99, **1.00 (x=305)**, 1.004, 1.01, 1.02, 1.03, 1.05, 1.09, 1.14, **1.20**, 1.40, 1.64, 2.0, 2.8, 4.0. Fine resolution to λ 1.2, coarse beyond (1.2→1.4→1.64→2.0). | CONFIRMED (curve); sensor accuracy lean UNTESTED |
| Controller math at λ ≠ 1 | Error is relative to the (delayed) feed-forward setpoint 0x5B96A6/A4, not to 1.0; factor 0.75…1.25. The code already integrates at stock non-1.0 targets (full-load 0.922; lean cut target on the uncut bank). | CONFIRMED (math); LIKELY (behaviour) |
| Adaptation at λ ≠ 1 | Enable requires setpoint ≥ λ 0.90 only; no lean exclusion in INT 0x58AE8. EXT 0xF54F18 learning conditions not decoded (reads 3FC1E7/E8, 0x5B98AA/A2, rpm, load, temp). | CONFIRMED (enable) / NOT COMPLETED (learning) |
| Setpoint limits | lean limit 0x5B891D = CAL 0x1CE21C (all 154 = λ 1.203) or CAL 0x1CE218 (154) in diagnosis → any request > λ 1.203 is clipped. | CONFIRMED |
| Diagnostics assuming λ = 1 | (1) modulation flag 3FC1E3/E4 needs snapped setpoint = 1.000 → EXT 0xF6C710 enables its monitor bit only when 3FC1E3/E4 = 1 and the factor is not at a limit (0xF6E604 / 0xF707DC); (2) excitation diag EXT 0xFB13A4 sets inhibit bits 0x5B8D29 bit1/bit4 when bank cut or snapped setpoint > 0x1000; (3) diagnostic λ requests 0x5B969C/9A are ignored while 0x5B968C ≠ 1.0 or 0x3FC03A; (4) 3FC1E9/EA set on rich setpoint < 1.0 when 0x3FE0AC bits set. Monitors' exact identity (catalyst OSC vs sensor) HYPOTHESIS. | CONFIRMED gates / HYPOTHESIS meaning |

#### B.3 Feasibility table

| Method | OEM support | Feedback possible? | Adaptation possible? | Required architectural change | Main risk | Confidence |
|---|---|---|---|---|---|---|
| Lean request through an existing request slot (e.g. a lean base request B > 1.0 while R = 1.0) | Partial: arbitration passes a lean B when no rich request; limit allows up to λ 1.203 | Yes (release has no setpoint term) | Enable yes (≥ 0.90); learning internals unknown | A source for a lean B under defined conditions; snap window must not catch it | Catalyst/λ diagnostics lose their λ=1 modulation precondition (stay not-ready); NOx (3-way cat inefficient lean); misfire/drivability | LIKELY |
| Lean via cylinder-cut target curve CAL 0x1C6408 | Exists only during cuts | Cut bank no; uncut bank yes | Cut bank no (release blocked) | — (not a lean-cruise mechanism) | Uses the cut path only; enrichment hazard if feedback forced on mixed exhaust | CONFIRMED (mechanism) |
| Force 3FC1E3/E4 via CAL 0x1C947C bit2 | Calibration option exists | Does not change feedback (integrator independent) | No effect | none for feedback; it would add modulation off-λ1 | Diagnostics would run under wrong preconditions → false results; not recommended | CONFIRMED (code effect) |
| Open-loop lean (release off, CAL bits 0/1) | Calibration option exists | No | No | — | No error correction; diagnostics; adaptation frozen | CONFIRMED (code effect) |
| Lean above λ 1.2 | Not supported (lean limit 1.203; sensor curve coarse > 1.2) | Sensor range yes to 4.0, resolution low | Unknown | Limits and probably injector/ignition/torque model changes | Combustion stability, NOx, torque-model errors | LIKELY |
| Keep stock λ=1 window for diagnostics, lean only outside monitor windows | Bosch structure separates diag requests and modulation | Yes | Yes (enable) | Scheduling outside monitor windows | Monitor completion rate | HYPOTHESIS |

No firmware change is proposed here; this table records what the existing code would allow or block.


### D. Unresolved / evidence needed

| Item | Known | Needed |
|---|---|---|
| Physical bank of path A/B | A pairs with measured 0x5B970A and cut flag 0x3FBFFE | live data (unplug/upset one bank) |
| 0x5B86C0 / 0x5B86D2 scale | thresholds 0xB200…0xBE00, 0x1E00 | live log vs EGT; decode EXT 0xF4C78C |
| Adaptation learning conditions | enable only | decode EXT 0xF54F18 |
| Identity of monitors EXT 0xF6C710, 0xFB13A4 (state machine INT 0x21054), F68540, F6B7B8, FE1724 | gates found | 560B XDF names / A2L |
| 0x3FC2B2, 0x3FC03A sources (0x3FC0D4 EXT 0xF36190, 0x3FC28C EXT 0xF988A0, 0x3FC2AA EXT 0xF9ED98) | purge/tank-vent related HYPOTHESIS | decode those functions |
| 0x5B9DA0 / 0x5B9D9C (setpoint/measured offsets, copied from 0x5B8CD8 / 0x3FE1B0 in INT 0x50A38) | post-cat trim HYPOTHESIS | find writers |
| 0x5B9654 additive fuel term writer | not resolved (pointer) | follow pointer |
| Release inputs 0x3FC1ED/FC/F9 (EXT 0xF8B778) | not setpoint-based where read | full decode |
| Readers of 0x5B96B6/0x5B96B8 | none via xref | pointer-table search |
