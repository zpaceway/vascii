## Context

See proposal.md Why. Frozen state: skills/ at vascii-skill pins (determinism `21725c66`), blind harness `eval/blind/` with frozen scorer, best blind 110/190 ex-stale (photo 13/90, gui 97/100, diagram 45/89). R2 evidence: `eval/blind/scores_R2.md` per-row justifications.

## Goals / Non-Goals

**Goals:** Add true signal (color/zones/edges as numbers) and mechanical quoting rules; measure with the frozen scorer; adopt only on significance.
**Non-Goals:** New engines, network, model training, GUI changes (at ceiling), rubric changes.

## Decisions

- **Numeric features, not more adjectives.** New Wave-1 branch `photo_stats.py` (stdlib + Pillow/numpy only, JSON out): dominant-color clustering (k-means-lite, 4 clusters, basic color names), luma by vertical thirds + center, Sobel horizontal/vertical energy ratio, left-right mirror symmetry score, largest connected dark-mass bbox position, skin-tone pixel fraction (YCbCr box). Deterministic given bytes. Rationale: color and spatial statistics survive where glyph ramps collapse; the agent currently guesses blind on exactly these axes.
- **Threshold rules in SKILL.md photo-stats section** (conservative, abstention-preserving): blue-dominant + lower-half water-band → waterscape; green + high texture energy → vegetation; skin fraction + centered mass → figure; upper-mass majority + enclosure → interior; dark frame + point lights → night; none firing → keep prior behavior. Rationale: each rule targets an observed no-match cluster; thresholds documented with trigger examples.
- **Diagram quoting rule** (prompt-only, mechanical): verdicts on text-bearing images must embed ≥1 quoted OCR span; entity from layout vocabulary. Rationale: converts `token:X+no-text` misses to hits with zero perception risk — the text is already recovered.
- **Same frozen gate, tougher comparator**: adopt iff R3 headline clears best-blind 110/190 with p<0.05 (two-proportion) and CI above, else revert skill changes and keep harness. Rationale: ratchet against noise, not hope.
- **Stop rule**: two consecutive failed rounds, headline ≥75%, or photo ≥50% ends the program; the harness remains for any future work.

## Risks / Trade-offs

- [Feature thresholds overfit to 90 photos] -> Thresholds set from feature distributions across the full photo set, reported with margins; blind trial is the judge.
- [Color names mismatch rubric tokens] -> Rules emit rubric-hypernym buckets first, color words second; scorer matches either.
- [Quoting rule adds tokens] -> Quotes capped to top span; token caps re-verified.
