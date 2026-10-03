#!/usr/bin/env python3
"""Call-graph and RAM-consumer tracing for the 770B image.

    python tools/me9_callgraph.py callees 0x31B20 --depth 2   # what a task/function calls
    python tools/me9_callgraph.py callers 0x2C060 --depth 3   # who reaches a function
    python tools/me9_callgraph.py consumers 0x3FBFB3          # functions reading/writing a RAM address,
                                                              # each with its callers (one level)

Function boundaries come from me9_xref.function_start (prologue / previous blr),
so leaf functions without a prologue are attributed correctly only if they
follow a `blr`. Indirect calls (blrl through tables) are not followed.
"""
from __future__ import annotations

import argparse
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from me9_image import Image, region  # noqa: E402
from me9_xref import build, function_end, function_start  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--int")
    ap.add_argument("--ext")
    ap.add_argument("cmd", choices=["callees", "callers", "consumers"])
    ap.add_argument("address")
    ap.add_argument("--depth", type=int, default=1)
    args = ap.parse_args()
    img = Image.from_args(args)
    refs, calls = build(img)
    target = int(args.address, 0)

    if args.cmd == "callees":
        def walk(fn, d, seen):
            end = function_end(img, fn)
            for pc, t, _ in calls:
                if fn <= pc < end:
                    print(f"{'  ' * d}{pc:06X} -> {t:06X}")
                    if d + 1 < args.depth and t not in seen:
                        seen.add(t)
                        walk(t, d + 1, seen)
        walk(target, 0, {target})
    elif args.cmd == "callers":
        by_target = collections.defaultdict(list)
        for pc, t, _ in calls:
            by_target[t].append(pc)

        def up(fn, d, seen):
            for pc in by_target.get(fn, []):
                f = function_start(img, pc) or pc
                print(f"{'  ' * d}{fn:06X} <- {pc:06X} (fn {f:06X})")
                if d + 1 < args.depth and f not in seen:
                    seen.add(f)
                    up(f, d + 1, seen)
        up(target, 0, {target})
    else:
        print(f"{target:06X} [{region(target)}]")
        fns = collections.defaultdict(set)
        for pc, ea, k, sz in refs:
            if ea == target:
                fns[function_start(img, pc) or pc].add(k)
        for f, kinds in sorted(fns.items()):
            callers = sorted({function_start(img, pc) or pc for pc, t, _ in calls if t == f})
            print(f"  fn {f:06X} {''.join(sorted(kinds))}  called from: {' '.join(f'{c:06X}' for c in callers[:8])}")


if __name__ == "__main__":
    main()
