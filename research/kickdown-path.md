# Kickdown (B_kd) propagation (770B) — round 3

Address kinds as in `can-and-drive-modes.md`.

## 1. Detection (round 2, unchanged) — CONFIRMED

INT fn `0x3B80C` (called from INT `0x3D764`) writes `B_kd` = RAM `0x3FBFB3`. It requires pedal
`0x5B96D8` ≥ WPKDMN `0x1C1E4C` (= 0xFFFF) plus pedal-pot voltage `0x5B96D0` hysteresis between
4·`0x1C1E4B` (off) and 4·`0x1C1E4A` (on).

## 2. All consumers — CONFIRMED (complete for direct addressing)

`tools/me9_callgraph.py consumers 0x3FBFB3` finds exactly three functions:

| Function | Access | Role |
|---|---|---|
| INT `0x3B80C` | W | detection |
| EXT `0xF1BCC8` | R | diagnostic data-identifier handler (case values `0x400B`, `0x400C`, … pack status bits into a response buffer) — **no control effect** |
| EXT `0xFA8E70` (called from INT `0x5FDC0`) | R | pedal-status coder for CAN |

## 3. Path to the EGS — CONFIRMED

```text
B_kd 0x3FBFB3 ──► EXT 0xFA8E70: pedal/kickdown state 0x5B902B
                    if B_kd                      → 0x0B   (both branches, 0xFA9070 / 0xFA9104)
                    elif 0x3FBFAB (…)            → 0x0A
                    elif pedal 0x5B96D8 == 0     → 0x00 / 0x08
                    else                         → 0x01 / 0x09   (branch on 0x3FBEC4 / 0x3F9819)
               ──► INT 0x4B128 (TX builder): 0x0AA byte 6 bits 4-7 = 0x5B902B low nibble   (signal 0x33)
                                             0x0AA byte 0 checksum includes 0x5B902B·16
```

The same builder fills 0x0AA byte 3 with the pedal byte `0x5B92C9`. That byte is (pedal>>8) clamped
1…254, or the cruise-equivalent pedal `0x5B9822`>>8 when the state code < 8. Bytes 4-5 carry engine
speed `0x5B9A26` (0.25 rpm/bit; 0xFFFF when `0x3FBF00` = 0).

## 4. Effects inside the DME

* **Driver wish / max torque:** no direct use of B_kd. KFPED is already at its top row at 100 %
  pedal, and no kickdown-specific map or limit raise was found. Status: LIKELY (no consumer).
* **AEVAB / interventions:** none.
* **Gear/downshift:** only via the CAN state code above. The EGS performs the downshift.

## 5. Supporting an "E + kickdown → 8/8" override (analysis only)

Least-invasive signal options, ranked:

1. **Read `B_kd` (`0x3FBFB3`) directly** in a future efficiency controller: it has a single writer,
   is already debounced by voltage hysteresis, and is independent of EGS state. Cost: one read.
2. Read `0x5B902B == 0x0B`: equivalent, but couples to the CAN coder.
3. A softer "power request" earlier than the detent would need a new threshold. Changing WPKDMN would
   also change what the EGS receives as kickdown, so it is **not recommended**.

The return to E after release should use its own hysteresis/timer in the new controller, because
B_kd clears immediately when the voltage drops below the off threshold.
