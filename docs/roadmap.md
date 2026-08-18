# CausalIQ Analysis - Development Roadmap

**Last updated**: April 10, 2026

This project roadmap fits into the
[overall ecosystem roadmap](https://causaliq.org/projects/ecosystem_roadmap/).

## 🎯 Under Development

### v0.5.0 — Reproducibility

Assuring reproducibility of results and assets for published papers.

 * ✅ [Task 1 - workflow cache can be used as reference for `evaluate_graph`](current_task.md)


## ✅ Implemented Releases

### v0.4.0 — Evaluation and Summarisation

- **Structural Evaluation** (`evaluate_graph`) — Compute F1, precision, recall,
  SHD vs ground truth graphs, including equivalence class metrics
- **Optimal DAG Extraction** (`best_graph`) — Extract optimal DAG from PDGs
  using greedy algorithm with cycle avoidance
- **Summarisation** (`summarise`) — Summarise numerical metrics across
  experiments into publication-ready statistics (mean, SD, count) with CSV output
- **Merge Strategies** — Added `noisy_or` and `max` merge strategies
- **Validation Module** — Shared utilities for parameter validation, seed
  ranges, and filter expressions

### v0.3.0 — Graph Merging

Workflow actions to migrate legacy traces and merge graphs.

- **Trace Migration** (`migrate_trace`) — Convert legacy Trace pickle files
  to DAG/CPDAG in workflow caches
- **Graph Merging** (`merge_graphs`) — Merge multiple DAGs/CPDAGs/PDGs into
  a single PDG with edge probabilities, supporting metadata-driven weighting


### v0.2.0 — Legacy Trace Support

- Support for reading and writing structure learning traces in legacy
  pickle format

### v0.1.0 — Foundation Metrics

- CausalIQ and Bayesys structural graph metrics
- KL divergence metric

*See Git commit history for detailed implementation progress.*

## Documentation

- [Architecture Overview](architecture/overview.md) — Package structure and
  design principles
- [Summarisation Paradigm](architecture/summarisation_paradigm.md) — Core
  architecture for aggregation operations
- [User Guide](userguide/introduction.md) — Usage documentation



