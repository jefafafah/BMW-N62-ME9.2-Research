# Generator load management

> **Superseded concept note (pre-analysis).** Kept for history. Where it conflicts with the final static pass, the current document wins: [generator-control.md](../research/generator-control.md). The current concept keeps E-mode at 8/8; cylinder cut is only an optional late experiment ([final mode architecture](../research/final-mode-architecture.md)).


The reference definitions contain an OEM full-load generator-shedding mechanism.

Relevant symbols include:

- `TGENOFVL` — generator shutoff time during full-load acceleration;
- `VGENOFMN`, `VGENOGMX` and related thresholds;
- generator torque/load modelling and ramp parameters.

In the inspected 770B reference, the corresponding candidate calibration appeared effectively disabled/zero in the area studied; this must be ported and verified before any change.

## Concept

- reduce generator torque during hard acceleration;
- normal charging during steady operation;
- preferentially increase charging during overrun/deceleration when battery state permits;
- voltage/battery/temperature limits always override the efficiency strategy.

This is load shifting, not hybrid regenerative braking. Any fuel benefit is expected to be modest but measurable when combined with other changes.
