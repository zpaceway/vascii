# Tester protocol — blindness contract (binding)

You are the BLIND TESTER. You receive ONLY:

- `eval/blind/inputs/` (hashed pixel files, no names, no order signal)
- `eval/blind/run.sh` (pixels-only loop)
- the frozen skill (`skills/vascii/`, offline use only)

## 1. Forbidden reads

During the run, NEVER open, `cat`, `grep`, or search:

- `eval/dataset/manifest.jsonl` (labels + source URLs + `has_text` flags)
- `eval/blind/labels.jsonl.sealed` (the hash→label map; chmod 600)
- `eval/results/` (any shard — every row carries its label verbatim)
- `eval/report.md` (contains labels and per-row notes)
- any file outside `eval/blind/inputs/` that could reveal a subject,
  filename, URL, or label. No repo-wide `grep` for candidate words.

## 2. No filename / order / metadata reconstruction

- Refer to items ONLY by hash stem (`<h>` in `inputs/<h>.png`).
- `ls` order, file sizes, and timestamps are NOT labels; the scorer
  shuffles anyway. Do not sort, sequence, or narrate items as a series.
- Do not inspect EXIF/XMP/PNG-text chunks (inputs are stripped; keep it
  that way — never run metadata-dump tools on them).

## 3. Offline rule (report §4 stands)

No network calls, no vision-service APIs, no MCP calls. The frozen skill
(`img2ascii.py` + local `ocr.py`) is the only perception path.

## 4. Predictions schema (exact — §3)

One line per input hash in `predictions.jsonl`:

```json
{"h": "<hash>", "verdict": "<free-text subject>", "confidence": "high|medium|low", "mode": "photo|gui|auto", "ocr_text": "<top lines or empty>"}
```

- `h` MUST equal the input filename stem (the join key).
- No `label`, `filename`, or `notes` fields. Ever.
- Missing hashes score as incorrect; extra hashes are ignored with a warning.

## 5. Freeze before scoring

1. Fill every `verdict`/`confidence` from ASCII/OCR evidence alone.
2. Record `sha256sum predictions.jsonl`.
3. Only THEN run `score.py`. Any re-grade uses the frozen file.
4. If any label was ever exposed to you (accident counts), STOP: the run
   is void and the re-run requires a FRESH hash salt (`build.py --salt`).

## 6. Verdict guidance (granularity, §4.1)

- photo: coarse bucket is enough (waterscape / outdoor scene / figure /
  architecture-or-structure / vegetation / animal / text sign).
  `uncertain + best guess: <right bucket>` counts — say so explicitly.
- gui: name the app/page subject (e.g. "MDN docs", "Slack chat",
  "month calendar"), not just OCR words; generic "document page" fails.
- diagram/sprite: name the entity (`alien sprite`, `bar chart`, …); on
  text-bearing figures ALSO quote ≥1 on-figure text span you actually read
  via OCR (it must appear in your `ocr_text`).
- `confidence` never changes correctness — report it honestly.
