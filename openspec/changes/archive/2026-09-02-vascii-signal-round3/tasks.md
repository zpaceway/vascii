## 1. Signal

- [x] 1.1 Implement `scripts/photo_stats.py` (deterministic JSON features, byte-identical double-run) and verify on the photo set with reported feature distributions.
- [x] 1.2 Add SKILL.md photo-stats reading rules plus diagram quoting rule (disjoint anchors) and verify token caps plus contract (determinism, offline, banned refs).

## 2. Trial and Gate

- [x] 2.1 Blind R3 trial with fresh salt (4 testers, frozen scorer) and verify predictions freeze plus scores with CI and z vs best blind 110/190.
- [x] 2.2 Keep-or-discard per gate; on keep re-verify contract, on discard revert skills/ byte-clean; record verdict.
- [x] 2.3 Commit and push kept outcome; apply stop rule (2 failed rounds, headline ≥75%, or photo ≥50%).
