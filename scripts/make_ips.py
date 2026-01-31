#!/usr/bin/env python3
"""
Create an IPS patch from two ROM files.

Usage:
  python3 make_ips.py --orig path/to/orig.gbc --mod path/to/mod.gbc --out patches/centipede_highscore_save.ips
"""

from __future__ import annotations

import argparse
from pathlib import Path


def load(path: Path) -> bytes:
    return path.read_bytes()


def iter_diff_runs(orig: bytes, mod: bytes):
    """Yield (offset, data_bytes) for contiguous diff runs."""
    length = min(len(orig), len(mod))
    i = 0
    while i < length:
        if orig[i] == mod[i]:
            i += 1
            continue
        start = i
        i += 1
        while i < length and orig[i] != mod[i]:
            i += 1
        yield start, mod[start:i]

    # If mod is longer, append tail as a diff run
    if len(mod) > len(orig):
        yield len(orig), mod[len(orig):]


def write_ips(orig: bytes, mod: bytes, out_path: Path) -> None:
    with out_path.open("wb") as f:
        f.write(b"PATCH")

        for offset, data in iter_diff_runs(orig, mod):
            # Split long runs into <= 0xFFFF
            idx = 0
            while idx < len(data):
                chunk = data[idx:idx + 0xFFFF]
                size = len(chunk)
                # 3-byte big-endian offset
                f.write(bytes([(offset >> 16) & 0xFF, (offset >> 8) & 0xFF, offset & 0xFF]))
                # 2-byte big-endian size
                f.write(bytes([(size >> 8) & 0xFF, size & 0xFF]))
                f.write(chunk)
                idx += size
                offset += size

        f.write(b"EOF")


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate IPS patch from orig/mod ROMs.")
    ap.add_argument("--orig", required=True, help="Original ROM path")
    ap.add_argument("--mod", required=True, help="Modified ROM path")
    ap.add_argument("--out", required=True, help="Output IPS path")
    args = ap.parse_args()

    orig = load(Path(args.orig))
    mod = load(Path(args.mod))

    if len(orig) != len(mod):
        print(f"Warning: ROM sizes differ (orig={len(orig)}, mod={len(mod)}). IPS will include tail data.")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_ips(orig, mod, out_path)

    print(f"Wrote IPS patch: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
