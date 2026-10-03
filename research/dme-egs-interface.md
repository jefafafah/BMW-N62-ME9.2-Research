# DME ↔ EGS interface as seen from the 770B DME — round 3

> **Final-pass status:** 0x0BA/0x0B5/0x5C3 fully traced; 0x0B5 carries an EGS torque request (raw-buffer decode); 0x3FBEDD is a driver-wish rise limiter; D/S/M absent (HIGH CONFIDENCE). See the *Final static pass* section at the end of this file.


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
| Transmission input (turbine) speed | EGS→DME | `0x5B9982` | INT `0x46E3C` (÷ engine speed `0x5B9A26`, selected by CAL `0x1C8532` bit 0x02); INT `0x5F52C` (inactive) | 0x1A2 bytes0-1 | u16, raw, 0xFFFF → 0, timeout → 0; 0.125 rpm/bit LIKELY | LIKELY (round 6; output speed REJECTED) |
| Turbine/engine speed ratio | derived | `0x5B981E` | INT `0x46E28…0x46EB0` → map CAL `0x1C84B0` | from 0x1A2 | min((n<<13)/rpm, 0xFFFF); 0x4000 = 1.0 LIKELY | CONFIRMED formula; no TCC state derived (round 6) |
| EGS torque/driver-wish limit | EGS→DME | `0x3FBEDD` | INT `0x463B0`: wish := min(KFPED, `0x3FB460`+`0x3FB45E`) | 0x0B5 byte5 bits6-7 ≠ 0 | flag | LIKELY |
| EGS torque request/limit | EGS→DME | `0x3FA04E`/`0x3FA04C`, mode `0x3FA048` | EXT `0xF15450` (raw RX buffer) → INT `0x4A700` → `0x5B94A4`/`0x5B94A2`/`0x5B94A8` | 0x0B5 bits 12-23 / 24-35 (s12), byte4 bits 4-5 | raw·56 + loss torque | CONFIRMED decode (final pass; round 3 said 'not read') |
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
| Converter | `0x5B9982`, `0x5B981E`, `0x5B9A26`, `0x5B97F0`, `0x5B982A`, `0x5B9808`, `0x5B97F8`, `0x5B9806`, `0x3FC18D`, `0x3FBED6` | 0x1A2, 0x0AA |
| Torque/interventions | `0x3FBEDD`, `0x3FB460`, `0x3FB45E`, `0x5B981A`, `0x5B981C`, `0x5B97DA`, `0x3FC32A`, `0x3FBF34`, `0x3FBF38`, `0x3FC195`, `0x3FC1A3`, `0x5B93E7`, `0x5B92EA` | 0x0A8, 0x0A9, 0x0B5, 0x0B6/0x0CE/0x19E/0x1A0 |
| Kickdown | `0x3FBFB3`, `0x5B902B`, `0x5B92C9`, `0x5B96D8` | 0x0AA |
| Temperatures / speed | `0x5B9229`, `0x5B9307`, vehicle speed `0x5B90BB` | 0x0B5 |

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

---

# Round 6 additions (2026-10-03): 0x1A2 speed / ratio path

Full trace in `egs-tcc-shift-state.md`. Summary:

| Item | Finding | Status |
|---|---|---|
| 0x1A2 decode | signal 0x13 → `0x5B9982` unscaled; 0xFFFF → 0; EGS-present `0x3FBED1` = 0 → 0; RX indication INT `0x1D974` sets `0x3FA58C`; after > 50 decoder calls without a frame → 0 (last value held until then) | CONFIRMED |
| Ratio | `0x5B981E = min((0x5B9982 << 13) / 0x5B9A26, 0xFFFF)`; rpm 0 → 0xFFFF (0 if numerator 0); numerator selector CAL `0x1C8532` bit 0x02 (set; alternative = DME model `0x5B97BA`, INT `0x5F398`) | CONFIRMED |
| Ratio scale | map axis 0.90/0.96/0.99/1.00/1.04/1.06 × 0x4000 → 0x4000 = n(0x1A2) = n(engine), 0x1A2 = 0.125 rpm/bit | LIKELY |
| Map CAL `0x1C84B0` | 6 (ratio) × 8 (gear `0x5B92CA`) u16, helper INT `0x17B64`, ratio-major data; factor 0x8000 = 1.0; 1.0 in gears 0/1/R, in gears 2–6: 0.2 at 0.90, 0.5–0.7 at 0.96, 1.0 at 0.99, 1.2–1.5 at 1.00–1.04, 1.0 at 1.06 | CONFIRMED (values/geometry) |
| Output `0x5B97F0` | divisor: `0x5B982A = clamp((0x5B9828 << 15) / 0x5B97F0, 1, 0xFFFF)` (CAL bit 0x08, active); second divisor for `0x5B9826` (bit 0x10) inactive | CONFIRMED |
| Behaviour | `0x5B982A` = gain of a unity-gain second-order low-pass on torque request `0x5B9808` → `0x5B97F8`, which replaces the request (`0x5B9806`) while the positive-step latch `0x3FC18D` is set | CONFIRMED structure; "tip-in shaping" LIKELY |
| 0x1A2 meaning | transmission input = converter turbine speed; output speed rejected (one ±6 % ratio axis for all gears) | LIKELY |
| TCC lock / slip state | none derived: no threshold, flag or derivative on `0x5B981E` | CONFIRMED absent; lock meaning of the map zone HYPOTHESIS |

---

# Final static pass (round 7, 2026-10-03)

This section supersedes conflicting statements earlier in this file. CONFIRMED items are re-checked by `tools/verify_770b_findings.py` (final-pass blocks).

Static analysis only. Address types: INT, EXT, CAL, RAM as in the brief. "EE0" = RAM `0x3FBEE0`, "EDF" = RAM `0x3FBEDF`.

### 0. Decoder recap (INT fn `0x392C8`, task INT `0x3D764`) and new structural facts

| Item | Finding | Status | PCs |
|---|---|---|---|
| EGS-present flag RAM `0x3FBED1` | set to 1 on every fresh 0x0BA frame (INT `0x39434`), with RAM `0x3FDCB6` = 0x55; cleared only when RAM `0x3FE176` ≠ 0 (INT `0x39854…0x39870`) and by init. A 0x0BA timeout does **not** clear it | CONFIRMED | INT `0x39430`, `0x39870` |
| 0x0BA timeout | counter RAM `0x3FA587` > 50 calls: gear `0x5B8F71` = 0, `0x3FBEDE` = `0x3FBEDA` = 0, **EE0 = EDF = 1**, `0x5B8F73` = 0, valid `0x3FBED2`/`0x3FBED8` = 0 | CONFIRMED | INT `0x39444…0x39494` |
| 0x3FBED1 = 0 | EE0 = EDF = 0, gear 0, `0x5B9982` = 0; 0x0B5 fields as on timeout (below) | CONFIRMED | INT `0x394BC…0x39520`, `0x395D8…0x3961C` |
| 0x0B5 timeout | counter RAM `0x3FA588` > 50: `0x3FBEDB` = `0x3FBEDC` = 0, `0x5B8F72` = 0xF, `0x3FBED9` = 0, `0x3FBEDD` = 0, `0x5B9229` := engine temperature `0x5B9307`, valid `0x3FBED4` = 0 | CONFIRMED | INT `0x397E4…0x39838` |
| Read API usage | all 37 call sites of INT `0x63660` pass a constant signal number; signal 0x14 (0x0B5 bytes 0-3) and 0x2D (0x5C3 bytes 4-7) are never read; RX copy buffers RAM `0x5BB618+0x14·h` are not read with absolute addresses (they are read through pointer `0x3FAE9C` by EXT `0xF15450`/`0xF1241C`, see the correction in §2) | CONFIRMED | verifier check |

### 1. CAN 0x0BA (handle 0x0D, DLC 7) — complete field map

| Bits (byte0 = LSB of signal 0x11) | RAM | Consumers | Status |
|---|---|---|---|
| byte0 bits0-3 gear code → table INT `0x15984` | `0x5B8F71` → `0x5B92CA`; `0x3FBEDE`/`0x3FBEDA` = gear ≠ 0 | many (round 3) | CONFIRMED |
| byte0 bits4-5 | — | not extracted | CONFIRMED unused |
| byte0 bit6 | **EE0** `0x3FBEE0` | see §1.1 | CONFIRMED position |
| byte0 bit7 | **EDF** `0x3FBEDF` | see §1.1 | CONFIRMED position |
| bytes 1-3 | — | signal 0x11 word not used beyond byte0 | CONFIRMED unused |
| bytes 4-5, byte6 bits0-3/7 | — | signal 0x12 only bits 20-22 extracted | CONFIRMED unused |
| byte6 bits4-6 (7 → 0) | `0x5B8F73` | none (writers only: decoder, init EXT `0xF27650`) | CONFIRMED unused |

#### 1.1 Consumer table for EE0 / EDF

| RAM | Writer | CAN source | Consumer (fn) | Behaviour | Active in this cal? | Likely meaning | Confidence |
|---|---|---|---|---|---|---|---|
| EE0, EDF | INT `0x392C8` (`0x393D4`/`0x393E4`; timeout `0x3948C`/`0x39484` = 1; absent `0x394F4`/`0x394EC` = 0); init EXT `0xF27648`/`0xF27640` | 0x0BA byte0 bit6 / bit7 | INT `0x23338` (misfire-type detector, crank-synchronous task INT `0x31B20`), 2nd stage | threshold offset `f3` = map value: EE0 → `0x3FA8A0` (map CAL `0x1C1500`), else EDF → `0x3FA89C` (CAL `0x1C1480`), else `0x3FA8A8` (CAL `0x1C1400`); priority above all three: `0x3FA8B4` when `0x3FC18B` && !`0x3FE48B.0` && `0x5B90BB` = 0. Result `0x3FA8E0`; detection `0x5B8E74`/`0x5B8E73` = (`0x3FA888` > threshold) | **yes**: the three 8×8 maps (load `0x3FC2B7` × rpm byte `0x5B9001`, writer INT `0x5C4C0`) all differ, EE0/EDF maps are higher in some cells and lower in others | alternative driveline-state calibration for the detector | behaviour CONFIRMED |
| EE0, EDF | " | " | INT `0x23338`, 1st stage | EDF selects threshold map CAL `0x1C1680` vs `0x1C1600`; EE0/EDF select factor maps CAL `0x1C1780`/`0x1C1740`/`0x1C1700` (writer INT `0x5C674`) | **no**: `0x1C1680` = `0x1C1600` = all 0xFFFF, the three factor maps are identical (all 255) | — | CONFIRMED (no effect) |
| EE0, EDF | " | " | INT `0x23734` (same detector family) | threshold `0x3FA8F4` (CAL `0x1C19B4`) if `0x3FC239`, else EE0 → `0x3FA8F0` (CAL `0x1C1934`), else EDF → `0x3FA8EC` (CAL `0x1C18B4`), else `0x3FA8F8` (CAL `0x1C1834`); rate-limited downward by CAL `0x1C1A34`; `0x5B8E75` = (`0x3FA838` > `0x3FA900`+thr) | **yes** (maps differ). `0x1C19B4` is all 0xFFFF, i.e. `0x3FC239` **blanks** this detector; EE0/EDF do **not** blank it | alternative driveline-state calibration | behaviour CONFIRMED |
| EE0, EDF | " | " | INT `0x5C99C` (detector disturbance events) | edge (either direction) of EDF / EE0 → `0x3FA92E` / `0x3FA930` → OR into event flag `0x5B8E8D` (→ INT `0x595B4`) | **no**: gated by CAL `0x1C1AC8` bit0 (EDF) / bit1 (EE0); value 0x50 has both clear. Active events in this cal: bit4 (`0x3FC18B` rising), bit6 (`0x3FC29F` edge) | "shift/transition event suppresses detection" mechanism exists but is calibrated out | CONFIRMED |
| EE0, EDF | " | " | INT `0x4533C` (driveline anti-jerk observer, task INT `0x3D764`) | any change of EE0 vs stored `0x3FB41F` or EDF vs `0x3FB41E` (stored at INT `0x4594C…0x45958`) → reset path INT `0x45860`: `0x3FC182` = 1, hold-off counter `0x5B93D1` := curve CAL `0x1C7C1C`(rpm byte), counter `0x3FB3E0` := CAL `0x1C7C29`, observer states cleared, model speed `0x5B97D8` re-initialised to `0x5B9A26`+`0x5B97C4`. Hold-off `0x3FC183` blocks enable `0x3FC180` | reset: yes; torque effect: **no** (next row) | EGS bits mark driveline-coupling transitions | behaviour CONFIRMED; meaning HYPOTHESIS |
| EDF | " | " | EXT `0xFA4628` (pointer table EXT `0xFBEF50`) | per-gear (index `0x5B9E7C` = gear 0…6, ≥6 → 6, from EXT `0xFA0750`) parameters: EGS absent → model gain `0x5B97C6` = CAL `0x1CF35C` {0,476,201,97,59,39,18}, observer gain `0x5B93D0` = `0x1CF2F8`, output gain `0x5B93CF` = `0x1CF310` {0,13,10,9,5,4,4}; EGS, EDF = 0 → `0x1CF340` {0,15,23,38,44,69,84}, `0x1CF2E8`, `0x1CF300`; EGS, EDF = 1 → `0x1CF34E` {0,135×6} (gear-independent), `0x1CF2F0` (24×6), `0x1CF308` | output gain tables `0x1CF300`/`0x1CF308` are **all 0** → anti-jerk torque `0x5B97C2` (INT `0x315F0`, read by INT `0x319AC` and torque-word fn INT `0x48F68`) is always 0 with EGS present | EDF = 1 selects a gear-independent ("decoupled"?) driveline model | table selection CONFIRMED; meaning HYPOTHESIS |
| EE0, EDF | " | " | EXT `0xF2EA9C` (init table EXT `0xFBE9F0`) | copies EDF→`0x3FB41E`, EE0→`0x3FB41F`, `0x3FC181` = 1, `0x3FB418` = 0 | init only | — | CONFIRMED |

No other reader exists: xref plus a raw scan of every D-form load/store with low half `0xBEE0`/`0xBEDF` (matches with other bases checked).

#### 1.2 Interpretation of EE0 / EDF (only what the consumers support)

| Candidate meaning | Evidence | Verdict |
|---|---|---|
| shift active | A shift flag would normally blank or desensitise the detector or raise an event. The edge-event path exists (INT `0x5C99C`) but is disabled; the bits select steady-state threshold maps that are neither uniformly higher nor lower; the real blanking input is `0x3FC239`, not EE0/EDF | not supported (HYPOTHESIS at most) |
| clutch / converter transition | edges reset the anti-jerk observer (INT `0x4533C`) | consistent, but the effect is torque-neutral in this cal |
| converter state (lock-up clutch closed/open/slipping) | persistent alternative detector calibrations (driveline stiffness changes crank-speed signatures); EDF switches the observer model from per-gear to gear-independent parameters (decoupled engine inertia is gear-independent) | **HYPOTHESIS (best fit)**; direction (which value = locked) not determinable |
| gear valid | gear validity is carried by the gear code itself (0 = invalid); EE0/EDF have no gear-validity consumer | not supported |
| transmission intervention | no torque-path consumer with effect | REJECTED for this calibration |
| misfire suppression during shifts | only threshold-map selection; no blanking | REJECTED as "suppression"; LIKELY as "driveline-state-dependent misfire thresholds" |

Summary: EE0 and EDF are **two driveline-state inputs to the crank-synchronous misfire-type detector** (CONFIRMED behaviour, LIKELY detector identity) and **reset triggers of the inactive anti-jerk observer**. Priority EE0 > EDF; timeout default = both 1 (EE0 maps used); EGS absent = both 0.

Detector identity: INT `0x22110…0x24798` are float functions in the segment task INT `0x31B20`; per-segment values indexed by `0x5B8FB1`; detections `0x5B8E6E/6F` feed per-cylinder counters in INT `0x23A64` (`0x5B99A6…`). Name "misfire / rough-running detection" LIKELY (unchanged from round 3).

### 2. CAN 0x0B5 (handle 0x0B, DLC 8)

> **Correction (torque analysis, CONFIRMED):** 0x0B5 bytes 0-3 are not read through the signal API, but EXT `0xF15450` reads the whole frame from the raw RX buffer (handle 0x0B): s12 bits 12-23 → `0x3FA04E`, s12 bits 24-35 → `0x3FA04C`, mode byte4 bits 4-5 → `0x3FA048` (1 = increase, 2 = reduce). So the DME **does** receive an EGS torque request/limit value; see `torque-and-modes.md` final pass §3a. Statements below that 0x0B5 bytes 0-3 are unread, or that no EGS torque value exists, apply to the signal-API path only.
 — complete field map

| Bits | RAM | Consumers | Behaviour | Likely meaning | Confidence |
|---|---|---|---|---|---|
| bytes 0-3 | — | none (signal 0x14 never read) | — | (EGS torque request/limit candidates are here on other platforms) | CONFIRMED unread |
| byte4 bits0-5 | — | not extracted | — | — | CONFIRMED unused |
| byte4 bit6 / bit7 (00→0/0, 01→1/0, 10→0/1, 11→1/1) | `0x3FBEDB` / `0x3FBEDC` | EXT `0xF9E148` | if both 0x0BA and 0x0B5 valid: `0x5BBAC7.2` = bit6 XOR bit7; else CAL `0x1D08FE` bit0 (= 1); coding `0x3FE313.0` → use stored `0x3FE2EF`. `0x5BBAC7.2` (or `0x5B8548`) → coolant target `0x5B91D1` := CAL `0x1D08FB` = 177 (= 84.75 °C in 0.75 °C/−48) instead of the map path (map `0x1D08A8`/group map `0x1D0900`) | EGS request for low coolant target (max cooling); also the default when EGS data are invalid | behaviour CONFIRMED; "thermal protection request" LIKELY |
| byte4 bit6 | `0x3FBEDB` | EXT `0xF48754` | sets latch `0x3FB8CC` (with `0x5B8548`, heater `0x3FC29B`, rpm > CAL `0x1D0899`) → `0x5B8E20.1`; fn writes `0x3FE2EA/EC/EE` | thermostat/coolant monitoring condition | HYPOTHESIS |
| byte4 bit6 or bit7 | both | EXT `0xFAEDB8` | if either set, or (EGS present and 0x0B5 invalid longer than CAL `0x1C750C` = 0): `0x5B93BD` := CAL `0x1C74DC` (= 0) instead of the max of condition-dependent minima (CAL `0x1C74E2…0x1C74F5`); then `max(…, r30)`, + offset `0x5B9409`, rate-limited into `0x3FB384` | suppresses a set of conditional minimum values (idle/torque-reserve-type) | behaviour CONFIRMED locally; meaning NOT COMPLETED |
| byte5 bits0-3 | `0x5B8F72` (default 0xF) | EXT `0xF61F70` | ignored if ≥ 0xC or coding `0x3FE313.0`. bit1 → `0x3FDC68.0`; rising edge (with `0x5B927F` = 0) → `0x3FDCE0` → `0x3FDCDD` bit3 → **sent back in 0x0A8 bits 56-60** (INT `0x4B128`). bits2/3 (only with 0x0BA valid): `0x3FDCDF` = b2 ∧ ¬b3, `0x3FDCDE` = ¬b2 ∧ b3 → EXT `0xF49E10`, merged with detector flags `0x5B8E7B`/`0x5B8E80` (INT `0x23A64`) and code `0x3FDCC9` (1/2) into request bits `0x5B927E.1/.2` → EXT `0xF5D68C`, `0xF5E068`, `0xF61E58`, `0xF30BF8`. bit0 unused | bit1: handshake/acknowledge echoed to EGS; bits2-3: two mutually exclusive EGS requests merged with misfire-detector requests (fault-lamp-type) | positions CONFIRMED; meaning HYPOTHESIS; downstream NOT COMPLETED |
| byte5 bits4-5 (01→1, else 0) | `0x3FBED9` | none | — | — | CONFIRMED unused |
| byte5 bits6-7 (≠ 0) | `0x3FBEDD` | INT `0x46348` at `0x463B0` | see §2.1: driver-wish **rise-rate limiter** | EGS request to soften the pedal/driver-wish build-up at low vehicle speed | behaviour CONFIRMED; meaning LIKELY |
| byte6 | — | not extracted | — | — | CONFIRMED unused |
| byte7 (0xFF → fallback, ≥ 0xB7 → 0xFF, else (raw+8)·4/3) | `0x5B9229` | EXT `0xF5A65C` | `0x5B9477` = `0x5B9229` (or CAL `0x1D09E1` when 0x0BA/0x0B5 invalid) → map CAL `0x1D0958` → offset `0x5B9476` added to a byte in the cooling-demand chain (`0x5B9471…`, `0x3FC2A7…A9`, CAL `0x1CBCF8…`, `0x1D09xx`) | transmission oil temperature → cooling demand | temperature HIGH CONFIDENCE (round 3); consumer role LIKELY, downstream NOT COMPLETED |

#### 2.1 `0x3FBEDD` and the origin of `0x3FB460` / `0x3FB45E` (corrects round 3 wording)

```
INT 0x46370  0x5B981A = KFPED(pedal 0x5B96D8, rpm 0x5B9A26)
INT 0x46384  if (0x3FE313.0 || 0x3FBEDD):
                 0x5B981C = min(0x5B981A, sat16(0x3FB460 + 0x3FB45E))
             else 0x5B981C = 0x5B981A
INT 0x46424  0x3FB460 = 0x5B981C            # every call: previous output
EXT 0xF889B0 0x3FB45E = curve CAL 0x1CF412(0x5B9D20)   # 2 points: x 1280 -> 164, x 3840 -> 32735
```

* `0x3FB460` is **not** an EGS value: it is the previous-cycle driver wish (only writer INT `0x46424`). CONFIRMED.
* `0x3FB45E` is a DME step size from a calibration curve over `0x5B9D20`; at low `0x5B9D20` the rise is limited to 164 per
  call (KFPED range 0…32768, i.e. ≈ 0.5 %/call), above 3840 it is effectively unlimited. Falling wish is never limited.
  CONFIRMED.
* So 0x0B5 byte5 bits6-7 ≠ 0 = "**rate-limit the driver-wish rise at low speed**", not a torque level and not a reduction.
  The same limiter is forced by coding bit `0x3FE313.0` (HYPOTHESIS: variant/coding without EGS evaluation; the same bit
  also bypasses EGS inputs in EXT `0xF9E148` and EXT `0xF61F70`).
* `0x5B9D20` = vehicle speed: LIKELY (side finding, §6).

#### 2.2 Is there an EGS torque-limit / reduction VALUE?

**Via the signal API: no. Via the raw buffer: yes (see the correction above).** Signal-API view: CONFIRMED by: signal 0x14 never read; byte6 never extracted; no other EGS-derived RAM enters a torque min/max
(consumer enumeration above). The only torque-path EGS inputs are `0x3FBEDD` (slew limiter, §2.1), gear `0x5B92CA`
(per-gear tables) and `0x5B9982` (tip-in filter gain, round 6). The AEVAB intervention flags `0x3FBF34/38`, `0x3FC195`,
`0x3FC1A3` have no 0x0B5/0x0BA source in the decoder (their CAN origin, if any, is outside the EGS frames).

| Asked field | Present in 0x0B5 as used by this DME? |
|---|---|
| gearbox torque limitation (value) | not via signal API; **yes via raw buffer**: `0x3FA04E`/`0x3FA04C` with mode `0x3FA048` (torque final pass §3a) |
| torque reduction request (shift intervention) | **yes**: mode 2 (reduce) → `0x5B94A4` fast limit → `0x3FC32A` → ignition retard (torque final pass §3a) |
| active shift | no |
| converter state | no (candidate is EDF in 0x0BA) |
| thermal protection | yes, as 2-bit cooling request (byte4 bits6-7) + oil temperature (byte7) |
| gearbox mode | no |
| EGS intervention state | only the driver-wish rise limiter (byte5 bits6-7) |

### 3. 0x1A2 / 0x5C3 follow-up (beyond round 6)

| Question | Finding | Status |
|---|---|---|
| Other readers of `0x5B9982` | none: xref + raw scan of all D-form accesses with low half `0x9982` → only INT `0x46E3C` (active) and INT `0x5F6D0` (inactive), plus decoder/init writes | CONFIRMED |
| Other readers of `0x5B981E` | only INT `0x46ED8` | CONFIRMED |
| Uses of `0x3FBED6` (0x1A2 fresh) | only INT `0x4A900` in INT fn `0x4A700` (EGS CAN monitoring): "0x0BA, 0x0B5 and 0x1A2 all fresh" condition for debounce counter `0x3F9B93` vs CAL `0x1C10D7` → status byte `0x3F9B9A` | CONFIRMED |
| Other n/n divisions | the only other ratio of a drivetrain speed to rpm is the computed-gear path INT `0x5E364…` (`0x5B9A26`<<12 vs `0x5B9D20`, thresholds CAL `0x1C1E30…`), used only when `0x3FBED1` = 0 (no EGS) | CONFIRMED (inactive with EGS) |
| Explicit TCC state / slip variable | none in the DME. Indirect candidates: ratio map zone (round 6) and EDF (§1.2) | CONFIRMED absent / HYPOTHESIS |
| Shift-state logic from turbine speed | none | CONFIRMED absent |
| 0x5C3 | bytes 0-3 only: byte0 = 1 and bytes1-2 = 0x038E → `0x3FBEE4`; INT `0x5B6D8` calls EXT `0xF5EBFC` once per rising edge, which packs `0x5B9D68` (or 0xFFFF if `0x3FBF00` = 0) and sends it via TX API INT `0x63DCC` (object 0x76) | request/response handshake, not a mode; HYPOTHESIS |

### 4. D / S / M — final systematic check

All decoded fields of 0x0BA, 0x0B5, 0x1A2, 0x5C3 and every consumer:

| Field | Consumer type | Selects an alternative driver-wish / pedal / engine / flap / idle map? |
|---|---|---|
| gear `0x5B92CA` | per-gear indexing (flap map `0x1D077C`, ratio map `0x1C84B0`, anti-jerk tables, DFCO, ...) | per gear only, not per program |
| `0x3FBEDE`/`0x3FBEDA` drive engaged | idle/diag/driver-wish gates | no |
| EE0 / EDF | misfire-detector thresholds; anti-jerk reset/model (no torque effect) | no driver-wish/engine map; detector maps only |
| `0x5B8F73` | none | — |
| `0x3FBEDB/DC` | coolant target fixed value, thermostat monitoring, FAEDB8 minima | coolant target only (fixed CAL value, default = same) |
| `0x5B8F72` | handshake echo; lamp/fault-type request merger | no |
| `0x3FBED9` | none | — |
| `0x3FBEDD` | driver-wish rise-rate limit (same KFPED) | no alternative map; a rate limit |
| `0x5B9229` | cooling demand | no |
| `0x5B9982` | tip-in filter gain via ratio map | no |
| `0x3FBEE4` | one-shot reply | no |

Verdict: **"The ME9.2 770B DME does not maintain an explicit D/S/M drive-program state" → HIGH CONFIDENCE.**
Two independent lines: (1) no selector/program frame is received (0x192/0x1D2 absent from the message table, CONFIRMED
round 3); (2) every EGS bit that is decoded has been traced to its consumers and none selects alternative
driver-wish/pedal/engine/flap/idle maps; the bytes that are not decoded are provably never read (constant-signal check).
Limits: the DME can still **react indirectly** to the EGS program if the EGS changes gear, EE0/EDF, the 0x0B5 byte5
bits6-7 limiter request or the cooling request with the program (e.g. S or winter mode). That is EGS behaviour and needs
logs. Not fully traced: downstream of `0x5B927E` (EXT `0xF5D68C` etc.), EXT `0xFAEDB8` minima, EXT `0xF5A65C` output. None of
them is in the driver-wish path, so they do not affect the verdict.

Implications for a future custom E/D/S/M architecture (design notes only, UNTESTED):
* A mode signal cannot come from existing DME logic. Sources: (a) a field the EGS already sends but the DME ignores
  (0x0B5 bytes 0-3/byte6, 0x0BA bytes 1-5, 0x5C3 bytes 4-7) — needs the EGS to put a program code there and new DME
  read code; (b) a new RX object (e.g. 0x192/0x1D2) — needs a message-table change; (c) derivation from inputs the DME
  already has (gear, kickdown `0x3FBFB3`, pedal, cruise, `0x5B9D20`); (d) a coding/calibration switch.
* Existing DME mechanisms an E mode could reuse instead of new maps: the driver-wish rise limiter (`0x3FB45E`/curve
  `0x1CF412`, gate at INT `0x46384`), the tip-in filter gain (`0x5B982A`), the fixed coolant target (`0x5B91D1` =
  CAL `0x1D08FB`), the flap map, and the KFPED lookup (INT `0x46370`).
* EGS program logic (shift maps, converter lock-up) stays in the EGS; the DME cannot impose D/S/M shift behaviour.

### 5. EGS-side unknowns (need EGS firmware dump and/or synchronous PT-CAN + DME RAM logs)

1. Physical meaning and polarity of 0x0BA byte0 bit6/bit7 (converter lock-up state? which value = locked/slipping/open?).
   Log: EE0/EDF vs `0x5B981E` (turbine/engine ratio) during steady cruise, tip-in and shifts.
2. When the EGS sets 0x0B5 byte5 bits6-7 (garage shift N→D/R, launch, winter/program?), and the two values 01/10/11.
3. 0x0B5 byte4 bits6-7 trigger (oil temperature threshold? converter-clutch load?) and why 01 and 10 are both "request".
4. 0x0B5 byte5 bits0-3: meaning of bit1 (handshake) and of the exclusive patterns bit2/bit3; meaning of 0x0A8 bits 56-60
   as received by the EGS.
5. Content of 0x0B5 bytes 0-3 and byte6 and 0x0BA bytes 1-5 (torque request/limit, program, target gear?) — sent but
   unused by this DME.
6. Whether any decoded field changes with D/S/M selection (static test P→R→N→D→S→M and M-gate taps).
7. 0x1A2 unit (0.125 rpm/bit LIKELY) and 0x5C3 request semantics (code 0x038E, reply object 0x76).
8. EGS timeout behaviour (what the EGS does when 0x0AA disappears) — outside the DME.


* RAM `0x5B9D20` = vehicle speed: LIKELY. Written in INT `0x3D03C` from `0x5B9D1C` (period input, INT `0x3CF9C`,
  helper INT `0x66DD4`), slew-limited; used as speed in the no-EGS gear computation INT `0x5E3A0` (rpm<<12 vs `0x5B9D20`),
  standstill flag `0x3FC0CE`. **`0x5B90BB` = `0x5B9D20`/160 (clamped 255) and `0x5B90BA` = its signed change** (INT
  `0x3D2C0…0x3D308`). This contradicts the round-3 re-labelling of `0x5B90BB` as a temperature; the round-2 "speed"
  reading looks right (thresholds 0xE0/0xF0 would then be high-speed thresholds). The misfire detector also uses
  `0x5B90BB` = 0 as a standstill condition (INT `0x23624`). Needs a separate check before docs are changed.
* Anti-jerk / surge-damping observer INT `0x4533C` + INT `0x315F0` (model speed `0x5B97D8`, error `0x5B97D4`, output
  `0x5B97C2` with dead band ±819): output gain is 0 in automatic configuration (§1.1). Name LIKELY.

### 7. Not completed

| Item | Known | Needed |
|---|---|---|
| EXT `0xFAEDB8` role of `0x5B93BD`/`0x3FB384`/`0x5B977C` | 0x0B5 byte4 bits6-7 force `0x5B93BD` = 0 | trace `0x3FB384` consumers and `r30` source |
| `0x5B927E` downstream (EXT `0xF5D68C`, `0xF5E068`, `0xF61E58`, `0xF30BF8`) | merges EGS byte5 bits2-3 with detector flags | follow to lamp/CAN output |
| EXT `0xF5A65C` output | oil temperature → offset `0x5B9476` in cooling chain | find fan/PWM output |
| Physical meaning of EE0/EDF | consumer behaviour above | EGS dump / logs (§5) |
