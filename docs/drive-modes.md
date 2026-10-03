# Drive-mode concept

## E — Efficiency

Normal operation is constrained to 4/8 or 6/8 firing density once eligibility conditions are met. 8/8 is reserved for a native kickdown power override, safety fallback or conditions in which E cannot be safely active.

Candidate eligibility gates:

- engine and oil sufficiently warm;
- lambda control ready;
- no active misfire/knock/temperature/fuel-system fault;
- stable battery voltage;
- suitable RPM and gear/TCC state;
- no OEM torque intervention that conflicts with E-mode control.

Transition concept:

```text
E request latched
    |
    +-- low stable load --------> 4/8
    |
    +-- moderate/high E load ---> 6/8
    |
    +-- B_kd == 1 -------------> temporary 8/8 POWER override
                                   |
                                   +-- B_kd clears
                                         |
                                         +-- stabilization delay
                                                |
                                                +-- 6/8
                                                       |
                                                       +-- stable low load -> 4/8
```

The return thresholds need hysteresis so the system does not oscillate between 4/8 and 6/8.

## D — Daily

OEM-like drivability with mild efficiency features. Initial proposal: primarily 6/8 and 8/8, with 4/8 only after E-mode testing proves it produces acceptable NVH and fuel economy.

## S — Sport

Always 8/8. Performance-oriented driver wish, VANOS, Valvetronic, ignition, torque request, generator/A/C transient load shedding and exhaust-flap behaviour.

## M — Manual

Keep manual gear selection intact; engine side follows the performance strategy unless later testing finds a reason to separate it from S.
