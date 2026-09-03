## Purpose

Gives text-only agents deterministic numeric photo signal (color, zones, edges, symmetry) that ASCII rendering destroys, bound by protocol rules to coarse verdict buckets.

## ADDED Requirements

### Requirement: Deterministic photo feature extraction

The skill SHALL provide a script emitting deterministic JSON photo features (dominant colors with basic names, luma by thirds, edge-orientation energy, symmetry score, largest-mass position, skin-tone fraction) with identical output for identical input bytes.

#### Scenario: Same bytes give identical features

- **WHEN** the script runs twice on the same file
- **THEN** both JSON outputs are byte-identical

### Requirement: Feature-bound photo verdict rules

The skill SHALL map documented feature thresholds to coarse buckets (water, vegetation, figure, interior, night) and SHALL fall back to prior behavior when no rule fires, never inventing species or names from features alone.

#### Scenario: Blue lower-band water scores

- **WHEN** features show blue-dominant clusters with lower-half banding and symmetry
- **THEN** the verdict names the waterscape bucket with the feature citation
