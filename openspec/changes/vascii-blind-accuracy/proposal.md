## Why

The 44/96 blind-comparable figure (photos_02 22/46, gui_02 22/50) is the honest measure of vascii, but no current shard is grade-blind: all 281 result rows embed manifest labels, 179/280 filenames overlap label tokens, and GUI origin URLs double as hints. We cannot trust any improvement claim until the harness is blind, and three deep failure analyses have named concrete prompt/config fixes worth +10–16 (photos) and 28/28 miss resolution (GUI) that deserve a measured trial.

## What Changes

- Adds `eval/blind/` true-blind harness: EXIF-stripped sha-hashed inputs, chmod-600 sealed labels, pixels-only tester protocol, post-hoc `score.py` with frozen semantic rubric, hypernym/alias sets, Wilson CI + two-proportion significance vs the 44/96 baseline.
- Modifies `skills/vascii/SKILL.md` reading protocol (prompt-only): water-bias disambiguation, coarse-taxonomy calibration, interior/exterior cues, close-up router, species abstention, OCR salience guard, OCR-led GUI verdict order, structural templates (crop/mobile/dense-UI/challenge), subject-evidence confidence rule.
- Adds `skills/vascii/data/keyword_packs.json` (per-app token sets) and ships it as config, not code.
- Tunes defaults (config, no new engine): GUI small-input high-accuracy by default, narrow-page row-cap relief, photo contrast percentile stretch, single EXIF-absent demotion.
- Dataset hygiene: relabels 4 stale captures (Render dashboard, Anubis block ×2 via crop inheritance, Reddit network-block) so truthful reads score correct.
- Baseline-first discipline: blind-run the current skill before fixes land, then re-run after; keep the new config only if blind k/n clears the frozen bar (CI strictly above 0.458, p<0.05, ≈≥56/96), else discard.

## Capabilities

### New Capabilities

- `vascii/blind-harness`: sealed-label blind eval harness with deterministic scoring and significance reporting.

### Modified Capabilities

- None. The skill-behavior trial (prompt/config tuning) missed the frozen significance bar (110/190, p=0.053) and was reverted per the keep-or-discard gate; only dataset hygiene (4 truthful relabels) was kept.

## Impact

- `skills/vascii/SKILL.md` prompt sections rewritten; new `data/keyword_packs.json`; default flag changes in `ocr.py`/`img2ascii.py` (backward compatible, all overrides still available).
- `eval/blind/` is dev-only and never referenced by shipped artifacts; agnostic/offline contract unchanged.
- Manifest relabels touch 4 rows with reason recorded; stale originals optionally re-captured later.
