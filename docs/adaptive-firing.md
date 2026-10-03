# Adaptive firing density / cylinder cut research

> **Superseded concept note (pre-analysis).** Kept for history. Where it conflicts with the final static pass, the current document wins: [firing-density-feasibility.md](../research/firing-density-feasibility.md). The current concept keeps E-mode at 8/8; cylinder cut is only an optional late experiment ([final mode architecture](../research/final-mode-architecture.md)).


## Confirmed OEM primitive

The 560B XDF defines:

- `CWEVAB` — *Codewort zur Abschaltung von Einspritzventilen* (codeword for injector shutoff)
- `REDABM` — *Ev-Abschaltmuster für Momentenreduzierung* (injector shutoff pattern for torque reduction)

The `REDABM` matrix is byte-identical in the 560B reference and the 770B external flash.

## REDABM matrix

Rows correspond to starting injector/event phase; columns represent increasing reduction steps.

```text
01 11 15 55 57 77 7F FF
02 22 2A AA AB BB BF FF
04 44 54 55 57 77 7F FF
08 88 A8 AA BA BB FB FF
10 11 51 55 75 77 F7 FF
20 22 A2 AA EA EE EF FF
40 44 45 55 D5 DD BF FF
80 88 8A AA AB BB BF FF
```

At reduction step four the table alternates between:

- `0x55` = `01010101`
- `0xAA` = `10101010`

This is exactly the balanced 4-of-8 pattern expected from a sequential torque-reduction implementation.

## Design implication

Do **not** hard-cut arbitrary injector wires or force a static four-cylinder mask. The preferred path is to route an efficiency firing-density request through the OEM sequencing machinery while ensuring the torque/load coordinator compensates appropriately.

## Open questions

- Exact 770B `CWEVAB` location and all runtime xrefs.
- Whether 6/8 operation can reuse the existing reduction steps without undesired torque-model side effects.
- How lambda coordination reacts to repeated rotating skip-fire at steady cruise.
- NVH with locked torque converter.
- Catalyst oxygen storage/temperature effects.
