# Roadmap

## Phase 0 — Evidence discipline

- [x] Hash all reference inputs.
- [x] Separate third-party source material from publishable derived research.
- [x] Define confidence labels: `CONFIRMED`, `LIKELY`, `HYPOTHESIS`, `UNTESTED`.
- [x] Confirm REDABM 560B -> 770B byte identity.
- [ ] Reproduce all provisional RAM/function addresses from disassembly and store scripts/notes.

## Phase 1 — DME map and function port

- [ ] Port selected 560B symbols into the 770B layout using local signatures and cross-references.
- [ ] Confirm `CWEVAB` target address.
- [ ] Locate the complete `MDRED -> AEVAB -> evz_aus/evz_austot -> injector output` chain.
- [ ] Document torque, lambda, Valvetronic, VANOS, ignition, generator, thermostat and exhaust-flap control.
- [ ] Create a minimal 770B definition containing only verified symbols.

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
- [ ] Reverse engineer D/S/M status and DME <-> EGS torque messages.
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
