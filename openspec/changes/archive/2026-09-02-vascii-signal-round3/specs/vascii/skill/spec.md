## ADDED Requirements

### Requirement: Diagram verdict quotes salient text

The skill SHALL require verdicts on text-bearing diagram images to quote at least one OCR span, with the entity named from layout vocabulary.

#### Scenario: Chart verdict carries its title

- **WHEN** OCR recovered on-figure text such as a chart title
- **THEN** the verdict contains the entity plus the quoted span
