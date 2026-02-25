# CausalIQ Analysis - Development Roadmap

**Last updated**: February 23, 2026  

This project roadmap fits into the
[overall ecosystem roadmap](https://causaliq.org/projects/ecosystem_roadmap/)

## 🚧  Under development

- **Release v0.3.0 - Graph Merging & Optimal Extraction**

**Scope**

### Legacy Trace Migration (`migrate_trace`)

Convert legacy Trace pickle files to DAG/CPDAG in workflow caches.

- **Core functionality** (`src/causaliq_analysis/trace.py` - extend):
  - `trace_to_dag(trace: Trace) -> DAG` - extract final DAG from trace
  - `trace_to_cpdag(trace: Trace) -> CPDAG` - extract and convert to CPDAG

- **Workflow action** (`migrate_trace`):
  - Input: trace file path pattern, sample_size filter, seeds filter
  - Output: DAG/CPDAG written to workflow cache (one entry per trace)
  - Metadata: original trace context (network, sample_size, seed, etc.)

### Graph Merging (`merge_graphs`)

**Background: Summarisation Paradigm**

`merge_graphs` is the first "summarisation" action in causaliq-analysis. Other
future examples include aggregating accuracy metrics, scores, execution times,
and statistical significance. We adopt a consistent paradigm across all
summarisation actions, drawing terminology from BI software (Power BI/dbt) and
CI workflows (GitHub Actions).

**Core Concepts**

| Concept | Parameter | Purpose |
|---------|-----------|---------|
| Grouping dimensions | `group_by` | Defines output granularity - one output per unique combination |
| Input filtering | `where` | Restricts inputs by metadata values before grouping |
| Output elements | (action-specific) | Metrics/values produced (e.g., F1, SD, merged_graph) |

**Workflow vs Action Separation**

- **Matrix** (workflow level) - orchestration/expansion, defines combinations
- **group_by** (action level) - declares grouping dimensions for the action

```yaml
# Workflow example
matrix:
  network: [asia, alarm]
  sample_size: [500, 1000]

actions:
  merge_graphs:
    group_by:
      network: "{{network}}"
      sample_size: "{{sample_size}}"
    where:
      execution_status: completed
    inputs:
      - cache: discovery_results
```

**CLI Parity**

The CLI uses identical `group_by` and `where` parameters, producing a single
summary output for exploration before incorporating into workflows:

```powershell
causaliq-analysis merge-graphs `
  --group-by network=asia `
  --group-by sample_size=500 `
  --where execution_status=completed `
  --input discovery_cache
```

**Execution Model**

Two-phase execution:
1. **Scan phase** - read inputs, apply `where` filters, group by dimensions
2. **Execute phase** - run summarisation for each output data point

**Requirements**

- Shared validation/execution code between CLI and workflow actions
- Support for multiple input workflow caches
- Action validates that input metadata contains declared `group_by` keys

**Specific `merge_graphs` functionality**

Merge multiple DAGs/CPDAGs/PDGs into a single PDG with edge probabilities.

- **Core functionality** (`src/causaliq_analysis/graph/merge.py`):
  - `merge_graphs(graphs: List[Union[DAG, CPDAG, PDG]],
                  weights: Optional[List[float]] = None) -> PDG`
  - Weighted averaging of edge probabilities
  - Support for uniform weights (default) and custom weights
  - DAG/CPDAG edges converted to 1.0 probability before averaging

- **Merge strategies**:
  - `weighted_average` - Simple weighted mean (initial implementation)
  - `bayesian` - Prior/posterior updating (future)

- **Workflow action** (`merge_graphs`):
  - Input: list of GraphML file paths or cache entry references
  - Output: graphml (PDG string), metadata (source count, weights)

### Optimal Graph Extraction (`best_graph`)

Extract the "best" DAG or CPDAG from a PDG.

- **Core functionality** (`src/causaliq_analysis/graph/optimal.py`):
  - `extract_best_dag(pdg: PDG, method: str = "greedy") -> DAG`
  - `extract_best_cpdag(pdg: PDG, method: str = "greedy") -> CPDAG`

- **Extraction methods**:
  - `greedy` - Threshold edges, apply Meek's rules (initial)
  - `ilp` - Integer linear programming optimisation (future)

- **Workflow action** (`best_graph`):
  - Input: GraphML file path or cache entry reference (PDG)
  - Output: graphml (DAG/CPDAG string), metadata

### Structural Evaluation (`evaluate`)

Compute F1, precision, recall vs true graph.

- **Core functionality** (`src/causaliq_analysis/metrics/comparison.py`):
  - `evaluate_structure(predicted: Graph, true: Graph) -> Metrics`
  - Skeleton metrics (ignoring orientation)
  - Oriented metrics (including orientation)

- **Workflow action** (`evaluate`):
  - Input: predicted graph (GraphML/cache), true graph (GraphML/cache)
  - Output: metrics dict (F1, precision, recall, SHD, etc.)

### Integration

- Workflow cache read/write via causaliq-workflow
- GraphML interchange format for all graph types
- Graph inputs to actions via file paths or cache references

---

## ✅ Implemented Releases

- **Release v0.1.0 - Foundation Metrics**: CausalIQ and Bayesys structural graph metrics and KL metric.
- **Release v0.2.0 - Legacy Trace**: Support for reading and writing structure learning traces in legacy pickle format (this will be superseded by a more open format).

*See Git commit history for detailed implementation progress*

## 🛣️ Upcoming Releases

- none scoped yet


