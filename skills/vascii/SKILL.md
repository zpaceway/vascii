---
name: vascii
description: Turn an image file into structured, confidence-scored understanding via deterministic ASCII, local OCR, file metadata, and explicit uncertainty handling. Fully offline: image path in, UTF-8 text out.
license: MIT
---

# vascii

Gives a text-only agent a portable, fully offline way to read an image file:
deterministic ASCII rendering (`photo | gui | auto` modes), OCR on original
pixels with a high-accuracy fallback, file metadata with thin-source
handling, and a confidence-scored conclusion that asks for context instead
of guessing when evidence is thin.

## Bootstrap

Before any other step, verify the runtime. From this directory:

```
python3 scripts/check.py
```

The check reports each dependency as `present` or `missing` and, for
anything missing, prints the exact install commands for your OS. It never
installs anything itself, never requests elevated privileges, and performs
no network activity. Install what it names, then re-run the check until it
reports all dependencies present.

Pinned dependencies live in `requirements.txt` and can be installed with:

```
python3 -m pip install -r requirements.txt
```

## Offline rules

- All processing is local: image path in, UTF-8 text out.
- No step installs packages, fetches models or fonts, or contacts any
  service at runtime. OCR model files must already be in the engine cache
  before working offline; the check output says so explicitly.
- The optional Tesseract pre-filter path is the only step with a
  system-package note (Debian/Ubuntu `apt`, macOS `brew`, Windows
  `winget`); everything else is plain `pip`.

## Pipeline

1. Render ASCII (`photo | gui | auto`), OCR the original pixels, and read
   file metadata as independent first-wave branches.
2. Read visual patterns from the ASCII, then join: all branches must land,
   with gaps marked absent and confidence lowered.
3. Emit a `high | medium | low` conclusion with evidence agreement. On
   `low` with thin metadata, stop with explicit `needs_context` questions;
   a single re-conclude is allowed once new context arrives.
4. The inverse-render silhouette check is conditional only: after the join,
   on low/medium confidence or branch disagreement, and only for
   invertible (ordered-ramp, mono, undithered) output.

## Parallel invocation order

Run the branches as two waves at the agent level. Invoke each branch
tool separately; do not merge them into one script.

Wave 1 — invoke these three together, in parallel:

1. `img2ascii` on the image file → ASCII block (Invocation examples
   for mode choice).
2. `ocr` on the original pixels (an upscaled copy is fine) → per-line
   text with confidence. Never OCR the ASCII block.
3. `meta` on the file → EXIF plus stat (size, dimensions, format),
   plus filename and directory hints. Never needs OCR text.

Wave 2 — only after the ASCII block lands:

4. `pattern` — read the ASCII block yourself in the fixed order of the
   Pattern-reading protocol and write structured notes. No tools needed.

Barrier join — only after waves 1 and 2 all complete:

5. Join every branch output, marking gaps, then write the
   confidence-scored conclusion. Nothing concludes early; never emit a
   verdict from a subset of branches.

## Pattern-reading protocol (regions -> lines -> depth -> masses)

Read the ASCII block in exactly this order. Write one bullet per step.
Do not skip ahead: each step constrains the next.

1. **Regions.** Split the block into background vs foreground. Note
   which columns/rows are near-empty filler (repeating `.`, ` `, `:`)
   and where the dense glyph mass sits (e.g. "dense mass cols 20-70,
   rows 3-55; sparse filler elsewhere"). State the frame: full-figure
   centered, cropped close-up, wide scene, or document page.
2. **Lines.** Trace continuous strokes: outlines, box borders, divider
   rules, limbs, horizons. Note direction (vertical/horizontal/diagonal)
   and breaks. For UI captures, transcribe the box-and-divider layout
   as structure ("header rule row 2, two-column split col 40"), not prose.
3. **Depth.** Read the density ramp as depth: darkest glyphs
   (`@`, `#`, `%`) are shadow/outline/foreground; lightest
   (`.`, `:`, `-`) are highlight/background. Name the light source side
   only if shading is consistent across the whole mass; otherwise mark
   lighting `unknown`.
4. **Masses.** Group connected dark masses into at most 5 named blobs
   with relative positions ("upper-left blob = raised arm",
   "center mass = torso", "lower-right blob = extended leg"). Then state
   in one sentence what figure or layout those masses form.

Rules: describe only glyphs you can point to by row/col. Mark anything
you cannot anchor as `absent`, never as implied. Silhouette-level masses
only — no facial expressions, logos, or small text from ASCII alone.

## Barrier join with proceed-with-gaps

The conclusion waits for all four evidence sections: `ascii_notes`
(Pattern-reading protocol), `ocr_lines`, `meta`, `pattern_verdict`.
Join policy:

- Every section must be present or explicitly marked absent:
  `OCR: absent (no text found)`, `EXIF: absent`, `lighting: unknown`.
- An empty branch never blocks the pass and never retries silently.
  Proceed with the gap marked and confidence lowered.
- A retry is explicit opt-in only: re-running one branch with fallback
  settings, recorded as which engine and settings produced the final
  text. One retry per branch at most.
- After the join, check agreement: do the ASCII masses, the OCR text,
  and the metadata hints describe the same subject? Record `agreement`
  as `agree`, `partial`, or `conflict` with one line of evidence each.

## Confidence-scored conclusion

Emit `confidence` as `high`, `medium`, or `low`, plus `agreement`.

Start at `high`, then apply demotions (each at most once):

- Any evidence section marked absent: demote one level.
- Metadata thin (no EXIF and no filename/directory/caller hints
  beyond the bare path): demote one level.
- OCR and ASCII masses contradict each other: set `low` directly.
- Silhouette re-read disagrees with the first reading: hold
  (no promotion); disagreement escalates toward a context request.

Promotion (at most one level total, never above `high`):

- A conditional silhouette re-read that agrees with the first reading
  on masses only promotes one level. Agreement on detail the ASCII
  cannot carry does not promote.

Agreement rule:

- `high` requires all present sections to agree (`agree`).
- Mixed agreement (`partial`) caps confidence at `medium`.
- `conflict` forces `low`.
- Finalize as `uncertain + best guess` whenever confidence is `low`
  (Context-request escalation decides whether you may ask first).

Absent-section marking stays in the final output verbatim so a later
reader sees exactly what was missing.

## Context-request escalation (single-shot)

When confidence is `low` AND metadata is thin, stop the pass. Do not
guess. Emit exactly one `needs_context` object and halt:

```json
{
  "questions": ["<exact question whose answer unblocks re-conclude>"],
  "missing": ["<evidence section or fact that is absent>"]
}
```

Rules: 1-3 questions, each answerable by the caller (source note,
what the image shows, higher-resolution file). `missing` names the
absent sections from the join.

Re-conclude cap: when new context arrives, re-run only the synthesis
(join + conclusion), at most once. After that single re-conclude,
finalize even if still uncertain, in this fixed shape:

- `verdict: uncertain`
- `best_guess`: one sentence, labeled as a guess.
- `would_resolve`: what evidence would settle it.

Never loop. Never stream partial conclusions before the join.

## Invocation examples (photo | gui | auto)

- Photo (person, mascot, scene, product shot on plain background):
  run the converter in `photo` mode — wide detailed ramp, moderate
  width. Then the protocol sections as written.
- UI screenshot (window, dialog, form, terminal, diagram with text):
  run the converter in `gui` mode — narrow short ramp, high width,
  sharp edges; boxes and dividers must survive as glyph structure.
  Lean on `ocr_lines` for text; ASCII carries layout, not letters.
- Unknown source: run the converter in `auto` mode and record which
  mode it selected; the rest of the protocol is identical.

Record the mode used in the notes header (`mode: photo|gui|auto`).

## Token caps per mode

| mode  | columns | rows                                             | ramp     | worst case |
| ----- | ------- | ------------------------------------------------ | -------- | ---------- |
| photo | 80-120  | natural aspect                                   | detailed | ~120 x 60  |
| gui   | 160-240 | capped, truncate past cap with `[truncated N rows]` marker | short | 200 x 80 |
| auto  | selected mode's caps apply | same                                    | same     | same       |

Keep OCR output to top lines with confidence; keep pattern notes to
the protocol bullets. The join must never drown the conclusion: if a
branch exceeds its cap, truncate with a marker and mark the truncation
in the notes.

## Worked example (mascot fixture: 72 rows x 100 cols)

- Header: `mode: photo` (plain-background figure).
- Regions: sparse `.` filler cols 0-20 and right edge; dense
  `@`/`#`/`%` mass cols 20-70 rows 1-55; narrow
  `*`/`+`/`=` mass rows 44-72 lower-right. Frame: full figure centered.
- Lines: closed outer contour around the center mass; diagonal limbs
  upper-left (raised arm) and lower-right (extended leg); no box rules,
  so not a UI capture.
- Depth: darkest glyphs on the outer contour and lower mass (outline
  and shadow); light filler around. Lighting: `unknown` (flat backdrop).
- Masses: upper-left blob = raised fist; center mass = torso with cap
  brim line rows 3-5; lower blobs = bent knee and extended leg.
  Sentence: a small cartoon mascot figure mid-jump, fist raised.
- Join: OCR `absent (no text found)`; EXIF `absent`; filename hint
  thin. Agreement: sections present agree → `partial`
  (two sections absent).
- Conclusion: start `high`, demote twice (OCR absent, meta thin) →
  `low` + thin meta → emit `needs_context` (`questions`: ["What
  character or subject is this image of?", "Where did this file come
  from?"], `missing`: ["ocr_lines", "meta.exif"]) and stop, no guessing.
  On re-conclude with a source note naming the subject, synthesis
  re-runs once → finalized verdict with raised confidence.
