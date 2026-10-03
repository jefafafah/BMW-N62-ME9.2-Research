# Full-load lambda and protection enrichment (770B) — round 4

> **Final-pass status:** full-load lambda 0.922 via curve 0x1CE1D8; protection request 0x5B9C2E/2C structure CONFIRMED and always at least as rich as full-load. See the *Final static pass* section at the end of this file.


Address kinds: INT = internal-flash CPU, EXT = external-flash CPU, CAL = calibration alias, RAM = runtime.
Lambda format: 4096 = λ 1.000 (HIGH CONFIDENCE, sensor curve CAL `0x1C6D0A`); byte requests are ×32.

## 1. Arbitration INT fn `0x1A4F0` and its inputs

| Input (RAM) | Writer | Evidence | Role | Status |
|---|---|---|---|---|
| `0x5B891A` | EXT `0xF7E200` | map CAL `0x1CE1BC` (4×4), curve `0x1CE1D8` (16), full-load flag `0x5B8F26`, rpm byte `0x5B9001`, engine temperature `0x5B9307`, `0x3FC2B7`; also sets `0x3FC035` | **full-load / driver-wish enrichment request** | LIKELY |
| `0x5B9C2E` (with `0x5B9C2C`) | EXT `0xF7C014` | maps CAL `0x1C5642` (16×12 byte, rpm×load), `0x1C5552` (16×6), `0x1CD9CC` (8×8), curves `0x1C5720…0x1C5797`; per-cylinder-like bytes `0x5B9448…0x5B944F` | **component protection (exhaust-temperature model) enrichment** | HYPOTHESIS |
| `0x5B968C` | INT `0x433C8` | compared with 0x1000 in the arbitration; uses `0x3FC034`, `0x5B9634` | warm-up / catalyst-heating λ | HYPOTHESIS |
| `0x5B969E`, `0x5B96A0` | INT `0x1A8C0` (from `0x5B968C`, `0x5B9766`, `0x5B976C`) | per-bank derived requests | bank-specific λ | HYPOTHESIS |
| `0x5B969A`, `0x5B969C` | EXT `0xF7E340` | same function that sets the min/max limits `0x5B891C/0x5B891D` and the cut setpoint `0x5B891E` | limits / special requests | LIKELY |

**KFLAMFA** (560B `0xE0AE`, "driver-wish lambda map") → CAL map record `0x1CE1BC` (data ≈ `0x1CE1C6`):
the local delta (≈ +0x116 to +0x118, as for CWEVAB at `0xD8B4`) matches, and the function (full-load
λ request) matches. **LIKELY**. Not promoted further until the 560B XDF is re-opened.

## 2. Final target by operating state

| State | Final target path | Status |
|---|---|---|
| Normal cruise | arbitration → snapped to exactly 1.000 inside the 0.9985…1.0012 window → closed loop | CONFIRMED (structure) |
| High load / max power | `0x5B891A` (full-load request) through the arbitration; rich limit `0x5B891C` (curve CAL `0x1CE20C` or 0x5A = λ 0.70) | LIKELY |
| Temperature protection | `0x5B9C2E` / limits path | HYPOTHESIS |
| Cylinder cut | `0x5B891E` (curve CAL `0x1C6408`, λ 1.055…1.20) replaces the base setpoint, open loop | CONFIRMED |

Exact priority rules inside INT `0x1A4F0` (min/max order) are not fully decoded. Coolant and
intake-temperature enrichment and transient enrichment were not isolated.

---

# Final static pass (round 7, 2026-10-03)

This section supersedes conflicting statements earlier in this file. CONFIRMED items are re-checked by `tools/verify_770b_findings.py` (final-pass blocks).

### C. Full-load / component-protection lambda

#### C.1 Full-load request 0x5B891A (EXT 0xF7E200) — CONFIRMED

```text
if 0x5B9307 > CAL 0x1CE1FA (24 = −30 °C): latch 0x3FAE0B := 1 (cleared only at init EXT 0xF2C2C8)
a = (0x5B8F26 && 0x3FAE0B) ? curve CAL 0x1CE1D8(rpm byte 0x5B9001) : 0x80      # stock: all 118 → λ 0.922
b = map CAL 0x1CE1BC(rpm 0x5B9001 x: 62..88, load byte 0x3FC2B7 y: 27..47)        # stock: all 128 → none
r = min(a, b)
if r < 0x80: (counter 0x3FAE0A from CAL 0x1CE1F9 = 0 → no delay) 0x5B891A = r<<5  else 0x5B891A = 0x1000
```
KFLAMFA candidate = map CAL 0x1CE1BC: role fits (always-on rpm×load lambda request), name LIKELY (unchanged). The effective full-load enrichment in this calibration is curve CAL 0x1CE1D8 (KFLAMFA is neutral).

#### C.2 Protection request 0x5B9C2E / 0x5B9C2C (EXT 0xF7C014) — CONFIRMED structure

```text
ign_A = avg(0x5B9448,944A,944D,944F)  ign_B = avg(0x5B9449,944B,944C,944E)   # per-cylinder ignition angle bytes (INT 0x33650, clamp −0x20..0x48)
ref   = 0x5B8F26 ? curve CAL 0x1C5797(rpm 0x5B9A26) : map CAL 0x1C5642(rpm/160, load 0x3FC302>>5)   → 0x5B9058
ret_X = max(0, ref − ign_X)                                         → 0x5B9056 / 0x5B9057  (ignition retard per bank)
dλ_X  = ret_X × map CAL 0x1CD9CC(ign_X, rpm) × 0xBF >> 8            → 0x5B9C24 / 0x5B9C22, PT1 (τ curve CAL 0x1C5774(rpm), helper INT 0x1EBE4)
                                                                     → 0x5B9C26 / 0x5B9C20 (frozen while 0x3FC184 ‖ 0x3FC223 ‖ 0x3FC189)
λbase = 0x5B8F26 ? curve CAL 0x1C5732(rpm) : map CAL 0x1C5552(rpm, load 0x3FC302)   → 0x5B9C30 (×8 scale, LIKELY from the >>3 / >>18 blend arithmetic)
λprot_X = (dλ_X < λbase) ? λbase − dλ_X : λbase      → 3FAD82 / 3FAD84 (guard as coded)
w     = curve CAL 0x1C5720(0x5B86C0): x 0xB200,0xB600,0xBA00,0xBE00 → 0, 0x5333, 0x7332, 0x8000 (0…1.0)
enable = (0x5B8EF9 ‖ 0x5B9053): hysteresis 0x5B86C0 > CAL 0x1C57DA / 0x5B86D2 > CAL 0x1C57DC (width CAL 0x1C57D8), w ≠ 0,
         variant CAL 0x1C57DE (stock 2 → 0x5B9053)
0x5B9C2E = enable ? λFL + w·(λprot_A − λFL) : 0x1000        (λFL = 0x5B891A)
```
0x5B86C0 / 0x5B86D2 are outputs of the temperature-model function EXT 0xF4C78C (reads air flow 0x3FC2FC, overrun 0x3FC19F, engine temp): exhaust/catalyst temperature model = LIKELY, exact quantity HYPOTHESIS.

#### C.3 Request table

| Request source | Condition | Target (stock) | Priority | Final consumer | Confidence |
|---|---|---|---|---|---|
| Full-load curve CAL 0x1CE1D8 → 0x5B891A | full-load flag 0x5B8F26, engine once > −30 °C | λ 0.922 | min with protection, then min with base | 0x5B96B4/A2 → feed-forward + controller target | CONFIRMED |
| Part-load map CAL 0x1CE1BC → 0x5B891A | always | λ 1.0 (neutral) | as above | same | CONFIRMED |
| Exhaust-temperature / ignition-retard protection 0x5B9C2E/2C | model temp 0x5B86C0 above threshold (weight curve 0x1C5720) | blend from λFL toward λbase − retard term | min with full-load (richest) | same, per bank | CONFIRMED structure; physical meaning LIKELY |
| Knock / retard | part of protection (retard = reference − actual ignition per bank) | enrichment ∝ retard | inside protection | same | LIKELY (input bytes = ignition angle LIKELY) |
| Coolant / warm-up 0x5B968C | after start (time 0x5B9CFC < CAL 0x1C5904) map CAL 0x1C5906 (λ 0.85–0.90); warm-up map CAL 0x1CE0F0 (λ 0.883 cold → 1.0 warm) while 0x3FC034 | base request B | lower than any rich R (min) | same | CONFIRMED structure |
| Engine-temperature limits 0x5B891C/1D | always | rich λ 0.75 (0.703 ≥ 90 °C), lean λ 1.203 | hard clamp after arbitration | 0x5B96A6/A4 | CONFIRMED |
| Special-mode rich limit CAL 0x1CE1FC | 0x3FC2B2 | λ 0.773…0.703 vs 0x5B86A4 | clamp | same | CONFIRMED code; meaning of 0x3FC2B2 HYPOTHESIS |
| Diagnostic limits CAL 0x1CE209/0x1CE218 | 0x3FC132 && (0x3FC038 ‖ 0x3FC039) | λ 0.703 / 1.203 | clamp | same | CONFIRMED |
| IAT-related | none of the arbitration inputs reads intake temperature | — | — | — | NOT FOUND (searched all request writers) |
| Cylinder cut 0x5B891E | 0x3FBFFE ‖ 0x3FBFFF | λ 1.055–1.20 | overrides arbitration, then clamp | both banks | CONFIRMED |

**Does protection win over full-load/performance?** Yes in the min sense: `R = min(0x5B891A, 0x5B9C2E)` and the protection value is itself a blend starting from 0x5B891A, so the richer of the two always reaches the setpoint (CONFIRMED). The only things that can override it afterwards are the cylinder-cut substitution and the temperature rich limit 0x5B891C (λ 0.75), which caps any request richer than that (CONFIRMED).
