# Full-load lambda and protection enrichment (770B) — round 4

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
