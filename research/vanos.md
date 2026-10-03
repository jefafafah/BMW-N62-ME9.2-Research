# VANOS (770B) — round 5: control path located

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
