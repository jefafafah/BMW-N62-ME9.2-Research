# EGS speed / ratio path in the 770B DME — round 6

Scope: the single signal path CAN 0x1A2 → RAM `0x5B9982` → ratio `0x5B981E` → map CAL `0x1C84B0` →
`0x5B97F0` and every consumer of those three RAM words. Static analysis of SW 1037389760 only (reference
dump hashes as in `tools/me9_image.py`). Addresses: INT = internal-flash CPU, EXT = external-flash CPU,
CAL = calibration alias, RAM = runtime. Checks marked ✔ are re-run by `tools/verify_770b_findings.py`
(round-6 block, 12 checks).

The file name follows the original question (TCC / shift state). The result is that the DME derives
**no** TCC-lock or shift state from this path; see §7.

## 1. CAN reception (0x1A2 → `0x5B9982`)

| Item | Finding | Status |
|---|---|---|
| Message object | handle 0x05, ID 0x1A2, TouCAN A, RX, DLC 2 | CONFIRMED (round 3) |
| Signal | 0x13 = bytes 0-3 field of handle 0x05; INT `0x39530` calls the read API `0x63660(0x13, &tmp)`, low 16 bits used (= bytes 0-1, byte 0 LSB as for 0x0BA) | CONFIRMED ✔ |
| RX indication | INT `0x1D974` (from dispatcher fn INT `0x1FA3C`) sets `0x3FA58C` (new data), `0x3FBED6`, `0x3FBED7` = 1 | CONFIRMED ✔ |
| Decoder | INT fn `0x392C8`, called from task INT `0x3D764` (same task as the consumer fn `0x46348`) | CONFIRMED |
| Scaling in decoder | none: `0x5B9982 = raw` | CONFIRMED ✔ |
| Invalid | raw `0xFFFF` → `0x5B9982 = 0` (INT `0x39564`/`0x39574`) | CONFIRMED ✔ |
| Not enabled | EGS-present flag `0x3FBED1` = 0 → `0x5B9982 = 0`, `0x3FBED6 = 0` | CONFIRMED |
| Timeout | counter `0x3FA589` reset on each new frame; incremented on every decoder call without one; when it is already > 50 (0x32), `0x5B9982 = 0` and `0x3FBED6 = 0`. The last value is **held** for 51 calls, then forced to 0 | CONFIRMED ✔ (call raster of task `0x3D764` not determined) |
| Init | EXT `0xF27610` (init table EXT `0xFBE860`) writes `0x5B9982 = 0` | CONFIRMED |

## 2. Ratio `0x5B981E` (INT `0x46E28…0x46EB0`, fn `0x46348`)

```
num  = (CAL 0x1C8532 & 0x02) ? 0x5B9982 : 0x5B97BA          ; 0x1C8532 = 0x0E -> 0x5B9982
num  = num << 13                                               ; rlwinm 13 (no loss, u16 input)
rpm  = 0x5B9A26                                                ; r25 = &0x5B9A26 for the whole fn
if rpm != 0:  0x5B981E = min(num / rpm, 0xFFFF)                ; divwu, unsigned
else:         0x5B981E = (num != 0) ? 0xFFFF : 0
```

* Exact formula (active calibration): **`0x5B981E = min(⌊(0x5B9982 · 8192) / 0x5B9A26⌋, 0xFFFF)`**. ✔
* Enable conditions: none besides the CAL selector. It is computed on every call of fn `0x46348`. Bit 0x02
  of CAL `0x1C8532` only chooses the numerator. With bit 0x02 clear the DME uses its own substitute
  `0x5B97BA` from INT `0x5F398` (`0x5B9D20 × filtered per-gear byte CAL 0x1C7B0C[gear] × 0x7F >> 12`,
  plus a lead term on falling values). That path is inactive here.
* Behaviour on CAN loss: `0x5B9982 = 0` → `0x5B981E = 0` while the engine runs → the map lookup clamps
  to its first breakpoint (ratio 0.90). See §3 for the effect.
* Scaling: `0x5B9A26` = 0.25 rpm/bit (CONFIRMED round 3). The map axis (§3) is placed symmetrically
  around `0x4000` with breakpoints at exactly 0.90/0.96/0.99/1.00/1.04/1.06 × 0x4000. Reading
  `0x4000` as 1.0 means `0x5B981E = 16384 · n(0x1A2) / n(engine)` with **0x1A2 at 0.125 rpm/bit**.
  Status: **LIKELY**. It is inferred from the axis structure, not from a unit constant in the code.

## 3. Map CAL `0x1C84B0` (6 × 8 u16) and lookup

* Caller: INT `0x46EDC`, in fn `0x46348`, only when CAL `0x1C8532 & 0x04` (set). Otherwise
  `0x5B97F0` = curve CAL `0x1CF804` at the precomputed index `0x5BA09C` (values 0x7FFF/0x8000 at the
  start). It is the only reference to `0x1C84B0`. ✔
* Helper INT `0x17B64`: `r3` = record, `r4` = x input, `r5` = y input. The u16 header is `[nx=6][ny=8]`,
  then x axis, y axis, data. The axis search clamps at both ends (no extrapolation). Interpolation core INT
  `0x192C8`: element offset `xi·ny + yi`, so the data is stored **ratio-major** (8 gear values per ratio
  breakpoint), bilinear, result u16. ✔
* x input = `0x5B981E` (ratio), y input = `0x5B92CA` (current gear: 1…6, 7 = R, 0 = other; round 3). ✔
* Output → `0x5B97F0`.

Values (factor = value / 0x8000):

| gear \ ratio (x/0x4000) | 0.90 | 0.96 | 0.99 | 1.00 | 1.04 | 1.06 |
|---|---|---|---|---|---|---|
| 0 (other) | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |
| 1 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |
| 2 | 0.2 | 0.7 | 1.0 | 1.25 | 1.25 | 1.0 |
| 3 | 0.2 | 0.7 | 1.0 | 1.5 | 1.5 | 1.0 |
| 4 | 0.2 | 0.5 | 1.0 | 1.5 | 1.5 | 1.0 |
| 5 | 0.2 | 0.5 | 1.0 | 1.4 | 1.4 | 1.0 |
| 6 | 0.2 | 0.5 | 1.0 | 1.4 | 1.2 | 1.0 |
| 7 (R) | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |

Raw words: 0x8000, 0x199A, 0x599A, 0x4000, 0xA000, 0xC000, 0xB333, 0x999A. Output scaling
0x8000 = ×1.0 is **CONFIRMED** by the consumer: it is used as the divisor in `(x << 15) / 0x5B97F0`
(§4), so 0x8000 leaves x unchanged.

## 4. Consumers of `0x5B97F0`

| PC | Use | Active in this calibration |
|---|---|---|
| INT `0x46F4C` | `0x5B982A = clamp((0x5B9828 << 15) / 0x5B97F0, 1, 0xFFFF)`, gated by CAL `0x1C8532 & 0x08`; with the bit clear `0x5B982A = 0x5B9828` | **yes** (0x0E has 0x08) ✔ |
| INT `0x475D8` | `0x5B9826 = clamp((0x5B9824 << 15) / 0x5B97F0, 1, 0xFFFF)` (0x5B9824 = map CAL `0x1CF744`), gated by `& 0x10` | no (bit 0x10 clear → `0x5B9826 = 0x5B9824`) ✔ |
| EXT `0xF88874` | same as `0x475D8` in EXT fn `0xF887A0` (pointer table EXT `0xFBF15C`, raster unresolved) | no ✔ |

No other code reads `0x5B97F0` (xref plus a raw scan for the `0x5C`/`-0x6810` pair).

### What `0x5B982A` controls (INT `0x46FAC…0x470C4`)

`0x5B982A` (K) is the step gain of a second-order low-pass on the torque request `0x5B9808`
(= min(driver-request torque `0x5B980A`, maximum available torque `0x5B9854` read through `r19`), written at
INT `0x46828`; the `r19` identity was resolved in the final pass). Helper INT `0x16070` is a saturating
32-bit `state += K · delta`, and INT `0x1DEC4` is `(a·b) >> 16`.

```
w = 0x5B9808, y = 0x5B97F8 (previous output), D = 0x5B97E4
s1 (0x3FB444, 16.16) += K · sat16((w >> 3) − (y >> 3))
s2 (0x3FB448, 16.16) += K · sat16(s1.hi − (((y · D) >> 16) >> 1))
y = s2.hi <= 0 ? 0 : s2.hi < 0x2000 ? s2.hi << 3 : 0xFFFF
reset (flag 0x3FC18A): s1 = ((0x5B97F2·D) >> 16) >> 1, s2 = 0x5B97F2 >> 3
```

The steady state is y = w (unity DC gain). Both integrators scale with K, so the response time scales
with 1/K. ✔ (structure)

* K base `0x5B9828` = CAL `0x1C8944` (0x0A39) with damping CAL `0x1C8536` (0x3334) while `0x3FC18E` is set
  and `0x5B980E` < curve CAL `0x1CF810`. Otherwise K base = `0x3FB458`, D = `0x3FB45A` (EXT `0xF887A0`:
  maps CAL `0x1CF7A4` / `0x1CF41C`; init EXT `0xF2EB38`: 0x0CCD / 0x8000).
* The filtered value `0x5B97F8` is used only while latch `0x3FC18D` is set. The latch sets when
  `(w − y)/2 > 0x5B97EA` (positive step of the request), with enable `0x3FC187` (CAL `0x1C8531`/`0x1C8530`
  bit 2). It clears when `(w − 0x5B9806)/2 < 0x5B97EC` or when the enable is gone.
* Selection at INT `0x476C8…0x47714`: `0x5B9806` := `0x5B97FE` if `0x3FC189`, else `0x5B97F6` (second
  filter, gain `0x5B9826`) if `0x3FC184`, else **`0x5B97F8` if `0x3FC18D`**, else unfiltered `0x5B9808`.
  Then `0x5B97FC = clamp(0x5B9806 + 2·0x5B97F4)`, high byte → `0x5B93DF`. `0x5B97FC` is read by INT
  `0x4533C`, `0x47AB0`, `0x480AC` and the torque-word fn `0x48F68` (source of the 0x0A8/0x0A9 words, round 4).
  ✔ (copy of `0x5B97F8` into `0x5B9806`)

Net effect of the ratio map in gears 2–6 (the only gears where it is not 1.0):

| ratio n(0x1A2)/n(engine) | factor | K | torque-rise shaping |
|---|---|---|---|
| ≤ 0.90 (also CAN invalid/timeout → 0) | 0.2 | ×5 (clamped 0xFFFF) | much faster, i.e. weaker |
| 0.96 | 0.5–0.7 | ×1.4–2 | faster |
| 0.99 and ≥ 1.06 | 1.0 | ×1 | base |
| 1.00 – 1.04 | 1.2–1.5 | ÷1.2–1.5 | slower, i.e. stronger |

Behaviour: **CONFIRMED** (code). Name "tip-in / load-change torque shaping" is **LIKELY**. It is a
positive-step-triggered second-order filter on the requested torque.

## 5. All consumers of the three words

| RAM | Readers | Writers |
|---|---|---|
| `0x5B9982` | INT `0x46E3C` (ratio, active); INT `0x5F6D0` in fn `0x5F52C` (inactive: needs CAL `0x1C7AB4` bit0, value 0x00) ✔ | INT `0x392C8` (4 stores), EXT `0xF27610` (init 0) |
| `0x5B981E` | INT `0x46ED8` (map x input) only | INT `0x46E78/0x46E84/0x46EA0/0x46EB0` |
| `0x5B97F0` | INT `0x46F4C` (active), INT `0x475D8`, EXT `0xF88874` (both inactive) | INT `0x46EE4` (map), `0x46F28` (curve fallback) |

None of the three is sent on CAN, written to a diagnostic or fault path, or compared against a threshold.

Inactive consumer INT `0x5F52C` (for completeness): with CAL `0x1C7AB4` bit0 set it would compute
`0x5B93CD = min(0xFF, speed / (0x5B93C2·5/2))` from `0x5B9982` (bit1 set) or from the model `0x5B97BA`,
look it up in curve CAL `0x1C7AB8` and produce `0x5B97B6`. Only R (gear 7) and the EGS status
`0x3FBEDA` gate it. Not analysed further because it never runs with this calibration.

## 6. Interpretation of 0x1A2 and `0x5B981E`

Code evidence:

1. The DME divides the 0x1A2 value by engine speed and looks the quotient up on **one ratio axis for all
   gears**, with breakpoints only between 0.90 and 1.06 of a centre value. Transmission output speed
   divided by engine speed differs by the gear ratio (several × between 1st and 6th). A common ±6 %
   axis could then cover at most one gear. Output speed is therefore **rejected** on code grounds.
2. The quotient is only weighted in gears 2–6 and not in R/1st/other. That rules out a generic
   gear-ratio plausibility use.
3. With bit 0x02 clear the DME replaces 0x1A2 by its own model `0x5B97BA` built from `0x5B9D20` and a
   per-gear calibration byte. So 0x1A2 is a quantity the DME can approximate from a vehicle-side speed
   per gear, i.e. a speed on the gearbox side of the drivetrain.

| Candidate for 0x1A2 | Verdict |
|---|---|
| transmission input = converter turbine speed | **LIKELY** (best fit; in a converter automatic these are the same shaft) |
| transmission output speed | REJECTED (point 1) |
| another rotational speed | not supported |

`0x5B981E` = turbine-to-engine **speed ratio** (×16384 = 1.0, LIKELY scale). It is the converter speed
ratio ν. Converter slip is `1 − ν`, carried implicitly, not as a separate variable. It is **not** a
gear ratio.

## 7. Thresholds / states derived from the ratio

* No comparison of `0x5B981E` (or `0x5B97F0`) against any constant exists. No flag, counter or
  debounce is derived from it. There is no "ratio ≈ 1", "ratio changing" or "ratio stable" state, and no
  derivative of `0x5B981E` is computed.
* The only "near 1.0" behaviour is continuous, through the map: the strongest filtering is at 1.00–1.04 and
  returns to neutral at 0.99 and 1.06.
* **A TCC lock state cannot be inferred in the DME from this path.** The consumer behaviour (strongest
  torque-rise smoothing when engine and turbine speeds are equal, much weaker smoothing with clear slip)
  is consistent with "stiff driveline when the converter is not slipping". But the code never labels or
  latches a lock condition. Treat any lock interpretation as HYPOTHESIS.

## 8. Unresolved

* Physical unit of 0x1A2 (0.125 rpm/bit is inferred from the axis, LIKELY). Needs a PT-CAN log with the
  converter locked at steady speed: expect raw(0x1A2) ≈ 2 × raw(0x0AA rpm).
* Call raster of task INT `0x3D764`, which sets the 0x1A2 timeout time (51 calls).
* Raster/role of EXT `0xF887A0` (pointer table `0xFBF15C`). It writes the normal K base `0x3FB458` and
  damping `0x3FB45A`.
* Meaning of `0x5B9D20` and the per-gear bytes CAL `0x1C7B0C` used by the inactive model path. The bytes
  (0, 55, 25, 43, 56, 87, 99, 110 for gears 0–7) are not monotonic, so they are not a plain ratio table.
* Physical time constants of the filter (need the raster).
