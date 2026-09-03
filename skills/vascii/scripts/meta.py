#!/usr/bin/env python3
"""vascii meta - file metadata with thin-source handling.

Reports EXIF where present plus file stat (size, dimensions, format),
falling back to filename and directory hints and a caller-supplied
source note, in this priority order:

    exif > stat > filename/dir hints > --source-note

Output is a single JSON object on stdout; the script exits 0 on
success. Images without EXIF (e.g. screenshots) still yield context:
stat plus filename/directory hints with "exif_present" marked false.

Example:
    python3 meta.py photo.jpg --source-note "phone camera, noon"
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone


TOOL_NAME = "vascii-meta"

TOKEN_SPLIT = re.compile(r"[^A-Za-z0-9]+")


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="EXIF + stat + path-hint metadata for one image (JSON to stdout)."
    )
    p.add_argument("image", help="input image file path")
    p.add_argument(
        "--source-note",
        default=None,
        help="caller-supplied source note (lowest priority context)",
    )
    return p.parse_args(argv)


def json_safe(value):
    """Convert EXIF/info values to JSON-safe primitives."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8")
        except UnicodeDecodeError:
            return value.decode("latin-1", errors="replace")
    if isinstance(value, (tuple, list)):
        return [json_safe(v) for v in value]
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    try:
        import numbers

        if isinstance(value, numbers.Rational):
            return float(value)
    except ImportError:
        pass
    return str(value)


def read_exif(img):
    """Return (exif_present, exif_dict) decoded with human tag names."""
    try:
        from PIL.ExifTags import TAGS
    except ImportError:  # Pillow missing is reported by the caller below
        raise
    try:
        raw = img.getexif()
    except Exception:
        return False, {}
    if not raw:
        return False, {}
    decoded = {}
    for tag_id, value in raw.items():
        name = TAGS.get(tag_id, "Tag%d" % tag_id)
        decoded[str(name)] = json_safe(value)
    if not decoded:
        return False, {}
    return True, decoded


def path_hints(path):
    """Filename/dir hint tokens; basenames only, never absolute paths."""
    dirname, filename = os.path.split(path)
    stem, suffix = os.path.splitext(filename)
    tokens = [t for t in TOKEN_SPLIT.split(stem) if t]
    parents = []
    head = dirname
    for _ in range(2):
        head, tail = os.path.split(head)
        if not tail:
            break
        parents.append(tail)
    parents.reverse()
    return {
        "filename": filename,
        "stem_tokens": tokens,
        "suffix": suffix.lower() or None,
        "parent_names": parents,
    }


def main(argv=None):
    args = parse_args(argv)
    path = args.image

    try:
        from PIL import Image
    except ImportError:
        print(
            "error: Pillow is required to read image metadata.\n"
            "Install it with: python3 -m pip install Pillow",
            file=sys.stderr,
        )
        return 2

    if not os.path.exists(path):
        print("error: image file not found: %s" % path, file=sys.stderr)
        return 1

    try:
        st = os.stat(path)
    except OSError as exc:
        print("error: cannot stat %s: %s" % (path, exc), file=sys.stderr)
        return 1

    try:
        img = Image.open(path)
        img.load()
    except OSError as exc:
        print("error: cannot read image %s: %s" % (path, exc), file=sys.stderr)
        return 1

    exif_present, exif = read_exif(img)

    container_info = {}
    try:
        for key, value in (img.info or {}).items():
            container_info[str(key)] = json_safe(value)
    except Exception:
        container_info = {}

    mtime = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat()

    context_used = ["stat", "filename_dir_hints"]
    if exif_present:
        context_used.insert(0, "exif")
    if args.source_note:
        context_used.append("source_note")

    report = {
        "tool": TOOL_NAME,
        "image": path,
        "format": img.format,
        "mode": img.mode,
        "width": img.width,
        "height": img.height,
        "file_size_bytes": st.st_size,
        "mtime_utc": mtime,
        "exif_present": exif_present,
        "exif": exif,
        "container_info": container_info,
        "hints": path_hints(path),
        "source_note": args.source_note,
        "priority": ["exif", "stat", "filename_dir_hints", "source_note"],
        "context_used": context_used,
    }
    if not exif_present:
        report["note"] = (
            "no EXIF present (typical for screenshots); "
            "context falls back to stat plus filename/directory hints"
        )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
