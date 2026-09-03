"""Conditional ASCII-back-to-grayscale silhouette validation for vascii.

Re-renders fixed-width ASCII art (produced by img2ascii.py with a known
ordered density ramp) back to a low-resolution grayscale image by mapping
each character index to a gray value, then compares per-cell means against
either a supplied reference image or a self round-trip. This is a
corroboration-only check: agreement promotes confidence by at most one
level and the result is never usable as primary perception.

Silhouette only: the re-render recovers coarse light/dark masses, never
photometric detail. Anything outside the invertible subset is skipped with
an explicit reason string (dither, color, edge-glyphs, unknown ramp,
unknown width, high confidence).
"""

import argparse
import json
import sys

EDGE_GLYPHS = set("/\\|_()[]{}<>^v")
ANSI_ESC = "\x1b["

PROMOTE = {"low": "medium", "medium": "high", "high": "high"}


def fail(message):
    print(json.dumps({"status": "error", "reason": message}))
    return 1


def skipped(reason, extra=None):
    report = {
        "status": "skipped",
        "reason": reason,
        "agreement": 0.0,
        "delta": 0.0,
        "promoted": False,
    }
    if extra:
        report.update(extra)
    print(json.dumps(report, indent=2))
    return 0


def gray_of_index(idx, n, invert):
    step = 255.0 / (n - 1)
    if invert:
        return round(idx * step)
    return round(255.0 - idx * step)


def index_of_gray(gray, n, invert):
    step = 255.0 / (n - 1)
    if invert:
        idx = int(round(gray / step))
    else:
        idx = int(round((255.0 - gray) / step))
    return max(0, min(n - 1, idx))


def load_meta(path_or_json):
    import os

    if path_or_json is None:
        return {}
    text = path_or_json
    if os.path.exists(path_or_json):
        with open(path_or_json, "r", encoding="utf-8") as fh:
            text = fh.read()
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def read_ascii_rows(path):
    with open(path, "r", encoding="utf-8") as fh:
        content = fh.read()
    rows = content.split("\n")
    if rows and rows[-1] == "":
        rows = rows[:-1]
    return rows, content


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Conditional ASCII-back-to-grayscale silhouette check."
    )
    ap.add_argument("--ascii", required=True, help="Path to the ASCII art file.")
    ap.add_argument(
        "--ramp",
        default=None,
        help="Ordered density ramp, light first (e.g. ' .:-=+*#%%@').",
    )
    ap.add_argument("--width", type=int, default=None, help="Expected row width.")
    ap.add_argument("--invert", action="store_true", help="Ramp runs dark first.")
    ap.add_argument("--ref", default=None, help="Reference image for cell compare.")
    ap.add_argument(
        "--confidence",
        default="low",
        choices=("low", "medium", "high"),
        help="Incoming confidence level.",
    )
    ap.add_argument(
        "--threshold",
        type=float,
        default=0.85,
        help="Agreement fraction needed to promote.",
    )
    ap.add_argument("--dither", action="store_true", help="Forward used dithering.")
    ap.add_argument("--color", action="store_true", help="Forward used color/ANSI.")
    ap.add_argument("--edge", action="store_true", help="Forward used edge glyphs.")
    ap.add_argument("--meta", default=None, help="Forward-params JSON or path.")
    ap.add_argument("--out", default=None, help="Write NEAREST-upscaled view here.")
    ap.add_argument("--scale", type=int, default=8, help="Upscale factor for --out.")
    args = ap.parse_args(argv)

    meta = load_meta(args.meta)

    dither = args.dither or bool(meta.get("dither", False))
    color = args.color or bool(meta.get("color", False))
    edge = args.edge or bool(meta.get("edge", False))
    ramp = args.ramp if args.ramp is not None else meta.get("ramp")
    width = args.width if args.width is not None else meta.get("width")
    invert = args.invert or bool(meta.get("invert", False))
    confidence = meta.get("confidence", args.confidence)
    if confidence not in ("low", "medium", "high"):
        return fail("bad confidence: %r (want low|medium|high)" % (confidence,))

    base = {
        "confidence_in": confidence,
        "confidence_out": confidence,
        "invert": bool(invert),
    }

    if dither or str(meta.get("mode", "")).lower() == "dither":
        return skipped("dither: dithered output is not invertible", base)
    if color:
        return skipped("color: color/ANSI output is not invertible", base)
    if edge:
        return skipped("edge-glyphs: edge-channel output is not invertible", base)
    if confidence == "high":
        return skipped(
            "high-confidence: validation runs only on low/medium confidence "
            "or branch disagreement",
            base,
        )
    if not ramp:
        return skipped(
            "unknown-ramp: --ramp (or meta ramp) is required for inversion", base
        )
    if len(ramp) < 2 or len(set(ramp)) != len(ramp):
        return skipped(
            "unknown-ramp: ramp must hold >=2 distinct chars, got %r" % (ramp,),
            dict(base, ramp=ramp),
        )

    try:
        rows, content = read_ascii_rows(args.ascii)
    except OSError as exc:
        return fail("cannot read ascii file: %s" % (exc,))

    if not rows:
        return skipped("unknown-width: ascii file holds no rows", base)
    if ANSI_ESC in content:
        return skipped(
            "color: ANSI escape sequences detected in ascii file", base
        )

    lengths = {len(r) for r in rows}
    if len(lengths) != 1:
        if width is None:
            return skipped(
                "unknown-width: ragged rows %s with no --width metadata"
                % (sorted(lengths),),
                dict(base, ramp=ramp),
            )
        rows = [(r + " " * width)[:width] for r in rows]
    grid_w = len(rows[0])
    if width is not None and width != grid_w:
        return skipped(
            "unknown-width: --width %d disagrees with file width %d"
            % (width, grid_w),
            dict(base, ramp=ramp),
        )
    width = grid_w
    height = len(rows)

    ramp_index = {ch: i for i, ch in enumerate(ramp)}
    unknown = sorted({ch for r in rows for ch in r} - set(ramp))
    if unknown:
        if any(ch in EDGE_GLYPHS for ch in unknown):
            return skipped(
                "edge-glyphs: chars outside ramp look like edge marks: %s"
                % ("".join(unknown),),
                dict(base, ramp=ramp, width=width, height=height),
            )
        return skipped(
            "unknown-ramp: chars not in ramp: %s" % ("".join(unknown),),
            dict(base, ramp=ramp, width=width, height=height),
        )

    n = len(ramp)
    step = 255.0 / (n - 1)

    lowres = [
        [float(gray_of_index(ramp_index[ch], n, invert)) for ch in r] for r in rows
    ]

    roundtrip_ok = 0
    total = width * height
    for y in range(height):
        for x in range(width):
            back = index_of_gray(lowres[y][x], n, invert)
            if back == ramp_index[rows[y][x]]:
                roundtrip_ok += 1
    roundtrip = roundtrip_ok / total if total else 0.0

    dark_cells = sum(1 for row in lowres for v in row if v < 128.0)
    dark_mass = dark_cells / total if total else 0.0

    mode = "roundtrip"
    agreement = roundtrip
    if args.ref is not None:
        mode = "ref-compare"
        try:
            from PIL import Image
        except ImportError:
            return fail("Pillow is required for --ref comparison")
        try:
            ref_img = Image.open(args.ref).convert("L")
        except OSError as exc:
            return fail("cannot read ref image: %s" % (exc,))
        ref_small = ref_img.resize((width, height), Image.BILINEAR)
        ref_px = list(ref_small.tobytes())
        tol = step + 0.5
        diffs = []
        hits = 0
        k = 0
        mass_ref_dark = 0
        for y in range(height):
            for x in range(width):
                rv = float(ref_px[k])
                k += 1
                if rv < 128.0:
                    mass_ref_dark += 1
                d = abs(lowres[y][x] - rv)
                diffs.append(d)
                if d <= tol:
                    hits += 1
        agreement = hits / total if total else 0.0
        delta = sum(diffs) / len(diffs) if diffs else 0.0
        mass_delta = abs(dark_mass - mass_ref_dark / total) if total else 0.0
    else:
        delta = 0.0
        mass_delta = 0.0

    promoted = False
    confidence_out = confidence
    if agreement >= args.threshold:
        confidence_out = PROMOTE[confidence]
        promoted = confidence_out != confidence

    if args.out is not None:
        try:
            from PIL import Image
        except ImportError:
            return fail("Pillow is required for --out rendering")
        scale = max(1, args.scale)
        flat = [int(round(v)) for row in lowres for v in row]
        img = Image.new("L", (width, height))
        img.putdata(flat)
        img.resize((width * scale, height * scale), Image.NEAREST).save(args.out)

    report = dict(base)
    report.update(
        {
            "status": "validated",
            "reason": None,
            "mode": mode,
            "ramp": ramp,
            "ramp_size": n,
            "step": step,
            "tolerance": step,
            "width": width,
            "height": height,
            "agreement": agreement,
            "roundtrip": roundtrip,
            "delta": delta,
            "dark_mass": dark_mass,
            "mass_delta": mass_delta,
            "threshold": args.threshold,
            "promoted": promoted,
            "confidence_out": confidence_out,
            "note": (
                "silhouette-only corroboration, never primary perception; "
                "agreement promotes confidence at most one level"
            ),
        }
    )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
