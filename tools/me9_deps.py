#!/usr/bin/env python3
"""RAM writer/reader dependency graph for the 770B image (heuristic, read-only).

    python tools/me9_deps.py access 0x5B97F0                 # every reader/writer PC with its function
    python tools/me9_deps.py upstream 0x5B982A --depth 3     # what feeds a RAM word
    python tools/me9_deps.py downstream 0x5B9982 --depth 3   # what a RAM word feeds
    python tools/me9_deps.py upstream 0x5B982A --dot > g.dot # Graphviz output

Model: for every *write* of the target, the RAM/CAL addresses *read* in the
`--window` instructions before that write (same function) are taken as its
inputs; for every *read*, the RAM addresses *written* in the `--window`
instructions after it are taken as its outputs. This is a local, syntactic
approximation, not a data-flow proof: it over-approximates inside dense code
and misses values that travel through stack slots, pointers held across long
distances, or indirect calls. Use it to find candidates, then confirm each
edge in the disassembly (`me9_xref.py dis`). Output contains addresses only.
"""
from __future__ import annotations

import argparse
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from me9_image import Image, region  # noqa: E402
from me9_xref import build, function_start  # noqa: E402


def index(img: Image):
    refs, _ = build(img)
    by_ea = collections.defaultdict(list)
    by_fn = collections.defaultdict(list)
    for pc, ea, k, sz in refs:
        if k not in ("R", "W"):
            continue
        fn = function_start(img, pc) or pc
        by_ea[ea].append((pc, k, fn))
        by_fn[fn].append((pc, ea, k))
    for v in by_fn.values():
        v.sort()
    return by_ea, by_fn


def edges(target, direction, by_ea, by_fn, window):
    """Yield (src, dst, pc) edges one level from target."""
    want = "W" if direction == "up" else "R"
    for pc, k, fn in by_ea.get(target, []):
        if k != want:
            continue
        lo, hi = (pc - 4 * window, pc) if direction == "up" else (pc, pc + 4 * window)
        for p2, ea2, k2 in by_fn[fn]:
            if not (lo <= p2 <= hi) or ea2 == target:
                continue
            if direction == "up" and k2 == "R" and region(ea2) in ("XRAM", "IRAM", "CAL"):
                yield ea2, target, pc
            elif direction == "down" and k2 == "W" and region(ea2) in ("XRAM", "IRAM"):
                yield target, ea2, pc


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--int")
    ap.add_argument("--ext")
    ap.add_argument("cmd", choices=["access", "upstream", "downstream"])
    ap.add_argument("address")
    ap.add_argument("--depth", type=int, default=2)
    ap.add_argument("--window", type=int, default=24, help="instructions before a write / after a read")
    ap.add_argument("--dot", action="store_true")
    args = ap.parse_args()
    img = Image.from_args(args)
    by_ea, by_fn = index(img)
    target = int(args.address, 0)

    if args.cmd == "access":
        print(f"{target:06X} [{region(target)}]")
        for pc, k, fn in sorted(by_ea.get(target, [])):
            print(f"  {k} @ {pc:06X}  fn {fn:06X}")
        return

    direction = "up" if args.cmd == "upstream" else "down"
    seen, frontier, out = {target}, [target], []
    for d in range(args.depth):
        nxt = []
        for t in frontier:
            grouped = collections.defaultdict(set)
            for src, dst, pc in edges(t, direction, by_ea, by_fn, args.window):
                grouped[(src, dst)].add(pc)
            for (src, dst), pcs in sorted(grouped.items()):
                out.append((d, src, dst, " ".join(f"{p:06X}" for p in sorted(pcs))))
                node = src if direction == "up" else dst
                if node not in seen and region(node) != "CAL":
                    seen.add(node)
                    nxt.append(node)
        frontier = nxt

    if args.dot:
        print("digraph deps {\n  rankdir=LR;")
        for _, src, dst, pc in out:
            print(f'  "{src:06X}" -> "{dst:06X}" [label="{pc}"];')
        print("}")
    else:
        for d, src, dst, pc in out:
            print(f"{'  ' * d}{src:06X} [{region(src)}] -> {dst:06X} [{region(dst)}]  @ {pc}")


if __name__ == "__main__":
    main()
