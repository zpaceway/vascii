#!/usr/bin/env python3
"""Blind harness builder: snapshot -> EXIF-stripped hashed inputs + sealed labels.

Run ONCE by the harness author (NOT the tester)::

    python3 eval/blind/build.py

Reads eval/dataset/manifest.jsonl (280 rows), writes under eval/blind/:
  freeze.sha256          sha256 of manifest + every source file (pre-copy snapshot)
  inputs/<sha16>.png     blind pixels only, EXIF/XMP/PNG-text chunks stripped
  labels.jsonl.sealed    hash -> {category, label, source, has_text} (chmod 600)

The tester receives ONLY inputs/ + run.sh + the frozen skill. The hash->original
mapping lives ONLY in labels.jsonl.sealed, which the tester must never open.
Re-runs after any label exposure require a FRESH salt (pass --salt).
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import stat
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BLIND = os.path.join(REPO, "eval", "blind")
MANIFEST = os.path.join(REPO, "eval", "dataset", "manifest.jsonl")
INPUTS = os.path.join(BLIND, "inputs")
FREEZE = os.path.join(BLIND, "freeze.sha256")
SEALED = os.path.join(BLIND, "labels.jsonl.sealed")


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def resolve_source(rel: str) -> str:
    # Manifest prefixes: photos/.., gui/.. (relative to eval/dataset/),
    # eval/dataset/diagrams/.. (relative to repo root).
    if rel.startswith("eval/"):
        return os.path.join(REPO, rel)
    return os.path.join(REPO, "eval", "dataset", rel)


def strip_to_png(src_bytes: bytes) -> bytes:
    """Re-render pixels to a fresh PNG: drops EXIF/XMP/COMMENT/text chunks.

    The image is re-created from raw pixels so no metadata chunk survives;
    alpha is flattened onto white for byte-stable RGB output.
    """
    from PIL import Image

    img = Image.open(io.BytesIO(src_bytes))
    img.load()
    if img.mode == "RGBA":
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        img = bg
    else:
        img = img.convert("RGB")
    fresh = Image.frombytes("RGB", img.size, img.tobytes())
    buf = io.BytesIO()
    fresh.save(buf, format="PNG")  # no exif=, no pnginfo= -> no metadata chunks
    return buf.getvalue()


def main() -> int:
    ap = argparse.ArgumentParser(description="Build the true-blind harness inputs.")
    ap.add_argument("--salt", default="", help="Hash salt; change for a fresh run.")
    args = ap.parse_args()

    rows = [json.loads(l) for l in open(MANIFEST) if l.strip()]
    if len(rows) != 280:
        print(f"refusing: manifest has {len(rows)} rows, expected 280", file=sys.stderr)
        return 1

    os.makedirs(INPUTS, exist_ok=True)

    # 1. Snapshot: sha256 of manifest + every source file, pre-copy.
    freeze_lines = ["# blind-input snapshot: sha256 of sources pre-copy",
                    "# conversion: all inputs normalized to RGB PNG, EXIF/XMP stripped",
                    f"# salt: {args.salt!r}" if args.salt else "# salt: (none)"]
    freeze_lines.append(f"{sha256_file(MANIFEST)}  eval/dataset/manifest.jsonl")
    for r in rows:
        src = resolve_source(r["file"])
        if not os.path.exists(src):
            print(f"refusing: missing source {src}", file=sys.stderr)
            return 1
        freeze_lines.append(f"{sha256_file(src)}  {r['file']}")
    with open(FREEZE, "w") as f:
        f.write("\n".join(freeze_lines) + "\n")

    # 2. Hashed EXIF-stripped copies + sealed label map.
    # Hash preimage = salt + manifest index + clean pixels. The index keeps
    # pixel-identical duplicates distinct (dataset contains one such pair:
    # wiki_11..._ans.png == wiki_12... byte-for-byte, different labels);
    # sha256 is one-way so the index leaks nothing to the tester.
    seen: dict[str, str] = {}
    sealed_lines = []
    for i, r in enumerate(rows):
        with open(resolve_source(r["file"]), "rb") as f:
            raw = f.read()
        clean = strip_to_png(raw)
        digest = hashlib.sha256(args.salt.encode() + i.to_bytes(4, "big")
                                + clean).hexdigest()
        h, stem = digest[:16], digest[:16] + ".png"
        if h in seen:  # 3. Collision guard on the 16-hex prefix.
            print(f"refusing: hash-prefix collision {h}: {seen[h]} vs {r['file']}",
                  file=sys.stderr)
            return 1
        seen[h] = r["file"]
        with open(os.path.join(INPUTS, stem), "wb") as f:
            f.write(clean)
        sealed_lines.append(json.dumps({
            "h": h,
            "sha256": digest,
            "category": r["category"],
            "label": r["label"],
            "source": r.get("source", ""),
            "has_text": bool(r.get("has_text", False)),
        }))
    with open(SEALED, "w") as f:
        f.write("\n".join(sealed_lines) + "\n")
    os.chmod(SEALED, stat.S_IRUSR | stat.S_IWUSR)  # 600: owner read/write only

    # 4. Quarantine check: no hash->original side files may linger in eval/blind/.
    for name in sorted(os.listdir(BLIND)):
        if name not in ("build.py", "run.sh", "score.py", "TESTER_PROTOCOL.md",
                        "freeze.sha256", "inputs", "labels.jsonl.sealed",
                        "predictions.jsonl", "scores.md"):
            print(f"warning: unexpected file in eval/blind/: {name}", file=sys.stderr)

    print(f"built {len(seen)} blind inputs -> {INPUTS}")
    print(f"sealed labels: {SEALED} (mode 600)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
