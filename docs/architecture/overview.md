# Architecture Overview

## CausalIQ Ecosystem

causaliq-analysis is a component of the overall
[CausalIQ ecosystem architecture](https://causaliq.org/projects/ecosystem_architecture/).

## Package Purpose

causaliq-analysis provides tools for analysing and summarising results from
causal discovery experiments:

- **Graph merging** — Combine multiple learned graphs into probabilistic
  dependency graphs (PDGs)
- **Structural evaluation** — Compute accuracy metrics against ground truth
  for deterministic graphs (DAG/PDAG/CPDAG) and probabilistic dependency
  graphs (PDGs)
- **Trace migration** — Convert legacy experiment traces to modern formats

## Key Architectural Concepts

### Summarisation Paradigm

The [summarisation paradigm](summarisation_paradigm.md) provides a consistent
pattern for aggregating experimental results across different dimensions.
This enables workflows that:

- Group results by network, sample size, algorithm, etc.
- Filter inputs by metadata criteria
- Apply metadata-driven weighting
- Produce outputs with full provenance tracking

### Graph Types

The package works with graph types from causaliq-core:

| Type | Description |
|------|-------------|
| **DAG** | Directed acyclic graph with fully oriented edges |
| **CPDAG** | Completed partially directed acyclic graph (Markov equivalence class) |
| **PDG** | Probabilistic dependency graph with edge probabilities |

`evaluate_graph` compares deterministic graphs (DAG/PDAG/CPDAG) directly and
PDGs probabilistically: each node pair contributes the sixteen products of the
reference and graph edge-state probabilities (`forward`, `backward`,
`undirected`, `none`), so low-level edge counts are fractional. Since a PDG can
represent a DAG, PDAG or CPDAG, this single comparison path supports all
graph types produced by the CausalIQ ecosystem.

### Integration Points

| Component | Integration |
|-----------|-------------|
| **causaliq-core** | Graph types, filter evaluation, weight computation |
| **causaliq-workflow** | Workflow actions, cache storage, matrix execution |
| **causaliq-data** | Dataset loading for evaluation |

## Module Structure

```
src/causaliq_analysis/
├── __init__.py         # Package exports
├── cli.py              # Command-line interface
├── graph.py            # Graph action enumerations
├── graph_io.py         # Graph file reading (including PDGs)
├── merge.py            # Graph merging to PDG
├── metrics.py          # Structural comparison metrics
├── migrate.py          # Trace migration utilities
├── trace.py            # Legacy Trace format support
├── validation.py       # Input validation
└── workflow_action.py  # Workflow action interface
```
