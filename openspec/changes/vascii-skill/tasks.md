## 1. ASCII Core

- [x] 1.1 Implement deterministic `img2ascii.py` (`photo | gui | auto`, recorded forward params) and verify same input twice yields byte-identical output.
- [x] 1.2 Tune photo vs GUI presets (widths, ramps, aspect, contrast) on real photos and screenshots and verify legibility within token caps.
- [x] 1.3 Add row-cap and truncation behavior and verify oversized GUI captures stay within documented limits.

## 2. OCR and Metadata Branches

- [x] 2.1 Integrate default local OCR on original pixels (upscaled copy) with per-line confidence and verify text extraction on 11-13px UI crops.
- [x] 2.2 Add high-accuracy fallback path with tuned detection params and verify it recovers low-confidence crops and records the producing engine.
- [x] 2.3 Implement metadata extraction (EXIF + stat + filename/dir hints + caller note priority) and verify EXIF-less screenshots still yield context with EXIF marked absent.

## 3. Reading Protocol and Conclusion

- [x] 3.1 Write pattern-reading protocol (regions, line flow, depth, masses) and verify it produces structured notes from ASCII alone.
- [x] 3.2 Implement confidence-scored conclusion with evidence agreement and verify high/medium/low outcomes match branch agreement.
- [x] 3.3 Implement context-request escalation with single re-conclude cap and verify low-confidence thin-meta cases stop with explicit questions instead of guessing.

## 4. Inverse-Render Validation

- [x] 4.1 Implement conditional grayscale re-render (ramp inversion, NEAREST upscale for viewing, low-res cell-mean compare with +-1 tolerance) and verify Mario-class silhouette agreement promotes confidence one level.
- [x] 4.2 Enforce skip rules (dither, color, edge-glyphs, unknown ramp, high confidence) and verify each skip records its reason.

## 5. Bootstrap and Packaging

- [x] 5.1 Implement `check` command (importlib + platform detection) and verify it reports present versus missing on Linux, macOS, and Windows.
- [x] 5.2 Add per-OS install guidance output and verify no silent installs or network fetches occur at runtime.
- [x] 5.3 Assemble portable skill (`SKILL.md` + scripts + pinned deps, no MCP/network/absolute-path references) and verify offline install plus network-off run.

## 6. Dev-Harness Bake-off and Freeze

- [x] 6.1 Collect real eval set (photos, GUI screenshots, platform captures, diagrams incl. Mario fixture) with independent ground-truth labels and verify coverage per category.
- [x] 6.2 Run parallel bake-off lanes (OCR candidates, ASCII modes, bootstrap matrix) with a single synthesizer verdict and verify winners match frozen pins (RapidOCR default, Paddle fallback, hand-rolled core).
- [x] 6.3 Run full validation (`openspec validate --strict`, determinism, offline, token-cap checks) and verify the change passes before apply.
