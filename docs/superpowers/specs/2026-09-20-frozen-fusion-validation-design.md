# Frozen Fusion Validation Design

Fit the preselected logprob `logistic_l2` once on every train row with an observed session score. Store feature order, coefficients, intercept, training-table hash, and the already selected 1%/5% thresholds as JSON. Validation reads this JSON and a verified validation Judge run, computes scores without fitting or threshold selection, and writes metrics for both operating points.
