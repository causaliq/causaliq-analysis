# Graph Merging

The `merge_graphs` function combines multiple learned causal graphs into a
single **Probabilistic Dependency Graph (PDG)** that captures structural
uncertainty. This is useful when you have graphs from different random seeds,
sample sizes, or algorithms.

## Parameters

| Parameter | CLI | Action | Required | Description |
|-----------|-----|--------|----------|-------------|
| `inputs` | `--input` | `inputs` | Yes | Input workflow cache or file path(s) |
| `group_by` | `--group-by` | `group_by` | Yes | Grouping dimensions (repeatable in CLI) |
| `where` | `--where` | `where` | No | Filter conditions (repeatable in CLI) |
| `weights` | `--weights` | `weights` | No | Custom weights (comma-separated in CLI) |
| `output` | `--output` | — | CLI only | Output file or directory path |

**Notes:**

- In CLI, `--group-by` and `--where` use `Key=Value` format and can be
  repeated for multiple dimensions
- In workflow actions, use matrix variables in `group_by` for batch
  processing: `network: "{{network}}"`
- Weights must sum to 1.0; if omitted, uniform weights (1/n) are used

---

## How It Works

### Step 1: Convert Input Graphs to Edge Probabilities

Each input graph (DAG or PDAG) is converted to edge probabilities before
merging. For each node pair (A, B) where A < B alphabetically:

**For DAG/PDAG inputs:**

| Edge in Source Graph | P(forward) | P(backward) | P(undirected) | P(none) |
|---------------------|------------|-------------|---------------|---------|
| A → B | 1.0 | 0.0 | 0.0 | 0.0 |
| B → A | 0.0 | 1.0 | 0.0 | 0.0 |
| A — B (undirected) | 0.0 | 0.0 | 1.0 | 0.0 |
| No edge | 0.0 | 0.0 | 0.0 | 1.0 |

**For PDG inputs:**

PDG edge probabilities are used directly as-is.

### Step 2: Combine Probabilities with Weighted Averaging

For each node pair, the final probabilities are computed as weighted averages:

$$P_{merged}(state) = \sum_{i=1}^{n} w_i \cdot P_i(state)$$

Where:
- $w_i$ is the weight for graph $i$ (default: uniform weights $1/n$)
- $P_i(state)$ is the probability of that edge state in graph $i$
- $state \in \{forward, backward, undirected, none\}$

### Example

Consider merging three graphs for nodes A and B:

| Graph | Edge | Weight |
|-------|------|--------|
| Graph 1 | A → B | 0.333 |
| Graph 2 | B → A | 0.333 |
| Graph 3 | (no edge) | 0.333 |

**Result:**

| State | Calculation | Probability |
|-------|-------------|-------------|
| P(forward) | 0.333 × 1.0 + 0.333 × 0.0 + 0.333 × 0.0 | 0.333 |
| P(backward) | 0.333 × 0.0 + 0.333 × 1.0 + 0.333 × 0.0 | 0.333 |
| P(undirected) | 0.333 × 0.0 + 0.333 × 0.0 + 0.333 × 0.0 | 0.0 |
| P(none) | 0.333 × 0.0 + 0.333 × 0.0 + 0.333 × 1.0 | 0.333 |

---

## Python API

### Function Signature

```python
from causaliq_analysis import merge_graphs
from causaliq_core.graph import DAG, PDAG, PDG

def merge_graphs(
    graphs: List[Union[DAG, PDAG, PDG]],
    weights: Optional[List[float]] = None,
) -> PDG:
    """Merge multiple graphs into a single PDG with edge probabilities.

    Args:
        graphs: List of graphs to merge. Must all have identical node sets.
        weights: Optional weights for each graph. Must sum to 1.0 if
            provided. If None, uniform weights (1/n) are used.

    Returns:
        PDG with weighted average edge probabilities.

    Raises:
        TypeError: If graphs or weights have invalid types.
        ValueError: If graphs list is empty, nodes differ across graphs,
            weights don't match graph count, or weights don't sum to 1.0.
    """
```

### Basic Usage

```python
from causaliq_analysis import merge_graphs
from causaliq_core.graph import DAG

# Create sample graphs
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

---

## CLI Usage

The `merge-graphs` command provides CLI access to graph merging with
`group_by` and `where` parameters for filtering and grouping inputs.

### Example Commands

```powershell
# Merge all graphs for a specific network and sample size
causaliq-analysis merge-graphs `
  --group-by network=asia `
  --group-by sample_size=500 `
  --where execution_status=completed `
  --input discovery_cache `
  --output merged_asia_500.graphml

# Merge with custom weights
causaliq-analysis merge-graphs `
  --group-by network=alarm `
  --weights 0.5,0.3,0.2 `
  --input discovery_cache `
  --output merged_alarm.graphml
```

---

## Workflow Action

The `merge_graphs` action can be used in causaliq-workflow definitions
for batch processing across multiple dimension combinations.

### Example Workflow

```yaml
# merge_discovery_results.yaml
description: "Merge structure learning results by network and sample size"

matrix:
  network: [asia, alarm, insurance]
  sample_size: [500, 1000, 5000]

actions:
  merge_graphs:
    inputs:
      - cache: discovery_results
    group_by:
      network: "{{network}}"
      sample_size: "{{sample_size}}"
    where:
      execution_status: completed
```

This workflow produces 9 merged PDGs (3 networks × 3 sample sizes), each
combining all graphs matching the specified network and sample size.

### Execution Model

The workflow action executes in two phases:

1. **Scan phase**: Read all input entries, apply `where` filters, group
   by the specified dimensions
2. **Execute phase**: Run `merge_graphs` for each unique dimension
   combination, writing results to the output cache

---

## Output Format

The merged PDG can be serialised to GraphML format for interchange with
other tools. The PDG includes:

- All nodes from the input graphs
- Edge probabilities for each node pair where P(none) < 1.0
- Metadata about source graph count and weights used

### Accessing Results

```python
# Get probabilities for a specific node pair
probs = pdg.get_probabilities("A", "B")

# Iterate over all edges with non-zero existence probability
for source, target, probs in pdg.existing_edges():
    print(f"{source}-{target}: P(exist)={probs.p_exist:.3f}")

# Get most likely edge state
probs = pdg.get_probabilities("A", "B")
print(f"Most likely: {probs.most_likely_state()}")
```

---

## See Also

- [Development Roadmap](../roadmap.md) - Planned features including
  optimal graph extraction and structural evaluation
- [PDG API Reference](../api/overview.md) - Full PDG class documentation
