# Centipede (GBC) – High Score Save Patch

Version: 0.1

This repo contains scripts and patches to add battery-backed high score saving to the **ModRetro Atari Centipede** Game Boy Color ROM. It **does not** include any copyrighted ROM data.

[Atari '90s Rewind Collection - ModRetro](https://modretro.com/products/atari)

### Quickstart
Download the .ips from [Releases](https://github.com/davidgovea/centipede_mod/releases) and use an [online patcher](https://www.romhacking.net/patch/) to apply to your personal ROM dump.

## What this patch does
- Enables SRAM+Battery in the cartridge header.
- Loads high scores from SRAM on boot (or falls back to defaults if empty).
- Saves high scores to SRAM after name confirmation.

## Files
- `scripts/patch_highscore_save.py` – patches a clean ROM into a save-enabled ROM.
- `scripts/make_ips.py` – generates an IPS patch from original + modified ROMs.
- `patches/centipede_highscore_save_v0.1.ips` – IPS patch (generated from clean ROM + patched ROM).

## Usage

### 1) Patch a clean ROM
```
python3 scripts/patch_highscore_save.py \
  --in  /path/to/CENTIPEDE-0.orig.gbc \
  --out /path/to/CENTIPEDE-0.gbc
```

### 2) (Optional) Regenerate the IPS patch
```
python3 scripts/make_ips.py \
  --orig /path/to/CENTIPEDE-0.orig.gbc \
  --mod  /path/to/CENTIPEDE-0.gbc \
  --out  patches/centipede_highscore_save_v0.1.ips
```

## Notes
- Expected ROM size: **1MB (0x100000)**.
- Save data is stored in SRAM bank 0 at `A000` with magic `HS`.

## Legal
This project contains only **original code** and **binary patches**. You must provide your own legally obtained ROM to use it.
