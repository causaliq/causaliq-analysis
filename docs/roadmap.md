# CausalIQ Analysis - Development Roadmap

**Last updated**: March 02, 2026

This project roadmap fits into the
[overall ecosystem roadmap](https://causaliq.org/projects/ecosystem_roadmap/).

## Under Development

- none

## ✅ Implemented Releases

### v0.3.0 — Graph Merging

Workflow actions to migrate legacy traces and mere graphs.

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

## 🛣️ Upcoming Releases

### v0.4.0 — Evaluation Workflows

- **Optimal Graph Extraction** (`best_graph`) — Extract the "best" DAG or
  CPDAG from a PDG using threshold-based methods
- **Structural Evaluation** (`evaluate`) — Compute F1, precision, recall,
  SHD vs ground truth graphs

## Documentation

- [Architecture Overview](architecture/overview.md) — Package structure and
  design principles
- [Summarisation Paradigm](architecture/summarisation_paradigm.md) — Core
  architecture for aggregation operations
- [User Guide](userguide/introduction.md) — Usage documentation



