# CAN inputs and drive-mode representation (770B) — round 3

Address kinds: **INT** = internal-flash CPU address; **EXT** = external-flash CPU address (file =
CPU − 0xF00000); **CAL** = calibration CPU alias (file = CPU − 0x100000); **RAM** = runtime address.
Reproduce: `python tools/me9_can.py --users`, `python tools/verify_770b_findings.py`.

## 1. TouCAN driver structure — CONFIRMED

| Item | Address | Evidence |
|---|---|---|
| TouCAN A / B module base | IO `0x307080` / `0x307480` | IFLAG (`base+0x24`) polled in INT `0x62704` / `0x62768` |
| Receive/transmit interrupt handler | INT `0x63FC8` (r3 = module base, r4 = controller 0/1) | walks set IFLAG bits; per-buffer type from RAM table `0x3FAEA0` |
| Message-object index table | EXT `0xFDFAC8` → objects at EXT `0xFDFAF4` (30 × 24 bytes); diagnostic set at EXT `0xFDFDC4` | pointer stored to RAM `0x3FAF34` by INT `0x638F4` |
| Message object layout | +0 handle, +0x0C CAN ID (11-bit), +0x11 controller (0 = A, 1 = B), +0x13 bit0 = TX, +0x14 DLC | TX bit used by the ISR at INT `0x6417C`; IDs/DLCs below |
| RX copy buffers | RAM `0x5BB618 + 0x14·handle` (pointer `0x3FAE9C`, set by INT `0x62478`) | copy routine EXT `0xF0A180` |
| Signal table | EXT `0xFDF967 + 5·sig`: {sig, msg handle, byte order, start bit, length} | read API INT `0x63660`, write API INT `0x63C3C` |
| Signal granularity | every message is exposed as two 32-bit Intel-order words (bytes 0-3, bytes 4-7) | bit fields are extracted in the consumer functions |
| A second copy of the driver | EXT `0xF09900–0xF0AC00` (in the `0xF00000–0xF0FF48` sub-block that also holds a copy of the startup code) | **HYPOTHESIS:** boot/flash-loader CAN driver |

Bitrate: the PT-CAN rate (500 kbit/s in the external reference) has not been derived from the TouCAN
CTRL/PRESDIV setup yet. Status: open.

## 2. Message table (EXT `0xFDFAF4`) — CONFIRMED

| CAN ID | Dir | Ctrl | DLC | DME consumer / producer | External reference (damienmaguire/BMW-E65-CANBUS) |
|---|---|---|---|---|---|
| 0x0A8 | TX | A | 8 | INT `0x4B128` (sig 0x2E/0x2F) | in DME filter set ✔ |
| 0x0A9 | TX | A | 8 | INT `0x4B128` (sig 0x30/0x31) | in DME filter set ✔ |
| 0x0AA | TX | A | 8 | INT `0x4B128` (sig 0x32/0x33) | in DME filter set ✔ (Arduino comment "transmission address" is **wrong**; DME is the producer) |
| 0x0B5 | RX | A | 8 | INT `0x392C8` (bytes 4-7 only) | EGS filter set ✔ |
| 0x0BA | RX | A | 7 | INT `0x392C8` | EGS filter set ✔ |
| 0x1A2 | RX | A | 2 | INT `0x392C8` | EGS filter set ✔ |
| 0x5C3 | RX | A | 8 | EXT `0xF5F9B4` | EGS filter set ✔ |
| 0x0B6, 0x0CE, 0x19E, 0x1A0 | RX | A | 5/8/8/8 | INT `0x5B988` (one function) | not in DME/EGS sets → other node (**HYPOTHESIS:** DSC) |
| 0x0B7 | RX | A | 6 | EXT `0xFA7D38` | — |
| 0x0C4, 0x194 | RX | A | 6/4 | EXT `0xFD3B64` | — |
| 0x130 | RX | A | 5 | INT `0x38EF8` | — (commonly terminal status; unverified) |
| 0x1AC | RX | A | 4 | INT `0x5B7C8` | — |
| 0x1B4, 0x310, 0x330, 0x5E0 | RX | A | 8/7/8/8 | EXT `0xF5F3AC` | — |
| 0x1B5 | RX | A | 5 | no reader found | — |
| 0x334, 0x3B4 | RX | A | 2/8 | EXT `0xF3C228` | — |
| 0x184, 0x18C | RX | **B** | 8 | EXT `0xF83C8C` | not on PT-CAN captures |
| 0x185, 0x18D | RX | **B** | 8 | INT `0x50008` | not on PT-CAN captures |
| 0x1FF, 0x105, 0x10D | TX | **B** | 8 | INT `0x4FB78`, EXT `0xF2D910` | not on PT-CAN captures |
| diagnostic set: 0x7E8, 0x612, 0x110, 0x480, 0x600, 0x7BC, 0x7BD, 0x7A0 | mixed | A/B | 8 | — | — |

TouCAN B carries a private bus (IDs 0x1xx not seen on the PT-CAN captures). **HYPOTHESIS:** the local
link to a second control unit (e.g. Valvetronic / second-bank controller). Not analysed further.

**Not received by the DME:** `0x192` (selector lever) and `0x1D2` (gear/program display). Also absent
from the table: 0x1B6, 0x1D0, 0x200, 0x492, 0x592 (DME candidates from the reference) and 0x498 (EGS
candidate). If the DME sends them, it does so through a path not covered by this table (not found).
Status: REJECTED for the RX hypothesis on 0x192/0x1D2; open for the other TX candidates.

## 3. Decoded EGS fields (INT `0x392C8`) — bit positions CONFIRMED, meanings as stated

Bytes are numbered 0-7 in CAN order (Intel word assembly confirmed by the byte-swap in INT `0x63660`).

| Frame / field | RAM | Consumers | Meaning | Status |
|---|---|---|---|---|
| 0x0BA byte0 bits0-3 (gear code) → table INT `0x15984` {5..10 → 1..6, 2 → 7, else 0} | `0x5B8F71` | INT `0x5E320` → `0x5B92CA` | current gear (7 = reverse, 0 = P/N/invalid) | **CONFIRMED** mapping; P/N/R semantics LIKELY |
| (`0x5B8F71 ≠ 0`) | `0x3FBEDE`, `0x3FBEDA` | driver-wish/idle/diag fns (`0x4C8C0`, `0xFAEDB8`, `0xF1BCC8`, …) | "drive engaged" | LIKELY |
| 0x0BA byte0 bit6 / bit7 | `0x3FBEE0` / `0x3FBEDF` (both forced 1 on timeout) | INT `0x23338`, `0x23734`, `0x5C99C`, `0x4533C`, EXT `0xF2EA9C` | status bits used by misfire/rough-running and other monitoring | function HYPOTHESIS (shift active / converter state candidates) |
| 0x0BA byte6 bits4-6 (7 = invalid) | `0x5B8F73` | none in application (reset only) | unused | CONFIRMED unused |
| 0x1A2 bytes0-1 (0xFFFF = invalid) | `0x5B9982` | driver-wish fn INT `0x46E3C` (divided by engine speed, selected by CAL `0x1C8532` bit1), INT `0x5F52C` | speed signal related to engine speed | **LIKELY** turbine speed (→ converter slip) |
| 0x0B5 bytes0-3 | — | **no reader** | — | CONFIRMED unused by DME |
| 0x0B5 byte4 bit6 / bit7 | `0x3FBEDB` / `0x3FBEDC` | coolant-target fn EXT `0xF9E148` (XOR → bit `0x5BBAC7.2`), EXT `0xF48754`, `0xFAEDB8` | 2-bit status (01/10 valid) | HYPOTHESIS |
| 0x0B5 byte5 bits0-3 (default 0xF) | `0x5B8F72` | EXT `0xF61F70` | 4-bit status | HYPOTHESIS |
| 0x0B5 byte5 bits4-5 | `0x3FBED9` | none | unused | CONFIRMED unused |
| 0x0B5 byte5 bits6-7 (≠ 0) | `0x3FBEDD` | driver wish INT `0x463B0`: wish := min(KFPED, `0x3FB460`+`0x3FB45E`) | **EGS-requested driver-wish/torque limitation** | LIKELY |
| 0x0B5 byte7 (0xFF invalid, ≥ 0xB7 → 0xFF) | `0x5B9229` = (raw+8)·4/3 | EXT `0xF5A65C` | transmission oil temperature (raw − 40 °C, converted to DME 0.75 °C/−48 format); falls back to `0x5B9307` | **HIGH CONFIDENCE** (exact unit conversion) |
| 0x5C3 byte0 = 1 and bytes1-2 = 0x038E | `0x3FBEE4` | — | identification/handshake flag | HYPOTHESIS |
| message freshness/timeout | `0x3FBED2/D3/D4/D5/D6/D7/D8`, counters `0x3FA587…0x3FA58C` (timeout after > 50 calls) | many | per-message valid flags | CONFIRMED |
| EGS present / automatic | `0x3FBED1` | > 25 functions | selects CAN gear vs. computed gear (INT `0x5E364` path) | LIKELY |

## 4. D / S / M / kickdown / TCC / interventions — what the DME actually sees

| Concept | In 770B DME? | Evidence | Status |
|---|---|---|---|
| D/S/M selector program | **No direct input.** 0x192/0x1D2 are not received; no decoded EGS field is consumed by driver-wish or mode logic except `0x3FBEDD` (limit) | message table + consumer search | **LIKELY: the DME has no D/S/M state** |
| Current gear | yes: `0x5B92CA` (from 0x0BA) | §3 | CONFIRMED |
| Requested gear | no field identified | — | not found |
| TCC lock/slip | indirectly: 0x1A2 speed (`0x5B9982`) ÷ engine speed | INT `0x46E3C` | LIKELY |
| Kickdown | DME → EGS: B_kd → `0x5B902B = 0x0B` → 0x0AA byte6 bits4-7 | `research/kickdown-path.md` | CONFIRMED |
| EGS torque intervention | (a) `0x3FBEDD` driver-wish limit; (b) intervention flags in the AEVAB path (`0x3FBF34/38`, `0x3FC195`, `0x3FC1A3`) — their CAN origin is not yet traced | — | (a) LIKELY, (b) HYPOTHESIS |
| DSC torque intervention | frames 0x0B6/0x0CE/0x19E/0x1A0 are decoded together in INT `0x5B988`; link to the AEVAB enable flags not yet traced | — | HYPOTHESIS |

## 5. Can an E mode coexist with D/S/M handling?

Because the 770B DME holds **no** D/S/M state of its own, an E mode would not collide with existing
DME mode logic. It also cannot reuse one. An E-mode request therefore needs a new input: a new CAN
signal (would require a message-table change), a coding/calibration switch, or a derived condition
such as gear + pedal + cruise state. The cleanest DME-side read-only inputs already available are
gear `0x5B92CA`, B_kd `0x3FBFB3`, pedal `0x5B96D8`, the EGS limit flag `0x3FBEDD` and cruise state
(`0x3FC188`, `0x5B954E`). Status: design HYPOTHESIS.

## 6. External reference used

damienmaguire/BMW-E65-CANBUS (see `references/SOURCES.md`). Used only to cross-check producer/consumer
roles of IDs. Every confirmed ID above comes from the DME message table, not from the reference.
Claims from that repository **not** confirmed here: the 500 kbit/s bitrate (not yet derived), the
0x192 S-M-D decoding (not received by the DME), and 0x1D2 semantics (not received by the DME).

---

# Round 4 additions (2026-10-03)

* TouCAN-B (private bus) is the **Valvetronic link** on the DME side: per-bank lift requests in 0x105
  (bank 1) and 0x10D (bank 2), rpm/status in 0x1FF, feedback in 0x184/0x185/0x18C/0x18D. CONFIRMED
  (DME side); details in `valvetronic.md`.
* Torque fields of 0x0A8/0x0A9/0x0AA decoded at bit level: `dme-egs-interface.md` (round-4 section).
* No new evidence on D/S/M; the round-3 verdict (no D/S/M state in the DME) stands.
