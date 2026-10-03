# DME ↔ EGS interface as seen from the 770B DME — round 3

Addresses: INT = internal-flash CPU, EXT = external-flash CPU, CAL = calibration alias, RAM = runtime.
CAN IDs and byte positions below are taken from the DME message/signal tables and the decoder code
(`can-and-drive-modes.md`). The external E65 reference only corroborates the direction.

## 1. Signal table

| Signal | Dir | DME RAM | Source / consumer function | CAN origin (proven) | Scaling | Confidence |
|---|---|---|---|---|---|---|
| Current gear | EGS→DME | `0x5B8F71` → `0x5B92CA` | INT `0x392C8` → INT `0x5E320`; consumers: driver wish, flap EXT `0xF97D8C`, many | 0x0BA byte0 bits0-3 via table INT `0x15984` | 1…6, 7 = R, 0 = other | CONFIRMED (mapping), LIKELY (P/N/R meaning) |
| Drive engaged | EGS→DME | `0x3FBEDE`/`0x3FBEDA` | derived from gear ≠ 0 | 0x0BA | flag | LIKELY |
| Selector / program (P,R,N,D,S,M) | — | none | not received (0x192/0x1D2 absent) | — | — | CONFIRMED absent |
| Status bits (shift-active / lock candidates) | EGS→DME | `0x3FBEE0` (bit6), `0x3FBEDF` (bit7) | misfire/rough-running monitors INT `0x23338`, `0x23734`; INT `0x5C99C`, `0x4533C`; EXT `0xF2EA9C` | 0x0BA byte0 bits6-7 | flags, both 1 on timeout | positions CONFIRMED, meaning HYPOTHESIS |
| Turbine/output speed candidate | EGS→DME | `0x5B9982` | INT `0x46E3C` (÷ engine speed `0x5B9A26`, enabled by CAL `0x1C8532` bit1), INT `0x5F52C` | 0x1A2 bytes0-1 | u16, 0xFFFF invalid; unit open | LIKELY |
| TCC slip | derived | ratio written to `0x5B981E` | INT `0x46E54…0x46E84` | from 0x1A2 | (speed<<13)/rpm | HYPOTHESIS |
| EGS torque/driver-wish limit | EGS→DME | `0x3FBEDD` | INT `0x463B0`: wish := min(KFPED, `0x3FB460`+`0x3FB45E`) | 0x0B5 byte5 bits6-7 ≠ 0 | flag | LIKELY |
| EGS torque-reduction value | EGS→DME | not found | 0x0B5 bytes0-3 are **not read** by the DME | — | — | open; possibly not via 0x0B5 in this pairing |
| 2-bit EGS status → coolant logic | EGS→DME | `0x3FBEDB`/`0x3FBEDC` | EXT `0xF9E148` (sets `0x5BBAC7.2` if exactly one bit set), EXT `0xF48754`, `0xFAEDB8` | 0x0B5 byte4 bits6-7 | 2-bit | HYPOTHESIS |
| 4-bit EGS status | EGS→DME | `0x5B8F72` | EXT `0xF61F70` | 0x0B5 byte5 bits0-3 | 0xF = invalid | HYPOTHESIS |
| Transmission oil temperature | EGS→DME | `0x5B9229` | EXT `0xF5A65C` | 0x0B5 byte7 | (raw+8)·4/3 → 0.75 °C/bit −48 °C; raw = °C + 40 | HIGH CONFIDENCE |
| EGS identification/handshake | EGS→DME | `0x3FBEE4` | EXT `0xF5F9B4` | 0x5C3 byte0 = 1, bytes1-2 = 0x038E | flag | HYPOTHESIS |
| Engine speed | DME→EGS | `0x5B9A26` → `0x3F9C24` | INT `0x4B128` | 0x0AA bytes4-5 | 0.25 rpm/bit; 0xFFFF invalid | CONFIRMED |
| Pedal | DME→EGS | `0x5B92C9` | EXT `0xFA8E70` → INT `0x4B128` | 0x0AA byte3 | (pedal>>8) 1…254 (or cruise equivalent) | CONFIRMED |
| Pedal/kickdown state | DME→EGS | `0x5B902B` | EXT `0xFA8E70` → INT `0x4B128` | 0x0AA byte6 bits4-7 | 0x0B = kickdown, 0x0A, 0x09/0x08/0x01/0x00 | CONFIRMED |
| 0x0AA byte0/1 | DME→EGS | `0x5B9224`, `0x5B9227` | INT `0x4B128` | 0x0AA | byte0 = additive checksum (+0xAA seed), byte1 low nibble = counter | LIKELY |
| Torque values in 0x0A8/0x0A9 | DME→EGS | `0x5B94C6…0x5B94D2`, `0x5BBA56…` (inputs of INT `0x4B128`) | INT `0x4B128` sig 0x2E-0x31 | 0x0A8/0x0A9 | not decoded yet | open |

## 2. Read-only logging plan for in-car correlation

Log DME RAM through the diagnostic logger and raw PT-CAN (all IDs, timestamps) at the same time.

| Group | RAM variables | CAN |
|---|---|---|
| Gear/program | `0x5B92CA`, `0x5B8F71`, `0x3FBEDE`, `0x3FBEE0`, `0x3FBEDF`, `0x5B8F72`, `0x5B8F73`, `0x3FBEDB`, `0x3FBEDC`, `0x3FBED9` | 0x0BA, 0x0B5, 0x1D2, 0x192 |
| Converter | `0x5B9982`, `0x5B981E`, `0x5B9A26` | 0x1A2, 0x0AA |
| Torque/interventions | `0x3FBEDD`, `0x3FB460`, `0x3FB45E`, `0x5B981A`, `0x5B981C`, `0x5B97DA`, `0x3FC32A`, `0x3FBF34`, `0x3FBF38`, `0x3FC195`, `0x3FC1A3`, `0x5B93E7`, `0x5B92EA` | 0x0A8, 0x0A9, 0x0B5, 0x0B6/0x0CE/0x19E/0x1A0 |
| Kickdown | `0x3FBFB3`, `0x5B902B`, `0x5B92C9`, `0x5B96D8` | 0x0AA |
| Temperatures | `0x5B9229`, `0x5B9307`, `0x5B90BB` | 0x0B5 |

Manoeuvres: as in `egs-integration-plan.md` §3. Add a static test with the engine running and the
selector cycled P→R→N→D→S→M, plus M-gate up/down taps. Every unresolved field above should be
labelled from the time correlation.

---

# Round 4 additions (2026-10-03): torque content of 0x0A8 / 0x0A9 / 0x0AA

Encoding: every torque word passes INT `0x4BCCC` (or `0x4BD40` with `+0x5B9784`):
`CAN = clamp_s12( ((T >> 1) − (0x5B94BC >> 1)) · 0x5B922A >> 10 )`, where `0x5B94BC` = copy of
`0x5B97AA` (reference torque) and `0x5B922A` is a scale byte. 0x800 is reserved; the builder sends
0x801 instead. Producer of the words: INT fn `0x4BDDC`. All field positions below are **CONFIRMED**
from the packing code in INT `0x4B128`; names are as stated.

| Frame | Bits (Intel, byte0 LSB) | Content (RAM source → word) | Name | Status |
|---|---|---|---|---|
| 0x0A8 | 0-7 | checksum `0x5B9222` (byte sum, seed 0xB7) | checksum | LIKELY |
| 0x0A8 | 8-11 | counter `0x5B9225` | alive counter | LIKELY |
| 0x0A8 | 12-23 | `0x5B983A` (fn INT `0x4790C`) → `0x5B94CA` (signed variant) | torque incl. intervention (fast path) | HYPOTHESIS |
| 0x0A8 | 24-27 | `0x5B902C` (EXT `0xFA8E70`) | status nibble | HYPOTHESIS |
| 0x0A8 | 28-39 | `0x5B9878` (INT fn `0x48F68`) → `0x5B94C6` | torque word (base/indicated candidate) | HYPOTHESIS |
| 0x0A8 | 40-43 | constant 0xF | — | CONFIRMED |
| 0x0A8 | 44-55 | 2-bit flags from `0x3FBFAA`, `0x3FBFB0` and others | status | HYPOTHESIS |
| 0x0A8 | 56-60 / 61-63 | `0x3FDCDD` bits 0-4 / 3-bit field | status | HYPOTHESIS |
| 0x0A9 | 0-7 / 8-11 | checksum `0x5B9223` / counter `0x5B9226` | | LIKELY |
| 0x0A9 | 12-15 | 2-bit flags (`0x3FC16F`, …) | status | HYPOTHESIS |
| 0x0A9 | 16-27 | conv(0) = −(reference torque `0x5B97AA`) scaled → `0x5B94D0` | **loss/drag torque** | LIKELY |
| 0x0A9 | 28-39 | `0x5B9854` (EXT full-load fn `0xFA4D04`) → `0x5B94CC` | **maximum available torque** | LIKELY |
| 0x0A9 | 40-51 | `0x5B985C` (= torque reachable without cut, AEVAB input) → `0x5B94D2` | minimum/ignition-limited torque | HYPOTHESIS |
| 0x0A9 | 52-63 | `0x5B987A` (INT fn `0x48F68`) → `0x5B94C8` | torque word | HYPOTHESIS |
| 0x0AA | 12-23 | `0x5B980A` (driver-wish fn INT `0x467F0`), forced 0 in overrun cut `0x3FC19F` → `0x5B94CE` | **driver-request torque** | LIKELY |
| 0x0AA | 24-31, 32-47, 52-55 | pedal byte, rpm ×4, kickdown nibble | (round 3) | CONFIRMED |

Status of the EGS fields from round 3 (0x0BA bits 6/7, 0x1A2 speed, ratio `0x5B981E`): no new
consumer evidence in round 4. Meanings remain HYPOTHESIS / LIKELY as listed above.
