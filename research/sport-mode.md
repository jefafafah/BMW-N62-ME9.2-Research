# Sport mode in 770B — round 3 verdict

## Question

Is sport behaviour (KFPEDS-type driver wish, sport acceleration/resume ramps, sport pedal/torque
modifiers) present **and used** in this 770B build, rather than only in the ME9.2.1 (725D) reference?

## Findings

| Check | Result | Status |
|---|---|---|
| Sport/selector input on CAN | 0x192 (selector incl. S-M-D button per external reference) and 0x1D2 are **not** in the DME message table | CONFIRMED |
| EGS fields consumed by driver-wish/torque logic | only `0x3FBEDD` (0x0B5 byte5 bits6-7) → driver-wish **limit**; no field selects an alternative map | CONFIRMED (consumer search) |
| Unused EGS fields (would be natural carriers of a program/mode code) | 0x0BA byte6 bits4-6 (`0x5B8F73`), 0x0B5 byte5 bits4-5 (`0x3FBED9`), 0x0B5 bytes0-3: decoded or available, **no consumer** | CONFIRMED |
| Second driver-wish map | the only other 16×8 pedal×rpm map, CAL `0x1CF610`, is linear and fed by the cruise-control path (EXT `0xFAA384`) | REJECTED as KFPEDS (round 2, unchanged) |
| Map pairs selected by a mode flag in the driver-wish fn INT `0x46348` | none found: KFPED/KFMRMI/KFMIMR are single instances | LIKELY |
| Sport acceleration/resume ramps (BRABEVI2/BRAWAVI2-type) | cruise ramps exist (`research/torque-and-modes.md` §6) without a sport variant | LIKELY absent |
| Sport button flags (`B_sptvar` in 725D) | no candidate | not found |

## Verdict

**LIKELY: sport driver-wish behaviour is not present in this 770B calibration/software.** The D/S/M
program lives in the EGS. The DME sees only gear, an EGS limit request and status bits.

Counter-evidence and limits: indirect (pointer-based) reads are not covered by the xref scanner, and
`0x5B8F72` (0x0B5 byte5 low nibble) / `0x3FBEDB/DC` have consumers whose meaning is still open (thermal
and diagnosis functions). A live capture with D vs S selected (logging matrix in
`dme-egs-interface.md`) would settle whether any of these fields change with the program.

## Consequence for an S/E mode design

S and E behaviour would both have to be **added**. Recommended approach (design, UNTESTED): one new
mode variable feeding (a) a driver-wish map selector at the KFPED lookup (INT `0x46370`), (b) the flap
threshold (EXT `0xF97F0C`), (c) the coolant-target selection (EXT `0xF9E148`), and (d) the efficiency
firing request (`aevab-integration-points.md`).
