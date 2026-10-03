# Logging and test plan

> **Superseded concept note (pre-analysis).** Kept for history. Where it conflicts with the final static pass, the current document wins: [in-car-validation-plan.md](../research/in-car-validation-plan.md). The current concept keeps E-mode at 8/8; cylinder cut is only an optional late experiment ([final mode architecture](../research/final-mode-architecture.md)).


## Minimum stock baseline channels

- engine speed;
- pedal position and kickdown state;
- requested and actual torque/load;
- MAF/load/filling;
- requested and measured lambda per bank;
- fuel trims;
- ignition advance and knock corrections per cylinder where available;
- Valvetronic lift/position;
- VANOS requested/actual positions;
- coolant, oil and intake-air temperature;
- vehicle speed;
- gear and transmission input/output speeds;
- TCC command and slip;
- generator voltage/load/torque if exposed;
- misfire/rough-running counters;
- relevant protection/fault flags.

## Test progression

Never combine multiple unvalidated subsystems in the first test.

1. Verify stock read and recovery.
2. Establish repeatable stock logs.
3. Change one calibration family.
4. Compare against stock.
5. Revert if behaviour is not clearly understood.
6. Only then combine successful changes.

## 4/8 and 6/8 test gates

Abort to 8/8 on:

- unstable lambda control;
- misfire/rough-running increase;
- unacceptable knock activity;
- excessive vibration/NVH;
- unexpected temperature rise;
- EGS/TCC oscillation;
- any protection or communication fault.
