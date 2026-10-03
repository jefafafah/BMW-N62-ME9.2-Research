# External sources and provenance

Third-party material is referenced, not redistributed, unless its license clearly permits redistribution.

## Public source repositories

- MadScientist789, **BMW-XDFs-1**: <https://github.com/MadScientist789/BMW-XDFs-1>
- MotorMouth93, **BMW-XDFs**: <https://github.com/MotorMouth93/BMW-XDFs>

The research session used files found under the public ME9 directories, including a 7180A560B reference binary/XDF and a ME9.2.1 725D A2L. Their hashes are recorded in `research/verified-findings.md` so the exact inputs can be identified without republishing them here.

## ECU dump provenance

A reference KTAG full dump was acquired separately for analysis. Its external flash identifies Bosch HW `0261209002` and SW `1037389760` / 770B family. The supplied archive label and listing metadata showed a BMW DME part-number discrepancy, which is why this project treats hardware/software IDs and hashes as more reliable identifiers than a marketplace title.

No full dump or EEPROM is committed to this repository.

## Documentation classes used during research

- Bosch ME9/ME9.2 function-framework terminology and symbol names.
- BMW N62 technical training material for engine architecture and firing order.
- Public BMW ME9 XDF/A2L/DAMOS-derived definitions used strictly as external research references.

If a source is later included directly in this repository, its redistribution/license status must be documented first.

## Round 3 reference (CAN)

- damienmaguire, **BMW-E65-CANBUS**: <https://github.com/damienmaguire/BMW-E65-CANBUS>. It holds PT-CAN
  captures from an E65 735i, SavvyCAN filter sets (`dme_msgs.ftl`, `egs_msgs.ftl`, `dme_egs_msgs.ftl`)
  and an Arduino sketch (`E65_PTCAN.ino`). Cloned locally for comparison only; nothing from it is
  redistributed here.
  - Used as evidence: which IDs appear in the DME vs EGS filter sets (direction cross-check).
  - Confirmed against the 770B message table: 0x0A8/0x0A9/0x0AA are DME transmit; 0x0B5/0x0BA/0x1A2/0x5C3 are DME receive (EGS-originated).
  - Not confirmed / contradicted by 770B: 0x192 and 0x1D2 are **not** received by the DME; the sketch's comment calling 0x0AA a transmission frame is wrong (the DME builds it, with rpm×4 in bytes 4-5); the 500 kbit/s bitrate is not yet derived from the TouCAN setup.
