## Why

Text-only agents cannot see images. `vascii` gives them portable eyes: a deterministic, fully offline image-to-understanding skill (ASCII + OCR + metadata + synthesis) that runs anywhere without network calls or environment-specific integrations.

## What Changes

- Adds a new portable agent skill `vascii`: image file in, structured understanding out.
- Deterministic ASCII core (`photo | gui | auto` modes) owned by the skill; no runtime dependency on third-party ASCII libraries.
- Parallel fan-out execution: ASCII + OCR-on-original-pixels + metadata run together, pattern-read follows ASCII, hard barrier join before conclusion.
- Local OCR default with documented high-accuracy fallback path for small UI text.
- Conditional inverse-render silhouette check (ASCII back to grayscale) gated on low/medium confidence and invertible output only.
- Confidence-scored conclusion with explicit context-request escalation when evidence is thin.
- Dependency bootstrap contract: detect-then-guide per OS, never silent auto-install.
- Dev-only training harness (real images via browser downloads/screenshots, independent ground-truth cross-checks) lives outside the shipped skill and is never referenced by it.

## Capabilities

### New Capabilities

- `vascii/skill`: portable offline image-understanding skill covering ASCII conversion, pattern reading, local OCR, metadata extraction, inverse-render validation, confidence-scored conclusion, and dependency bootstrap guidance.

### Modified Capabilities

- None. Greenfield project with no existing specs.

## Impact

- New skill directory with `SKILL.md` plus small deterministic scripts (`Pillow`, `numpy`, `rapidocr`/`onnxruntime` at runtime).
- No breaking changes. No network calls, no MCP references, no absolute paths in shipped artifacts.
- Dev harness may use heavyweight models and large eval sets; shipped defaults stay light.
