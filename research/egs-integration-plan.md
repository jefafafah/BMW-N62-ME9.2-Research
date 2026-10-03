# EGS / ZF 6HP integration — capture and correlation plan

No EGS binary is available, so nothing on the EGS side is modified or claimed. This plan defines
what to capture so that D/S/M, kickdown, converter lock, gear and torque intervention can later be
correlated with DME internals.

## 1. What the DME side already gives us (770B, static)

| Signal | DME address | Status |
|---|---|---|
| kickdown `B_kd` | `0x3FBFB3` | CONFIRMED function (INT `0x3B80C`) |
| pedal / pedal-pot voltage | `0x5B96D8` / `0x5B96D0` | LIKELY |
| driver-wish torque (KFPED output) | `0x5B981A` | CONFIRMED source, scale LIKELY |
| full-pedal wish | `0x5B9816` | HYPOTHESIS |
| base torque / target torque | `0x5B97DA` / `0x3FC32A` | LIKELY |
| AEVAB step / state / final mask | `0x5B93E7` / `0x5B92E8` / `0x5B92EA` | CONFIRMED |
| current gear (as used by DME maps) | `0x5B92CA` (0…6) | LIKELY |
| candidate CAN-status packer (reads B_kd, pedal, interventions) | EXT fn `0xFA8E70` → `0x5B92C9`, `0x5B902B/2C` | HYPOTHESIS |
| CAN controllers | TouCAN A `0x307080`, TouCAN B `0x307480`; drivers INT `0x62704/0x62768`, EXT `0xF09D0C/0xF09D50` | CONFIRMED hardware, mapping open |

## 2. CAN capture

* Bus: PT-CAN between DME, EGS and DSC. The bitrate must be measured; it is commonly 500 kbit/s on
  E6x, but treat that as a HYPOTHESIS. Capture with timestamps, all IDs, no filtering.
* Message IDs commonly cited for E6x PT-CAN (0x0A8/0x0A9/0x0AA engine torque and rpm, 0x0BA/0x0B5
  transmission torque and gear data, 0x1D2 selector/gear display, 0x1A0 speed) are **external,
  unverified references**. Do not hard-code them. Identify each message by correlating it with the
  logged DME variables above.

## 3. Logging matrix

Each row is one scripted manoeuvre on the fixed test route (95 RON, warm engine, same load). Log DME
RAM (via the existing diagnostic logger) and raw CAN at the same time.

| # | Manoeuvre | Purpose | Expected observable |
|---|---|---|---|
| 1 | P→R→N→D→S→M at standstill, foot on brake | selector encoding | one CAN byte/bit field changes per position; DME `0x5B92CA` unchanged (0) |
| 2 | M: manual up/down shifts 1→6→1 at steady 2000 rpm | requested vs. actual gear | requested-gear field leads actual gear; `0x5B92CA` follows actual |
| 3 | D: gentle acceleration 0→100 km/h | shift points, converter lock | slip (rpm − turbine rpm) → ~0 after lock; lock-state bit |
| 4 | D vs S: identical pedal ramp 30 %→80 % | shift-programme difference | different shift rpm; any DME-side difference (expect none in 770B until a sport flag is found) |
| 5 | Kickdown from 80 km/h in 6th (pedal through detent) | kickdown chain | `0x3FBFB3` = 1 only past detent; the CAN bit mirrors it; EGS downshift |
| 6 | Full-load upshifts 2→3→4 | torque intervention | `0x3FC32A` dips below `0x5B97DA` during shift; whether AEVAB acts (`0x5B93E7` > 0) or only ignition |
| 7 | Overrun from 120 km/h, foot off | overrun cut / converter | `0x3FC19F` (HYPOTHESIS overrun cut), lock behaviour |
| 8 | Cruise control 60/100/130 km/h | cruise path | `0x5B954E`, `0x5B9822`, `0x3FC188`; set-speed steps of 1 km/h (cal `0x1C2002`) |
| 9 | DSC intervention on low-µ (safe area only) | ASC torque request | `0x3FBF34/0x3FBF38`, AEVAB step and mask |

## 4. Derived signals to compute offline

* Converter slip = engine rpm (`0x5B9A26` × 0.25) − turbine rpm (from CAN, field to be identified).
* Torque intervention depth = (`0x5B97DA` − `0x3FC32A`) / `0x5B97DA`. Compare with the AEVAB step
  prediction round(8 × depth).
* Gear consistency: CAN gear vs. `0x5B92CA`.

## 5. Exit criteria before any EGS work

1. The exact EGS hardware/software ID is read out and its binary is available locally.
2. Every row of §3 is captured at least twice with consistent results.
3. Selector, requested gear, actual gear, lock state and torque-intervention fields are each
   identified, with the evidence documented here.
