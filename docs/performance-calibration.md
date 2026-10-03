# Performance calibration concept

> **Superseded concept note (pre-analysis).** Kept for history. Where it conflicts with the final static pass, the current document wins: [performance-mode.md](../research/performance-mode.md). The current concept keeps E-mode at 8/8; cylinder cut is only an optional late experiment ([final mode architecture](../research/final-mode-architecture.md)).


Efficiency and peak performance occupy different load regions, so the project can optimize both without making one compromise map.

## Fuel requirement

95 RON is the hard minimum design fuel. Better fuel may allow the existing knock-adaptation system to retain more ignition advance, but the base calibration must remain safe and usable on 95 RON.

## Relevant reference areas

- `KFMIRL` — requested load calculation.
- `KFMIOP` — optimal engine torque model.
- `KFZWOP` / variants — optimal ignition angle reference.
- `KFWESVL` — full-load inlet cam spread versus RPM and knock intensity.
- `KFWASVL` — full-load exhaust cam spread versus RPM and knock intensity.
- Valvetronic and VANOS target maps for warm/unthrottled operation.

## Proposed behaviour

- **E normal:** efficiency load and firing-density strategy.
- **E kickdown / S / M:** 8/8, performance load target, optimized VANOS/Valvetronic, knock-limited ignition, stock protection/enrichment.
- Avoid claiming a final horsepower number until baseline and modified dyno/load data exist.

A naturally aspirated N62B36 will not produce turbo-like software gains. The main objective is better area-under-the-curve and response while preserving 95-RON safety.
