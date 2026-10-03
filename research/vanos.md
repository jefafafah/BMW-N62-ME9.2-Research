# VANOS (770B) — round 5: control path located

> **Final-pass status:** 0.1 °CA angles (HIGH CONFIDENCE); objects 0/2 = intake, 1/3 = exhaust (HIGH CONFIDENCE); pairs {0,1}/{2,3} = banks (HIGH CONFIDENCE), bank 1 vs 2 open; PWM-table field correction in the PWM section of thermal-management.md. See the *Final static pass* section at the end of this file.


Address kinds: **INT** = internal-flash CPU (= file offset in `mpc555-6.bin`), **EXT** = external-flash
CPU, **CAL** = calibration alias (FILE = CPU − 0x100000), **IO** = MPC555 peripheral, **RAM** = runtime.
Rows marked CONFIRMED are re-checked by `tools/verify_770b_findings.py` (round-5 section, 10 checks).

Naming: the four actuators below behave like the N62 cam phasers (four PWM outputs, a position loop
on camshaft-edge measurements, rpm×load target maps). "VANOS" is therefore **HIGH CONFIDENCE** for
the subsystem. Which object is intake/exhaust and which is bank 1/2 is **not** proven; the objects
are labelled by index and calibration group only.

## 1. Corrections from the start of round 5

| Item | Finding | Status |
|---|---|---|
| EXT `0xF12018` | single argument (0/1): sets/clears bit 16 of RAM `0x3FA43C` and writes 0x4800/0x4000 to IO `0x306086` only. Not a multi-channel duty writer | CONFIRMED |
| EXT `0xF36FE8` (7 calls to `0xF12018`) | test sequence: switch channel, busy-wait ≈ 50 timebase ticks, read pin status of MIOS channel 0x1C via EXT `0xF11FD8` (IO `0x3060E6` bit 15), set fault flags `0x3FBE9B`/`0x3FBE99`. `0x3FBE99` feeds bit 0x100 of the total-cut word `0x5BBBA8` (round 2) | CONFIRMED structure; output-stage test, **REJECTED** as VANOS |
| INT `0xA558` | packs 3–4 boolean flags into fields of output port 9 (field table INT `0x14EF0`) | CONFIRMED; **REJECTED** as PWM |

## 2. PWM output layer — CONFIRMED

| Layer | Address | Content |
|---|---|---|
| Application PWM API | INT `0x671AC` (r3 = logical channel, r4 = duty 0…10000 = 0.01 %, r5 = period factor) | validates duty, applies polarity, dispatches to driver |
| Logical channel table | INT `0x156AC`, 24-byte records, 10 channels | +4 hardware channel, +8 period factor, +0xD driver index, +0x12/+0x13 polarity |
| Driver list | INT `0x1579C` (16-byte records: base IO `0x306000`, init, service) | driver 0: INT `0x13E08`/`0x13E60`; driver 1: INT `0x145B8`/`0x145E4` |
| MIOS PWM register helpers | INT `0x142C8` (pulse), `0x14308` (period+pulse+enable), `0x14340` (enable/polarity), generic set INT `0x148B0` (pulse = period·duty/10000) | IO `0x306000 + 8·n` |

VANOS-candidate channels (all set by INT `0x4FA8C`, period factor 0x28, duty clamped 1…9999):

| Actuator index | PWM logical ch | MIOS hw channel | Table record (INT) | Status |
|---|---|---|---|---|
| 0 | 2 | 0x0C | `0x156DC` | CONFIRMED mapping |
| 1 | 7 | 0x0B | `0x15754` | CONFIRMED mapping |
| 2 | 3 | 0x1E | `0x156F4` | CONFIRMED mapping |
| 3 | 6 | 0x1F | `0x1573C` | CONFIRMED mapping |

EXT `0xFE3D74` drives the same four logical channels to 10000 together (actuator-test/initialisation
path, HYPOTHESIS). The other PWM users are listed in §6.

## 3. Controller structure — CONFIRMED

Main loop INT `0x3FBAC` (one caller of the output routine):

```text
0x5B8D85 = curve CAL 0x1CA890 (x = 0x5B930A)      # duty compensation factor (supply voltage candidate, HYPOTHESIS)
0x5B8D84 = curve CAL 0x1CA880 (x = 0x5B9307)      # engine-temperature factor
for i in 0..3:  obj = INT 0x1BC9C + 0x78·i
    INT 0x3F60C(obj)   fetch latest cam capture (INT 0x4F904 time, 0x4F42C angle); reject angle > 0x1C20 (7200)
    INT 0x3EF24(obj)   write target  *(+0x30)
    INT 0x3F3B8(obj)   write measured position *(+0x2C) from capture data (+0x14)
    if *(+0x44) (mode):  INT 0x3F2E0  velocity estimate *(+0x00), extrapolated position *(+0x38)
                         INT 0x3F848  PI-type loop: error = *(+0x38) − *(+0x30);
                                      gain curves CAL *(+0x6C), *(+0x70) over filtered error *(+0x18);
                                      integrator-like *(+0x40) limited by CAL 0x1D062C/0x1D062A;
                                      hold/base term *(+0x20) limited by CAL 0x1D0636/0x1D0634
    else:               duty = *(+0x48)·100 (fixed duty)
    INT 0x3F0B4(obj, duty)   duty × 0x5B8D85 >> 7, rate limit CAL 0x1D0638 (= 300 → 3 %), enable mask CAL 0x1D0616 (= 0x0F)
                             → INT 0x4FA8C(index, duty) → PWM API
```

### Object table (RAM unless marked CAL)

| Field | obj 0 | obj 1 | obj 2 | obj 3 | Role | Status |
|---|---|---|---|---|---|---|
| +0x74 index | 0 | 1 | 2 | 3 | actuator index | CONFIRMED |
| +0x30 target | `0x5B8DCC` | `0x5B8DA8` | `0x5B8DBA` | `0x5B8D96` | target position | CONFIRMED (written by `0x3EF24`, error operand) |
| +0x2C measured | `0x5B8DCA` | `0x5B8DA6` | `0x5B8DB6` | `0x5B8D92` | measured cam position at last edge | CONFIRMED (written by `0x3F3B8`); read by air-mass model EXT `0xFACD74`, torque fn INT `0x45C3C`, INT `0x41600`, Valvetronic INT `0x4E21C` |
| +0x38 estimated | `0x5B8DC8` | `0x5B8DA4` | `0x5B8DB8` | `0x5B8D94` | extrapolated position | CONFIRMED |
| +0x00 velocity | `0x5B8DD4` | `0x5B8DB0` | `0x5B8DC2` | `0x5B8D9E` | position rate | LIKELY |
| +0x10 duty | `0x5B8DCE` | `0x5B8DAA` | `0x5B8DBC` | `0x5B8D98` | PWM duty (0.01 %) | CONFIRMED |
| +0x44 mode (CAL) | `0x1D0618` | `0x1D0613` | `0x1D0618` | `0x1D0613` | 1 = closed loop, 2 = fixed target | CONFIRMED |
| +0x48 fixed duty (CAL) | `0x1D0619` | `0x1D0614` | `0x1D0619` | `0x1D0614` | open-loop duty /100 | LIKELY |
| +0x4C fixed target (CAL) | `0x1D0628` | `0x1D0622` | `0x1D0628` | `0x1D0622` | target in mode 2 | CONFIRMED |
| +0x6C / +0x70 gain curves (CAL) | `0x1CA986` / `0x1CA944` | `0x1CA902` / `0x1CA8C0` | `0x1CA986` / `0x1CA944` | `0x1CA902` / `0x1CA8C0` | controller gain vs. error | LIKELY |
| +0x08 per-object scalar (CAL) | `0x1D0626` | `0x1D0620` | `0x1D0624` | `0x1D061E` | per-object offset/limit | HYPOTHESIS |

Objects 0 and 2 share every calibration item except +0x08, and so do objects 1 and 3. This is the
signature of **two actuator types × two instances** (consistent with intake/exhaust × bank;
assignment open). CONFIRMED structure.

## 4. Cam position feedback — CONFIRMED chain, hardware link LIKELY

| Index | Angle RAM | Timestamp RAM | Writer (INT) | Called from (INT) |
|---|---|---|---|---|
| 0 | `0x5B9C9A` | `0x5BA058` | `0x2F7AC` | `0x31C4C` |
| 1 | `0x5B9C96` | `0x5BA050` | `0x2FA78` | `0x31CA4` |
| 2 | `0x5B9C98` | `0x5BA054` | `0x2FD44` | `0x31CF8` |
| 3 | `0x5B9C94` | `0x5BA04C` | `0x30010` | `0x31D4C` |

* The angle fetch rejects values > 7200. That fits a 0–720 °CA window in 0.1° units. Scale **HYPOTHESIS**.
* Edge acquisition: four TPU edge objects on **TPU A channels 9, 10, 11, 12**. The table is selected
  by CAL `0x1C6DAA` (stock 4 → INT `0x1AB2C`) with count CAL `0x1C6D98` (= 4), in EXT `0xF2D274`.
  Handlers are INT `0x69CF4` (TPU A) / `0x69C4C` (TPU B) → INT `0x69B20` (CISR test/clear, pin level,
  per-object callbacks). Object state lives at RAM `0x3FC450 + 0x70·i`, the config struct at RAM
  `0x3F9B24`, and edge parameters at CAL `0x1C6D94…0x1C6D97`.
  The link "TPU A ch 9–12 → cam functions INT `0x2F7AC…0x30010`" goes through an application
  callback pointer that is RAM-initialised and not traced. **LIKELY.**

## 5. Targets — CONFIRMED structure, map roles HYPOTHESIS

Target writer INT `0x3EF24`:
* mode 1: target = byte `0x5B911A`·8 (objects 0/2) or `0x5B910F`·8 (objects 1/3). Optional
  low-rpm clamp below rpm byte CAL `0x1D061C` (75) to CAL `0x1CA878[i]` − CAL `0x1D061D`, enabled by
  CAL `0x1D0615` bits (stock 0 = disabled). Both instances of a type share one target, so there is
  no per-bank target.
* mode 2: target = CAL `*(+0x4C)`.

Target composer INT `0x3DA70` (first half → `0x5B911A`, second half → `0x5B910F`; each the clamped
sum of terms around 0x80):

| Map group (CAL) | Geometry | Axes | Feeds | Status |
|---|---|---|---|---|
| `0x1C9E6C`, `0x1CA1CC`, `0x1C9C2C`, `0x1CA2EC`, `0x1C9F8C`, `0x1CA25C`, `0x1C9EFC` | 7 × (12×12 u8, data only) | shared group axes: `0x5BA174` from rpm curve CAL `0x1CA83C` (x = `0x5B9A26`, 2080…24000 → 520…6000 rpm) and `0x5BA178` from curve CAL `0x1CA856` (x = `0x5B9DFE`, 427…3627, load-type variable) | intermediate bytes `0x5B9117`, `0x5B9118`, `0x5B9128`, `0x5B9121`, `0x5B9119`, `0x5B9120`, `0x5B911F` → `0x5B911A` | CONFIRMED lookups; roles (base/warm-up/full-load/idle variants) HYPOTHESIS |
| `0x1C9CBC`, `0x1CA01C`, `0x1C9B9C`, `0x1CA13C`, `0x1C9DDC`, `0x1CA0AC`, `0x1C9D4C` | 7 × (12×12 u8) | same axes | → `0x5B910F` | as above |
| `0x1CA552` / `0x1CA3E4` | 12×5 u16 | x rpm 2200…24000, y 427…1280 | `0x5B9122` (first half) | HYPOTHESIS: full-load/limit term |
| `0x1D0568`, `0x1D04C4` / `0x1D0420`, `0x1D037C` | 8×8 u16, all zero in stock | x `0x5B9C08` 200…1000, y `0x5B9B34` 1792…17920 | `0x5B9DFC`, `0x5B9DFA` / `0x5B9DF8`, `0x5B9DF6` | correction maps, inactive in stock |
| `0x1CA5F0`, `0x1CA658` / `0x1CA482`, `0x1CA4EA` | 16×2 | x rpm 4000…28000, y `0x3FC2E8` (0…30 / 0…255) | blend terms | HYPOTHESIS |
| curves `0x1CA7F8`, `0x1CA7EC`, `0x1CA812` / `0x1CA803`; `0x1CA798`; `0x1CA783` / `0x1CA76D`; maps `0x1CA3B0` / `0x1CA37C` (4×4) | — | engine temperature `0x5B9307`, `0x5B953E`, `0x3FC302` | temperature / warm-up weighting | HYPOTHESIS |

No table is named KFWES*/KFWAS*: the consumer evidence ties these maps to the two VANOS target
bytes, but not to intake vs exhaust.

## 6. Other PWM users (same API, for completeness)

| Logical ch | Writers | Duty source (RAM) | Status |
|---|---|---|---|
| 4 | INT `0x5F2B8`, EXT `0xFB2860` | on/off (0 / 10000) from `0x3FC159`/`0x3FC250`; `0x5B8D4A` | unidentified |
| 5 | EXT `0xF2DA04`, `0xF84070`, `0xFB28B8` | on/off from `0x3FC2AF`, `0x3FC155` | unidentified |
| 8 | EXT `0xF2C9C0`, `0xF823E0` | `0x5B9C12`, `0x5B9052` | unidentified (electric-fan candidate, not verified) |
| 9 | EXT `0xF2D78C`, `0xF578D8`, `0xFB2784` | `0x5B946F` | unidentified |

## 7. Remaining unknowns

* Intake/exhaust and bank assignment of objects 0–3. Live test: command a target change and watch
  which cam sensor moves, or correlate with the Valvetronic/air-model consumers.
* Physical units of target bytes (×8), measured positions and the 7200 limit.
* How `0x3DA70` blends its seven maps per type (condition flags `0x3FC2E8`, `0x5B8D70…0x5B8D7B`).
* The RAM-initialised callback that links TPU A ch 9–12 to INT `0x2F7AC…0x30010`.
* Knock-dependent full-load target corrections: none identified among the maps above.

---

# Final static pass (round 7, 2026-10-03)

This section supersedes conflicting statements earlier in this file. CONFIRMED items are re-checked by `tools/verify_770b_findings.py` (final-pass blocks).

### B. VANOS

#### B1. Units and reference (HIGH CONFIDENCE)

* **Raw edge angle** (`0x5B9C94…0x5B9C9A`, from the angle service INT `0x688B0`):
  * INT `0x3F60C` rejects values > 7200.
  * It subtracts CAL `0x1CA870[i]` (all 0), then reduces modulo **1800** in repeated −0x708 steps, counting the edge index 0..3.
  * Window setup EXT `0xF2D274` uses nominal CAL `0x1C6DA2[i]` ± 10·byte and wraps at 7200.
  * Together these give **0.1 °CA over a 720 °CA cycle, with 4 cam edges 180 °CA apart**. CONFIRMED arithmetic; unit HIGH CONFIDENCE.
* **Measured position** (+0x2C) (INT `0x3F3B8`):
  * delta = reduced angle `0x5B8D86[i]` − learned reference (*(+0x04): `0x3FE2C8`/`C4`/`C6`/`C2`).
  * Even objects: position = CAL `0x1CA878[i]` + delta. Odd objects: position = CAL `0x1CA878[i]` − delta.
  * Clamped to ≤ CAL `0x1CA878[i]` = **1200** (flag bit 2 when clamped).
  * Result: both cam types read **120.0 °CA at the park stop** and **decrease** when the cam moves away from park. This matches BMW "spread" angles (intake/exhaust spread, max at park). CONFIRMED arithmetic.
* **Target**: byte·8 → 0.8 °CA per byte. Map values 75…154 give 60.0…123.2 °CA. Values ≥ 150 lie at or beyond park (saturate), so the all-153/154 maps mean "park". CONFIRMED arithmetic.
* **Default / park request** (INT `0x3DA70`):
  * Both families use the constant 0x384, which gives byte 225 → target 1800 = 180.0 °CA, beyond the 120.0 park clamp, so the actuator is driven to the stop.
  * Taken when: !`0x3FE954` (not running), !`0x3FBFB7` (before start-end), `0x5B8D7A` (coolant ≤ CAL `0x1CA836` = 24 with hysteresis), or the start-delay timer `0x3FB7D8` / `0x3FB7D9` is running (curves CAL `0x1CA7F8` / `0x1CA7EC` of coolant, armed while the measured position is near park).
  * CONFIRMED.
* **Mode 2** (CAL +0x44 = 2): fixed target CAL `0x1D0628` = 1170 (type A) / `0x1D0622` = 1200 (type B). Stock mode = 1 for all objects, so mode 2 is unused.
* **Adjustment ranges in maps**: type A 60.0…123 °CA (≈ 60 °CA authority); type B 68…122 °CA (≈ 52 °CA). This fits published N62 VANOS authorities (each cam roughly 50–60 °CA), but those figures were not checked from code.

#### B2. Intake vs exhaust: **type A (obj 0/2, byte `0x5B911A`) = intake, type B (obj 1/3, byte `0x5B910F`) = exhaust** (HIGH CONFIDENCE)

Independent lines of evidence:
1. **Valvetronic coupling**:
   * INT `0x4E21C` uses only the type-A position: obj0 measured `0x5B8DCA` or target `0x5B8DCC` (CAL `0x1C51B4`), or `0x5B9E02` = type-A map byte·8 (written by INT `0x3DA70` at `0x3E3A8`).
   * It combines that position with lift-dependent terms (`0x5B9BC6` = cam position + 30·curve `0x1C652E`(lift); map `0x1C4DE0`(lift, cam position)).
   * The air model EXT `0xFACD74` forms curve `0x1C36DC`(lift) − type-A position. Type-B positions only enter as CAL `0x1C3752`/`0x1C3754` (1270) − position.
   * Valvetronic acts on the intake valves only, so the cam combined with lift is the intake cam. CONFIRMED code; inference HIGH.
2. **Direction**:
   * Even (type-A) objects can only report edges **earlier** than the learned park edge (delta ≤ 0 under the clamp), which is cam advance.
   * Odd (type-B) objects only report edges **later**, which is cam retard.
   * The plausibility windows mirror this: type A nominal 132.0° with window −80/+20 °CA, type B nominal 72.0° with window −20/+80 °CA (CAL `0x1C6DAB…0x1C6DB2` bytes ×10 → 0.1 °CA). Both windows cover the same absolute span 52.0…152.0 °CA.
   * The N62 intake cam parks retarded and advances; the exhaust cam parks advanced and retards.
   * This assumes the raw angle increases with crank rotation, which is the normal angle-capture convention. HIGH CONFIDENCE.
3. Both the type-A and the type-B max/park reference are 1200, and the residual-gas model sums intake + exhaust spread per bank (B4). This is consistent with the assignment but does not distinguish the two types on its own.

The assignment is not CONFIRMED because no symbol names it. Live confirmation is in B7.

#### B3. Bank pairing: **{obj0, obj1} = one bank, {obj2, obj3} = other bank** (HIGH CONFIDENCE); which is bank 1 is NOT RESOLVED

* EXT `0xFACD74`:
  * `0x5B9B04` = obj0 + obj1 measured; `0x5B9B02` = obj2 + obj3 measured (intake + exhaust spread sum = overlap measure).
  * Each sum is the y-axis (1800…2400) of maps CAL `0x1C3208` / `0x1C304C` (x = Valvetronic lift 250…9600 µm). The outputs feed the per-pair residual/charge terms `0x5B9AE0…0x5B9AEA` (INT `0x4DF50`).
  * Pairing one intake with one exhaust cam is only meaningful within a bank. CONFIRMED arithmetic.
* Hardware layout also groups the pairs: obj0/obj1 → MIOS PWM 0x0C/0x0B (adjacent), obj2/obj3 → 0x1E/0x1F.
* Bank 1 vs bank 2: no static evidence.
  * Both type-A nominals (1320) and both type-B nominals (720) are identical, with no bank offset.
  * The lift input for both pair models is the same bank-1-derived actual (`0x5B9BA2` = `0x5B9B9C`).
  * The cam-capture functions INT `0x2F7AC…0x30010` are symmetric.
  * NOT RESOLVED.

#### B4. Consumers of VANOS positions

| Consumer | Uses | Role |
|---|---|---|
| EXT `0xFACD74` → INT `0x4DF50` | sums obj0+1 / obj2+3; curve(lift) − obj0 / obj2; 1270 − obj1 / obj3 | per-bank residual-gas / volumetric terms (maps `0x1C3208`, `0x1C304C`, curves `0x1C2AC0`, `0x1C2AEA`, `0x1C2B14`, `0x1C2B3E`, `0x1C36DC`) — LIKELY |
| INT `0x4E21C` | obj0 measured/target or type-A byte | Valvetronic lift ↔ intake timing terms (stock correction forced off) |
| INT `0x41600`, `0x45C3C` | obj0 and obj1 measured (one bank pair) | load / torque models (round 5) |
| INT `0x3DA70` | max(obj0, obj2) → `0x5B8D7E`; max(obj1, obj3) → `0x5B8D7C` | near-park detection for the start-delay logic (`0x5B8D76`/`0x5B8D75`: within CAL `0x1CA837` = 30 of park) |
| EXT `0xF95540` / `0xF94FE0` | targets of obj0/2 / obj1/3 | diagnostics per type (LIKELY) |

#### B5. Target composer INT `0x3DA70` — map roles

Inputs:
* weights `0x5B9123…0x5B9126` = byte curves of coolant (EXT `0xF34ABC`: CAL `0x1CA7AC`, `0x1CA7BC`, `0x1CA7CC`, `0x1CA7DC`);
* `0x5B9127` / `0x5B9128` = maps CAL `0x1CA708` / `0x1CA6C0` (coolant × time after start `0x5B953E`);
* family weight `0x5B903C`.

Type A (intake), result `0x5B911A`:

| Term | Formula | Maps (stock content) |
|---|---|---|
| `0x5B911E` | `0x1CA2EC` + (`0x1C9F8C` − `0x1CA2EC`)·`0x5B9126`/256 + corr `0x5B9DFA` | `0x1CA2EC` active 77…150; `0x1C9F8C` active 75…148, but weight curve `0x1CA7DC` = 0 → **only `0x1CA2EC` used**; correction map `0x1D04C4` all 0 |
| `0x5B911D` | `0x1CA25C` + (`0x1C9EFC` − `0x1CA25C`)·`0x5B9125`/256 | `0x1CA25C` active 104…154; `0x1C9EFC` = 154 (park); weight `0x1CA7CC`: 255 at coolant byte 40 → 0 at ≥ 111 → **cold: towards park, warm: `0x1CA25C`** |
| `0x5B911B` | filt(`0x1C9E6C` + (`0x1CA1CC` − `0x1C9E6C`)·`0x5B9127`) + (`0x1C9C2C` − filt)·`0x5B9128` | all three ≈ park (153; `0x1CA1CC` 131 in the low-load row) → post-start / idle family, practically park |
| `0x5B911C` | map `0x1CA552`(rpm, load `0x5B9DFE`) 12×5 + temperature term (group curve CAL `0x1CA812`) + corr `0x5B9DFC` | idle / low-load alternative |
| final | if `0x5B8F26`: `0x1CA5F0` + (`0x1CA658` − `0x1CA5F0`)·`0x5B903C`/255 (16×2, rpm × `0x3FC2E8`) | **full-load maps** |
| | elif `0x3FC18B`: `0x5B911C` + (`0x5B911B` − `0x5B911C`)·`0x5B903C`/255 (+ rpm curve `0x1CA782` if `0x5B8D71`) | idle/mode family |
| | else: `0x5B911E` + (`0x5B911D` − `0x5B911E`)·`0x5B903C`/255 | **normal part load** |
| | then override map `0x1CA3B0`(rpm, `0x3FC302`) when `0x5B8D72` (`0x3FC2E8` ≥ CAL `0x1CA83A` and rpm byte < CAL `0x1CA831`); filter `0x3FB7DC` (CAL `0x1CA832` = 255); fixed CAL `0x1CA824` (150) if CAL `0x1CA830`; CAL `0x1CA82E` (150) if `0x5B8871`; lower bound `0x5B9E04` (0 in stock); + (`0x5B9912` − 0x80) when `0x3FC125` && !`0x5B888B` && `0x3FC18B` | |

Type B (exhaust), result `0x5B910F`: the same structure.
* Maps `0x1CA3E4` (12×5), `0x1C9CBC`/`0x1CA01C` (park), `0x1C9B9C` (park), `0x1CA13C` (active 102…153), `0x1C9DDC` (active 85…153).
* `0x1CA0AC`/`0x1C9D4C` (park), weights `0x5B9123`/`0x5B9124`, full-load maps `0x1CA482`/`0x1CA4EA`, override `0x1CA37C`, offset `0x5B9910`.

Role summary:
* **Normal**: A `0x1CA2EC` ↔ `0x1CA25C`, B `0x1C9DDC` ↔ `0x1CA13C` (pairs blended by `0x5B903C`).
* **Warm-up**: the coolant weight moves the second map of each pair to park.
* **Full load**: `0x1CA5F0`/`0x1CA658` and `0x1CA482`/`0x1CA4EA`.
* **Idle / mode `0x3FC18B`**: `0x1CA552` / `0x1CA3E4` and the park-like post-start maps.
* **Cold / start**: forced park.
* **Catalyst heating**: no dedicated map is identifiable. `0x1CA3B0`/`0x1CA37C` (rpm × `0x3FC302`) are an override candidate (HYPOTHESIS).
* Status: structure CONFIRMED; roles LIKELY. The name of `0x5B903C` is open.

#### B6. Limp-home / fallback

* Park request (0x384 → beyond stop) as listed in B1.
* PWM enable mask CAL `0x1D0616` = 0x0F (all four enabled).
* Optional low-rpm clamp (CAL `0x1D0615` = 0, disabled).
* Fixed-duty mode 2 is unused.
* No fault-specific target other than park was found in INT `0x3EF24` / `0x3F0B4`. The fault-to-park path (if any) goes through the default-request conditions or through the output stage. NOT COMPLETED (diagnosis fns EXT `0xF95540` / `0xF94FE0` not read).

#### B7. Live validation (read-only; no actuation, no connector pulling)

Log at ≥ 50 Hz through the existing diagnostic RAM read: rpm `0x5B9A26`, targets `0x5B8DCC` / `0x5B8DA8` / `0x5B8DBA` / `0x5B8D96`, measured `0x5B8DCA` / `0x5B8DA6` / `0x5B8DB6` / `0x5B8D92`, raw edges `0x5B9C9A` / `0x5B9C96` / `0x5B9C98` / `0x5B9C94`, target bytes `0x5B911A` / `0x5B910F`, Valvetronic `0x5B9BB6` / `0x5B9D16` / `0x5B9D14`, λ `0x5B9708` / `0x5B970A`.

1. **Intake / exhaust**. Manoeuvre: warm engine, idle → steady 2000 rpm at light load (≈ 20 % pedal), then back.
   * Expected for type A (obj 0/2): target byte drops from ~113–154 to ~75–100 (spread ≈ 60–80 °CA). The raw edge angle `0x5B9C9A`/`0x5B9C98` moves **earlier** (decreases mod 180) by the same amount, i.e. intake advance.
   * Expected for type B (obj 1/3): byte ~85–138, and the raw edge moves **later**.
   * With a passive scope on a cam-sensor signal against the crank signal, the intake sensor's edge must move earlier relative to the crank when the type-A value falls.
2. **Bank 1 vs bank 2** (two read-only options):
   * (a) Read the BMW tester's bank-labelled live values (e.g. "intake camshaft bank 1 actual") together with the RAM values in the same session, and match by value. Choose a transient where the values differ (start, park release).
   * (b) Probe passively (high-impedance scope) the bank-1 intake cam sensor (cyl 1–4 side), and correlate its edge timing with the `0x5B9C9A` vs `0x5B9C98` changes and with the moment of park release after start (`0x3FB7D8` expiry).
   * A wiring diagram tracing the DME pins for MIOS 0x0B/0x0C vs 0x1E/0x1F to the bank-1 solenoids answers the question statically.
3. **Scale**: at hot idle, park state → measured = 1200 (120.0 °CA). The tester's spread value should read about 120° for both cams at park, and in-range values should track measured/10.

---------------------------------------------------------------------------------------------------

### Unresolved / next evidence

* Bank 1 vs 2 for VANOS pairs: tester correlation or wiring (B7).
* Writers of `0x5B903C`, `0x3FC1BD`, `0x3FC1C2`, `0x5B9DB8` / `0x5B9DBA` (pointer-indirect or diagnostic). A pointer-tracking pass over INT `0x406B0` / `0x41600` and the diagnostic job table would resolve them.
* Throttle actuator path and its coupling to Valvetronic fault modes.
* Learning path into `0x3FE17A[]` (balance table) inside EXT `0xF410DC`.
* Calling context of EXT `0xFB50E4` (stop/after-run override).
* VANOS +0x08 per-object scalar (1270 type A / 710 type B): not used in INT `0x3EF24…0x3FBAC`, so another reader holds it.
