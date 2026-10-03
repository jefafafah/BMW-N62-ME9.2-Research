# BMW N62 / Bosch ME9.2 Research

Open research project for understanding and experimentally extending the Bosch ME9.2 powertrain control used with early BMW N62 engines, with an initial focus on the E65 735i / N62B36.

This repository is **research-first**. It documents confirmed findings, working hypotheses, design concepts, tooling, test plans, and future experiments. It is not a collection of copyrighted firmware images and it is not a ready-to-flash tune.

## Project goals

1. Preserve OEM safety/fallback behaviour while understanding the ME9.2 control architecture.
2. Build a repeatable symbol/feature map for the `0087180A770B / 1037389760` software family.
3. Explore an additional **E (Efficiency)** drive mode using existing Bosch control primitives where possible.
4. Keep **D** usable as a daily mode and make **S/M** performance-oriented.
5. Optimize cruise efficiency and high-load performance as separate operating regions.
6. Later integrate the ZF 6HP EGS so DME and transmission calibration behave as one powertrain.

## Intended mode concept

| Mode | Firing strategy | Fuel/load strategy | Transmission intent |
|---|---|---|---|
| **E** | 4/8 or 6/8 firing density | efficiency first, experimental mild lean cruise | early upshift, early/controlled TCC lock |
| **E + kickdown** | temporary 8/8 | power override | aggressive downshift, then automatic return to E |
| **D** | 6/8 or 8/8; 4/8 only if proven useful | OEM-like daily behaviour with efficiency improvements | balanced |
| **S** | 8/8 | performance calibration | sport shift programme |
| **M** | 8/8 | performance calibration | manual gear selection retained |

The preferred implementation is **rotating/selective firing density**, not permanently disabling the same four cylinders. The N62 does not have OEM mechanical valve deactivation, so fixed cylinder shutdown would still incur pumping and friction losses.

## Current high-confidence findings

- The 1 MiB external flash reference identifies Bosch HW `0261209002` and SW `1037389760` / software family `0087180A770B`.
- The 560B reference XDF contains `CWEVAB` (injector shutoff codeword) and `REDABM` (injector shutoff pattern for torque reduction).
- The `REDABM` matrix from 560B occurs byte-identically in the 770B reference at external-flash offset `0xC5510`.
- Reduction step 4 uses alternating masks `0x55` and `0xAA`, proving that the Bosch strategy already has a balanced 4-of-8 firing pattern available.
- Bosch ME9.2.1 reference material exposes a kickdown state (`B_kd`) and calibrations for kickdown detection, making an E-mode power override feasible without inventing an arbitrary pedal percentage.
- The reference definitions include generator load-shedding, exhaust-flap control, sport-mode driver wish, cylinder-cut lambda handling, knock adaptation, VANOS/Valvetronic maps, thermal management and torque-model infrastructure.

See [`RESEARCH_STATUS.md`](RESEARCH_STATUS.md) and [`research/verified-findings.md`](research/verified-findings.md) for evidence and confidence levels.

## What is deliberately not stored here

- Full BMW/Bosch firmware images
- EEPROM contents
- VIN/immobilizer-specific data
- Paid/commercial dump archives
- WinOLS project files, DAMOS/A2L files, or third-party copyrighted material unless redistribution rights are explicit

The repository instead records hashes, identifiers, source links, derived research notes and reproducible tools.

## Safety and validation

No experimental calibration should be flashed before:

- an ECU-specific full backup exists;
- the exact HW/SW IDs are confirmed;
- checksum handling is verified;
- a stable programming power supply is used;
- stock recovery is proven;
- changes are tested one subsystem at a time with logging;
- lambda, knock, temperature, misfire and transmission behaviour are monitored.

This project intentionally keeps OEM protection paths as the default fallback.

## Status

**Research / reverse-engineering phase. No public flash-ready calibration yet.**

Last structured update: 2026-10-03.
