# CausalIQ Analysis Metrics

This module provides functions for analysing and comparing causal graphs, including structural metrics, Kullback-Leibler divergence calculations, and Bayesys compatibility metrics.

## Core Functions

::: causaliq_analysis.metrics.pdag_compare
    options:
        show_root_heading: true
        show_source: false
        heading_level: 3

Compare a PDAG with a reference PDAG to compute structural comparison metrics including precision, recall, F1 score, and Structural Hamming Distance (SHD).

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

- **Arc metrics**: matched, reversed, missing, extra
- **Edge metrics**: matched, missing, extra, not-arc conversions  
- **Summary metrics**: precision, recall, F1 score, Structural Hamming Distance (SHD)
- **Bayesys compatibility**: Optional Bayesys v1.3-v1.6 metrics

The function includes built-in sanity checks to ensure metric consistency and can optionally identify specific edges in each category for detailed analysis.

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

### With Bayesys Compatibility

```python
# Include Bayesys v1.6 metrics
result = pdag_compare(learned_graph, reference_graph, bayesys="v1.6")
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