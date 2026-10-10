# CausalIQ Analysis Metrics

This module provides functions for analysing and comparing causal graphs, including structural metrics, Kullback-Leibler divergence calculations, and Bayesys compatibility metrics.

## Core Functions

::: causaliq_analysis.metrics.pdag_compare
    options:
        show_root_heading: true
        show_source: false
        heading_level: 3

Compare a PDAG with a reference PDAG to compute structural comparison metrics including precision, recall, F1 score, and Structural Hamming Distance (SHD).

::: causaliq_analysis.metrics.pdg_compare
    options:
        show_root_heading: true
        show_source: false
        heading_level: 3

Compare a PDG with a reference PDG to compute structural comparison metrics. Deterministic DAG/PDAG/CPDAG inputs are converted to PDGs first, so this provides a single probabilistic comparison path for every supported graph type.

::: causaliq_analysis.metrics.kl
    options:
        show_root_heading: true
        show_source: false
        heading_level: 3

Compute the Kullback-Leibler divergence of one probability distribution from another reference distribution.

::: causaliq_analysis.metrics.bayesys_metrics
    options:
        show_root_heading: true
        show_source: false
        heading_level: 3

Compute Bayesys-compatible metrics from structural comparison results, including precision, recall, F1 with half-match support, Bayesys Scoring Function (BSF), and Delta Dependency Measure (DDM).

## Overview

### PDAG Comparison

The `pdag_compare` function provides comprehensive structural comparison between two Partially Directed Acyclic Graphs (PDAGs). It computes detailed edge-level metrics including:

- **Arc metrics**: `arc_matched`, `arc_reversed`, `arc_missing`, `arc_extra`
- **Edge metrics**: `edge_matched`, `edge_missing`, `edge_extra`,
  `edge_not_arc`, `arc_not_edge`
- **Confusion matrix**: `missing_matched` counts the edges absent from both
  graphs, completing the 2x2 confusion matrix
- **Summary metrics**: precision, recall, F1 score, Structural Hamming
  Distance (SHD)
- **Bayesys compatibility**: Optional Bayesys v1.5+ metrics

The constant `EDGE_METRICS` lists all ten low-level count names and is used by
the `evaluate_graph` CLI command and workflow action to expand the `edge` and
`equiv.edge` metric requests.

The function includes built-in sanity checks to ensure metric consistency and can optionally identify specific edges in each category for detailed analysis.

### PDG Comparison

The `pdg_compare` function extends the comparison to Probabilistic Dependency
Graphs (PDGs), which assign a probability to each possible edge state between a
pair of variables: `forward` (`A -> B`), `backward` (`A <- B`), `undirected`
(`A -- B`) and `none` (no edge). Deterministic graphs (DAG/PDAG/CPDAG) are
converted to PDGs first, so `pdg_compare` compares every supported graph type.

For each node pair the four reference states and four graph states are combined
in sixteen products, for example:

| Reference | Graph | Metric | Contribution |
|-----------|-------|--------|--------------|
| `A -> B` **0.6** | `A -> B` **0.4** | `arc_matched` | `0.6 x 0.4 = 0.24` |
| `A -> B` **0.6** | `A <- B` **0.3** | `arc_reversed` | `0.6 x 0.3 = 0.18` |
| no edge **0.3** | no edge **0.2** | `missing_matched` | `0.3 x 0.2 = 0.06` |

The fractional contributions add up to `1.0` for each node pair. Deterministic
inputs (probabilities of `0.0`/`1.0`) therefore reproduce the integer counts of
`pdag_compare`, which is retained as a wrapper around `pdg_compare` for
compatibility.

The derived metrics (precision, recall, F1 and SHD) are computed from the
fractional counts in exactly the same way as for `pdag_compare`.

### Distribution Analysis

The `kl` function computes Kullback-Leibler divergence for comparing probability distributions, commonly used in causal discovery for independence testing and model comparison.

### Bayesys Metrics

The `bayesys_metrics` function converts structural metrics to Bayesys-compatible format, supporting the half-match concept where reversed arcs and edge/arc mismatches are treated as partial matches. This enables comparison with results from the Bayesys causal discovery software.

## Usage Examples

### Basic PDAG Comparison

```python
from causaliq_analysis.metrics import pdag_compare
from causaliq_core.graph import PDAG

# Compare two PDAGs
result = pdag_compare(learned_graph, reference_graph)
print(f"F1 Score: {result['f1']}")
print(f"SHD: {result['shd']}")
```

### PDG Comparison

```python
from causaliq_analysis.metrics import pdg_compare
from causaliq_core.graph import PDG, EdgeProbabilities

learned = PDG(
    ["A", "B"],
    {("A", "B"): EdgeProbabilities(forward=0.4, backward=0.3, none=0.3)},
)
reference = PDG(
    ["A", "B"],
    {("A", "B"): EdgeProbabilities(forward=0.6, backward=0.1, none=0.3)},
)

# Compare edge probabilities (fractional low-level counts)
result = pdg_compare(learned, reference)
print(f"Matched: {result['arc_matched']}")
print(f"F1: {result['f1']}")
```

### With Bayesys Compatibility

```python
# Include Bayesys v1.5+ metrics
result = pdag_compare(
    learned_graph, reference_graph, bayesys="v1.5+"
)
print(f"Bayesys F1: {result['f1-b']}")
print(f"BSF Score: {result['bsf']}")
```

### KL Divergence

```python
from causaliq_analysis.metrics import kl
import pandas as pd

# Compare two probability distributions
dist1 = pd.Series([0.4, 0.3, 0.3], index=['A', 'B', 'C'])
dist2 = pd.Series([0.33, 0.33, 0.34], index=['A', 'B', 'C'])
divergence = kl(dist1, dist2)
print(f"KL Divergence: {divergence}")
```