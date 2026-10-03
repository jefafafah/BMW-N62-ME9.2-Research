# Roadmap

## Phase 0 — Evidence discipline

- [x] Hash all reference inputs.
- [x] Separate third-party source material from publishable derived research.
- [x] Define confidence labels: `CONFIRMED`, `LIKELY`, `HYPOTHESIS`, `UNTESTED`.
- [x] Confirm REDABM 560B -> 770B byte identity.
- [x] Reproduce provisional RAM/function addresses from disassembly and store scripts/notes (round 2: `tools/me9_*.py`, `tools/verify_770b_findings.py`).
- [x] Add `HIGH CONFIDENCE` and `REJECTED` labels.

## Phase 1 — DME map and function port

- [~] Port selected 560B symbols into the 770B layout (round 2: 10 symbols by semantics/order; byte-signature porting pending a local 560B bin/XDF).
- [x] Confirm `CWEVAB` target address (CPU `0x1CD9CA`, function confirmed).
- [x] Locate the `torque ratio -> step request -> AEVAB -> evz_aus/evz_austot -> injector output` chain (`research/aevab-redabm.md`).
- [~] Document torque, lambda, Valvetronic, VANOS, ignition, generator, thermostat and exhaust-flap control (round 2 notes exist; VANOS/Valvetronic/knock not located).
- [ ] Create a minimal 770B definition containing only verified symbols (start from `research/symbol-map-770B.csv`, CONFIRMED/HIGH CONFIDENCE rows only).

### Round-3 open questions and next static experiments

1. Re-open the 560B bin/XDF locally. Re-check the KFMIMR/KFMRMI/KFPED record sizes, LASOABML shape (scalar vs. 6-point curve) and the inconsistent `CWAKR`/`KFAKR_GANG` offsets in `reference-symbols.csv`. Run `find_signature.py`/`local_alignment.py` per symbol window.
2. Determine the rate of the task `0x31B20` that runs AEVAB and injection time: decode the OS task table at INT `0x6F878`.
3. Identify the intervention sources `0x3FBF34/0x3FBF38` (fn `0x404D4`), `0x3FC1A3`, `0x3FC195/0x3FC198`, `0x3FC162` (ASC/DSC vs. EGS vs. limiter).
4. Static masks `0x5B8FD1` (fn `0xF37E34`) and `0x5B90D8`; the `0x3FC234`/`0x5B90F9` path.
5. Locate AEVABU, AEVABZK, IMLEVABS, KFLAMFA, KFDLASO, TGENOFVL.
6. Lambda controller, adaptation and measured λ (follow consumers of `0x5B96AA/0x5B96A8`).
7. ~~Sport-mode flag and CAN message map~~ — done in round 3 (`research/can-and-drive-modes.md`); no sport flag exists in the DME.
8. VANOS/Valvetronic maps (candidates `0x1C21AC`, `0x1C2500`, `0x1C2636`), knock adaptation, fan PWM (MIOS).
9. Physical scalings: λ 4096 = 1.0, rpm 0.25/bit, rpm byte 40/bit, temperature 0.75 °C − 48, speed 1/128 km/h. Confirm each with a live log.

### Next in-car experiments (read-only logging first)

* Log the AEVAB chain (`0x5B93E7`, `0x5B92E8`, `0x5B92EA`, `0x5B92EC`) during DSC and EGS shift interventions to confirm the step = round(8·depth) model and the latched phase.
* Bench check with an injector-pulse logger (or noid lights) that mask bit order = firing order.
* Kickdown: confirm `0x3FBFB3` sets only past the detent at 100 % pedal.
* Exhaust flap: confirm the polarity of `0x3FC286`.
* Cruise control: CAN capture of lever presses to see where a 10 km/h jump (if any) originates.

## Phase 2 — Logging baseline

- [ ] Capture stock logs on 95 RON.
- [ ] Record pedal, requested/actual torque, load, RPM, gear, TCC slip, lambda targets/actual, STFT/LTFT, knock retard, VANOS, Valvetronic, MAF/load, coolant/oil/air temperatures and generator load.
- [ ] Establish fixed A/B test route and repeatability tolerance.

## Phase 3 — Efficiency building blocks

- [ ] Stock 8/8 baseline.
- [ ] Valvetronic/VANOS cruise optimization.
- [ ] Ignition optimization with 95 RON as the hard minimum fuel quality.
- [ ] Generator load shifting.
- [ ] DFCO/coast optimization.
- [ ] Mild lean-cruise experiments only after lambda target path is verified.
- [ ] 6/8 firing tests.
- [ ] 4/8 firing tests.
- [ ] Combine features only after isolated validation.

## Phase 4 — E mode

- [ ] Implement latched E-mode request.
- [ ] E operates at 4/8 or 6/8 under normal conditions.
- [ ] Native `B_kd` triggers temporary 8/8 power override.
- [ ] Power override returns automatically to E after hysteresis/stabilization.
- [ ] Fail-safe returns to stock 8/8 behaviour on invalid conditions or faults.

## Phase 5 — Performance calibration

- [ ] Optimize high-load torque request.
- [ ] Optimize VANOS/Valvetronic at high load.
- [ ] Optimize ignition on 95 RON with knock-adaptive benefit on better fuel.
- [ ] Maintain OEM temperature and catalyst protection paths.
- [ ] Validate on a dyno or equivalent controlled load measurement before publishing claims.

## Phase 6 — ZF 6HP EGS integration

- [ ] Obtain and identify the exact EGS software.
- [~] Reverse engineer D/S/M status and DME <-> EGS torque messages (round 3: DME side decoded; D/S/M not present in DME; 0x0A8/0x0A9 torque fields still open).
- [ ] Tune low-load shift schedule, hysteresis and TCC strategy.
- [ ] Integrate E-mode shift programme.
- [ ] Validate NVH with 6/8 and 4/8 firing, especially with locked converter.

## Stretch research

- Dynamic skip-fire rather than fixed-cylinder deactivation.
- Fuel-quality-adaptive high-load calibration.
- Exhaust-flap behaviour per drive mode.
- A/C and generator load shedding during transient acceleration.
- Thermal target selection by drive mode.
- CAN-driven E-mode indicator and OEM-like UI integration.

## Round 4 — open questions and next experiments

Static:
1. Decode 0x0A8/0x0A9 torque fields in the TX builder INT `0x4B128` (inputs `0x5B94C6…0x5B94D2`, `0x5BBA56…`).
2. Trace the CAN origin of the AEVAB enable flags `0x3FBF34/0x3FBF38` (fn INT `0x404D4`) and `0x3FC1A3`/`0x3FC195`, in particular whether DSC frames (0x0B6/0x0CE/0x19E/0x1A0, decoder INT `0x5B988`) feed them.
3. Derive the PT-CAN bitrate from the TouCAN CTRL1/PRESDIV initialisation.
4. Enumerate `bl 0xAC00` output-channel calls (flap = channel 12) to find the thermostat heater and fan outputs.
5. Split the lambda controller (INT `0x56DD0`) into P/I/adaptation; locate full-load and protection enrichment inputs of INT `0x1A4F0`.
6. Confirm the meaning of `0x5B90BB` and `0x5B9307` (temperatures?) from their writers.
7. Re-check TGENOFVL/LASOABML/KFMIMR/KFMRMI names against a locally supplied 560B XDF.

In-car / bench (read-only first):
1. PT-CAN capture with the selector cycled P-R-N-D-S-M and M-gate taps, correlated with `0x5B92CA`, `0x3FBEE0/DF`, `0x5B8F72`, `0x5B8F73`, `0x3FBEDB/DC`.
2. Kickdown: confirm 0x0AA byte6 high nibble = 0xB exactly while `0x3FBFB3` = 1.
3. Converter: correlate 0x1A2 (`0x5B9982`) with engine speed during lock/unlock.
4. Flap polarity on output channel 12.
5. AEVAB during DSC/EGS interventions (`0x5B93E7`, `0x5B92EA`, `0x3FBF34/38`), plus exhaust λ/catalyst temperature during any cut event.
