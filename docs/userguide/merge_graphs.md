# Graph Merging

The `merge_graphs` function combines multiple learned causal graphs into a
single **Probabilistic Dependency Graph (PDG)** that captures structural
uncertainty. This is useful when you have graphs from different random seeds,
sample sizes, or algorithms.

## Parameters

| Parameter | CLI | Required | Description |
|-----------|-----|----------|-------------|
| `input` | `-i`/`--input` | Yes | Input files (`.graphml` or `.db` cache). |
| `output` | `-o`/`--output` | Yes | Output destination - path for CLI, `.db` cache for action |
| `filter` | — | No | Filter expression for cache entries (Python syntax, action only) |
| `weights` | `-w`/`--weights` | No | JSON file specifying metadata-driven weights |
| `cpdag` | `--cpdag` | No | Convert DAGs to CPDAGs before merging |
| `strategy` | `-s`/`--strategy` | No | Merge strategy: `average` (default), `noisy_or`, or `max` |


**Notes:**

- Input type is auto-detected by file extension:
  - `.graphml`: Read as GraphML file (filter/weights not applicable)
  - `.db`: Read all graphml objects from WorkflowCache entries
- In CLI, use `-i` multiple times for multiple inputs
- In workflows, `merge_graphs` is an aggregation action requiring `input`,
  `output`, and a `matrix` definition
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

### Step 2: Combine Probabilities

The `strategy` parameter controls how edge probabilities from different
sources are combined. Three strategies are available.

#### Average (default)

Weighted averaging of probability vectors. For each node pair, the final
probabilities are computed as:

$$P_{merged}(state) = \sum_{i=1}^{n} w_i \cdot P_i(state)$$

Where:
- $w_i$ is the weight for graph $i$ (default: uniform weights $1/n$)
- $P_i(state)$ is the probability of that edge state in graph $i$
- $state \in \{forward, backward, undirected, none\}$

This strategy treats absence of an edge as positive evidence against
existence. If only one of two equally-weighted sources reports an edge,
the merged existence probability is halved.

#### Noisy-OR

Noisy-OR for edge existence combined with weighted orientation averaging.
An edge exists if **any** source supports it:

$$P(none) = \prod_{i=1}^{n} P_i(none)^{\alpha_i}$$

where $\alpha_i = w_i \cdot n$. Under uniform weights, each
$\alpha_i = 1$ giving standard noisy-OR.

Edge existence is then $P(exist) = 1 - P(none)$ and the directional
probabilities are computed as a weighted average of the conditional
orientations from contributing sources:

$$P(dir) = P(exist) \cdot \frac{\sum_i w_i \cdot P_i(exist) \cdot P_i(dir \mid exist)}{\sum_i w_i \cdot P_i(exist)}$$

This strategy is useful when fusing heterogeneous sources — for example,
an LLM with good orientation knowledge and a structure-learning algorithm
with good existence detection. Because absence in one source does not
cancel presence in another, orientation knowledge is preserved.

#### Max

Selects the single most confident source per edge. For each node pair,
the source with the highest weighted existence score is chosen:

$$\text{best} = \arg\max_i \; w_i \cdot P_i(exist) \cdot n$$

The complete probability vector from that source is used as-is. This is
useful as a simple baseline or when one source is expected to dominate.

### Example (Average)

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

### Example (Noisy-OR)

Same three graphs with uniform weights ($\alpha_i = 1$):

| State | Calculation | Probability |
|-------|-------------|-------------|
| P(none) | $0.0^1 \times 0.0^1 \times 1.0^1$ | 0.0 |
| P(exist) | $1 - 0$ | 1.0 |
| P(forward) | $1.0 \times \frac{0.333 \times 1.0}{0.333 + 0.333}$ | 0.5 |
| P(backward) | $1.0 \times \frac{0.333 \times 1.0}{0.333 + 0.333}$ | 0.5 |

Because Graph 1 and Graph 2 both report a definite edge, the noisy-OR
combination gives P(exist) = 1.0, and orientation is split between
forward and backward according to the contributing sources.

---

## Python API

### Function Signature

```python
from causaliq_analysis import merge_graphs
from causaliq_core.graph import DAG, PDAG, PDG

def merge_graphs(
    graphs: List[Union[DAG, PDAG, PDG]],
    weights: Optional[List[float]] = None,
    cpdag: bool = False,
    strategy: str = "average",
) -> PDG:
    """Merge multiple graphs into a single PDG with edge probabilities.

    Args:
        graphs: List of graphs to merge. Must all have identical node sets.
        weights: Optional weights for each graph. Must sum to 1.0 if
            provided. If None, uniform weights (1/n) are used.
        cpdag: If True, convert DAGs to their CPDAG (equivalence class)
            before merging.
        strategy: Merge strategy. 'average' for weighted averaging
            (default). 'noisy_or' for noisy-OR existence with
            weighted orientation. 'max' to select the most
            confident source per edge.

    Returns:
        PDG with combined edge probabilities.

    Raises:
        TypeError: If graphs or weights have invalid types.
        ValueError: If graphs list is empty, nodes differ across graphs,
            weights don't match graph count, weights don't sum to 1.0,
            or strategy is invalid.
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

### CPDAG Conversion

```python
# Convert DAGs to CPDAGs before merging (averages over equivalence classes)
pdg = merge_graphs([dag1, dag2, dag3], cpdag=True)
```

### Noisy-OR Strategy

```python
# Noisy-OR preserves edges reported by any source and
# blends orientation from contributing sources
pdg = merge_graphs([dag1, dag2, dag3], strategy="noisy_or")

# Combine with custom weights (e.g., trust LLM orientation more)
pdg = merge_graphs(
    [llm_graph, fges_graph],
    weights=[0.6, 0.4],
    strategy="noisy_or",
)
```

### Max Strategy

```python
# Select the most confident source per edge
pdg = merge_graphs([dag1, dag2, dag3], strategy="max")
```

---

## CLI Usage

The `merge-graphs` command provides CLI access to graph merging. Input type
is auto-detected by file extension (`.graphml` or `.db`).

### Example Commands

```powershell
# Merge multiple GraphML files
causaliq-analysis merge-graphs `
  -i graph1.graphml `
  -i graph2.graphml `
  -i graph3.graphml `
  -o merged.graphml

# Merge all graphs from a workflow cache
causaliq-analysis merge-graphs `
  -i discovery_results.db `
  -o merged.graphml

# Mix GraphML files and cache databases
causaliq-analysis merge-graphs `
  -i baseline.graphml `
  -i experiment_results.db `
  -o merged.graphml

# Filter cache entries before merging
causaliq-analysis merge-graphs `
  -i results.db `
  -f "network == 'asia' and sample_size > 500" `
  -o merged.graphml

# With metadata-driven weights (JSON file) and CPDAG conversion
causaliq-analysis merge-graphs `
  -i results.db `
  -w weights.json `
  -o merged.graphml `
  --cpdag

# Noisy-OR merge strategy
causaliq-analysis merge-graphs `
  -i results.db `
  --strategy noisy_or `
  -o merged.graphml

# Max strategy with filtering
causaliq-analysis merge-graphs `
  -i results.db `
  -f "network == 'asia'" `
  --strategy max `
  -o merged.graphml
```

---

## Workflow Action

The `merge_graphs` action is an **aggregation action** — it requires `input`,
`output`, and `matrix` parameters. The matrix controls output dimensionality:
entries from the input cache are grouped by matrix variable values and merged
into new entries in the output cache.

See [Workflow Action Patterns](introduction.md#workflow-action-patterns) for
details on action patterns.

### Example Workflow

```yaml
# merge_discovery_results.yaml - Merge graphs per network
id: "merge_by_network"
description: "Merge structure learning results by network"

matrix:
  network: ["asia", "cancer"]

steps:
  - name: "Merge Graphs"
    uses: "causaliq-analysis"
    with:
      action: "merge_graphs"
      input: "results/discovery_results.db"
      output: "results/merged.db"
```

If `discovery_results.db` contains entries for multiple sample sizes per
network, this produces one merged PDG per network in `merged.db`.

```yaml
# Noisy-OR fusion of LLM and BNSL results
id: "fuse_noisy_or"
description: "Fuse LLM and structure learning graphs"

matrix:
  network: ["asia", "cancer"]

steps:
  - name: "Fuse Graphs"
    uses: "causaliq-analysis"
    with:
      action: "merge_graphs"
      input: "results/discovery_results.db"
      strategy: "noisy_or"
      output: "results/fused.db"
```

```yaml
# With filtering and CPDAG conversion
id: "merge_filtered"
description: "Merge filtered graphs"

matrix:
  network: ["asia"]

steps:
  - name: "Merge Filtered"
    uses: "causaliq-analysis"
    with:
      action: "merge_graphs"
      input: "results/discovery_results.db"
      filter: "sample_size > 500"
      cpdag: true
      output: "results/merged.db"
```

### Input Types

Input type is auto-detected by file extension:

- **`.graphml` files**: Read directly as GraphML (filter/weights not applicable)
- **`.db` files**: Read all graphml objects from WorkflowCache database entries
  (filter/weights can be applied)

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
