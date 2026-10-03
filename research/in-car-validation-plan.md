# Baseline in-car validation plan (read-only logging)

Purpose: confirm or reject the static findings on the real car **without changing anything**. All
items are passive: diagnostic RAM reads (the variables below are runtime RAM), a passive PT-CAN
capture, and BMW tester live values. No actuator tests that bypass protections, no connectors pulled
while driving, no calibration changes. WOT pulls only where safe and legal.

Tooling assumptions: a diagnostic logger able to read DME RAM by address at ≥ 10 Hz (≥ 50 Hz for
VANOS/ignition/torque transients), a PT-CAN logger with timestamps (all IDs, raw), and a BMW tester
for bank-labelled live values. Logs from all sources must be time-aligned (start marker: ignition on).

## A. Stationary tests

| # | Test | Duration / action | Main questions |
|---|---|---|---|
| A1 | Cold start (overnight soak) | start, idle 10 min without touching the pedal | catalyst-heating coordinator (`0x3FC0D4`, `0x3FC0D9`, `0x5B9348`), post-start λ (`0x5B968C`), post-start minimum angle (`0x5B9460`), VANOS park release (`0x3FB7D8`), start lift (Valvetronic start maps), multi-spark count (`0x5B9430`), fan/thermostat start values |
| A2 | Warm idle in P | 3 min | idle lift, idle ignition, λ modulation (`0x3FC1E3/E4`), knock activity baseline, flap closed (command 1) |
| A3 | Selector P → R → N → D → S → M, M-gate up/down taps | 10 s each | whether **any** decoded EGS field changes with the program (0x0BA bits 6/7 `0x3FBEE0`/`0x3FBEDF`, 0x0B5 byte4/byte5 fields `0x3FBEDB/DC/DD`, `0x5B8F72`), 0x192/0x1D2 on CAN but not in the DME (D/S/M verdict) |
| A4 | A/C off → on → max | 1 min each | 0x1B5 IHKA stage `0x5B854A`, fan duty `0x5B9470`, loss torque `0x5B97AA` and 0x0A9 bits 16-27 step, thermostat forced-low flag `0x5B8548` |
| A5 | Electrical load off → on (headlights, rear-window heater, seat heaters) | 1 min each | generator request `0x5B8F7B` (CAN 0x334), `0x5B8C7E`/`0x5B90F8`, BSD load `0x5B89EA`, generator torque `0x5B8C4A`, idle reserve `0x5B97AE`, battery voltage `0x5B930A` vs multimeter (scale) |
| A6 | Standstill rev to 3000 rpm in P | 3 short blips | flap stays closed at standstill (CW bit 2), driver request vs actual torque words |

## B. Driving tests

Same route and direction for every repeat; warm engine and gearbox; ≥ 3 repeats.

| # | Test | Main questions |
|---|---|---|
| B1 | Steady 30 / 50 / 80 / 100 / 120 km/h (60 s each, D) | speed scale of `0x5B90BB`/`0x5B9D20` vs dash/GPS (1.25 vs 0.625 km/h per bit), turbine/engine ratio `0x5B981E` at lock-up (expect ≈ 0x4000 → confirms 0.125 rpm/bit for 0x1A2), part-load Valvetronic/VANOS/ignition operating points, coolant target map region |
| B2 | Light, medium acceleration (20 %, 50 % pedal) | tip-in filter: `0x5B9808` → `0x5B97F8` → `0x5B9806`, gain `0x5B982A`, latch `0x3FC18D`, map factor `0x5B97F0`; transient ignition flag `0x5B8DE0`; flap thresholds |
| B3 | WOT pull 2nd/3rd gear where safe and legal | full-load flag `0x5B8F26`, full-load lift/VANOS/ignition maps, full-load λ (0.922) and protection λ `0x5B9C2E/2C`, knock retard per cylinder `0x3FC2E0[8]`, 0x0A9 max torque vs 360 Nm (Nm/bit hypothesis 0.5 Nm per CAN bit) |
| B4 | Steady cruise 5 min | λ adaptation `0x5B96BE`/`0x5B96BA`, Valvetronic balance learning `0x3FE17A[]`/trims `0x5B8AEA`/`0x5B8AEC`, bank-to-bank λ |
| B5 | Converter-slip transition (gentle acceleration through lock-up speed) | ratio `0x5B981E` crossing 0.96 → 1.00 → map factor change; 0x0BA bits 6/7 timing (converter-state hypothesis) |
| B6 | Normal upshift / downshift (D) | EGS torque request 0x0B5 bits 12-23/24-35/mode (`0x3FA04E`/`0x3FA04C`/`0x3FA048`), fast limit `0x5B94A4`, target `0x3FC32A`, intervention angle `0x5B9434`, AEVAB step `0x5B93E7` (expected 0 for EGS-only reductions) |
| B7 | Manual up/downshift (M) | same as B6; any DME-visible M behaviour |
| B8 | Kickdown | `B_kd` `0x3FBFB3`, 0x0AA byte 6 nibble 0x0B, flap opens via pedal 100 %, no DME torque path |
| B9 | Lift-off and coast in gear (DFCO) | DFCO status byte `0x3FB351`, `0x5B93B4…0x5B93B8`, request `0x3FC162`, cut `0x3FC19F`, ramp-out (target `0x3FC32A` vs `0x5B985C`), overrun ignition at minimum angle |
| B10 | Fuel resume (coast down to resume rpm; pedal tip-in during DFCO) | resume rpm vs coolant temperature, post-cut window `0x3FB451`, λ release after air-mass integral (`0x3FC1F7`, CAL `0x1C99C6`) |

## C. Minimum signal set

### C.1 DME RAM (address type RAM)

| Group | Variables |
|---|---|
| Engine / driver | rpm `0x5B9A26` (0.25 rpm/bit), rpm byte `0x5B9001` (40 rpm/bit), pedal `0x5B96D8`, pedal voltage `0x5B96D0`, kickdown `0x3FBFB3`, idle flag `0x3FC18B`, engine running `0x3FBFB7`, time since start `0x5B953E` |
| Gear / transmission | gear `0x5B92CA`, raw gear `0x5B8F71`, 0x0BA bits `0x3FBEE0`/`0x3FBEDF`, 0x0B5 fields `0x3FBEDB`/`0x3FBEDC`/`0x3FBEDD`/`0x5B8F72`, EGS torque request `0x3FA04E`/`0x3FA04C`/`0x3FA048`, transmission temperature `0x5B9229`, EGS present `0x3FBED1` |
| Turbine speed | 0x1A2 value `0x5B9982`, ratio `0x5B981E`, map factor `0x5B97F0`, filter gain `0x5B982A`, 0x1A2 fresh `0x3FBED6` |
| Torque | driver wish `0x5B981A`, rise-limited `0x5B981C`, driver request `0x5B980A`, capped `0x5B9808`, filtered `0x5B97F8`, selected `0x5B9806`, fast request `0x5B97FC`, base `0x5B97DA`, max `0x5B9854`, ignition-only min `0x5B985C`, actual `0x5B983A`, loss `0x5B97AA`, target `0x3FC32A`, rev limit `0x5B9870`, gear limit `0x5B9832`, DSC `0x5B949C`/`0x5B94A0`, EGS `0x5B94A4`/`0x5B94A2`/`0x5B94A8`, flags `0x3FC195`, `0x3FC198`, `0x3FC1A3`, `0x3FBEB8`, AEVAB step `0x5B93E7`, total cut `0x5BBBA8` |
| Lambda | targets feed-forward A/B `0x5B96A6`/`0x5B96A4`, snapped `0x5B96AA`/`0x5B96A8`, measured `0x5B970A`/`0x5B9708`, factors `0x5B98AA`/`0x5B98A2`, adaptation `0x5B96BE`/`0x5B96BA`, release `0x3FC1EE`/`0x3FC1EF`, modulation `0x3FC1E3`/`0x3FC1E4`, full-load request `0x5B891A`, protection `0x5B9C2E`/`0x5B9C2C`, cut flags `0x3FBFFE`/`0x3FBFFF`, model temperature `0x5B86C0` |
| Valvetronic | requests `0x5B9D10`/`0x5B9D12`, actuals `0x5B9D16`/`0x5B9D14`, target `0x5B9BB0`, lift actual `0x5B9BA2`, trims `0x5B8AEA`/`0x5B8AEC`, feedback faults `0x5B8F1A`/`0x5B8F1B`, full-load flag `0x5B8F26` |
| VANOS | targets `0x5B8DCC`/`0x5B8DA8`/`0x5B8DBA`/`0x5B8D96`, measured `0x5B8DCA`/`0x5B8DA6`/`0x5B8DB6`/`0x5B8D92`, raw edges `0x5B9C9A`/`0x5B9C96`/`0x5B9C98`/`0x5B9C94`, target bytes `0x5B911A` (intake) / `0x5B910F` (exhaust), family weight `0x5B903C` |
| Ignition / knock | base `0x5B9454`, warm-up `0x5B9462`, intervention `0x5B9434`, minimum `0x5B9460`, applied `0x3FC2EF`, final `0x3FC2F1`, per-cylinder retard `0x3FC2E0[8]`, tip-in retard `0x3FC2D9`, knock active `0x3FC0F4`, transient flag `0x5B8DE0` |
| Thermal | engine temperature `0x5B9307`, second coolant sensor `0x5B9308`, intake temperature `0x5B9306`, coolant target `0x5B91D1`/`0x5B91D3`, thermostat heater `0x3FC29B`, fan request `0x5B9475`, fan duty `0x5B9470`, IHKA stage `0x5B854A`, vehicle speed `0x5B90BB`/`0x5B9D20` |
| Flap | command `0x3FC286`, cruise-dominant `0x3FC188` |
| Generator | CAN request `0x5B8F7B`, request mV `0x5B8C7E`/`0x5B8C80`, output `0x5B90F8`, BSD load `0x5B89EA`, generator torque `0x5B8C4A`, idle reserve `0x5B97AE`, battery voltage `0x5B930A` |
| DFCO | status `0x3FB351`, control `0x5B93B4`, entry/resume `0x5B93B6`/`0x5B93B7`, request `0x3FC162`, cut `0x3FC19F`, post-cut window `0x3FB451` |

### C.2 CAN (passive capture, all IDs)

0x0A8, 0x0A9, 0x0AA (DME → EGS torque/rpm/pedal), 0x0B5, 0x0BA, 0x1A2, 0x5C3 (EGS → DME), 0x0B6
(torque intervention, DSC LIKELY), 0x1A0 (vehicle speed LIKELY), 0x0CE (wheel speeds LIKELY), 0x1B5
(IHKA), 0x334 (power module → generator request), 0x192, 0x1D2 (selector / gear display; not received
by the DME). Private bus (if accessible): 0x105/0x10D (Valvetronic requests), 0x185/0x18D (actuals),
0x1FF.

## D. Static hypotheses each test resolves

| Hypothesis | Test |
|---|---|
| 0x1A2 = turbine speed, 0.125 rpm/bit | B1, B5 |
| 0x0BA bits 6/7 = converter/driveline state | B5, B6 |
| Nm per CAN bit = 0.5 | B3 |
| `0x5B90BB` speed unit | B1 |
| VANOS bank 1 vs bank 2, intake/exhaust confirmation | A2 (tester values), B1 load steps |
| Valvetronic lift in µm / request in 0.1° eccentric | A2, B3 vs tester values |
| Flap command 1 = closed | A2/A6 (listen/observe), B2 |
| Fan PWM ch 9, thermostat DIG ch 6 | A4, warm-up in A1 |
| DFCO thresholds and resume curve | B9, B10 |
| Catalyst-heating coordinator | A1 |
| D/S/M not visible to the DME | A3 |
