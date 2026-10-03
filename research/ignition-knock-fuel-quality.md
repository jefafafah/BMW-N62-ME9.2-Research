# Ignition, knock and fuel quality (770B) — round 4

Address kinds: INT = internal-flash CPU, EXT = external-flash CPU, CAL = calibration alias, RAM = runtime.

## 1. Ignition path — candidates (from round 2, extended)

| Item | Address | Evidence | Status |
|---|---|---|---|
| Ignition-angle function | INT `0x49600` | uses three 24×16 signed-byte maps on rpm/40 × load×0.75 axes, plus 8×8/12×5/8×5/6×6 corrections; writes `0x5B9451…0x5B9457` | LIKELY |
| Base/alternate/optimal maps | CAL `0x1CAD5A`, `0x1CAF04`, `0x1CB186` | values rise with rpm and fall with load (spark-advance shape) | LIKELY maps, roles HYPOTHESIS |
| Torque-model ignition efficiency | INT `0x4A014`, CAL `0x1CB8AC`/`0x1CB98A`/`0x1CBA68` (16×12 s8) | writes `0x3FC2F9`, which scales the "torque without cut" used by AEVAB (`0x5B985C`, also sent on 0x0A9) | LIKELY torque-model part |

## 2. Knock control and adaptation — not located

* No per-cylinder knock-retard array was identified this round. The only 8-byte per-cylinder array
  found (`0x5B9467…0x5B946E`, EXT `0xF986FC`) is fed by catalyst-diagnosis variables. REJECTED as knock.
* Method for round 5: find the knock-sensor acquisition (QADC A/B fast conversions in a crank-angle
  window, TPU-scheduled). Follow the per-cylinder integrator values into a comparator with a
  reference level. The retard array is the object that is decremented quickly and recovered slowly;
  its long-term part is stored in EEPROM-backed RAM.

## 3. Fuel-quality question (95 RON baseline with automatic gain on better fuel)

* No fuel-quality detector or octane switch was found.
* Whether the stock knock control has a **long-term adaptive** component that would retain more
  advance on 98 RON cannot be answered until the knock adaptation is located. Status: open.
* Working rule (unchanged): calibrate hard limits for 95 RON and rely only on mechanisms that are
  proven to exist.
