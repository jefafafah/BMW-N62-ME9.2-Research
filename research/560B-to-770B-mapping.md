# 560B → 770B symbol mapping — method and round-2 results

> **Final-pass status:** round-2 port table. Several 'not located' symbols were found later: IMLEVABS → CAL `0x1C99C2` (round 4), KFLAMFA candidate → CAL `0x1CE1BC` (final pass, neutral in stock), TGENOFVL → CAL `0x1C9412` (round 4). Current status per symbol: `symbol-map-770B.csv`.


## 1. Inputs and a limitation of this round

* 770B: local dumps (hashes in `verified-findings.md`), analysed in CPU address space with
  `tools/me9_image.py`.
* 560B: only the symbol list already recorded in `research/reference-symbols.csv` (name, 560B offset,
  description). The 560B binary/XDF and the 725D A2L were **not** re-opened in this round, so no new
  byte-signature matching against 560B was possible. All mappings below come from 770B code
  semantics, table geometry and ordering, checked against the recorded 560B offsets.
* Re-running `tools/find_signature.py` / `tools/local_alignment.py` against a locally supplied 560B
  bin is the first step of round 3.

## 2. Address model

* 560B XDF offsets are offsets into its calibration image. For REDABM (560B `0x54A0`), the 770B
  bytes sit at ext file `0xC5510` = calibration offset `0x5510` = CPU `0x1C5510`.
* So the 770B CPU address = `0x1C0000 + 560B offset + local delta`. **One global delta is REJECTED.**
  Measured deltas run from −0x84 to +0x118 and change with position:

| 560B offset | Symbol | 770B CPU | local delta | Evidence type | Confidence (name) |
|---|---|---|---|---|---|
| `0x1ECE` | UPWGKDO | `0x1C1E4A` | **−0x84** | kickdown code semantics + identical byte/byte/word order | HIGH CONFIDENCE |
| `0x1ECF` | UPWGKDU | `0x1C1E4B` | −0x84 | same | HIGH CONFIDENCE |
| `0x1ED0` | WPKDMN | `0x1C1E4C` | −0x84 | same | HIGH CONFIDENCE |
| `0x54A0` | REDABM | `0x1C5510` | +0x70 | byte-identical 64 bytes + code xref | CONFIRMED |
| `0x6349` | LASOABML | `0x1C6408` (record) | +0xBF | function (cut-lambda setpoint); shape disagreement noted | LIKELY |
| `0x8506` | KFMIMR | `0x1C85FA` (record) | +0xF4 | record order/size identical to 560B | LIKELY |
| `0x85F6` | KFMRMI | `0x1C86EA` (record) | +0xF4 | same | LIKELY |
| `0x86E6` | KFPED | `0x1C87DA` (record) | +0xF4 | same + pedal×rpm lookup semantics | HIGH CONFIDENCE |
| `0x8902` | MDHYEZ | `0x1C8A1A` | +0x118 | hysteresis use in cylinder-blanking decision | HIGH CONFIDENCE |
| `0xD8B4` | CWEVAB | `0x1CD9CA` | +0x116 | static mask OR-ed into injector-cut mask; round-1 alignment candidate | HIGH CONFIDENCE (function CONFIRMED) |

The deltas grow monotonically from `0x54A0` to `0x8902`, which is consistent with small insertions.
They are **not** monotonic across the whole image: −0x84 at `0x1ECE`, and `0xD8B4` (+0x116) is
smaller than `0x8902` (+0x118). So every new symbol needs its own evidence. A delta model only
narrows the search window.

## 3. Not located / rejected in round 2

| 560B offset | Symbol | Result |
|---|---|---|
| `0x92FA` | TGENOFVL | window `0x1C9410–0x1C9420` checked; `0x1C941A` is a speed/temperature-like threshold, not a time → **REJECTED** candidate; not located |
| `0x98AA` | IMLEVABS | not located (expected ≈ `0x1C99C0`) |
| `0x12C5` | KFDLASO | not located (negative-delta region) |
| `0xE0AE` | KFLAMFA | not located (expected ≈ `0x1CE1C0`) |
| `0xD2827` | CWAKR | 560B offset inconsistent with a calibration-image offset; 770B function found at `0x1D07E8` (LIKELY) by semantics only |
| `0x10655` | KFAKR_GANG | same inconsistency; 770B map found at `0x1D077C` (LIKELY) by semantics only |
| 725D A2L addresses (`0xFCxxxx/0xFDxxxx`) | KFPEDS, BRABEVI2, KFZWOP, KFWES*, … | ME9.2.1 uses a different layout; these addresses are **not** valid in 770B (REJECTED as direct addresses) |

## 4. Recommended workflow (round 3)

1. Place the 560B bin + XDF locally (outside the repo). For each XDF symbol, compute the window
   `0x1C0000 + off + [−0x100, +0x180]`.
2. For tables: match by record geometry (nx, ny, element width) and axis values with
   `tools/me9_tables.py` (CSV) inside the window. Then confirm the consuming function's inputs.
3. For scalars: confirm with `tools/me9_xref.py refs`. Require a code use that matches the XDF
   description before going above LIKELY.
4. Record every result in `research/symbol-map-770B.csv` with both name and function confidence.
