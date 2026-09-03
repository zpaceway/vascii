## Context

See proposal.md Why. Prior change `vascii-skill` (17/17 done): frozen pins are hand-rolled `img2ascii.py`, RapidOCR 3.9.2 default, Paddle fallback, token caps. Blind-comparable baseline 44/96 = 45.8%, Wilson 95% [0.362, 0.558]. Three analyses ground this design: `/tmp/photo_analysis.md` (24 misses, fixes 1–8), `/tmp/gui_analysis.md` (28 misses + 2 stale, fixes F1–F7), `/tmp/harness_analysis.md` (leakage inventory 179/280 token-hit, `eval/blind/` design, re-test bar ≥56/96).

## Goals / Non-Goals

**Goals:**
- Trustworthy blind number for the current skill before any fix lands.
- Prompt/config-only accuracy lift (no new engine, no network, no re-capture except stale originals).
- Keep-or-discard verdict with frozen statistical bar; discard path costs nothing but the trial.

**Non-Goals:**
- New OCR engines or model training; photometric restoration; multi-round interrogation; touching shipped offline/agnostic contract.

## Decisions

- **Baseline first, fixes second.** Rationale: without a blind number for the current skill, any post-fix score is incomparable (old 44/96 came from leaky lanes). The harness runs once on the frozen skill, seals the baseline, then fixes land and it re-runs. Alternative (fixes first) rejected: confounds harness effects with fix effects.
- **Photo fixes are prompt-only deltas to SKILL.md pattern protocol** (photo fixes 1–6, 8): water rule requires banding + mirror symmetry + low-center mass (sky-top runs and dark_frac<0.03 snowfields never water); fixed verdict vocabulary `{waterscape, vegetation, mountain, sky, architecture, interior, figure, object/still-life, text-sign, close-up, night}` with routing thresholds (vertical-density>0.06 architecture, upper-mass triad interior, mass-fills-frame close-up); interior test (enclosure 3+ sides, overhead arcs, wall verticals); close-up router (filler-minimal + dark_frac extremes forbids scene tokens); species abstention (coarse hypernym ceiling); OCR salience guard (text-sign only with planar bounds, else `figure with visible text`); single EXIF-absent demotion. Rationale: 71% of photo misses are vocabulary/routing, not perception — masses are located, filed wrongly.
- **GUI fixes are OCR-led reordering + data + templates** (F1–F5): head names `{App} {page-type}` from OCR tokens before any layout phrase; `data/keyword_packs.json` maps app→token sets and the head cites the fired pack; structural templates for crops (name parent), narrow-mobile (hedge layout, lean OCR), dense UIs (calendar/chat/diff/editor/inbox/thread/file-manager/IDE discriminators), challenge pages (block head, never label subject). Confidence: `high` requires named subject + ≥2 OCR tokens + one structural cue; generic heads cap at medium; filename/OCR conflict follows OCR at medium. Rationale: recovery is solved (100% hit both lanes) — 26/28 misses already contain the subject in the snippet.
- **Config tuning without new deps** (photo fix 7, F5): photo contrast 1st–99th percentile stretch; photo width 120 default for thin-stroke rows; GUI small-side<480px implies high-accuracy flags; narrow-page row-cap relief/windowing for 79/238 truncations. Rationale: enabling fixes — spreads mid-tones so fixes 1–3 cues stay visible, keeps thin strokes.
- **Harness per `/tmp/harness_analysis.md` §3–§6**: `eval/blind/{build.py,inputs/,labels.jsonl.sealed,run.sh,predictions.jsonl,score.py,scores.md,freeze.sha256}`; EXIF-stripped hashed copies; pixels-only tester protocol; frozen rubric (photo coarse-bucket, GUI strict subject-naming, diagram entity+salient-text), hypernym/alias sets, stale+fixture exclusions; significance rule (two-proportion z vs 44/96, α=0.05, plus Wilson non-overlap; ≈≥56/96 clears). Rationale: exact design already reviewed; implement as specified.
- **Dataset hygiene as config** (F7): 4 relabels with reason recorded (Render dashboard, Anubis block, inherited crop, Reddit challenge); stale stays miss until relabeled. Rationale: truthful reads must score correct or the metric punishes honesty.
- **Keep-or-discard gate**: adopt new config only if blind re-run clears the frozen bar AND no shipped-contract violation (determinism, offline, caps, banned-refs re-verified). Else revert skills/ to the frozen pins and keep only the harness + hygiene. Rationale: user's explicit instruction — discarding is a first-class outcome.

## Risks / Trade-offs

- [Fixes overfit to 96 analyzed rows] -> Blind re-test uses all 280 hashed rows across 3 categories, not just the analyzed shards; gate requires significance, not point estimate.
- [Keyword packs become label leakage in reverse] -> Packs are app-vocabulary (public knowledge: "Inbox", "Algolia"), never dataset-specific strings; scorer aliases are frozen pre-run.
- [Prompt bloat drowns the reader] -> Templates are conditional branches, not preamble; token caps re-verified after the rewrite.
- [Relabels accused of grade inflation] -> Relabels record pixel evidence (OCR text of actual render) and are reported separately; headline shows both denominators.
- [Harness salt reuse across runs] -> Fresh hash salt per blind run if any tester saw labels; predictions frozen (sha256) before scoring.
