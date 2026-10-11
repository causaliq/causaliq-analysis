# Ensure all modules meet development guidelines

**Status: complete.** All modules now satisfy the limits checked by
`scripts/check_code_rules.py`. This was a Hat 2 (refactoring) task: runtime
behaviour and public APIs are unchanged.

## Context

Create a plan to ensure all modules in causaliq-analysis meet the development
policy guidelines as checked by `scripts/check_code_rules.py`. Split up
modules if they become too large.

The user will commit the changes in two commits: (1) code and tests;
(2) documentation.

## Changes

The 16 legacy function breaches reported by the checker were flattened or
split within five modules; no module exceeded the ~200-statement target, so
none was split into a sub-package.

- `graph_io.py` — extracted `_read_text` so GraphML auto-detection in
  `read_graph_or_pdg_file` no longer nests.
- `merge.py` — `merge_graphs` delegates to validation, weight normalisation
  and strategy helpers; the SDG accumulation cascade became a single
  `_edge_state` lookup, and the noisy-OR combination was split into
  existence and orientation helpers.
- `metrics.py` — `pdg_compare` is split into argument validation, per-pair
  accumulation, summary derivation and Bayesys attachment, and
  `bayesys_metrics` into confusion counts and scores.
- `migrate.py` — metadata, filtering, logging, graph generation and file
  writing were extracted into helpers, with a shared logger factory.
- `validation.py` — the CLI and workflow seed parsers share range helpers,
  and sample-size and metric-spec parsing were split.
- `tests/unit/test_validation.py` — added a case covering the non-list
  metric-spec branch.

## Verification

- `python scripts/check_code_rules.py --strict src/causaliq_analysis` —
  zero breaches.
- `pytest` full suite — passes with 100 % coverage.
- `black`, `isort`, `flake8` and `mypy` — clean.

The completed design is recorded in `docs/architecture/overview.md` (section
"Merge, Metrics, Migration and Validation Modules") and the status in
`docs/roadmap.md`.