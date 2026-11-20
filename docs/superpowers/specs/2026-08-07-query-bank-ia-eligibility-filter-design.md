# Query Bank IA Eligibility Filter Design

## Context

`ag_news_queries_v1` is structurally valid, but the default 10+10 experiment
fails before replay because some documents cannot supply the balanced `yes`/`no`
IA turns required by the sampler. The query-bank validator intentionally accepts
unbalanced `yes`/`no`/`unknown` distributions, so experiment eligibility must be
enforced by the sampler rather than by changing the dataset contract.

## Decision

Filter documents for IA eligibility before shuffling and selecting the member and
nonmember cohorts. A document is eligible only when it contains enough accepted
`yes` and `no` IA queries to support either balanced allocation that the existing
random selector may choose.

For `turn_count = n`, each document must contain at least `floor(n / 2)` queries
of one label and `ceil(n / 2)` of the other, in both directions. Therefore, the
three-turn experiment requires at least two `yes` and two `no` queries per
document. `unknown` remains valid query-bank data but is not used by the existing
balanced IA experiment.

The filtering occurs alongside the existing requirement that all four attacks
and benign queries be present. The existing seeded document shuffling and
`_choose_ia` selection behavior remain unchanged.

## Failure behavior

After filtering, the sampler retains its existing explicit errors when there are
not enough eligible member or nonmember documents. This avoids selecting a cohort
that will fail later with the less actionable balanced-IA error.

## Tests

Regression coverage will verify that:

1. IA-ineligible documents are skipped before cohort selection.
2. Odd-turn allocations cannot fail after filtering.
3. Insufficient eligible member or nonmember pools produce the existing clear
   document-count error.
4. The real `ag_news_queries_v1` bank can be sampled with the default 10+10 seed.

## Execution sequence

After the code and full test suite pass, run the default 10+10 experiment and
validate its manifests and metrics. Only after that result is complete should a
larger run be configured, capped by the eligible cohort sizes reported after
filtering.
