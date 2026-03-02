# Graph Merging

The `merge_graphs` function combines multiple learned causal graphs into a
single **Probabilistic Dependency Graph (PDG)** that captures structural
uncertainty. This is useful when you have graphs from different random seeds,
sample sizes, or algorithms.

## Parameters

| Parameter | CLI | Action | Required | Description |
|-----------|-----|--------|----------|-------------|
| `inputs` | `-i`/`--input` | `inputs` | Yes | Input files (`.graphml` or `.db` cache). Repeatable in CLI. |
| `output` | `-o`/`--output` | — | CLI only | Output file path for merged PDG |
| `cpdag` | `--cpdag` | `cpdag` | No | Convert DAGs to CPDAGs before merging |


**Notes:**

- Input type is auto-detected by file extension:
  - `.graphml`: Read as GraphML file
  - `.db`: Read all entries from WorkflowCache database
- In CLI, use `-i` multiple times for multiple inputs
- In workflow actions, `inputs` is a list of file paths
- Weights must sum to 1.0; if omitted, uniform weights (1/n) are used
- When `cpdag=True`, DAGs are converted to their CPDAG (equivalence class)
  before merging, so the result averages over equivalence classes rather
  than specific edge orientations

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

The `merge-graph` command provides CLI access to graph merging. Input type
is auto-detected by file extension (`.graphml` or `.db`).

### Example Commands

```powershell
# Merge multiple GraphML files
causaliq-analysis merge-graph `
  -i graph1.graphml `
  -i graph2.graphml `
  -i graph3.graphml `
  -o merged.graphml

# Merge all graphs from a workflow cache
causaliq-analysis merge-graph `
  -i discovery_results.db `
  -o merged.graphml

# Mix GraphML files and cache databases
causaliq-analysis merge-graph `
  -i baseline.graphml `
  -i experiment_results.db `
  -o merged.graphml

# With custom weights and CPDAG conversion
causaliq-analysis merge-graph `
  -i graph1.graphml `
  -i graph2.graphml `
  -o merged.graphml `
  -w 0.7,0.3 `
  --cpdag

# Specify object name for cache entries
causaliq-analysis merge-graph `
  -i results.db `
  -o merged.graphml `
  -n learned_graph
```

---

## Workflow Action

The `merge_graphs` action can be used in causaliq-workflow definitions
for batch processing.

### Example Workflow

```yaml
# merge_discovery_results.yaml
description: "Merge structure learning results"

actions:
  merge_graphs:
    inputs:
      - "results/asia_seed1.graphml"
      - "results/asia_seed2.graphml"
      - "results/asia_seed3.graphml"

# Or merge from a workflow cache database
actions:
  merge_graphs:
    inputs:
      - "discovery_results.db"
    object_name: graph  # Default object name in cache entries

# With custom weights and CPDAG conversion
actions:
  merge_graphs:
    inputs:
      - "graph1.graphml"
      - "graph2.graphml"
    weights: [0.6, 0.4]
    cpdag: true
```

### Input Types

The `inputs` parameter accepts a list of file paths. Type is auto-detected:

- **`.graphml` files**: Read directly as GraphML
- **`.db` files**: Read all entries from WorkflowCache database, extracting
  the object specified by `object_name` (default: `graph`)

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

- [Summarisation Paradigm](../architecture/summarisation_paradigm.md) —
  Architecture for aggregation operations including filtering and weighting
- [PDG API Reference](../api/overview.md) — Full PDG class documentation
