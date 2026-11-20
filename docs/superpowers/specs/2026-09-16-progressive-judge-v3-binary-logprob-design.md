# Progressive Judge v3 Binary Logprob Design

## Goal

Replace the v2 three-label, anchor-weighted logprob score with a binary conditional attack probability while preserving v2 artifacts and evaluating two pre-registered false-positive-rate operating points.

## Scoring contract

The logprob prompt permits exactly `BENIGN` and `ATTACK`. `ATTACK` means validated evidence makes the attack explanation more plausible than a benign explanation; incomplete suspicion alone is not sufficient. The numeric score is `P(ATTACK) / (P(ATTACK) + P(BENIGN))`. The client must return exactly these two finite, normalized candidate probabilities.

`x1` is the binary query score and `x2` is the binary session score. A session score remains unavailable before the configured history length; unavailable values are not converted to zero.

## Compatibility and provenance

v2 config and traces remain unchanged. v3 has new immutable baseline and Qwen configs, a distinct prompt version, and records the binary scoring definition in the trace/artifact contract. New generated artifacts use a v3-specific output root and must bind their frozen input split, model identity, Judge config, and prompt version.

## Analysis, fusion, and thresholds

Train-only separability and grouped OOF fusion operate on the v3 `logprob` head without changing the existing rubric baseline. Threshold reports must include exactly the pre-registered 1% and 5% benign-FPR constraints, each reporting macro and weakest-attack recall. Documents are grouping units for folds and bootstrap. OOF results select the model and candidate thresholds; a later locked validation run must evaluate the frozen selection without fitting or reselecting. Test data remains forbidden during Judge training/calibration.
