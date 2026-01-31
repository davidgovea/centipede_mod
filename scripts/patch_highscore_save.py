#!/usr/bin/env python3
"""
Patch Centipede (GBC) ROM to add battery-backed high score saving.

Default usage:
  python3 patch_highscore_save.py \
    --in  Centipede_ModRetro/CENTIPEDE-0.orig.gbc \
    --out Centipede_ModRetro/CENTIPEDE-0.gbc
"""

from __future__ import annotations

import argparse
from pathlib import Path

# --- Patch constants ---
STUB_ADDR = 0x0828
INIT_ADDR = 0x0830
LOAD_ADDR = 0x0850
SAVE_ADDR = 0x08A0

# Original bytes we expect before patching
EXPECT_INIT_BYTES = bytes([0x21, 0x86, 0x04])  # LD HL,$0486
EXPECT_POSTNAME_CALL = bytes([0xCD, 0x0E, 0x49])  # CALL $490E

# Injected code
STUB = bytes([
    0xCD, 0x0E, 0x49,                    # CALL $490E
    0xCD, SAVE_ADDR & 0xFF, (SAVE_ADDR >> 8) & 0xFF,  # CALL SaveHighScores
    0xC9                                 # RET
])

INIT = bytes([
    0xCD, LOAD_ADDR & 0xFF, (LOAD_ADDR >> 8) & 0xFF,  # CALL LoadHighScores
    0xB7,                    # OR A
    0xC0,                    # RET NZ
    0x21, 0x86, 0x04,         # LD HL,$0486
    0x11, 0x00, 0xDD,         # LD DE,$DD00
    0x01, 0x5A, 0x00,         # LD BC,$005A
    0x2A,                    # LD A,(HL+)
    0x12,                    # LD (DE),A
    0x13,                    # INC DE
    0x0B,                    # DEC BC
    0x78,                    # LD A,B
    0xB1,                    # OR C
    0x20, 0xF8,              # JR NZ,-8
    0xC9                     # RET
])

LOAD = bytes([
    0xC5,                    # PUSH BC
    0xD5,                    # PUSH DE
    0xE5,                    # PUSH HL
    0xF0, 0x70,              # LDH A,($70)
    0x4F,                    # LD C,A
    0x3E, 0x01,              # LD A,$01
    0xE0, 0x70,              # LDH ($70),A
    0x3E, 0x0A,              # LD A,$0A
    0xEA, 0x00, 0x00,        # LD ($0000),A  ; RAMG
    0xAF,                    # XOR A
    0xEA, 0x00, 0x40,        # LD ($4000),A  ; RAMB=0
    0x21, 0x00, 0xA0,        # LD HL,$A000
    0x7E,                    # LD A,(HL)
    0xFE, 0x48,              # CP $48 ('H')
    0x20, 0x21,              # JR NZ,invalid
    0x23,                    # INC HL
    0x7E,                    # LD A,(HL)
    0xFE, 0x53,              # CP $53 ('S')
    0x20, 0x1B,              # JR NZ,invalid
    0x21, 0x02, 0xA0,        # LD HL,$A002
    0x11, 0x00, 0xDD,        # LD DE,$DD00
    0x06, 0x5A,              # LD B,$5A
    0x2A,                    # LD A,(HL+)
    0x12,                    # LD (DE),A
    0x13,                    # INC DE
    0x05,                    # DEC B
    0x20, 0xFA,              # JR NZ,loop
    0xAF,                    # XOR A
    0xEA, 0x00, 0x00,        # LD ($0000),A ; disable SRAM
    0x79,                    # LD A,C
    0xE0, 0x70,              # LDH ($70),A
    0xE1,                    # POP HL
    0xD1,                    # POP DE
    0xC1,                    # POP BC
    0x3E, 0x01,              # LD A,$01
    0xC9,                    # RET
    # invalid:
    0xAF,                    # XOR A
    0xEA, 0x00, 0x00,        # LD ($0000),A ; disable SRAM
    0x79,                    # LD A,C
    0xE0, 0x70,              # LDH ($70),A
    0xE1,                    # POP HL
    0xD1,                    # POP DE
    0xC1,                    # POP BC
    0xAF,                    # XOR A
    0xC9                     # RET
])

SAVE = bytes([
    0xC5,                    # PUSH BC
    0xD5,                    # PUSH DE
    0xE5,                    # PUSH HL
    0xF0, 0x70,              # LDH A,($70)
    0x4F,                    # LD C,A
    0x3E, 0x01,              # LD A,$01
    0xE0, 0x70,              # LDH ($70),A
    0x3E, 0x0A,              # LD A,$0A
    0xEA, 0x00, 0x00,        # LD ($0000),A  ; RAMG
    0xAF,                    # XOR A
    0xEA, 0x00, 0x40,        # LD ($4000),A  ; RAMB=0
    0x21, 0x00, 0xDD,        # LD HL,$DD00
    0x11, 0x02, 0xA0,        # LD DE,$A002
    0x06, 0x5A,              # LD B,$5A
    0x2A,                    # LD A,(HL+)
    0x12,                    # LD (DE),A
    0x13,                    # INC DE
    0x05,                    # DEC B
    0x20, 0xFA,              # JR NZ,loop
    0x3E, 0x48,              # LD A,$48
    0xEA, 0x00, 0xA0,        # LD ($A000),A
    0x3E, 0x53,              # LD A,$53
    0xEA, 0x01, 0xA0,        # LD ($A001),A
    0xAF,                    # XOR A
    0xEA, 0x00, 0x00,        # LD ($0000),A ; disable SRAM
    0x79,                    # LD A,C
    0xE0, 0x70,              # LDH ($70),A
    0xE1,                    # POP HL
    0xD1,                    # POP DE
    0xC1,                    # POP BC
    0xC9                     # RET
])


def set_bytes(data: bytearray, offset: int, payload: bytes) -> None:
    data[offset:offset + len(payload)] = payload


def calc_header_checksum(data: bytearray) -> int:
    x = 0
    for i in range(0x0134, 0x014D):
        x = (x - data[i] - 1) & 0xFF
    return x


def calc_global_checksum(data: bytearray) -> int:
    total = sum(data) - data[0x014E] - data[0x014F]
    return total & 0xFFFF


def check_expected(data: bytearray, offset: int, expected: bytes, label: str, errors: list[str]) -> None:
    actual = data[offset:offset + len(expected)]
    if actual != expected:
        errors.append(
            f"{label} @ 0x{offset:06X}: expected {expected.hex(' ')}, got {actual.hex(' ')}"
        )


def check_code_cave(data: bytearray, start: int, length: int) -> bool:
    region = data[start:start + length]
    return all(b == 0x00 for b in region)


def patch_rom(data: bytearray, force: bool = False) -> None:
    errors: list[str] = []

    check_expected(data, 0x0474, EXPECT_INIT_BYTES, "Init routine bytes", errors)
    check_expected(data, 0x18CE8, EXPECT_POSTNAME_CALL, "Post-name call bytes", errors)

    cave_len = 0x08D0 - 0x0828
    if not check_code_cave(data, 0x0828, cave_len):
        errors.append("Code cave 0x0828-0x08CF is not empty (non-zero bytes found)")

    if errors and not force:
        msg = "\n".join(errors)
        raise SystemExit(
            "Refusing to patch due to unexpected bytes.\n"
            "Re-run with --force to override.\n\n" + msg
        )

    # Inject routines
    set_bytes(data, STUB_ADDR, STUB)
    set_bytes(data, INIT_ADDR, INIT)
    set_bytes(data, LOAD_ADDR, LOAD)
    set_bytes(data, SAVE_ADDR, SAVE)

    # Hook init and commit paths
    set_bytes(data, 0x0474, bytes([0xC3, INIT_ADDR & 0xFF, (INIT_ADDR >> 8) & 0xFF]))
    set_bytes(data, 0x18CE8, bytes([0xCD, STUB_ADDR & 0xFF, (STUB_ADDR >> 8) & 0xFF]))

    # Header changes for SRAM + battery
    data[0x0147] = 0x1B  # MBC5 + RAM + BATTERY
    data[0x0149] = 0x02  # 8KB SRAM

    # Checksums
    data[0x014D] = calc_header_checksum(data)
    checksum = calc_global_checksum(data)
    data[0x014E] = (checksum >> 8) & 0xFF
    data[0x014F] = checksum & 0xFF


def main() -> int:
    ap = argparse.ArgumentParser(description="Patch Centipede ROM for high score SRAM saving.")
    ap.add_argument("--in", dest="input", required=True, help="Input ROM path (clean/original).")
    ap.add_argument("--out", dest="output", required=True, help="Output ROM path.")
    ap.add_argument("--force", action="store_true", help="Patch even if expected bytes differ.")
    args = ap.parse_args()

    in_path = Path(args.input)
    out_path = Path(args.output)

    data = bytearray(in_path.read_bytes())
    if len(data) != 0x100000:
        print(f"Warning: ROM size is {len(data)} bytes, expected 0x100000.")

    patch_rom(data, force=args.force)
    out_path.write_bytes(data)

    print(f"Patched ROM written to: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
