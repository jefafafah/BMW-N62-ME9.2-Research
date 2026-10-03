# Proposed powertrain architecture

## Principle

Reuse OEM Bosch mechanisms where they already solve difficult real-time problems (injector sequencing, kickdown state, knock adaptation, generator load handling, lambda recovery, fault fallback) and add as little custom logic as possible.

```mermaid
flowchart TD
    Selector[Drive-mode request] --> Mode[Mode state machine]
    Pedal[Pedal / driver wish] --> KD[Native kickdown detection B_kd]
    KD --> Mode

    Mode -->|E normal| ECO[E efficiency controller]
    Mode -->|E + kickdown| PWR[Power override]
    Mode -->|D| DLY[Daily controller]
    Mode -->|S/M| PWR

    ECO --> FD[Firing-density request 4/8 or 6/8]
    FD --> AEVAB[OEM AEVAB / REDABM]
    AEVAB --> INJ[Injector-output path]

    ECO --> LOAD[Valvetronic / VANOS / torque target]
    ECO --> LAMBDA[Lambda target coordinator]
    ECO --> GEN[Generator load strategy]

    PWR --> FULL[8/8 firing]
    PWR --> LOADP[Performance load / VANOS / ignition]

    Fault[Fault / protection / invalid state] --> SAFE[OEM 8/8 safe fallback]
    SAFE --> INJ
```

## Priority rules

1. OEM engine protection and fault handling always wins.
2. OEM DSC/EGS torque interventions must remain functional.
3. E-mode efficiency logic is allowed only when all prerequisites are valid.
4. Native kickdown overrides E-mode firing limits temporarily.
5. When kickdown ends, the mode request remains latched and the controller returns to E after a stabilization timer/hysteresis.

## Why dynamic/rotating firing density

The N62 does not close intake/exhaust valves on deactivated cylinders. Keeping the same four cylinders unfired for long periods would continue pumping air through them and create bank/lambda/thermal complications. Alternating OEM masks can keep all cylinders thermally active while reducing firing density.
