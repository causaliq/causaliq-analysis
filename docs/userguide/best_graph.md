# Extracting the Best Graph

The `best_graph` capability extracts an optimal DAG from a Probabilistic
Dependency Graph (PDG) using a greedy algorithm. This is useful when you have
a PDG representing structural uncertainty (e.g., from merged graphs) and need
to select a single best DAG for downstream analysis or inference.

This is an `update` action (see
[workflow patterns](https://workflow.causaliq.org/userguide/action_patterns/))
and so updates entries **in the input cache** by adding a DAG object to each
matched entry.

## Parameters

| Parameter   | CLI  | Required | Default | Description |
|-------------|------|----------|---------|-------------|
| `input`     | `-i` | Yes      | None    | Input PDG file (`.graphml`) or cache (`.db`) |
| `output`    | `-o` | Yes (CLI)| None    | Output directory for DAG and metadata files |
| `threshold` | `-t` | No       | 0.0     | Minimum edge probability threshold |
| `filter`    | `-f` | No       | None    | Filter entries in input cache |

**Notes:**

- Input type is auto-detected by file extension:
  - `.graphml`: Read as PDG file (CLI only)
  - `.db`: Read all entries from WorkflowCache database containing PDG objects
- The `output` parameter is **CLI only**. Creates output directory containing
  `dag.graphml` and `_meta.json`.
- In workflows, `best_graph` is an update action: `output` is **prohibited**.
  The action processes all entries in the input cache and adds a DAG object to
  each entry.

---

## How It Works

### Step 1: Order Edges by Probability

For each node pair, the algorithm computes an effective directed probability
by splitting undirected probability equally between forward and backward
directions:

$$P_{effective}(forward) = P(forward) + \frac{P(undirected)}{2}$$

$$P_{effective}(backward) = P(backward) + \frac{P(undirected)}{2}$$

Edges are then sorted by their maximum effective probability in descending
order.

### Step 2: Greedy Edge Selection

The algorithm greedily adds edges to the DAG in probability order:

1. Select the highest-probability edge not yet processed
2. Choose direction (forward or backward) based on higher effective
   probability
3. **Threshold check**: Skip if max probability < threshold
4. **Cycle check**: Skip if adding this edge would create a cycle
5. **Tie-breaking**: If probabilities are equal, use alphabetical ordering
   (source < target)
6. Add edge to DAG and continue

### Step 3: Return Statistics

The algorithm returns the DAG along with extraction statistics:

| Statistic | Description |
|-----------|-------------|
| `edges_included` | Number of edges in the optimal DAG |
| `edges_skipped_cycle` | Edges skipped to avoid cycles |
| `edges_skipped_threshold` | Edges below probability threshold |
| `tie_breaks_applied` | Direction ties resolved alphabetically |

### Example

Consider a PDG with three nodes and the following edge probabilities:

| Node Pair | P(forward) | P(backward) | P(undirected) | P(none) |
|-----------|------------|-------------|---------------|---------|
| (A, B)    | 0.6        | 0.1         | 0.2           | 0.1     |
| (B, C)    | 0.3        | 0.5         | 0.1           | 0.1     |
| (A, C)    | 0.0        | 0.0         | 0.0           | 1.0     |

**Effective probabilities after splitting undirected:**

| Node Pair | P_eff(forward) | P_eff(backward) | Max |
|-----------|----------------|-----------------|-----|
| (A, B)    | 0.7            | 0.2             | 0.7 |
| (B, C)    | 0.35           | 0.55            | 0.55|

**Result (threshold=0.0):**

1. Add A → B (0.7 > 0.2)
2. Add C → B (0.55 > 0.35)

Final DAG: A → B ← C (2 edges, 0 skipped, 0 tie-breaks)

---

## CLI Usage

### Basic Usage

Extract optimal DAG from a PDG file:

```bash
causaliq-analysis best-graph -i merged.graphml -o results/optimal
```

This creates:

- `results/optimal/dag.graphml` — The optimal DAG
- `results/optimal/_meta.json` — Extraction metadata and statistics

### With Threshold

Apply a minimum probability threshold to filter weak edges:

```bash
causaliq-analysis best-graph -i merged.graphml -o results/optimal \
    --threshold=0.5
```

Only edges with max effective probability ≥ 0.5 will be included.

---

## Workflow Usage

In a CausalIQ workflow, `best_graph` operates as an UPDATE action that adds
a DAG object to entries containing PDG objects:

```yaml
steps:
  - name: "Merge experimental graphs"
    uses: "causaliq-analysis"
    with:
      action: "merge_graphs"
      input: "results/learned_graphs.db"
      output: "results/merged.db"
    matrix:
      network: [asia, cancer]
      sample_size: [100, 1K]

  - name: "Extract optimal DAGs"
    uses: "causaliq-analysis"
    with:
      action: "best_graph"
      input: "results/merged.db"
      threshold: 0.3
```

After this workflow:

- Each entry in `results/merged.db` will contain both:
  - The original `pdg` object from merge_graphs
  - A new `dag` object from best_graph

---

## Output Metadata

The `best_graph` action writes extraction statistics to metadata, which can be
used for analysis or filtering:

```json
{
  "metadata": {
    "causaliq-analysis": {
      "best_graph": {
        "action": "best_graph",
        "timestamp": "2024-01-15T10:30:00+00:00",
        "threshold": 0.3,
        "edges_included": 5,
        "edges_skipped_cycle": 2,
        "edges_skipped_threshold": 1,
        "tie_breaks_applied": 0
      }
    }
  }
}
```

---

## Python API

### Using the Action Provider

```python
from causaliq_analysis.workflow_action import AnalysisActionProvider

action = AnalysisActionProvider()
status, metadata, objects = action.run(
    "best_graph",
    {"input": "merged.graphml", "threshold": 0.5},
    mode="run",
)

# Extract DAG content
dag_graphml = objects[0]["content"]
print(f"Edges included: {metadata['edges_included']}")
```

### Using PDG Directly

```python
from causaliq_core.graph import PDG, EdgeProbabilities
from causaliq_core.graph.io import graphml

# Load or create PDG
pdg = PDG(
    ["A", "B", "C"],
    {
        ("A", "B"): EdgeProbabilities(forward=0.8, none=0.2),
        ("B", "C"): EdgeProbabilities(forward=0.7, none=0.3),
    },
)

# Extract optimal DAG
result = pdg.to_dag_greedy(threshold=0.5)

print(f"Optimal DAG edges: {list(result.dag.edges)}")
print(f"Edges included: {result.edges_included}")
print(f"Edges skipped (cycle): {result.edges_skipped_cycle}")
print(f"Edges skipped (threshold): {result.edges_skipped_threshold}")
print(f"Tie-breaks applied: {result.tie_breaks_applied}")
```

---

## See Also

- [Graph Merging](merge_graphs.md) — Create PDGs by merging multiple graphs
- [Evaluating Graphs](evaluate_graph.md) — Evaluate extracted DAGs against
  reference graphs
- [Summarisation Paradigm](../architecture/summarisation_paradigm.md) —
  Architecture for aggregation operations
