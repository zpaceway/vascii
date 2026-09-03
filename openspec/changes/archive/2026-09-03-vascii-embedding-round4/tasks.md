## 1. Model and Branch

- [x] 1.1 Benchmark 2-3 local zero-shot models on the open photo set (accuracy, CPU s/image, RAM, weight size, offline vendoring) and verify a frozen winner with pinned versions plus weight hashes.
- [x] 1.2 Implement `scripts/embed.py` plus SKILL.md embedding-branch rules and verify determinism, offline run, token discipline, and contract (caps, banned refs).

## 2. Trial and Gate

- [x] 2.1 Blind R4 trial with fresh salt (4 testers, frozen scorer) and verify freeze plus scores with CI and z vs best blind 110/190.
- [x] 2.2 Keep-or-discard per gate (plus vendoring story on keep); on discard revert byte-clean; record verdict.
- [x] 2.3 Commit and push kept outcome.
