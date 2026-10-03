# Verified findings

## Reference inputs

The research session used three provided DME dump components and a public BMW-XDFs archive. Full proprietary/vehicle-specific inputs are not stored in this repository.

### Provided dump component hashes

| Component | Size | SHA-256 |
|---|---:|---|
| external flash (`28f200f3t.bin`) | 1,048,576 | `bcdac7a0f4c0169cb6aa2984bb156e66a2ac96033f28bd6dd993bbab15b1f661` |
| MPC555 read (`mpc555-6.bin`) | 462,848 | `bcd64e2e975e4d2b5a26c0e93f52cf60ab9af5898337ad851ebaade3e3a987c1` |
| EEPROM (`eeprom.bin`) | 4,096 | `0c7891ea01dd2007ef7319509f8b1571ea89b28ed561ca43dd849ba2bbf60ccd` |

**The EEPROM must not be published.** Its hash is included only so future work can identify the exact research input without redistributing it.

### Third-party reference hashes

| Reference | SHA-256 |
|---|---|
| `WinOLS (BMW E60-E61 (Original) - 7180A560B).bin` | `54404c7da32997344f77dcdd5b5c00190e533102f5e12ce0a174009fd208998d` |
| `WinOLS (BMW E60-E61 (Original) - 7180A560B).xdf` | `4c11a0a52121810807d2ab408707ceb2b9c66ee566ad8c35d26b58aef3948291` |
| `725D601B.a2l` | `4213d242912491e9b9585887b4b87a6b6129d1757c54033c11a6e2c27a0137f7` |

## REDABM port

560B XDF:

- symbol: `REDABM`
- description: injector shutoff pattern for torque reduction
- 560B file offset: `0x54A0`

770B external flash:

- byte-identical 64-byte matrix at offset `0xC5510`

Matrix:

```text
01 11 15 55 57 77 7F FF
02 22 2A AA AB BB BF FF
04 44 54 55 57 77 7F FF
08 88 A8 AA BA BB FB FF
10 11 51 55 75 77 F7 FF
20 22 A2 AA EA EE EF FF
40 44 45 55 D5 DD BF FF
80 88 8A AA AB BB BF FF
```

The fourth reduction column yields alternating `0x55` / `0xAA`, a balanced four-of-eight mask.

## 560B CWEVAB

The XDF defines `CWEVAB` at file offset `0xD8B4` as an 8-bit injector shutoff codeword.

Local 560B -> 770B alignment around this region contains multiple strong blocks, but small insert/delete changes occur around the candidate location. `~0xCD9CA` remains a **LIKELY** candidate and is not yet classified as confirmed.
