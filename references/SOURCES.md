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
