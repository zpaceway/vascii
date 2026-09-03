## Why

Three blind rounds prove heuristic prompt surgery cannot identify photo subjects (best photo lane: 18/90). The missing piece is semantic signal: a local zero-shot visual embedding branch would let the skill match image content against coarse-bucket descriptions without any network, training, or dataset fitting. Model selection on the open photo set is legitimate tuning; the blind trial stays the judge.

## What Changes

- Benchmarks local zero-shot embedding models (e.g., TinyCLIP/MobileCLIP/SigLIP-base/OpenCLIP ViT-B/32) on `eval/dataset/photos/` for coarse-bucket accuracy, CPU cost, memory, and offline-vendoring weight; picks one winner.
- Adds `skills/vascii/scripts/embed.py`: deterministic top-k bucket predictions with cosine scores from frozen local weights, plus SKILL.md embedding-branch rules (photo mode: embedding bucket joins as first-class evidence; high only with ASCII/OCR agreement preserved).
- Blind trial R4 with fresh salt, frozen scorer, same gate vs best blind 110/190 ex-stale (CI above, p<0.05). Weight/offline tradeoff documented; adoption requires the gate plus a vendoring story (weights pinned, pre-fetched, no runtime download).
- On miss: full revert, program returns to parked state.

## Capabilities

### New Capabilities

- `vascii/embedding-signal`: local zero-shot embedding branch with deterministic bucket predictions.

### Modified Capabilities

- None. (All prior trials fully reverted; this round adds one branch only.)
