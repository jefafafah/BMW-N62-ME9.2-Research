# Exhaust-flap strategy

> **Superseded concept note (pre-analysis).** Kept for history. Where it conflicts with the final static pass, the current document wins: [exhaust-flap.md](../research/exhaust-flap.md). The current concept keeps E-mode at 8/8; cylinder cut is only an optional late experiment ([final mode architecture](../research/final-mode-architecture.md)).


The reference definitions include exhaust-flap control, including `CWAKR` and `KFAKR_GANG` plus temperature/RPM/gear-dependent logic.

## Proposed mode behaviour

| Mode | Exhaust flap |
|---|---|
| E | OEM/quiet strategy |
| D | OEM or slightly earlier opening after validation |
| S | open during sport operation |
| M | open during performance operation |
| E + kickdown | open for the duration of the power override |

The purpose is sound/character, not a major horsepower gain. At high load the stock system already needs adequate exhaust flow.
