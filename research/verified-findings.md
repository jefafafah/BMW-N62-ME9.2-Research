# Verified findings

## Reference inputs

The research session used three provided DME dump components and a public BMW-XDFs archive. Full proprietary/vehicle-specific inputs are not stored in this repository.

### Provided dump component hashes

| Component | Size | SHA-256 |
|---|---:|---|
| external flash (`28f200f3t.bin`) | 1,048,576 | `bcdac7a0f4c0169cb6aa2984bb156e66a2ac96033f28bd6dd993bbab15b1f661` |
| MPC555 read (`mpc555-6.bin`) | 462,848 | `bcd64e2e975e4d2b5a26c0e93f52cf60ab9af5898337ad851ebaade3e3a987c1` |
| EEPROM (`eeprom.bin`) | 4,096 | `0c7891ea01dd2007ef7319509f8b1571ea89b28ed561ca43dd849ba2bbf60ccd` |

**The EEPROM must not be published.** Its hash is included only so future work can identify the exact research input without redistributing it.

### Third-party reference hashes

| Reference | SHA-256 |
|---|---|
| `WinOLS (BMW E60-E61 (Original) - 7180A560B).bin` | `54404c7da32997344f77dcdd5b5c00190e533102f5e12ce0a174009fd208998d` |
| `WinOLS (BMW E60-E61 (Original) - 7180A560B).xdf` | `4c11a0a52121810807d2ab408707ceb2b9c66ee566ad8c35d26b58aef3948291` |
| `725D601B.a2l` | `4213d242912491e9b9585887b4b87a6b6129d1757c54033c11a6e2c27a0137f7` |

## REDABM port

560B XDF:

- symbol: `REDABM`
- description: injector shutoff pattern for torque reduction
- 560B file offset: `0x54A0`

770B external flash:

- byte-identical 64-byte matrix at offset `0xC5510`

Matrix:

```text
01 11 15 55 57 77 7F FF
02 22 2A AA AB BB BF FF
04 44 54 55 57 77 7F FF
08 88 A8 AA BA BB FB FF
10 11 51 55 75 77 F7 FF
20 22 A2 AA EA EE EF FF
40 44 45 55 D5 DD BF FF
80 88 8A AA AB BB BF FF
```

The fourth reduction column yields alternating `0x55` / `0xAA`, a balanced four-of-eight mask.

## 560B CWEVAB

The XDF defines `CWEVAB` at file offset `0xD8B4` as an 8-bit injector shutoff codeword.

Local 560B -> 770B alignment around this region contains multiple strong blocks, but small insert/delete changes occur around the candidate location. `~0xCD9CA` remains a **LIKELY** candidate and is not yet classified as confirmed.

> **Round-2 update:** `0xCD9CA` (CPU `0x1CD9CA`) is read by EXT fn `0xF7BEE4` and OR-ed into the
> per-cylinder injector-cut mask `0x5B88C5` consumed by AEVAB. Function **CONFIRMED**, name
> **HIGH CONFIDENCE** (see below).

---

# Round 2 (2026-10-03) — static analysis of 770B code

Method: the internal-flash read and the external-flash read were loaded into one CPU address space
and scanned with a register-tracking xref builder. Lookup-helper call sites gave the table geometry.
All results come from 770B code. The 560B XDF/bin and the 725D A2L were **not** re-opened in this
round; only the 560B offsets/descriptions already recorded in `reference-symbols.csv` were used.

Every claim below marked CONFIRMED is re-checked by
`python tools/verify_770b_findings.py --int <mpc555-6.bin> --ext <28f200f3t.bin>`
(31/31 checks pass on the reference dump).

Confidence labels: **CONFIRMED** (direct from code/data), **HIGH CONFIDENCE** (two independent
lines of evidence, one of which depends on a reference not re-verified this round), **LIKELY**,
**HYPOTHESIS**, **REJECTED**.

Address kinds: *CPU* = MPC555 address; *ext file* = offset in `28f200f3t.bin`; *int file* = offset
in `mpc555-6.bin` (equal to its CPU address); *RAM* = runtime address, not in any dump.

## Memory architecture

| Finding | Status | Evidence |
|---|---|---|
| CPU = MPC555 (USIU `0x2FC000`, TPU3 A/B `0x304000/0x304400`, QADC A/B `0x304800/0x304C00`, QSMCM `0x305000`, MIOS `0x306000`, TouCAN A/B `0x307080/0x307480`, UIMB `0x307F80`) | CONFIRMED | I/O accesses in code hit exactly these blocks |
| Internal flash `mpc555-6.bin` maps at CPU `0x000000` (448 KiB code/data `0x00000–0x6FFFF`) | CONFIRMED | absolute branches (`ba 0x1C840`, `ba 0x1C7A0`) from the branch table at int `0x8000` land on valid code next to the application r2/r13 setup at int `0x1C828` |
| int `0x00000–0x7FFF`: boot/startup stubs and vectors (own r13 `0x4017F0`, r2 `0x00F7CC`) | LIKELY (extent) | vector stubs at `0x0`, `0x100`; own small-data bases at int `0x1E4` |
| int `0x70000–0x70FFF` (extra 4 KiB in the read: `0x40001000`, then `FF`) | HYPOTHESIS | MPC555 shadow/config row |
| External flash maps at CPU `0xF00000–0xFFFFFF` (ext file = CPU − `0xF00000`) | CONFIRMED | block headers hold self-pointers `0x00F00080`, `0x00FC0080`; absolute loads `lis 0xF0/0xF1` |
| Program block: header ext `0x00000` (`5A5A5A5A 33333333`), entry `0xF04218`, end markers at CPU `0xF0FF48` and `0xFEFFD0` | CONFIRMED | header fields and `5A5A5A5A` markers at those addresses |
| Data block: header ext `0xC0000` (`5A5A5A5A CCCCCCCC`), end marker CPU `0xFDFF58` | CONFIRMED | header field + marker |
| Calibration data occupies ext `0xC0000–~0xD2000`; ext `~0xD2000–0xDFF58` (CPU `0xFD2000…`) holds **code** | CONFIRMED | no prologues/`blr` below `0xD2000`; ≥ 120 `blr` above; code xrefs reach CPU alias only up to `0x1D2000` |
| ext `0xF0000–0xFFFFF` (CPU `0xFF0000…`): software ID `0087180A770B` at ext `0xF0018`, QADC channel table, exception dispatch target `0xFFC408` | CONFIRMED (ID, call target); table role LIKELY | |
| **Code reads calibration through CPU alias `0x1C0000–0x1DFFFF` = ext file `CPU − 0x100000`** | CONFIRMED | e.g. REDABM formed as `r2 − 0x2AE0 = 0x1C5510` at int `0x2C560`; ≈ 8,200 calibration refs via the alias vs ≈ 300 via `0xFCxxxx` |
| Alias mechanism (chip-select mirror vs. overlay) | HYPOTHESIS | not determined |
| Application small-data bases: **r13 = `0x401A20`**, **r2 = `0x1C7FF0`** | CONFIRMED | int `0x1C828–0x1C834` and ext `0xF0422C–0xF04238` (identical sequences) |
| r2 window `0x1C0000–0x1CFFEF` = first 64 KiB of calibration; rest via `lis 0x1D` | CONFIRMED | |
| r13 window covers internal SRAM `0x3F9A20–0x3FFFFF`; initial stack `0x3FF0F8` | CONFIRMED | |
| Internal SRAM `0x3F9800–0x3FFFFF` (≈ 27,900 refs) | CONFIRMED | |
| External RAM `0x5B8000–0x5BFFFF` (refs `0x5B7FFC…0x5C0000`, read/write) | CONFIRMED usage; size LIKELY | |
| Application code is split over internal **and** external flash (EXT→INT 2038 calls, INT→EXT 207) | CONFIRMED | e.g. AEVAB, injection time, kickdown, driver wish live in internal flash |
| EEPROM layout | not analysed (EEPROM deliberately not used) | |

## Selective injector shutoff (details: `aevab-redabm.md`)

| Finding | Status |
|---|---|
| REDABM at CPU `0x1C5510` is used by AEVAB (int `0x2C060`) as `REDABM[phase][step−1]` | CONFIRMED |
| Phase = (segment counter `0x5B907C` + 4) mod 8, latched once per reduction event | CONFIRMED |
| Mask bit *n* = *n*-th cylinder in firing order 1‑5‑4‑8‑6‑3‑7‑2; bit = 1 → injection time 0 | CONFIRMED (bank constant `0x5A`) |
| `0x55` cuts cylinders 1,4,6,7; `0xAA` cuts 5,8,3,2 | CONFIRMED |
| Step = round(8·(1 − target/base torque)) with hysteresis (`MDHYEZ` `0x1C8A1A`, rounding cal `0x1C8A1B/1C`) | CONFIRMED logic, torque-signal names LIKELY |
| Total cut: bit word `0x5BBBA8` ≠ 0 → mask `0xFF` | CONFIRMED |
| CWEVAB `0x1CD9CA` = static OR mask | CONFIRMED function, HIGH CONFIDENCE name |
| OEM pattern rotates every cycle | REJECTED |

## Torque, kickdown, lambda, flap, thermal, generator, cruise

| Finding | Status | Detail |
|---|---|---|
| KFPED = map `0x1C87DA` (16×8 u16; pedal `0x5B96D8` × rpm `0x5B9A26` → `0x5B981A`) | HIGH CONFIDENCE | `torque-and-modes.md` |
| KFMIMR `0x1C85FA`, KFMRMI `0x1C86EA` | LIKELY | same |
| Kickdown fn int `0x3B80C` → `B_kd` `0x3FBFB3`; UPWGKDO/UPWGKDU/WPKDMN = `0x1C1E4A/4B/4C` (WPKDMN = 100 %) | CONFIRMED fn, HIGH CONFIDENCE names | same |
| `0x1CF610` is a sport pedal map (KFPEDS) | REJECTED as working assumption (linear cruise-equivalent map) | same |
| Cruise control: no fixed set-speed presets in DME; 1 km/h set-speed step, speed breakpoints 30/50/70/100/130/200 km/h | LIKELY | same, §6 |
| Cylinder-cut lambda substitution (`0x3FBFFE/FF` → setpoint `0x5B891E` from curve `0x1C6408`) | CONFIRMED mechanism; LASOABML name LIKELY | `lambda-control.md` |
| Exhaust flap fn `0xF97D8C`, map `0x1D077C` (gear × rpm pedal thresholds), CW `0x1D07E8` | CONFIRMED fn; names LIKELY | `exhaust-flap.md` |
| Two-level coolant target map `0x1D08A8` (≈ 114 / 85 °C) | LIKELY | `thermal-management.md` |
| Generator voltage request fn `0xF8A9D0` (16.0/15.0/14.3/11.2/10.6 V constants) | LIKELY | `generator-control.md` |
| `0x1C941A` = TGENOFVL | REJECTED | same |
| Ignition maps `0x1CAD5A/0x1CAF04/0x1CB186` (24×16) in fn `0x49600` | LIKELY | `ignition-vanos-valvetronic.md` |
| One global 560B → 770B offset | REJECTED (deltas −0x84 … +0x118) | `560B-to-770B-mapping.md` |
| 725D A2L addresses usable directly in 770B | REJECTED | same |

---

# Round 3 (2026-10-03) — CAN, modes, kickdown, lambda, generator, flap

16 further checks were added to `tools/verify_770b_findings.py` (47/47 pass on the reference dump):
CAN message table (30 objects; EGS RX 0x0B5/0x0BA/0x1A2/0x5C3; DME TX 0x0A8/0x0A9/0x0AA; 0x192/0x1D2
absent), signal 0x11 → gear decode, gear-code table INT `0x15984`, gear `0x5B92CA` assignment, B_kd →
`0x5B902B = 0x0B` → 0x0AA byte6, rpm → 0x0AA bytes4-5, transmission-temperature conversion, λ sensor
curve `0x1C6D0A` (4096 = 1.0), measured-λ writers, fuel division by λ setpoint, the full-load generator
timer at `0x1C9412`, and the flap output channel. Details: `can-and-drive-modes.md`, `kickdown-path.md`,
`dme-egs-interface.md`, `sport-mode.md`, `aevab-integration-points.md` and the round-3 sections of
`lambda-control.md`, `generator-control.md`, `exhaust-flap.md`, `thermal-management.md`.

Correction: `0x5B90BB` was listed as "speed-like" in round 2; its thresholds (0xE0, 0xF0) indicate a
temperature-like quantity (HYPOTHESIS).

---

# Round 4 (2026-10-03) — cylinder-cut lambda, Valvetronic, torque CAN, outputs

15 further checks (62/62 total) cover: bank-cut reset of the air-mass integrators and the IMLEVABS /
post-overrun thresholds (INT `0x58AE8`); air-mass flow `0x3FC2FC`/`0x3FC2B6` origin; closed-loop
condition "setpoint ≈ 1.000" (INT `0x570E8`); controller reset and default factor 0x8000;
Valvetronic per-bank lift requests on CAN 0x105/0x10D (INT `0x4FB78`); output channel 6 ← coolant-target
fn; the CAN torque converter and the 0x0A8/0x0A9 torque sources; and the generator chain timer →
`0x5B8F2D` → voltage request.

Corrections in this round: a λ target ≠ 1.000 disables closed loop (round 3 implied it would move
the controller target); INT `0xAB88` handles digital inputs; the round-2 VANOS candidate fn INT
`0x406B0` is the air-charge model.
