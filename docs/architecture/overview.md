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
- **Metric summarisation** — Aggregate metric values from workflow cache
  entries into summary statistics (mean, SD, count) written to CSV
- **Plot generation** — Chart metric summaries produced by the summarise step
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

### Action Classes and Registry

Each workflow action is implemented as a small class in
`workflow_action/actions/`, subclassing the `AnalysisAction` contract with its
own `validate` and `run` methods. `workflow_action/actions/__init__.py` maps
action names to classes in `ACTION_CLASSES`. The provider in
`workflow_action/__init__.py` stays thin: it checks that the action is
supported and that the parameters are known, then delegates validation and
execution to the registered class. Adding an action therefore means adding one
module plus one registry entry, and nothing else in the provider.

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
└── workflow_action/    # Workflow action interface
    ├── __init__.py     # Provider class and public API
    ├── types.py        # Shared type imports and fallback stubs
    ├── helpers.py      # Cache parsing and graph extraction helpers
    └── actions/        # Individual workflow action classes
        ├── __init__.py # Action registry
        ├── base.py     # Abstract action contract
        ├── best_graph.py # BestGraphAction (optimal DAG extraction)
        ├── evaluate_graph.py # EvaluateGraphAction (structural metrics)
        ├── merge_graphs.py # MergeGraphsAction (graph merging to PDG)
        ├── migrate_trace.py # MigrateTraceAction (legacy traces to GraphML)
        ├── plot.py     # PlotAction (chart generation)
        └── summarise.py # SummariseAction (metric aggregation to CSV)
```
