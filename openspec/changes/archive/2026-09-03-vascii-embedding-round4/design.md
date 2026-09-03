## Context

See proposal.md Why. Frozen skill at vascii-skill pins; best blind 110/190 ex-stale (photo 13/90 baseline lane, R3 photo 18/90). Blind harness `eval/blind/` with frozen scorer unchanged.

## Goals / Non-Goals

**Goals:** Measure whether local zero-shot embeddings lift photo coarse-ID under the blind gate, with honest cost accounting.
**Non-Goals:** Training/fine-tuning, cloud APIs, GUI changes, rubric changes,PROP-fitting on eval labels (zero-shot descriptions only — no prototype fitting on the eval set).

## Decisions

- **Zero-shot bucket descriptions, no fitting.** Candidate bucket prompts are generic English (`a photo of the sea`, `a person outdoors`, …) fixed before measurement. Rationale: fitting prototypes on eval labels then testing on eval is leakage; zero-shot keeps the trial clean and the branch dataset-independent.
- **Benchmark-then-freeze.** One agent measures 2–3 models on the open photo set (accuracy + s/image CPU + RAM + weight size), picks the winner on accuracy-per-cost, pins versions + weight hashes. Rationale: selection is tuning (labels visible OK); the blind trial measures the frozen pick.
- **Embedding as evidence, not oracle.** The branch emits top-3 buckets + margins; SKILL.md rules: embedding agrees with ASCII masses → count as agreement for confidence; embedding alone never forces `high`; margins below threshold → abstain to prior behavior. Rationale: preserves calibration; embeddings err too.
- **Same gate, documented cost.** Adopt iff R4 clears 110/190 with p<0.05, plus offline vendoring verified (weights pre-placed, network-off run, no JIT download). Weight size recorded as the explicit tradeoff.

## Risks / Trade-offs

- [350MB+ weights vs portable skill] -> Recorded tradeoff; adoption may split skill into light (frozen pins) vs full (+embeddings) flavors.
- [CPU latency per image] -> Measured in benchmark; batch/offline acceptable, interactive cost noted.
- [Bucket-prompt sensitivity] -> Prompts frozen pre-trial alongside weights; no post-hoc prompt tuning on blind results.
