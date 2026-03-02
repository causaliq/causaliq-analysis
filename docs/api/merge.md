# CausalIQ Analysis Merge

This module provides functions for merging multiple graphs (DAG, PDAG, PDG)
into a single Probabilistic Dependency Graph (PDG) with weighted edge
probabilities.

## Core Functions

::: causaliq_analysis.merge.merge_graphs
    options:
        show_root_heading: true
        show_source: false
        heading_level: 3

Merge multiple graphs into a single PDG with weighted average edge
probabilities.

## Overview

### Graph Merging

The `merge_graphs` function combines multiple learned causal graphs into a
single **Probabilistic Dependency Graph (PDG)** that captures structural
uncertainty. This is useful when you have graphs from:

- Different random seeds
- Different sample sizes
- Different algorithms
- Bootstrap resampling experiments

### Input Graph Types

The function accepts any combination of:

| Type | Treatment |
|------|-----------|
| **DAG** | Edges treated as probability 1.0 for their direction |
| **PDAG** | Edges treated as probability 1.0 for their type |
| **PDG** | Edge probabilities used directly |

All input graphs must have identical node sets.

### CPDAG Conversion

When `cpdag=True`, DAGs are converted to their CPDAG (Completed Partially
Directed Acyclic Graph) before merging. This averages over Markov
equivalence classes rather than specific DAG orientations, which is often
more appropriate for comparing structure learning results.

### Weighting

By default, uniform weights (1/n) are applied. Custom weights can be
provided to give different graphs more or less influence on the final
result. Weights must:

- Have one value per input graph
- Sum to 1.0
- Be non-negative

## Usage Examples

### Basic Merging

```python
from causaliq_analysis import merge_graphs
from causaliq_core.graph import DAG

# Create sample graphs from different experiments
dag1 = DAG(["A", "B", "C"], [("A", "->", "B"), ("B", "->", "C")])
dag2 = DAG(["A", "B", "C"], [("A", "->", "B"), ("C", "->", "B")])
dag3 = DAG(["A", "B", "C"], [("B", "->", "A"), ("B", "->", "C")])

# Merge with uniform weights
pdg = merge_graphs([dag1, dag2, dag3])

# Inspect edge probabilities
probs = pdg.get_probabilities("A", "B")
print(f"P(A → B): {probs.forward:.3f}")
print(f"P(B → A): {probs.backward:.3f}")
print(f"P(A — B): {probs.undirected:.3f}")
print(f"P(no edge): {probs.none:.3f}")
```

### Custom Weights

```python
# Weight first graph more heavily (e.g., larger sample size)
pdg = merge_graphs([dag1, dag2, dag3], weights=[0.5, 0.25, 0.25])
```

### CPDAG Conversion

```python
# Convert DAGs to CPDAGs before merging
# This averages over equivalence classes
pdg = merge_graphs([dag1, dag2, dag3], cpdag=True)
```

### Merging PDGs

```python
from causaliq_core.graph import PDG

# PDGs can be merged with DAGs/PDAGs
# Their edge probabilities are used directly
pdg_combined = merge_graphs([pdg1, dag1, pdag1])
```

## See Also

- [Graph Merging User Guide](../userguide/merge_graphs.md) — Detailed usage
  including CLI and workflow action
- [Summarisation Paradigm](../architecture/summarisation_paradigm.md) —
  Architecture for aggregation operations
