## 1. Blind Harness

- [x] 1.1 Implement `eval/blind/` per design (build.py, run.sh, score.py with frozen rubric, hypernym/alias sets, Wilson CI, two-proportion test) and verify scorer reproduces 44/96 semantics on a dry run.
- [x] 1.2 Blind-run the frozen current skill over all hashed inputs and verify predictions freeze plus baseline blind k/n with CI recorded.

## 2. Skill Fixes

- [x] 2.1 Apply photo prompt fixes to SKILL.md (water rule, fixed vocabulary + routing thresholds, interior cues, close-up router, abstention, OCR salience guard, single EXIF demotion) and verify each new rule is triggerable on its cited miss rows.
- [x] 2.2 Apply GUI prompt fixes (OCR-led head order, structural templates, challenge template, subject-evidence confidence rule) plus `data/keyword_packs.json` and verify heads name subjects on the 26 content misses.
- [x] 2.3 Apply config tuning (percentile contrast stretch, photo width 120 for thin strokes, GUI small-input high-accuracy default, narrow-page cap relief) and verify determinism plus token caps still hold.
- [x] 2.4 Relabel 4 stale captures with recorded pixel evidence and verify scorer exclusions handle both denominators.

## 3. Re-test and Gate

- [x] 3.1 Blind re-run the fixed skill with fresh hash salt, score post-hoc, and verify the frozen bar (CI strictly above 0.458 with p below 0.05) is either cleared or missed.
- [x] 3.2 Keep-or-discard: on clear, keep config and re-verify shipped contract (determinism, offline, caps, banned refs); on miss, revert skills/ to frozen pins keeping harness plus hygiene, and verify revert is byte-clean.
- [x] 3.3 Commit and push the kept outcome to origin/master and verify the pushed SHA matches local HEAD.
