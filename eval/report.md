# vascii eval report — dev-harness bake-off (change `vascii-skill`, tasks 6.2–6.3)

Date (UTC): 2026-09-03. Source of every number: `eval/results/*.jsonl`
(281 rows), counted with python from the files; nothing hand-estimated.
Result and dataset files are read-only inputs to this report; this report
changes none of them.

## 1. Per-shard tally (methodology differs per shard — read the caveats)

| shard | rows | correct | accuracy | confidence split | methodology note |
| --- | --- | --- | --- | --- | --- |
| `photos_01.jsonl` | 45 | 45 | 100.0% | high 7 / medium 34 / low 4 | NON-BLIND. Labels visible during grading; pattern-brief + inverse-validated reads. Measures protocol compliance, not blind recognition. |
| `photos_02.jsonl` | 46 | 22 | 47.8% | high 1 / medium 24 / low 21 | BLIND heuristic lane: verdicts are coarse buckets (`outdoor scene`, `figure subject`, `waterscape`, …), finalized as `uncertain + best guess` at low confidence. Closest thing here to a blind photo score. |
| `gui_01.jsonl` | 51 | 49 | 96.1% | high 49 / medium 2 | OCR-KEYWORD lane: `ocr_hit` 51/51 (100%). Correct = label keywords / app tokens found in OCR text with branch agreement. Includes 2 stale captures (see §3). |
| `gui_02.jsonl` | 50 | 22 | 44.0% | high 43 / medium 7 | STRICT token-recall lane: `ocr_hit` 50/50 (100%) yet correct only 22/50. Verdict must name the app/page subject, not merely contain OCR text. Includes 10 downscaled small-font crops, 0/10 correct. |
| `diagrams_01.jsonl` | 45 | 45 | 100.0% | high 37 / medium 8 | Sprite/diagram lane with RICH filename hints in 45/45 rows; inverse used in 37/45. Filename + silhouette agreement do heavy lifting. |
| `diagrams_02.jsonl` | 44 | 44 | 100.0% | high 16 / medium 18 / low 10 | Same lane, harder set (flowcharts, `ocr_hit` 31/44); filename hints rich in 44/44 rows; inverse used in 19/44. |
| **overall** | **281** | **227** | **80.8%** | — | **NOT a blind-accuracy claim.** See §2. |

Coverage check: the 281 result rows are unique files; all 280
`eval/dataset/manifest.jsonl` entries have a result row, plus one extra
(`fixtures/images.jpeg`, mascot fixture).

## 2. Overall tally with honest caveats

- Raw tally: **227/281 = 80.78%** rows marked `"correct": true`.
- This number MUST NOT be quoted as blind accuracy. It mixes a non-blind
  lane (photos_01, 45/45 with labels visible), an OCR-keyword lane
  (gui_01, 49/51), filename-hint-assisted lanes (diagrams, 89/89), and two
  strict/blind lanes that score far lower (photos_02 22/46 = 47.8%,
  gui_02 22/50 = 44.0%).
- The two lanes closest to blind, unaided reading — photos_02 and gui_02 —
  combine to **44/96 = 45.8%**. That, not 80.8%, is the figure to use when
  anyone asks "how well does it read unseen images".
- Confidence is roughly calibrated in the blind lanes (photos_02: 21 low /
  24 medium / 1 high) but overconfident in gui_02 (43 high despite 28
  misses): high OCR confidence plus layout agreement promotes confidence
  even when the subject classification is wrong.

## 3. Failure patterns (observed in the rows, not assumed)

- Photo specifics ceiling (photos_02, 24 misses): silhouette-level ASCII
  supports coarse buckets only. Misses collapse to `outdoor scene` (11
  rows incl. `uncertain` variants), `figure subject` (10), `waterscape`
  (6), `text sign` (5). Species, names, interiors vs exteriors
  (concert hall → `outdoor scene`, stone structure indoors → `outdoor
  scene`, cathedral arches → `outdoor scene`) are unrecoverable at this
  resolution by design.
- Water bias: horizontal banding reads as water. `photo_049` (two girls
  jumping) → `waterscape`; `photo_054` (snowy mountain village) →
  `waterscape`; `photo_079` (ocean waves on rocks, genuinely water) →
  generic `outdoor scene`. Banding direction alone does not discriminate.
- Small-font recovery rarely decisive (gui_02): all 10 downscaled
  `gui_small_*` crops are incorrect (0/10) under strict recall, and all 50
  gui_02 rows record "high-accuracy fallback attempted, no new lines".
  Text is recovered (100% OCR hit) but the verdict still misses the
  subject — recovery without classification buys little.
- OCR fires, classification misses (gui_02, 28 misses): `local_chat_slack`
  (dense sidebar chat), `gui_web_lobsters`, `gui_web_reddit`,
  `local_calendar` (month grid), `local_editor_diff`, `local_mob_chat`
  read as generic `document page` despite rich OCR text. Layout-first
  verdicts under-specify dense interactive UIs.
- Inverse agreement ≈ stability, not correctness: photos_01 shows
  agreement 1.0 / promoted in 45/45 rows — alongside non-blind labels.
  Diagrams_01 promotes 37/45 on agreement. Agreement measures re-read
  stability of masses; it cannot confirm a label it never saw.
- EXIF absent everywhere: 0/281 rows record present EXIF. Explicitly
  marked absent in 261 rows (45 + 44 + 51 + 50 + 45 + 26); the remaining
  20 photos_02 rows carry thin filename-only metadata with no EXIF
  mention. Every conclusion therefore takes the metadata-thin demotion
  path; filename/dir hints and caller notes are the only metadata signal.
- OCR watermark/credit noise (photos_01): OCR is present in 43/45 rows
  but is license/credit fragments (`cc-nc-nd`, photographer names,
  `Pixsy`, `MGoBlog`) — neutral junk for the reading. Masses carry those
  verdicts; the join correctly treats credit text as non-evidence.
- Stale captures (gui_01, the only 2 misses): `gui_cloud_cloudflare.png`
  actually renders a Render dashboard (OCR shows `render`, not
  `cloudflare`); `gui_docs_archwiki.png` actually shows an Anubis
  "Access Denied" block page, not the install guide. Both are dataset
  staleness, correctly graded `correct: false` — the pipeline read what
  was on screen.

## 4. Frozen pins and fallback rules (bake-off winners, tasks 6.2)

- ASCII core: hand-rolled Pillow + numpy converter (`img2ascii.py`,
  `photo | gui | auto` modes, recorded forward params). Rejected as deps:
  ascii-magic, img2ascii-py, OpenCV edge overlay, `art`, pyascii-likes.
- Default OCR: RapidOCR (onnxruntime CPU, PP-OCRv6 det/rec; engine
  docstring pins 3.9.2) on an internally upscaled copy (auto 3x/2x/1x by
  image size; boxes rescaled to original coordinates). Per-line text +
  confidence; `result.vis()` never called (would fetch a font).
- High-accuracy fallback (small 11–13px UI fonts): `--high-accuracy`
  raises det unclip ratio 1.5 → 1.8 and det limit side 736 → 960;
  producing engine always recorded (`rapidocr-…-high-accuracy`).
- Second fallback: PaddleOCR path (`--engine paddle`, PaddleOCR 3.7.0 /
  PaddleX PP-OCRv6); absent package prints the exact install command and
  exits non-zero instead of failing cryptically.
- Retry discipline: one explicit retry per branch at most; gaps proceed
  marked absent with confidence lowered; single re-conclude cap, then
  finalize as `uncertain + best guess`.
- Inverse check stays conditional only: low/medium confidence or branch
  disagreement, invertible (ordered-ramp, mono, undithered) output;
  GUI short-ramp output always skips with reason recorded.
- Pinned runtime deps (`skills/vascii/requirements.txt`):
  `Pillow==12.3.0`, `numpy==2.5.1`, `rapidocr-onnxruntime==1.2.3`,
  `onnxruntime==1.29.0`.
- Token caps per mode (SKILL.md §Token caps): photo 80–120 cols, natural
  aspect (worst ~120×60); gui 160–240 cols, capped 200×80 with
  `[truncated] showing N/M rows` marker; auto inherits the selected
  mode's caps. OCR kept to top lines with confidence; pattern notes to
  protocol bullets.
- Eval/grading harness tooling is dev-only and lives outside the shipped
  skill: shipped artifacts (`SKILL.md` + scripts + pinned deps) reference
  no browser, vision-service, MCP, network, or absolute-path runtime
  dependency.

## 5. Validation proof (task 6.3)

- `openspec validate --all --strict --no-interactive` → 
  `✓ change/vascii-skill` · `Totals: 1 passed, 0 failed (1 items)`.
- Determinism re-proof: `img2ascii.py
  eval/dataset/diagrams/sprite_alien.png --mode photo` run twice →
  sha256 `57b3ebec…db5127` both runs, `cmp` identical
  (`DETERMINISM_OK`). Same-input-twice byte-identical holds.
- Banned-reference grep: no `vsense` / `acob` / `mcp` references in
  `skills/` (docs or code); no `localhost` / `http(s)` runtime URLs in
  shipped scripts — only comments documenting what the skill must NOT
  fetch. Offline rule intact (no socket/urllib/requests imports).
- Token-cap check (live run, sprite_alien fixture): photo 100 cols × 37
  rows (within 80–120 / ~120×60); gui 200 cols × 73 rows (within
  160–240 / ≤80); auto inherits photo 100×37. Forced `--rows 10` in gui
  mode emits `[truncated] showing 9/73 rows` with total ≤ cap. Row-cap
  truncation with marker verified.
- Manifest/results integrity: 281 unique result rows; 280/280 manifest
  entries covered + 1 fixture extra; results files untouched (read-only).

## 6. Bottom line for tasks 6.1–6.3

- 6.1 coverage: photos (91), GUI incl. mobile/small-font/local captures
  (101), diagrams incl. sprites, flowcharts, Mario-class mascot fixture
  (89) — 281 rows against 280 manifest entries + fixture. Done, evidence
  above.
- 6.2 bake-off verdict: hand-rolled core + RapidOCR default + Paddle
  fallback + documented token caps confirmed as frozen pins (§4). Done.
- 6.3 validation: strict validation passes, determinism re-proved,
  banned-reference grep clean, token caps verified live. Done.
- Standing limitation, stated plainly: blind coarse-subject reading is
  ~46% (44/96 on photos_02 + gui_02); the 80.8% overall tally is a
  mixed-methodology composite and must never be presented as blind
  accuracy.
