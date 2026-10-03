# Ignition, VANOS and Valvetronic (770B) — round 2 status

Address conventions as in `research/aevab-redabm.md`. This area got the least time in round 2.
Everything below is a candidate unless stated otherwise.

## 1. Ignition

| Item | Evidence | Status |
|---|---|---|
| INT fn `0x49600` | largest consumer of byte maps on rpm×load axes; 14 tables incl. three 24×16 maps | LIKELY = ignition-angle calculation |
| `0x1CAD5A`, `0x1CAF04`, `0x1CB186` (24×16, signed byte) | x = rpm byte 10…163 (×40 rpm), y = load byte 14…134 (×0.75 % → 10…100 %). Values rise with rpm and fall with load: typical spark advance (0.75 °/bit gives ≈ −15…+51 °) | LIKELY ignition maps. Which one is basic/optimal/alternate (KFZW/KFZW2/KFZWOP) is HYPOTHESIS |
| `0x1CB134`, `0x1CB330` (8×8), `0x1CB0AE` (12×5), `0x1CB0FD` (8×5), `0x1CACAC/0x1CAD28` (6×6) | same function | corrections; roles open |
| INT fn `0x4A014` with `0x1CB8AC`, `0x1CB98A`, `0x1CBA68` (16×12 signed byte, −29…+11) | writes `0x3FC2F9`, which scales the torque used by the AEVAB decision | HYPOTHESIS: ignition-efficiency / torque-model delta maps |

## 2. Efficiency vs. protection

Not separated yet. Working rule for the next round: tables feeding the torque model (`0x4A014`,
KFMIOP/KFZWOP-type) are efficiency/model maps. Knock, component-protection and catalyst-protection
paths add retard or enrichment and must stay OEM.

## 3. Knock adaptation / fuel quality (95 RON vs better)

Not located. Approach: knock detection uses the TPU/QADC window signals. Search for per-cylinder
8-element arrays in RAM that are both decremented (retard) and slowly incremented (recovery), plus
an adaptive learned value stored to EEPROM (EEPROM content is not analysed here and must not be
committed).

## 4. VANOS / Valvetronic

Not located. The 725D A2L addresses for `KFWESOPU/KFWASOPU/KFWESVL/KFWASVL` (ME9.2.1, a different
CPU address space) cannot be applied to 770B. Candidates to check: 16×24 u16 map `0x1C21AC` (x =
rpm×4 2200…24800, y = 200…8200, used at INT `0x40A64`/`0x54EFC`), and the 21×6 maps `0x1C2500`/`0x1C2636`
in the same function `0x409xx`.

Status of all section-4 items: **HYPOTHESIS**.
