#!/usr/bin/env python3
"""vascii img2ascii - deterministic image-to-ASCII core.

Modes: photo | gui | auto.
  photo: 80-120 cols (default 100), 70-step Bourke detailed ramp.
  gui:   160-240 cols (default 200), classic 10-step short ramp, mono fixed-width.
  auto:  deterministic heuristic (large images -> gui, small -> photo).

Pipeline (deterministic, offline, stdlib+Pillow+numpy only):
  open -> convert L -> LANCZOS downscale -> min-max contrast stretch
  -> fixed integer map onto ordered density ramp -> row-cap truncation.

Mapping is dark->dense: pixel 255 (white) -> ramp[0] (' '),
pixel 0 (black) -> ramp[-1] ('@' or '$'). Integer math only:
  idx = (255 - v) * (n - 1) // 255

Output is UTF-8 mono text only, no ANSI color. Same inputs+flags
always yield byte-identical output (no timestamps, no randomness,
no absolute paths in output).

Forward params (ramp, width, aspect, resample, contrast, ...) are
emitted as sorted-keys JSON via --params-only (stdout), --sidecar
FILE, or auto sidecar <output>.json when --output is used.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

GUI_RAMP = " .:-=+*#%@"  # classic 10-step, light -> dark
PHOTO_RAMP = " .'`^\",:;Il!i><~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"  # Bourke 70-step, light -> dark

CHAR_ASPECT = 0.55
RESAMPLE_NAME = "LANCZOS"

PHOTO_DEFAULT_WIDTH = 100  # within 80-120
GUI_DEFAULT_WIDTH = 200  # within 160-240
DEFAULT_MAX_ROWS = 80  # GUI 200x80 worst case per design

TRUNCATED_MARKER_FMT = "[truncated] showing {shown}/{total} rows"


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="Deterministic image-to-ASCII (photo|gui|auto). ASCII to stdout unless --output given."
    )
    p.add_argument("image", help="input image file path")
    p.add_argument("--mode", choices=["photo", "gui", "auto"], default="auto")
    p.add_argument("--width", type=int, default=None, help="target columns override")
    p.add_argument(
        "--rows",
        type=int,
        default=None,
        help="row-cap override (max output lines incl. marker; 0 = no cap)",
    )
    p.add_argument("--aspect", type=float, default=None, help="char aspect override (default 0.55)")
    p.add_argument("--ramp", type=str, default=None, help="custom ramp string override (light->dark)")
    p.add_argument("--contrast", choices=["stretch", "none"], default="stretch")
    p.add_argument("--output", type=str, default=None, help="write ASCII to FILE instead of stdout")
    p.add_argument("--sidecar", type=str, default=None, help="write forward-params JSON to FILE")
    p.add_argument("--params-only", action="store_true", help="print forward-params JSON to stdout, no ASCII")
    return p.parse_args(argv)


def pick_mode(requested: str, w: int, h: int) -> str:
    if requested in ("photo", "gui"):
        return requested
    # auto heuristic: large images (screenshots) -> gui, small (photos) -> photo.
    # Deterministic, pixel-count based, no randomness.
    if max(w, h) >= 800 or (w * h) >= 400_000:
        return "gui"
    return "photo"


def main(argv=None) -> int:
    args = parse_args(argv)

    try:
        from PIL import Image
    except ImportError:
        print("error: Pillow is required (pip install Pillow numpy)", file=sys.stderr)
        return 2
    try:
        import numpy as np
    except ImportError:
        print("error: numpy is required (pip install Pillow numpy)", file=sys.stderr)
        return 2

    if not os.path.isfile(args.image):
        print(f"error: input not found: {args.image}", file=sys.stderr)
        return 2

    # --- open + grayscale ---
    with Image.open(args.image) as im:
        orig_w, orig_h = im.size
        orig_format = im.format or os.path.splitext(args.image)[1].lstrip(".").upper() or "UNKNOWN"
        gray = im.convert("L")

    mode = pick_mode(args.mode, orig_w, orig_h)

    if args.ramp is not None:
        ramp = args.ramp
        ramp_name = "custom"
        if len(ramp) < 2:
            print("error: --ramp must have >= 2 characters", file=sys.stderr)
            return 2
    elif mode == "gui":
        ramp = GUI_RAMP
        ramp_name = "gui_short"
    else:
        ramp = PHOTO_RAMP
        ramp_name = "photo_detailed"

    width = args.width if args.width is not None else (GUI_DEFAULT_WIDTH if mode == "gui" else PHOTO_DEFAULT_WIDTH)
    if width < 1:
        print("error: --width must be >= 1", file=sys.stderr)
        return 2
    aspect = args.aspect if args.aspect is not None else CHAR_ASPECT
    if not (0.1 <= aspect <= 2.0):
        print("error: --aspect must be in [0.1, 2.0]", file=sys.stderr)
        return 2
    rows_cap = args.rows if args.rows is not None else DEFAULT_MAX_ROWS
    if rows_cap is not None and rows_cap < 0:
        print("error: --rows must be >= 0 (0 = no cap)", file=sys.stderr)
        return 2
    if rows_cap == 0:
        rows_cap = None  # no cap

    # --- target geometry: compensate for tall terminal glyphs ---
    target_h = max(1, int(round(orig_h * width / max(1, orig_w) * aspect)))

    # --- LANCZOS downscale (also used for upscale: single deterministic kernel) ---
    small = gray.resize((width, target_h), Image.LANCZOS)

    arr = np.asarray(small, dtype=np.uint8)

    # --- contrast stretch (deterministic min-max) ---
    if args.contrast == "stretch":
        lo = int(arr.min())
        hi = int(arr.max())
        if hi > lo:
            stretched = ((arr.astype(np.int32) - lo) * 255 // (hi - lo)).astype(np.uint8)
        else:
            stretched = arr.copy()  # flat image: nothing to stretch
        contrast = {"mode": "stretch", "low": lo, "high": hi}
    else:
        stretched = arr.copy()
        contrast = {"mode": "none", "low": 0, "high": 255}

    # --- map to ramp (integer math, dark -> dense) ---
    n = len(ramp)
    idx = (255 - stretched.astype(np.int32)) * (n - 1) // 255
    chars = [ramp[i] for i in range(n)]
    lines = ["".join(chars[k] for k in row) for row in idx.tolist()]
    total_rows = len(lines)

    # --- row-cap truncation with explicit marker ---
    truncated = False
    if rows_cap is not None and total_rows > rows_cap:
        truncated = True
        if rows_cap >= 1:
            keep = rows_cap - 1  # last line is the marker so total <= cap
            marker = TRUNCATED_MARKER_FMT.format(shown=keep, total=total_rows)
            lines = lines[:keep] + [marker]
        else:
            lines = []
    output_rows = len(lines)
    ascii_text = "\n".join(lines) + ("\n" if lines else "")

    forward_params = {
        "aspect": aspect,
        "contrast": contrast,
        "height_output": output_rows,
        "height_target": target_h,
        "image": {
            "format": orig_format,
            "height": orig_h,
            "name": os.path.basename(args.image),
            "width": orig_w,
        },
        "invert": True,
        "mode_effective": mode,
        "mode_requested": args.mode,
        "ramp": ramp,
        "ramp_length": n,
        "ramp_name": ramp_name,
        "resample": RESAMPLE_NAME,
        "rows_cap": rows_cap,
        "total_rows": total_rows,
        "truncated": truncated,
        "width": width,
    }
    params_json = json.dumps(forward_params, sort_keys=True, ensure_ascii=False, indent=2) + "\n"

    if args.params_only:
        sys.stdout.write(params_json)
        if args.sidecar:
            with open(args.sidecar, "w", encoding="utf-8") as f:
                f.write(params_json)
        return 0

    if args.output:
        with open(args.output, "w", encoding="utf-8", newline="\n") as f:
            f.write(ascii_text)
        sidecar_path = args.sidecar or (args.output + ".json")
        with open(sidecar_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(params_json)
    else:
        sys.stdout.write(ascii_text)
        if args.sidecar:
            with open(args.sidecar, "w", encoding="utf-8", newline="\n") as f:
                f.write(params_json)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
