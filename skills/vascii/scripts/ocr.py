#!/usr/bin/env python3
"""vascii ocr - local OCR on original image pixels.

Reads the input image file as pixels (never ASCII text) and extracts
printed text with per-line confidence. Output is a single JSON object
on stdout; the script exits 0 even when no text is found (lines == []).

Default engine is RapidOCR (3.9.2, onnxruntime CPU, PP-OCRv6 det/rec).
High-accuracy fallback for small UI fonts (11-13px):

    python3 ocr.py crop.png --high-accuracy

which raises the detection unclip ratio (1.5 -> 1.8) and enlarges the
detection size limit (736 -> 960 long side) so tight glyph boxes merge
less and small text is recovered. The producing engine is always
recorded in the output "engine" field.

Optional PaddleOCR fallback path (PaddleOCR 3.7.0 / PaddleX PP-OCRv6):

    python3 ocr.py crop.png --engine paddle --high-accuracy

requires the `paddleocr` package; when it is absent the script prints
the exact install command and exits non-zero instead of failing
cryptically.

Small-text handling: OCR runs on an internally upscaled *copy* of the
original pixels (LANCZOS). With --upscale auto (default) the scale is
3x when the smaller image side is < 160px, 2x when it is < 480px, and
1x otherwise, so 11-13px glyphs reach a detector-friendly height.
Reported boxes are rescaled back to original pixel coordinates.
Override with --upscale 1|2|3.

Offline notes: rapidocr is imported lazily (never at module import, so
`--help` and missing-dependency reports need no downloads), and
`result.vis()` is never called (it would fetch a display font).
First-time model weights are resolved by the engine's own cache; to
work fully offline, vendor or pre-fetch them before disconnecting.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import importlib.util
import json
import sys


TOOL_NAME = "vascii-ocr"

DEFAULT_DET_LIMIT = 736
HIGH_ACC_DET_LIMIT = 960
DEFAULT_UNCLIP = 1.5
HIGH_ACC_UNCLIP = 1.8

SMALL_SIDE_3X = 160
SMALL_SIDE_2X = 480


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="Local OCR on original pixels with per-line confidence (JSON to stdout)."
    )
    p.add_argument("image", help="input image file path (read as pixels, never ASCII)")
    p.add_argument(
        "--engine",
        choices=["rapidocr", "paddle"],
        default="rapidocr",
        help="OCR engine (default rapidocr; paddle is the documented fallback)",
    )
    p.add_argument(
        "--high-accuracy",
        action="store_true",
        help="fallback params: det unclip ratio %.1f->%.1f and det limit %d->%d"
        % (DEFAULT_UNCLIP, HIGH_ACC_UNCLIP, DEFAULT_DET_LIMIT, HIGH_ACC_DET_LIMIT),
    )
    p.add_argument(
        "--upscale",
        choices=["auto", "1", "2", "3"],
        default="auto",
        help="internal upscale of the pixel copy (default auto: 3x/2x/1x by image size)",
    )
    p.add_argument(
        "--min-conf",
        type=float,
        default=0.0,
        help="drop lines below this confidence (default keeps all)",
    )
    return p.parse_args(argv)


def auto_scale(width, height):
    small = min(width, height)
    if small < SMALL_SIDE_3X:
        return 3
    if small < SMALL_SIDE_2X:
        return 2
    return 1


def load_pixels(path):
    """Open image as RGB pixels; raise a clear error for missing/unreadable files."""
    try:
        from PIL import Image
    except ImportError:
        print(
            "error: Pillow is required to read image pixels.\n"
            "Install it with: python3 -m pip install Pillow",
            file=sys.stderr,
        )
        raise SystemExit(2)
    try:
        img = Image.open(path)
        img.load()
    except FileNotFoundError:
        print("error: image file not found: %s" % path, file=sys.stderr)
        raise SystemExit(1)
    except OSError as exc:
        print("error: cannot read image %s: %s" % (path, exc), file=sys.stderr)
        raise SystemExit(1)
    if img.mode != "RGB":
        img = img.convert("RGB")
    return img


def upscale_copy(img, scale):
    if scale == 1:
        return img
    from PIL import Image

    return img.resize(
        (img.width * scale, img.height * scale), Image.LANCZOS
    )


def engine_version(dist_name, fallback):
    try:
        return importlib.metadata.version(dist_name)
    except importlib.metadata.PackageNotFoundError:
        return fallback


def run_rapidocr(pixels, high_accuracy):
    if importlib.util.find_spec("rapidocr") is None:
        print(
            "error: the default OCR engine (rapidocr) is not installed.\n"
            "Install it with: python3 -m pip install rapidocr onnxruntime",
            file=sys.stderr,
        )
        raise SystemExit(2)
    from rapidocr import RapidOCR

    params = None
    if high_accuracy:
        params = {
            "Det.unclip_ratio": HIGH_ACC_UNCLIP,
            "Det.limit_side_len": HIGH_ACC_DET_LIMIT,
        }
    try:
        import numpy as np

        engine = RapidOCR(params=params) if params else RapidOCR()
        result = engine(np.asarray(pixels))
    except Exception as exc:
        print(
            "error: RapidOCR engine/model failure: %s\n"
            "The OCR model files may be missing. Vendor or pre-fetch them\n"
            "into the engine cache before working offline, then retry.\n"
            "Check dependencies with: python3 check.py" % exc,
            file=sys.stderr,
        )
        raise SystemExit(2)
    # NOTE: result.vis() is deliberately never called: it fetches a
    # display font over the network, which breaks offline use.
    version = engine_version("rapidocr", "unknown")
    name = "rapidocr-%s" % version
    if high_accuracy:
        name += "-high-accuracy"
    lines = []
    if result is not None and getattr(result, "txts", None):
        boxes = getattr(result, "boxes", None)
        scores = getattr(result, "scores", None)
        for i, text in enumerate(result.txts):
            box = None
            if boxes is not None and i < len(boxes):
                box = [[int(x), int(y)] for x, y in boxes[i]]
            conf = None
            if scores is not None and i < len(scores):
                conf = float(scores[i])
            lines.append({"text": text, "conf": conf, "box": box})
    return name, lines


def run_paddle(pixels, high_accuracy):
    if importlib.util.find_spec("paddleocr") is None:
        print(
            "error: the fallback OCR engine (paddleocr) is not installed.\n"
            "Install it with: python3 -m pip install paddleocr==3.7.0",
            file=sys.stderr,
        )
        raise SystemExit(2)
    try:
        import numpy as np
        from paddleocr import PaddleOCR

        kwargs = {"lang": "en", "use_angle_cls": True}
        if high_accuracy:
            kwargs["det_db_unclip_ratio"] = HIGH_ACC_UNCLIP
            kwargs["det_limit_side_len"] = HIGH_ACC_DET_LIMIT
        engine = PaddleOCR(**kwargs)
        raw = engine.ocr(np.asarray(pixels))
    except Exception as exc:
        print(
            "error: PaddleOCR engine/model failure: %s\n"
            "Vendor or pre-fetch the PaddleOCR model files before working\n"
            "offline, then retry." % exc,
            file=sys.stderr,
        )
        raise SystemExit(2)
    version = engine_version("paddleocr", "unknown")
    name = "paddleocr-%s" % version
    if high_accuracy:
        name += "-high-accuracy"
    lines = []
    for page in raw or []:
        for item in page or []:
            try:
                box, (text, conf) = item[0], item[1]
            except (TypeError, ValueError, IndexError):
                continue
            lines.append(
                {
                    "text": str(text),
                    "conf": float(conf),
                    "box": [[int(x), int(y)] for x, y in box],
                }
            )
    return name, lines


def main(argv=None):
    args = parse_args(argv)
    img = load_pixels(args.image)
    width, height = img.width, img.height

    if args.upscale == "auto":
        scale = auto_scale(width, height)
    else:
        scale = int(args.upscale)

    pixels = upscale_copy(img, scale)

    if args.engine == "paddle":
        engine_name, lines = run_paddle(pixels, args.high_accuracy)
    else:
        engine_name, lines = run_rapidocr(pixels, args.high_accuracy)

    if scale != 1:
        for line in lines:
            if line["box"] is not None:
                line["box"] = [
                    [x // scale, y // scale] for x, y in line["box"]
                ]

    if args.min_conf > 0.0:
        lines = [
            line
            for line in lines
            if line["conf"] is not None and line["conf"] >= args.min_conf
        ]

    report = {
        "tool": TOOL_NAME,
        "image": args.image,
        "engine": engine_name,
        "high_accuracy": bool(args.high_accuracy),
        "width": width,
        "height": height,
        "upscale_applied": scale,
        "lines": lines,
    }
    if not lines:
        report["note"] = "no text detected (branch absent; conclude with lowered confidence)"
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
