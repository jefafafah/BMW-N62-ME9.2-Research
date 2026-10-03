# Exhaust-flap strategy

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
