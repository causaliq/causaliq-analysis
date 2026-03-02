# CausalIQ Analysis User Guide

## Overview

The causaliq-analysis package provides tools for analysing experimental
results from causal discovery workflows:

| Capability | Description |
|------------|-------------|
| **[Graph Merging](merge_graphs.md)** | Combine multiple DAGs/PDAGs/PDGs into a single PDG with edge probabilities |
| **Optimal Extraction** | COMING SOON - Extract the "best" DAG or CPDAG from a PDG |
| **Structural Evaluation** | COMING SOON - Compute F1, precision, recall vs true graph |
| **[Trace Migration](migrate_trace.md)** | Convert legacy Trace pickle files to open-standards formats used by CausalIQ e.g. graphml |

These capabilities follow a **summarisation paradigm** that provides
consistent patterns for aggregating experimental results across different
dimensions (e.g., network, sample size, algorithm). See the
[architecture documentation](../architecture/summarisation_paradigm.md) for
details.

