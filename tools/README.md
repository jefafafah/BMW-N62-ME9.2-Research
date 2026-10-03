# Research tools

These scripts operate on **user-supplied local binaries**. They do not download or redistribute firmware.

- `hash_inputs.py` — reproducible SHA-256 identification.
- `redabm_decode.py` — decode an 8x8 REDABM block.
- `find_signature.py` — find exact reference signatures in another binary.
- `local_alignment.py` — compare two local regions when the build has insert/delete shifts.

Future tools should keep the same rule: accept firmware as an input path, emit derived metadata, and never embed proprietary firmware in the repository.
