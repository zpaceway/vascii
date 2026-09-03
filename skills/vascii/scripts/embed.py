#!/usr/bin/env python3
"""vascii embed - deterministic zero-shot coarse-bucket predictions, offline.

Encodes the input image with frozen MobileCLIP-S2 (datacompdr) weights and
ranks 12 fixed generic bucket prompts by cosine similarity. Output is one
JSON object on stdout with the deterministic top-3 buckets:

    python3 embed.py photo.jpg

    {"model": "MobileCLIP-S2/datacompdr", "buckets": [
      {"bucket": "animal", "score": 0.2841}, ...], "margin": 0.0312}

Same input bytes always give byte-identical output: eval mode, no
gradients, fixed CPU thread count, scores rounded to 4dp, keys sorted.

Frozen pick (benchmark 2026-09-03, 90 open-set photos, fixed prompts):
MobileCLIP-S2/datacompdr top-1 38/90 (42.2%), top-3 49/90 (54.4%),
0.064 s/image CPU, 380MB weights. Runners-up: ViT-B-16-SigLIP/webli
37/90 top-1, ViT-B-32/laion2b_s34b_b79k 29/90 top-1.

Pinned runtime (pip): open_clip_torch==3.3.0, torch==2.14.0+cpu,
torchvision==0.29.0+cpu, timm==1.0.29, huggingface_hub==1.29.0,
safetensors==0.8.0, tokenizers==0.23.1. Install while online, then run
offline. Weight blob (HF hub cache
models--apple--MobileCLIP-S2-OpenCLIP, 380MB):
sha256 8fe1e29df4c96fce3b79a66bb13c9adb7f810a2103979b744e257fcbc6cc5c9f
(blob id; file sha256 recorded at freeze time, re-verify with sha256sum).

Pre-fetch while online (weights land under ~/.cache/huggingface/hub):

    python3 -c "import open_clip; open_clip.create_model_and_transforms(
        'MobileCLIP-S2', pretrained='datacompdr', device='cpu')"

Offline rule: HF_HUB_OFFLINE is forced on at startup, so a missing
cache fails here with a clear message instead of downloading. A custom
cache root works via the standard HF_HUB_CACHE environment variable.

Exit codes: 0 on success (even when the margin is thin; the caller
applies the SKILL.md margin-abstain rule). 2 on missing/unreadable
input. 3 on missing weights or missing dependency, with the exact
remedy printed to stderr.
"""

import json
import os
import sys

os.environ["HF_HUB_OFFLINE"] = "1"

ARCH = "MobileCLIP-S2"
TAG = "datacompdr"
MODEL_ID = ARCH + "/" + TAG

PROMPTS = (
    ("waterscape", "a photo of the sea"),
    ("vegetation", "a photo of a forest"),
    ("mountain", "a photo of a mountain"),
    ("sky", "a photo of the sky"),
    ("architecture", "a photo of a building"),
    ("interior", "a photo taken indoors"),
    ("figure", "a photo of a person"),
    ("animal", "a photo of an animal"),
    ("object", "a photo of a car"),
    ("text-sign", "a photo of a sign"),
    ("night", "a photo taken at night"),
    ("close-up", "a close-up photo"),
)


def fail(code, message):
    sys.stderr.write("embed: " + message + "\n")
    sys.exit(code)


def main(argv):
    if len(argv) != 2:
        fail(2, "usage: python3 embed.py <image-file>")
    path = argv[1]
    if not os.path.isfile(path):
        fail(2, "no such file: " + path)

    try:
        import torch
    except ImportError:
        fail(3, "missing dependency: torch. Install the CPU build "
                "while online (pip install torch), then run offline.")
    try:
        import open_clip
        from PIL import Image
    except ImportError as exc:
        fail(3, "missing dependency: " + str(exc) +
                ". Install while online: pip install open_clip_torch Pillow")

    torch.set_num_threads(8)
    torch.set_num_interop_threads(1)

    try:
        with Image.open(path) as img:
            pixels = img.convert("RGB")
            pixels.load()
    except Exception:
        fail(2, "unreadable image: " + path)

    try:
        model, _, preprocess = open_clip.create_model_and_transforms(
            ARCH, pretrained=TAG, device="cpu")
    except Exception:
        fail(3, "weights not in local cache (offline mode, no download "
                "attempted). Pre-fetch while online: python3 -c "
                "\"import open_clip; open_clip.create_model_and_transforms("
                "'MobileCLIP-S2', pretrained='datacompdr', device='cpu')\" "
                "or set HF_HUB_CACHE to a pre-seeded cache root.")
    model.eval()
    tokenizer = open_clip.get_tokenizer(ARCH)

    with torch.no_grad():
        text = tokenizer([prompt for _, prompt in PROMPTS])
        text_feats = model.encode_text(text)
        text_feats = text_feats / text_feats.norm(dim=-1, keepdim=True)
        image_feats = model.encode_image(preprocess(pixels).unsqueeze(0))
        image_feats = image_feats / image_feats.norm(dim=-1, keepdim=True)
        sims = (image_feats @ text_feats.T).squeeze(0).tolist()

    ranked = sorted(range(len(PROMPTS)), key=lambda k: sims[k], reverse=True)
    top3 = [{"bucket": PROMPTS[k][0], "score": round(float(sims[k]), 4)}
            for k in ranked[:3]]
    margin = round(float(sims[ranked[0]] - sims[ranked[1]]), 4)
    sys.stdout.write(json.dumps(
        {"model": MODEL_ID, "buckets": top3, "margin": margin},
        sort_keys=True) + "\n")


main(sys.argv)
