#!/usr/bin/env python3
"""Load a user-supplied ME9.2 (770B family) dump into the CPU address space.

The images are never copied into the repository. Pass them on the command line
or via the environment variables ME9_INT (MPC555 internal flash read, e.g.
``mpc555-6.bin``) and ME9_EXT (1 MiB external flash read, e.g. ``28f200f3t.bin``).

Address model (see research/verified-findings.md, section "Memory architecture"):

    CPU 0x000000-0x070FFF  internal flash read (file offset == CPU address)
    CPU 0xF00000-0xFFFFFF  external flash, file offset = CPU - 0xF00000
    CPU 0x1C0000-0x1DFFFF  calibration alias used by code, file offset = CPU - 0x100000
                           (i.e. same bytes as CPU 0xFC0000-0xFDFFFF)
    CPU 0x3F9800-0x3FFFFF  MPC555 internal SRAM (not in the dump)
    CPU 0x5B8000-0x5BFFFF  external RAM (observed accesses 0x5B7FFC..0x5C0000, not in the dump)
    CPU 0x2FC000-0x307FFF  MPC555 USIU / IMB3 peripherals

Example:
    python tools/me9_image.py --int mpc555-6.bin --ext 28f200f3t.bin addr 0x1C5510
"""
from __future__ import annotations

import argparse
import hashlib
import os
import struct
from pathlib import Path

EXT_BASE = 0xF00000
CAL_ALIAS_BASE = 0x1C0000
CAL_ALIAS_END = 0x1E0000
CAL_ALIAS_TO_FILE = 0x100000  # file offset = alias address - 0x100000
R2_BASE = 0x1C7FF0   # application small-data-2 base (calibration), set at INT 0x1C830 / EXT 0xF04234
R13_BASE = 0x401A20  # application small-data base (internal SRAM), set at INT 0x1C828 / EXT 0xF0422C

REFERENCE_SHA256 = {
    "int": "bcd64e2e975e4d2b5a26c0e93f52cf60ab9af5898337ad851ebaade3e3a987c1",
    "ext": "bcdac7a0f4c0169cb6aa2984bb156e66a2ac96033f28bd6dd993bbab15b1f661",
}


def region(addr: int) -> str | None:
    if CAL_ALIAS_BASE <= addr < CAL_ALIAS_END:
        return "CAL"
    if 0x3F9800 <= addr < 0x400000:
        return "IRAM"
    if 0x5B0000 <= addr < 0x5D0000:
        return "XRAM"
    if 0x2F0000 <= addr < 0x310000:
        return "IO"
    if 0 <= addr < 0x71000:
        return "INT"
    if EXT_BASE <= addr < 0x1000000:
        return "EXT"
    return None


class Image:
    def __init__(self, int_path: str | os.PathLike, ext_path: str | os.PathLike):
        self.int_path = Path(int_path)
        self.ext_path = Path(ext_path)
        self.int = self.int_path.read_bytes()
        self.ext = self.ext_path.read_bytes()

    @classmethod
    def from_args(cls, args) -> "Image":
        ip = getattr(args, "int", None) or os.environ.get("ME9_INT")
        ep = getattr(args, "ext", None) or os.environ.get("ME9_EXT")
        if not ip or not ep:
            raise SystemExit("need --int/--ext or ME9_INT/ME9_EXT pointing at local dumps")
        return cls(ip, ep)

    def hashes(self) -> dict[str, str]:
        return {"int": hashlib.sha256(self.int).hexdigest(), "ext": hashlib.sha256(self.ext).hexdigest()}

    def is_reference(self) -> bool:
        return self.hashes() == REFERENCE_SHA256

    def segments(self):
        yield 0, self.int
        yield EXT_BASE, self.ext

    def file_location(self, addr: int) -> tuple[str, int] | None:
        """Translate a CPU address into (image, file offset)."""
        if 0 <= addr < len(self.int):
            return "int", addr
        if EXT_BASE <= addr < EXT_BASE + len(self.ext):
            return "ext", addr - EXT_BASE
        if CAL_ALIAS_BASE <= addr < CAL_ALIAS_END:
            return "ext", addr - CAL_ALIAS_TO_FILE
        return None

    def read(self, addr: int, n: int) -> bytes | None:
        loc = self.file_location(addr)
        if loc is None:
            return None
        img = self.int if loc[0] == "int" else self.ext
        b = img[loc[1]:loc[1] + n]
        return b if len(b) == n else None

    def u8(self, a: int) -> int:
        return self.read(a, 1)[0]

    def u16(self, a: int) -> int:
        return struct.unpack(">H", self.read(a, 2))[0]

    def s16(self, a: int) -> int:
        return struct.unpack(">h", self.read(a, 2))[0]

    def u32(self, a: int) -> int:
        return struct.unpack(">I", self.read(a, 4))[0]


def disassemble(img: Image, addr: int, count: int) -> list[str]:
    """Plain disassembly listing (requires the `capstone` package)."""
    import capstone  # type: ignore

    md = capstone.Cs(capstone.CS_ARCH_PPC, capstone.CS_MODE_32 | capstone.CS_MODE_BIG_ENDIAN)
    out = []
    for i in range(count):
        a = addr + 4 * i
        w = img.read(a, 4)
        if w is None:
            break
        ins = list(md.disasm(w, a))
        text = f"{ins[0].mnemonic} {ins[0].op_str}" if ins else ".word"
        out.append(f"{a:08X}: {w.hex()}  {text}")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--int", help="MPC555 internal flash read")
    ap.add_argument("--ext", help="1 MiB external flash read")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("addr", help="translate a CPU address to file offset")
    p.add_argument("address")
    p = sub.add_parser("dis", help="disassemble N instructions at a CPU address")
    p.add_argument("address")
    p.add_argument("count", nargs="?", default="16")
    sub.add_parser("hash", help="print SHA-256 and compare with the reference dump")
    args = ap.parse_args()
    img = Image.from_args(args)
    if args.cmd == "addr":
        a = int(args.address, 0)
        loc = img.file_location(a)
        print(f"cpu=0x{a:06X} region={region(a)} file={loc[0]}+0x{loc[1]:X}" if loc else f"cpu=0x{a:06X} region={region(a)} (not in dump)")
    elif args.cmd == "dis":
        print("\n".join(disassemble(img, int(args.address, 0), int(args.count, 0))))
    elif args.cmd == "hash":
        for k, v in img.hashes().items():
            print(f"{k}: {v}  {'reference' if REFERENCE_SHA256[k] == v else 'DIFFERENT'}")


if __name__ == "__main__":
    main()
