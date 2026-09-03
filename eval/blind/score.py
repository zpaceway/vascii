#!/usr/bin/env python3
"""Blind scorer: join predictions.jsonl to labels.jsonl.sealed, grade, report.

Post-hoc ONLY — run after predictions.jsonl is frozen (record its sha256
first). The scorer never feeds labels back to the tester before the run.

Usage:
    python3 eval/blind/score.py [--predictions P] [--out SCORES_MD]

Reads eval/blind/labels.jsonl.sealed + eval/blind/predictions.jsonl, writes
eval/blind/scores.md and prints a stdout summary: k/n, Wilson 95% CIs,
per-category tallies, stale/fixture exclusions, and the two-proportion z-test
vs the frozen 44/96 = 45.8% baseline (two-sided, alpha = 0.05).
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys

BLIND = os.path.dirname(os.path.abspath(__file__))
SEALED = os.path.join(BLIND, "labels.jsonl.sealed")
PREDS = os.path.join(BLIND, "predictions.jsonl")
SCORES = os.path.join(BLIND, "scores.md")

# --- Frozen reference figures (harness_analysis.md sections 2, 6) ---
BASELINE_K, BASELINE_N = 44, 96          # photos_02 22/46 + gui_02 22/50
BASELINE_P = BASELINE_K / BASELINE_N     # 0.4583
Z_ALPHA_HALF = 1.96                      # two-sided 95%

# --- 4.3 Stale-capture signatures: (label, source) pairs, excluded from the
# headline figure and reported separately. Matched post-hoc on sealed rows.
STALE_SIGNATURES = {
    ("Render cloud dashboard sign-in page with SSO buttons and email form",
     "https://dashboard.render.com/login"),
    ("ArchWiki installation guide dense text page",
     "https://wiki.archlinux.org/title/Installation_guide"),
}

# --- 4.2 Hypernym sets (frozen; extend only pre-run) ---
HYPERNYMS: dict[str, set[str]] = {
    "waterscape": {"sea", "ocean", "lake", "river", "waterfall", "rapids",
                   "waves", "beach", "pool"},
    "outdoor scene": {"street", "plaza", "park", "airfield", "village",
                      "mountain", "courtyard"},
    "figure subject": {"person", "people", "man", "woman", "girl", "boy",
                       "child", "crowd", "keeper", "player", "team"},
    "animal subject": {"cat", "dog", "lion", "elephant", "tiger", "bird",
                       "fish", "feline", "cub", "horse"},
    "architecture-or-structure": {"cathedral", "church", "hall", "arch",
                                  "building", "bridge", "tower", "temple",
                                  "structure"},
    "vegetation landscape": {"forest", "palms", "garden", "park", "trees",
                             "field"},
    "text sign": {"sign", "poster", "meme", "caption", "plaque", "billboard"},
}

# --- 4.2 GUI alias groups (frozen; bidirectional, case-insensitive) ---
GUI_ALIASES: dict[str, set[str]] = {
    "mdn": {"mdn", "mozilla", "developer"},
    "reddit": {"reddit", "old"},
    "gmail": {"gmail", "google", "mail"},
    "slack": {"slack", "local", "chat"},
    "calendar": {"calendar", "month", "grid"},
    "diff": {"diff", "local", "editor"},
    "htop": {"htop", "process", "monitor"},
    "syslog": {"syslog", "system", "log"},
}

BACKGROUND_TOKENS = {"dark", "light", "black", "white"}
SCAFFOLD_TOKENS = {"pixel", "art", "diagram", "image", "gui", "screenshot",
                   "uncertain", "best", "guess", "photo", "picture"}
STOP_TOKENS = {"with", "from", "near", "front", "rear", "side", "top", "view",
               "over", "under", "into", "onto", "per"}
GENERIC_GUI = {"page", "document", "site", "website", "screen", "window",
               "view", "app", "web", "online", "interface", "ui"}

DROP = BACKGROUND_TOKENS | SCAFFOLD_TOKENS | STOP_TOKENS
TOKEN_RE = re.compile(r"[a-z0-9]+")


def stem(tok: str) -> str:
    # Light frozen stemmer so inflections meet (skateboarding/skateboarder).
    # Applied to BOTH sides uniformly; strips only if the stem stays >=4 chars.
    for suf in ("ing", "er", "ed", "es"):
        if tok.endswith(suf) and len(tok) - len(suf) >= 4:
            return tok[: -len(suf)]
    if tok.endswith("s") and not tok.endswith("ss") and len(tok) - 1 >= 4:
        return tok[: -1]
    return tok


def tokens(text: str) -> set[str]:
    return {stem(t) for t in TOKEN_RE.findall(text.lower())} - DROP


def hypernym_hit(label_toks: set[str], verdict_toks: set[str]) -> str:
    """Return the shared hypernym-set name, or '' (4.2 step b)."""
    for name, members in HYPERNYMS.items():
        if (label_toks & members) and (verdict_toks & members):
            return name
    return ""


def gui_subject_hit(label_toks: set[str], verdict_toks: set[str]) -> str:
    """STRICT subject naming (4.1): alias-group hit on both sides, else an
    exact substantive label token (len>=4, non-generic) in the verdict.
    OCR text alone never counts: generic-only overlap is incorrect."""
    for name, members in GUI_ALIASES.items():
        if (label_toks & members) and (verdict_toks & members):
            return f"alias:{name}"
    shared = {t for t in (label_toks & verdict_toks)
              if len(t) >= 4 and t not in GENERIC_GUI}
    if shared:
        return f"token:{sorted(shared)[0]}"
    return ""


def photo_hit(label_toks: set[str], verdict_toks: set[str]) -> str:
    """Coarse bucket suffices (4.1): exact substantive token, else hypernym."""
    shared = {t for t in (label_toks & verdict_toks) if len(t) >= 4}
    if shared:
        return f"token:{sorted(shared)[0]}"
    hit = hypernym_hit(label_toks, verdict_toks)
    return f"hypernym:{hit}" if hit else ""


def diagram_hit(label_toks: set[str], verdict_toks: set[str],
                ocr_toks: set[str]) -> tuple[str, str]:
    """Entity naming + (has_text rows) OCR-backed salient-text span (4.1)."""
    shared = {t for t in (label_toks & verdict_toks) if len(t) >= 4}
    entity = ""
    if shared:
        entity = f"token:{sorted(shared)[0]}"
    else:
        hit = hypernym_hit(label_toks, verdict_toks)
        if hit:
            entity = f"hypernym:{hit}"
    text = ""
    backed = {t for t in (ocr_toks & verdict_toks & label_toks)
              if len(t) >= 2} - DROP
    if backed:
        text = f"ocr-text:{sorted(backed)[0]}"
    return entity, text


def wilson(k: int, n: int, z: float = Z_ALPHA_HALF) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    den = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - m) / den, (c + m) / den)


def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def two_proportion_z(k1: int, n1: int, k2: int, n2: int
                     ) -> tuple[float, float]:
    """Two-sided two-proportion z-test; returns (z, p)."""
    p1, p2 = k1 / n1, k2 / n2
    pp = (k1 + k2) / (n1 + n2)
    se = math.sqrt(pp * (1 - pp) * (1 / n1 + 1 / n2))
    z = (p1 - p2) / se if se else 0.0
    return z, 2 * (1 - norm_cdf(abs(z)))


def main() -> int:
    ap = argparse.ArgumentParser(description="Score frozen blind predictions.")
    ap.add_argument("--predictions", default=PREDS)
    ap.add_argument("--out", default=SCORES)
    args = ap.parse_args()

    if not os.path.exists(SEALED):
        print(f"refusing: sealed labels not found: {SEALED}", file=sys.stderr)
        return 1
    if not os.path.exists(args.predictions):
        print(f"refusing: predictions not found: {args.predictions}",
              file=sys.stderr)
        return 1

    labels = {}
    for line in open(SEALED):
        if line.strip():
            r = json.loads(line)
            labels[r["h"]] = r

    preds = {}
    for i, line in enumerate(open(args.predictions), 1):
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            print(f"warning: line {i} is not JSON, ignored", file=sys.stderr)
            continue
        for key in ("h", "verdict", "confidence", "mode", "ocr_text"):
            if key not in r:
                print(f"warning: line {i} missing {key!r}", file=sys.stderr)
        if "h" in r:
            preds[r["h"]] = r

    extra = sorted(set(preds) - set(labels))
    if extra:
        print(f"warning: {len(extra)} prediction hashes not in sealed map "
              f"(fixture/unknown, reported separately, never in headline): "
              f"{extra[:8]}", file=sys.stderr)

    rows = []  # (h, category, correct, basis, stale, missing)
    for h, lab in labels.items():
        stale = (lab["label"], lab.get("source", "")) in STALE_SIGNATURES
        p = preds.get(h)
        if p is None:
            rows.append((h, lab["category"], False, "missing-prediction",
                         stale, True))
            continue
        lt, vt = tokens(lab["label"]), tokens(str(p.get("verdict", "")))
        cat = lab["category"]
        if cat == "photo":
            basis = photo_hit(lt, vt)
            correct, basis = bool(basis), basis or "no-match"
        elif cat == "gui":
            basis = gui_subject_hit(lt, vt)
            correct, basis = bool(basis), basis or "no-match"
        else:
            ent, txt = diagram_hit(lt, vt, tokens(str(p.get("ocr_text", ""))))
            if lab.get("has_text"):
                correct = bool(ent) and bool(txt)
                basis = f"{ent or 'no-entity'}+{txt or 'no-text'}"
            else:
                correct, basis = bool(ent), ent or "no-match"
        # confidence is recorded but NEVER changes correctness (4.1).
        rows.append((h, cat, correct, basis, stale, False))

    def tally(sel) -> tuple[int, int]:
        ks = [r for r in sel]
        return sum(1 for r in ks if r[2]), len(ks)

    cats = {}
    for cat in ("photo", "gui", "diagram"):
        cats[cat] = tally(r for r in rows if r[1] == cat)
        cats[cat + "_fresh"] = tally(r for r in rows
                                      if r[1] == cat and not r[4])

    # Headline: photos+gui comparable rows; default ex-stale, always show both.
    k_all, n_all = tally(r for r in rows if r[1] in ("photo", "gui"))
    k_hd, n_hd = tally(r for r in rows if r[1] in ("photo", "gui") and not r[4])
    stale_rows = [r for r in rows if r[4]]
    missing = sum(1 for r in rows if r[5])

    lo, hi = wilson(k_hd, n_hd)
    blo, bhi = wilson(BASELINE_K, BASELINE_N)
    z, p = two_proportion_z(k_hd, n_hd, BASELINE_K, BASELINE_N)
    ci_above = lo > BASELINE_P
    significant = p < 0.05
    trusted = ci_above and significant

    lines = [
        "# Blind re-test scores",
        "",
        f"Headline (photos+gui, ex-stale): **{k_hd}/{n_hd} = "
        f"{k_hd / n_hd * 100:.1f}%** Wilson 95% CI "
        f"[{lo:.3f}, {hi:.3f}]" if n_hd else "Headline: n=0",
        f"Inclusive (photos+gui, with stale): {k_all}/{n_all} = "
        f"{k_all / n_all * 100:.1f}%" if n_all else "Inclusive: n=0",
        "",
        "## Per-category (fresh / all)",
        "",
    ]
    for cat in ("photo", "gui", "diagram"):
        kf, nf = cats[cat + "_fresh"]
        ka, na = cats[cat]
        flo, fhi = wilson(kf, nf)
        lines.append(f"- {cat}: fresh {kf}/{nf} = "
                     f"{kf / nf * 100:.1f}% [{flo:.3f}, {fhi:.3f}]" if nf
                     else f"- {cat}: fresh n=0")
        if (kf, nf) != (ka, na):
            lines.append(f"  all: {ka}/{na} = {ka / na * 100:.1f}%")
    lines += [
        "",
        "## Exclusions",
        "",
        f"- stale captures excluded from headline: {len(stale_rows)} "
        f"({sum(1 for r in stale_rows if r[2])} would-be-correct)",
    ]
    for h, cat, correct, basis, _, _ in stale_rows:
        lines.append(f"  - {h} [{cat}] correct={correct} basis={basis}")
    lines.append(f"- fixture/unknown prediction hashes (never in headline): "
                 f"{len(extra)}")
    for h in extra:
        lines.append(f"  - {h}")
    lines.append(f"- missing predictions (scored incorrect): {missing}")
    lines += [
        "",
        "## Re-test comparison vs 44/96 baseline",
        "",
        f"- baseline: {BASELINE_K}/{BASELINE_N} = {BASELINE_P * 100:.1f}% "
        f"Wilson 95% CI [{blo:.3f}, {bhi:.3f}]",
        f"- blind: {k_hd}/{n_hd} = {k_hd / n_hd * 100:.1f}% "
        f"[{lo:.3f}, {hi:.3f}]" if n_hd else "- blind: n=0",
        f"- delta vs 0.458: {(k_hd / n_hd - BASELINE_P) * 100:+.1f}pp"
        if n_hd else "- delta: n/a",
        f"- two-proportion z = {z:+.3f}, two-sided p = {p:.4g} "
        f"(alpha 0.05, {'SIGNIFICANT' if significant else 'not significant'})",
        f"- Wilson non-overlap sanity: blind CI lower {lo:.3f} "
        f"{'strictly above' if ci_above else 'NOT strictly above'} 0.458",
        f"- bar check: ~56/96 (58%) clears p<0.05 against 44/96 with n~=96/arm",
        f"- trusted (CI above 0.458 AND p<0.05, under tester protocol): "
        f"{'YES' if trusted else 'NO'}",
        "- never compare against the 227/281 = 80.8% mixed-methodology "
        "composite (Wilson [0.758, 0.850]); different, leakier measurement.",
        "",
        "## Per-row justifications (non-map matches use exact-token basis)",
        "",
    ]
    for h, cat, correct, basis, stale, miss in sorted(rows):
        flag = "STALE " if stale else ""
        lines.append(f"- {h} [{cat}] {flag}correct={correct} basis={basis}")
    lines.append("")

    with open(args.out, "w") as f:
        f.write("\n".join(lines))
    print("\n".join(lines[:10]))
    print(f"\n(scores.md written to {args.out}; "
          f"z={z:+.3f} p={p:.4g} trusted={'YES' if trusted else 'NO'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
