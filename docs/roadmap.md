# CausalIQ Analysis - Development Roadmap

**Last updated**: March 04, 2026

This project roadmap fits into the
[overall ecosystem roadmap](https://causaliq.org/projects/ecosystem_roadmap/).

## Under Development

### v0.4.0 — Evaluation and Summarisation

- **Structural Evaluation** (`evaluate_graph`) — Compute F1, precision, recall,
  SHD vs ground truth graphs
- **Summarisation** (`summarise`) — Summarise numerical metrics across
  experiments into publication-ready statistics (mean, SD, etc.)

#### Commit Plan

**causaliq-workflow changes** (prerequisite):

1. Implement action pattern validation:
   - Creation: output required, matrix required, input prohibited (for caches)
   - Update: input required, output prohibited, matrix prohibited
   - Aggregation: input required, output required, matrix required
2. Update action support to modify input cache entries (add metadata/objects)
3. Conservative execution for all action patterns:
   - Creation: skip if entry with matching matrix values exists in output
   - Update: skip if action metadata section exists in entry
   - Aggregation: skip if entry with matching matrix values exists in output
4. Add `--mode=force` to bypass conservative execution checks

Note: Conservative execution is implemented entirely within causaliq-workflow
by checking cache state before invoking actions — individual actions do not
need to implement any skip logic.

**causaliq-analysis changes**:

1. `evaluate_graph` CLI implementation with metric naming convention
2. `evaluate_graph` workflow action (update pattern)
3. `summarise` CLI implementation
4. `summarise` workflow action (aggregation pattern, CSV output)

## ✅ Implemented Releases

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

## 🛣️ Upcoming Releases

### v0.5.0 — PDG Evaluation

- **Optimal Graph Extraction** (`best_graph`) — Extract the "best" DAG or
  CPDAG from a PDG using threshold-based methods
- **Stability Evaluation** (`evaluate_pdg`) - compute stability measures of PDG

## Documentation

- [Architecture Overview](architecture/overview.md) — Package structure and
  design principles
- [Summarisation Paradigm](architecture/summarisation_paradigm.md) — Core
  architecture for aggregation operations
- [User Guide](userguide/introduction.md) — Usage documentation



