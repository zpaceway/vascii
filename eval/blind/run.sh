#!/usr/bin/env bash
# Blind run entry: pixels-only loop over eval/blind/inputs/.
#
# The tester sees ONLY inputs/ pixels (+ the frozen skill). NEVER open
# eval/dataset/manifest.jsonl, labels.jsonl.sealed, eval/results/, or
# eval/report.md during the run (see TESTER_PROTOCOL.md).
#
# For each inputs/<h>.png this runs the frozen skill (img2ascii.py in the
# requested --mode + local ocr.py) and appends ONE template line to
# predictions.jsonl:
#   {"h": "<hash>", "verdict": "", "confidence": "", "mode": "...", "ocr_text": "..."}
# The tester then fills "verdict" (free-text subject) and "confidence"
# (high|medium|low) per hash from the ASCII/OCR evidence alone, freezes
# predictions.jsonl (record sha256), and only then runs score.py.
#
# Usage: ./run.sh [--mode photo|gui|auto]   (default: auto)
set -euo pipefail
cd "$(dirname "$0")"

MODE="${1:-auto}"
case "$MODE" in --mode=*) MODE="${MODE#--mode=}";; esac
# (resolve robustly regardless of symlinked cwd)
SKILL="$(cd "$(dirname "$0")/../../skills/vascii/scripts" && pwd)"

: > predictions.jsonl
count=0
for img in inputs/*.png inputs/*.jpg; do
  [ -e "$img" ] || continue
  h="$(basename "$img")"; h="${h%.*}"
  python3 "$SKILL/img2ascii.py" "$img" --mode "$MODE" --output "/tmp/blind_$h.txt" >/dev/null
  ocr="$(python3 "$SKILL/ocr.py" "$img" | python3 -c \
    'import json,sys; d=json.load(sys.stdin); print("\n".join(l.get("text","") for l in d.get("lines",[]))[:500])')"
  python3 - "$h" "$MODE" "$ocr" <<'EOF' >> predictions.jsonl
import json, sys
h, mode, ocr = sys.argv[1], sys.argv[2], sys.argv[3]
print(json.dumps({"h": h, "verdict": "", "confidence": "",
                  "mode": mode, "ocr_text": ocr}))
EOF
  count=$((count + 1))
done
echo "wrote $count template rows -> predictions.jsonl (fill verdict/confidence, then freeze)"
