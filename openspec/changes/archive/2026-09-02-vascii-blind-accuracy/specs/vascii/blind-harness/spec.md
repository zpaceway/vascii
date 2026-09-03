## Purpose

Provides a sealed-label, pixels-only evaluation harness that produces blind accuracy numbers with confidence intervals and significance tests, so improvement claims about the vascii skill can be trusted.

## ADDED Requirements

### Requirement: Sealed-label blind dataset build

The harness SHALL produce EXIF-stripped hashed image copies keyed by content hash with labels sealed in a tester-inaccessible file and a freeze record of all source hashes.

#### Scenario: Tester cannot reach labels

- **WHEN** a tester holds only `eval/blind/inputs/` and the frozen skill
- **THEN** no filename, label, source URL, or text-presence flag is recoverable without the sealed file

### Requirement: Pixels-only run protocol with frozen predictions

The harness SHALL define a run procedure that consumes only input pixels and writes predictions keyed by hash, freezing them by recorded sha256 before any scoring.

#### Scenario: Predictions frozen before scoring

- **WHEN** the scorer runs
- **THEN** it verifies the predictions freeze hash matches the recorded value and refuses to score unfrozen predictions

### Requirement: Deterministic scoring with significance reporting

The scorer SHALL apply the frozen rubric (photo coarse-bucket, GUI strict subject-naming, diagram entity plus salient text), hypernym and alias sets, stale and fixture exclusions, and SHALL report per-category tallies with Wilson 95% intervals plus a two-proportion significance test against the 44/96 baseline.

#### Scenario: Improvement claim is statistically gated

- **WHEN** a re-test completes
- **THEN** scores.md states k/n, Wilson interval, delta vs 0.458, z and p values, and whether the frozen bar (interval strictly above 0.458 with p below 0.05) is cleared
