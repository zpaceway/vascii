## Context

See proposal.md Why. Greenfield repo: no existing code, specs, or conventions. Shipped skill must be agnostic and fully offline (image path in, UTF-8 text out; pinned deps `Pillow`, `numpy`, `rapidocr` + `onnxruntime`). Dev-only harness (real image collection, independent ground-truth cross-checks) lives outside the skill and is never referenced by shipped artifacts.

## Goals / Non-Goals

**Goals:**
- Dual-mode deterministic ASCII core (`photo | gui | auto`) with recorded forward params enabling conditional inverse validation.
- Parallel fan-out (ASCII + OCR-on-pixels + metadata), pattern-read after ASCII, hard barrier join, confidence-scored conclusion.
- Local OCR that survives 11-13px UI text via tuned detection params plus documented high-accuracy fallback.
- Bounded uncertainty handling: conditional inverse-render check plus explicit context-request escalation, capped at one re-conclude.
- Per-OS detect-then-guide dependency bootstrap with no silent installs.

**Non-Goals:**
- Cloud OCR / vision APIs at runtime; networked ASCII entrypoints (`from_url`, generative fills).
- Auto-install with sudo, background model downloads at runtime, bundled wheels.
- Photometric restoration from ASCII; GUI edge-direction or ANSI-color inversion.
- Multi-round interrogation loops; streaming partial conclusions before the join.

## Decisions

- **Hand-rolled Pillow + numpy ASCII core over ascii-magic / img2ascii-py / OpenCV dependency.** Rationale: only hand-rolled exposes all knobs (width, charset, aspect, resample, contrast, optional edge channel) needed for `photo|gui|auto` presets and records forward params for inversion. Alternatives: ascii-magic (light, maintained, but density-only; networked entrypoints violate offline rule - use as API-shape reference only); img2ascii-py (best config template `AsciiConfig`, but 1-star single-maintainer - reference only); OpenCV edge overlay (sharpest wireframes, heavy native wheel + brittle thresholds - reimplement idea in numpy/scipy if needed, not as dep). Rejected: `art` (text fonts only), `pyascii`/`image-to-Ascii` (stale, ratio sizing, no charset control).
- **RapidOCR 3.9.2 + onnxruntime CPU as default; PaddleOCR 3.7.0 / PaddleX PP-OCRv6 as `--high-accuracy` fallback; Tesseract 5.5.3 as cheap pre-filter only.** Rationale: RapidOCR is the best speed/weight/accuracy/offline/API balance for crisp UI screenshots; Paddle same family with stronger small-text levers (`det_db_unclip_ratio` 1.5->1.8, server det/rec, medium tier) paid only on low-confidence crops; Tesseract collapses on small fonts without 2-3x upscale + `--psm 11`. Rejected as defaults: EasyOCR (stale, heavy), Surya v2 (VLM server, document-specialized, off-distribution for screenshots).
- **Agent-level parallelism, not threaded mega-script.** Rationale: three small deterministic scripts invoked together keeps each branch testable against ground truth independently; parallelism is invocation order in SKILL.md. OCR runs on original pixels (upscaled copy), never on ASCII; metadata never needs OCR text, preserving the DAG.
- **Join policy: barrier with proceed-with-gaps.** Conclusion waits for all branches; empty branches are marked absent with lowered confidence. No silent retries; retry is explicit opt-in with fallback params.
- **Inverse-render as conditional post-barrier validation (Step 1b/4a).** Runs only on low/medium confidence or ascii-vs-OCR disagreement, and only for the invertible subset (fixed-width mono, ordered density ramp, no dither/color/edge-glyphs, known ramp + flags). Method: ramp-inversion pixel-block + `NEAREST` upscale for viewing; compare at low-res cell means with +-1 step tolerance. Agreement promotes confidence one level; disagreement holds and escalates. Never primary perception (same lossy source viewed twice).
- **Confidence + context-request escalation.** Step 4 emits `high | medium | low` plus evidence agreement. Low + thin meta emits `needs_context` questions and stops the pass; resume re-runs only step 4, max one re-conclude, then finalizes as `uncertain + best guess + what would resolve it`. Caller (not skill) decides fulfillment: interactive callers ask the user, headless callers surface uncertainty.
- **Bootstrap: `check` then per-OS guide.** `vascii --check` reports present/missing via importlib + `sys.platform`; missing emits exact install commands (pip + system notes for tesseract path only) and asks to run. Never silent sudo/pip, no downloads at import time; models vendored or pre-fetched, `result.vis()` font fetch skipped offline.
- **Token caps per mode.** Mono default; photo 80-120 cols with detailed ramp; GUI 160-240 cols with short ramp + row-cap/truncation. GUI 200x80 worst case documented so the join never drowns step 4.

## Risks / Trade-offs

- [Small UI text missed] -> Upscaled-copy OCR, `det_db_unclip_ratio` tuning, medium-tier fallback, confidence-gated retry.
- [GUI wireframes wash out in density ASCII] -> High-width sharp gui preset, short ramp, optional edge channel; edge-glyph output excluded from inversion.
- [EXIF empty for screenshots] -> Metadata priority exif > filename/dir hints > caller-supplied source note; thin meta lowers confidence instead of blocking.
- [Upscale halos hallucinated as structure] -> Silhouette-only reread rule; low-res cell-mean comparison.
- [Confidence inflation from self-agreement] -> Corroboration-only rule; no promotion past one level on inverse agreement alone.
- [Offline claim broken by JIT model/font downloads] -> Vendor/cache models, skip font fetch, verify with network-off test.
- [Parallel outputs flood context] -> Width/row caps, OCR char caps, pattern notes before join; heavyweight eval stays in dev harness.
