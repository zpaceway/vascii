## Why

Round 2 (vascii-blind-accuracy) was discarded at the gate (110/190, p=0.053): prompt-only routing fixes cannot create signal that ASCII destroys. The R2 justifications show exactly what is missing — 77/90 photo misses are `no-match` (verdict shares zero tokens with the label) while lucky color/material tokens (`blue`, `green`, `bright`, `night`) score, and 30+/44 diagram misses are `token:X+no-text` (entity named, required salient-text quote absent). Both point to the same remedy: give the agent deterministic numeric signal (color, zones, edges) plus mechanical verdict rules, instead of more wording.

## What Changes

- Adds `skills/vascii/scripts/photo_stats.py`: deterministic numeric photo features (dominant-color clusters with basic names, brightness by thirds, horizontal vs vertical edge energy, mirror symmetry, largest-mass position, skin-tone fraction) as JSON alongside ASCII.
- Adds SKILL.md photo-stats reading rules mapping feature thresholds to coarse buckets (blue-dominant + lower-band water; green + high texture vegetation; skin cluster + centered mass figure; ceiling-mass interior; banded-night night).
- Adds SKILL.md diagram verdict rule: for `has_text` images the verdict MUST quote the top OCR span; entity named from layout vocabulary (flowchart, arch, venn, network, chart-type, schematic, map, emblem, sprite).
- Blind trial R3 with fresh salt scored by the frozen scorer; adoption gate vs best blind (110/190 ex-stale): CI strictly above current best with p<0.05, else discard.
- Stop rule for the program: stop after two consecutive failed rounds, or when headline ≥75%, or photo ≥50%.

## Capabilities

### New Capabilities

- `vascii/photo-stats`: deterministic numeric photo-feature script plus protocol rules binding features to verdict buckets.

### Modified Capabilities

- `vascii/skill`: new photo-stats Wave-1 branch and diagram quoting rule (ADDED requirements on the existing capability; no existing requirement text changes).
