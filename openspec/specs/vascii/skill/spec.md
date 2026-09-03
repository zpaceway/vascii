# vascii/skill Specification

## Purpose
Gives any text-only agent a portable, fully offline way to turn an image file into a structured, confidence-scored understanding via deterministic ASCII, local OCR, file metadata, and explicit uncertainty handling.

## Requirements

### Requirement: Deterministic ASCII conversion with photo and GUI modes

The skill SHALL convert an image file to mono UTF-8 ASCII deterministically (same inputs and flags produce byte-identical output) and SHALL support `photo`, `gui`, and `auto` modes with mode-appropriate width, charset, and sharpness behavior.

#### Scenario: Same input twice gives identical output

- **WHEN** the agent converts the same image with the same flags twice
- **THEN** both ASCII outputs are byte-identical

#### Scenario: GUI screenshot stays legible at capped width

- **WHEN** the agent converts a UI screenshot in `gui` mode
- **THEN** the output is mono fixed-width ASCII within the documented column and row caps with boxes and dividers preserved as glyph structure

### Requirement: Parallel fan-out with barrier join

The skill SHALL run ASCII conversion, OCR on original pixels, and metadata extraction as independent branches that can be invoked in parallel, SHALL read visual patterns after ASCII lands, and SHALL require all branches to complete (with gaps explicitly marked) before concluding.

#### Scenario: Branches run independently

- **WHEN** the agent invokes the three first-wave steps together
- **THEN** OCR consumes original pixels (never ASCII) and metadata never requires OCR text

#### Scenario: Join waits for all evidence

- **WHEN** one branch returns empty (no text found, no EXIF)
- **THEN** the conclusion proceeds with that section marked absent and confidence lowered rather than blocking forever

### Requirement: Local OCR with fallback for small text

The skill SHALL extract text locally with a default engine and SHALL document a high-accuracy fallback path for small UI fonts, reporting per-line text with confidence.

#### Scenario: Small UI font recovered via fallback

- **WHEN** default OCR returns low confidence on a cropped UI region
- **THEN** the agent may retry that crop with high-accuracy settings and the final text records which engine produced it

### Requirement: File metadata with thin-source handling

The skill SHALL report EXIF where present plus file stat (size, dimensions, format), and SHALL fall back to filename, directory hints, and caller-supplied source notes in that priority order.

#### Scenario: Screenshot with no EXIF still yields context

- **WHEN** an image has no EXIF
- **THEN** the metadata output contains stat plus filename and directory hints and marks EXIF as absent

### Requirement: Confidence-scored conclusion with context request

The skill SHALL emit a final conclusion with `high | medium | low` confidence and evidence agreement, and SHALL stop with explicit `needs_context` questions instead of guessing when confidence is low and metadata is thin.

#### Scenario: Uncertain image asks instead of hallucinating

- **WHEN** ASCII, OCR, and metadata disagree or come back thin
- **THEN** the conclusion is marked `low`, lists what is missing, and poses the exact questions that would unblock a re-conclude

#### Scenario: New context triggers bounded re-conclusion

- **WHEN** additional context is supplied after a context request
- **THEN** only the synthesis step re-runs, at most once, after which the skill finalizes even if still uncertain

### Requirement: Conditional inverse-render silhouette check

The skill SHALL support an ASCII-back-to-grayscale silhouette check that runs only after the join, only on low or medium confidence or cross-branch disagreement, and only for invertible output (ordered density ramp, fixed-width mono, no dither, color, or edge-direction glyphs).

#### Scenario: Ambiguous mascot resolved by silhouette

- **WHEN** the first reading is uncertain but the ASCII used a known ordered ramp
- **THEN** the agent may re-render to grayscale, re-read silhouette-level masses only, and promote confidence by at most one level on agreement

#### Scenario: Non-invertible output skips the check

- **WHEN** the ASCII used dithering, color codes, or edge-direction glyphs
- **THEN** the inverse check is skipped and the conclusion records why

### Requirement: Dependency bootstrap guidance per platform

The skill SHALL provide a `check` command that detects present versus missing dependencies and SHALL emit exact per-OS install commands for anything missing without installing silently.

#### Scenario: Missing OCR runtime guides instead of failing cryptically

- **WHEN** the OCR runtime is absent on a supported platform
- **THEN** the check output names the missing package and prints the exact install command for that OS
