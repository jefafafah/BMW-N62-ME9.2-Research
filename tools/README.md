# Research tools

These scripts operate on **user-supplied local binaries**. They do not download or redistribute firmware.

- `hash_inputs.py` — reproducible SHA-256 identification.
- `redabm_decode.py` — decode an 8x8 REDABM block.
- `find_signature.py` — find exact reference signatures in another binary.
- `local_alignment.py` — compare two local regions when the build has insert/delete shifts.

Round 2 (ME9.2 770B, CPU address space; needs Python ≥ 3.9, `capstone` only for disassembly listings):

- `me9_image.py` — loads `mpc555-6.bin` + `28f200f3t.bin` into the CPU map (internal flash at 0, external flash at `0xF00000`, calibration alias `0x1C0000` = ext file `CPU − 0x100000`); `addr`, `dis`, `hash`.
- `me9_xref.py` — register-tracking xref builder (`build`, `refs`, `callers`, `func`, `dis`). Its cache is written to `~/.cache/me9_770b_xref.pkl`, outside the repo, and holds addresses only.
- `me9_tables.py` — catalogues curve/map records from lookup-helper call sites and writes CSV with geometry and axis ranges only, never table values.
- `verify_770b_findings.py` — re-checks every round-2 CONFIRMED claim against local dumps at operand level (no firmware bytes embedded); exits non-zero on failure.

Round 3:

- `me9_can.py` — dumps the CAN message-object table (ID, direction, controller, DLC) and the signal table; `--users` lists the functions reading/writing each signal.
- `me9_callgraph.py` — `callees`/`callers` trees and `consumers <RAM address>` (functions touching an address, with their callers).

Round 4:

- `me9_trace.py` — `outputs` (digital output-stage channels with command bytes; marks the INT `0xAB88` channels as inputs) and `lookups <fn>` (each curve/map lookup in a function with the RAM loads/stores around it).

Images are passed as `--int/--ext` or via `ME9_INT`/`ME9_EXT`, e.g.

```sh
export ME9_INT=/path/outside/repo/mpc555-6.bin ME9_EXT=/path/outside/repo/28f200f3t.bin
python tools/verify_770b_findings.py
python tools/me9_xref.py build && python tools/me9_xref.py refs 0x5B92EA
python tools/me9_tables.py > /tmp/770b-tables.csv
```

Future tools should keep the same rule: accept firmware as an input path, emit derived metadata, and never embed proprietary firmware in the repository.
