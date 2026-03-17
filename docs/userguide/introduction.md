# CausalIQ Analysis User Guide

## Overview

The causaliq-analysis package is part of the CausalIQ [CausalIQ ecosystem](https://causaliq.org/) for intelligent causal discovery and inference. CausalIQ Analysis provides the following capabilities for analysing experimental results from causal discovery and inference workflows:

| Capability | Pattern | Description |
|------------|---------|-------------|
| **[`best_graph`](best_graph.md)** | Update | Extract the optimal DAG from a PDG using greedy threshold-based selection |
| **[`evaluate_graph`](evaluate_graph.md)** | Update | Compute F1, precision, recall vs true graph |
| **`evaluate_pdg`** | Update | Compute stability measures of PDG (COMING IN v0.5.0)|
| **[`merge_graphs`](merge_graphs.md)** | Aggregate | Combine multiple DAGs/PDAGs/PDGs into a single PDG with edge probabilities |
| **[`migrate_trace`](migrate_trace.md)** | Create | Convert legacy Trace pickle files to open-standards formats used by CausalIQ e.g. GraphML and JSON |
| **`plot`** | Create | Publication-ready charts (COMING IN V0.6.0) |
| **[`summarise`](summarise.md)** | Aggregate | Statistically summarise numerical results across experiments into publication-ready metrics |
| **`table`** | Create | Publication-ready LaTeX tables (COMING IN V0.6.0) |

## Command Line, Workflow or Programmatic Access

As with all CausalIQ packages, users may access the capabilities of CausalIQ
Analysis in three ways:

- **Command Line Interface (CLI)** provides an easy introduction to performing
  analysis from the command line. This is primarily orientated to analysing a
  single result and thus gain an initial understanding of how to use the
  capability.

- **CausalIQ Workflows** allows users to include CausalIQ Analysis steps within
  workflows which can combine learning graphs from data or LLMs, performing
  inference, analysing results, through to generating publication tables and
  charts.

- **Programmatic Access** using the [Python API](../api/overview.md) for
  complete flexibility over the processing logic.

The CLI and workflow routes use the same command or action name respectively,
which in turn matches the capability name in the table above. Parameters are
named identically, and as far as practical, the capability behaviour is the
same in the CLI and workflow interfaces.

## Workflow Concepts

For common workflow concepts that apply across all CausalIQ packages, see the
[CausalIQ Workflow User Guide](https://workflow.causaliq.org/userguide/):

- [**Action patterns**](https://workflow.causaliq.org/userguide/action_patterns/)
  — Create, update, and aggregate patterns
- [**Common parameters**](https://workflow.causaliq.org/userguide/common_parameters/)
  — `input`, `output`, `filter` parameters
- [**Workflow caching**](https://workflow.causaliq.org/userguide/caching/)
  — Result storage and conservative execution
- [**CLI usage**](https://workflow.causaliq.org/userguide/cli/)
  — Execution modes (`run`, `dry-run`, `force`)

The individual action guides in this section document **analysis-specific
parameters and behaviour** for each capability.

