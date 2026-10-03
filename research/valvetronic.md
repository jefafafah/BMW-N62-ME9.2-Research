# Valvetronic (770B) — round 4

Address kinds: INT = internal-flash CPU, EXT = external-flash CPU, CAL = calibration alias, RAM = runtime.

## 1. Architecture — CONFIRMED (DME side)

The DME does not drive the eccentric-shaft motors itself. It sends one **lift request per bank**
over the private TouCAN-B bus and receives status back:

| Direction | CAN ID (TouCAN B) | DME variable | Function |
|---|---|---|---|
| DME → | 0x105 (signals 0x36/0x37) | bank-1 request `0x5B9D10` | INT `0x4FB78` |
| DME → | 0x10D (signals 0x38/0x39) | bank-2 request `0x5B9D12` | INT `0x4FB78` |
| DME → | 0x1FF (signals 0x34/0x35) | rpm `0x5B9A26`, status bytes | INT `0x4FB78` |
| → DME | 0x185 / 0x18D | `0x5B9D14…0x5B9D1A`, status `0x5B90A4…0x5B90B9`, `0x5B8F20…25` | INT `0x50008` |
| → DME | 0x184 / 0x18C | status/fault bytes `0x5B8A1D…0x5B8A36`, `0x5B8F1C…1F` | EXT `0xF83C8C` |

**HYPOTHESIS:** the separate node is the Valvetronic control unit. This is consistent with the N62
system layout; the node name is not proven from code.

## 2. Request calculation — CONFIRMED arithmetic

```text
bank 1:  req = min( 0x5B9B20 , 0x5B9BB6 + CAL 0x1C6F14 + 0x5B8AEA )      INT 0x4FCF8–0x4FD20
         req = min(req, 0x6EA);  0x5B9D10 = req·65536/0x6EA (≤ 0xFFFE)    → CAN 0x105
bank 2:  same with 0x5B9B22, CAL 0x1C6F12, 0x5B8AEC → 0x5B9D12          → CAN 0x10D
```

* `0x5B9BB6`: common lift target from INT fn `0x4E21C` (below).
* `0x5B8AEA` / `0x5B8AEC`: per-bank trims (written by EXT `0xF88494`, `0xF410DC`, init `0xF2E66C`). **HYPOTHESIS:** bank balancing.
* `0x5B9B20` / `0x5B9B22`: per-bank upper limits from EXT fn `0xFAD4B8` (map CAL `0x1C37DE` 4×4, scalars `0x1C38B4…0x1C38D0`; uses the fed-back values `0x5B9D14/16`). LIKELY fault/limit handling.
* `0x6EA` = 1770 = maximum request unit. Physical unit open (eccentric angle in 0.1° or lift in 1/180 mm are both plausible). HYPOTHESIS.

## 3. Target maps in INT fn `0x4E21C` (geometry CONFIRMED, roles HYPOTHESIS)

| CAL address | Geometry | Axes (inputs) | Output | Role (HYPOTHESIS) |
|---|---|---|---|---|
| `0x1C47E8` | 16×16 u16 | x engine speed 2200…24800 (0.25 rpm/bit: 550…6200 rpm), y `0x5B9B62` 427…4267 | `0x5B9BAC` | main part-load lift map (lift vs rpm × load demand) |
| `0x1C4C98` | 8×8 u16 | x 800…3600, y `0x5B9B64` 1280…4267 | `0x5B9BAC` | alternative/limit region |
| `0x1C4D3C` | 8×8 u16 | x 800…3600, y 24…184 (temperature-like) | `0x5B9BAC` | warm-up lift |
| `0x1C4A2C` / `0x1C4B62` | 21×6 u16 | x `0x5B9B4A` 200…6000 / 400…6000, y rpm 550…1200 | `0x5B9BAC` | idle / low-speed lift |
| `0x1C4DE0` | 16×16 u16 | x `0x5B9BAE` 0…10200, y `0x5B9BCC` or `0x5B9E02` 500…1300 | `0x5B9BBE` / `0x5B9BC0` | lift ↔ air-flow conversion (y possibly pressure 500…1300 mbar) |
| `0x1C503A` | 16 u16 | pedal `0x5B96D8` | — | pedal-based limit/feed-forward |
| `0x1C516C` | 6 u8 | `0x5B9307` (engine temperature) | `0x5B9048` | temperature factor |
| `0x1C50BE` | 12 u16 | 130…9600 | `0x5B9B9C` | rate/limit |

Min/max lift, full-load map, throttle backup interaction and fault fallback are not yet isolated.
Fn `0xFAD4B8` and the status decoding in INT `0x50008` are the next places to look.

## 4. Key question: can airflow through unfuelled cylinders be reduced?

* **Per cylinder: no.** The DME produces exactly two lift requests (bank 1, bank 2) and no
  per-cylinder value exists in the protocol. The N62 mechanism is one eccentric shaft per bank.
  CONFIRMED for the DME side.
* **Per bank: only by cutting a whole bank.** Lowering one bank's lift reduces airflow for all four
  cylinders of that bank, including fired ones. A meaningful reduction of pumped air therefore needs
  a bank-wise cut (mask `0x5A` or `0xA5`) plus minimum lift on that bank.
  * REDABM's balanced patterns are never bank-wise (2 per bank).
  * A single-bank firing order on the N62 cross-plane crank gives uneven intervals (positions 0,2,5,7
    → 180/270/180/90°), so NVH would be poor.
  * Minimum lift still flows air.
  Status: HYPOTHESIS (engineering inference).
