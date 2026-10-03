# Research status

## Confidence model

- **CONFIRMED** — reproduced directly from the provided binary/reference files or unambiguous source definitions.
- **LIKELY** — strongly supported by local alignment, related software definitions, or code structure but not yet independently proven end-to-end in 770B.
- **HYPOTHESIS** — technically plausible design or interpretation awaiting validation.
- **UNTESTED** — proposed calibration/behaviour not yet run on a vehicle.

## Current status summary

| Item | Status | Notes |
|---|---|---|
| Target external flash is 1 MiB | CONFIRMED | Provided `28f200f3t.bin` is 1,048,576 bytes |
| Bosch HW `0261209002` | CONFIRMED | Present in reference dump metadata/string data and source label |
| Bosch SW `1037389760` / 770B family | CONFIRMED | Present in external flash |
| Reference listing vs physical DME part-number mismatch | CONFIRMED | Source archive title and label do not use the same BMW DME number |
| 560B `REDABM` at file offset `0x54A0` | CONFIRMED | XDF definition + reference binary |
| 770B `REDABM` at external offset `0xC5510` | CONFIRMED | 64-byte matrix is byte-identical to 560B |
| Four-of-eight patterns are `0x55` / `0xAA` | CONFIRMED | Reduction-step-4 matrix values |
| 560B `CWEVAB` at `0xD8B4` | CONFIRMED | XDF definition |
| 770B `CWEVAB` candidate near `0xCD9CA` | LIKELY | Local sequence alignment crosses small insert/delete changes; exact byte still needs code/data xref confirmation |
| Native kickdown signal `B_kd` exists in ME9.2.1 reference | CONFIRMED | 725D A2L, function `BBKD` |
| E-mode can use native kickdown as override trigger | HYPOTHESIS | Requires 770B port and in-car validation |
| 4/6 firing can be used for efficiency | HYPOTHESIS | Bosch mechanism is torque reduction; efficiency benefit requires torque/load compensation and validation |
| Lean cruise can be implemented cleanly | HYPOTHESIS | Lambda coordinator/setpoint path must be proven first |
| EGS efficiency gain | HYPOTHESIS | Exact EGS binary not yet analyzed |

## Important architectural caution

`REDABM`/AEVAB is an OEM torque-reduction mechanism, not an OEM fuel-economy cylinder-deactivation feature. Reusing it for efficiency requires preserving demanded wheel torque by changing load/torque control on the firing events that remain active. Simply forcing a reduction step is not the same thing as an efficient V4/V6 mode.
