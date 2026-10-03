# E-mode kickdown power override

> **Superseded concept note (pre-analysis).** Kept for history. Where it conflicts with the final static pass, the current document wins: [final-mode-architecture.md](../research/final-mode-architecture.md). The current concept keeps E-mode at 8/8; cylinder cut is only an optional late experiment ([final mode architecture](../research/final-mode-architecture.md)).


## Existing Bosch mechanism

The ME9.2.1 725D A2L exposes the function `BBKD` and output `B_kd` (*Bedingung Kick-Down*). Relevant calibration symbols include:

- `UPWGKDO` — upper potentiometer-voltage hysteresis threshold for kickdown detection;
- `UPWGKDU` — lower hysteresis threshold;
- `WPKDMN` — minimum pedal value for kickdown detection.

This is preferable to inventing a synthetic rule such as `pedal > 95%`.

## Proposed state machine

```text
E_REQUESTED = 1

if B_kd == 0:
    E powertrain strategy
    firing density = 4/8 or 6/8

if B_kd == 1:
    POWER_OVERRIDE = 1
    firing density = 8/8
    performance lambda/load/ignition
    EGS may use kickdown/downshift behaviour

when B_kd returns to 0:
    retain 8/8 for a short stabilization interval
    transition to 6/8
    transition to 4/8 only after stable low-load conditions
```

The E request itself remains latched, so the driver does not need to manually reselect E after overtaking.
