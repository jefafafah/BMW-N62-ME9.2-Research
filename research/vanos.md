# VANOS (770B) — round 4 status: not located

Address kinds: INT = internal-flash CPU, CAL = calibration alias, RAM = runtime.

## What was checked

| Approach | Result | Status |
|---|---|---|
| Round-2 candidate fn INT `0x406B0` with CAL `0x1C21AC` (16×24), `0x1C2500`/`0x1C2636` (21×6) | its inputs are air-mass flow `0x3FC2FC` and engine speed, and its outputs `0x5B9AC2…0x5B9AD8` feed the load/air-charge model | **REJECTED** as VANOS; LIKELY air-charge model |
| Digital output stage INT `0x38A54` (`0xAC00` channels 2–24, 38–41) | on/off outputs only; none follows a cam-angle variable | VANOS is not on these channels |
| INT `0x388B0` / `0xAB88` (channels 0–11) | digital **inputs**, not outputs | REJECTED as PWM outputs |

## Candidate map table

No map can yet be tied to an intake/exhaust cam target with consumer evidence, so the table is
empty by design. The 725D A2L names (KFWESOPU, KFWASOPU, KFWESVL, KFWASVL) have no 770B equivalent
established. Do not apply the 725D addresses.

## Next step (round 5)

VANOS solenoids are PWM-driven. Find the TPU3 (`0x304000` / `0x304400`) or MIOS (`0x306000`) channel
parameter writes with a duty-cycle value. Trace that value back to a PID whose setpoint comes from
an rpm×load map. Then find the cam-position measurement (TPU capture of the cam sensors) as the
actual-angle feedback.
