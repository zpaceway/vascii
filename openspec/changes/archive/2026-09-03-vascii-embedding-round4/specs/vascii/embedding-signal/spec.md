## Purpose

Provides local zero-shot visual embedding signal that names photo content at the coarse-bucket level, deterministically and offline, for agents that cannot see images.

## ADDED Requirements

### Requirement: Deterministic zero-shot bucket predictions

The skill SHALL provide a script emitting deterministic top-k coarse-bucket predictions with scores from frozen local weights, byte-identical for identical input bytes, with no network access and no dataset-fitted parameters.

#### Scenario: Same bytes give identical predictions

- **WHEN** the script runs twice on the same file offline
- **THEN** both JSON outputs are byte-identical
