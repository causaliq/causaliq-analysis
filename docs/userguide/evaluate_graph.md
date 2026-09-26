# Evaluating Graphs

The `evaluate_graph` capability structurally evaluates a graph (PDAG, CPDAG, or
DAG) against a reference graph. Note that comparisons between general SDG
graphs are not supported.

This is an `update` action (see
[workflow patterns](https://workflow.causaliq.org/userguide/action_patterns/))
and so updates the metadata for an existing graph **in the input cache** with
the requested metrics when used within a CausalIQ workflow.

---

## Parameters

| Parameter   | CLI Flag           | Required | Description |
|-------------|--------------------|----------|-------------|
| `input`     | `-i`/`--input`     | Yes      | Learned graph file (CLI) or workflow cache `.db` (action) |
| `reference` | `-r`/`--reference` | Yes      | Reference graph file (`.csv`, `.graphml`, `.tetrad`, `.xdsl`, `.dsc`) or workflow cache (`.db`) |
| `metric`    | `-m`/`--metric`    | Yes      | Metric(s) to compute (repeatable in CLI) |
| `output`    | `-o`/`--output`    | CLI only | Output directory for `_meta.json` file |
| `filter`    | —                  | No       | Filter expression for cache entries (workflow only) |

**Supported Metrics:** `f1`, `shd`, `precision`, `recall`, `edge`, `equiv.f1`,
`equiv.shd`, `equiv.edge`

**Notes:**

- In CLI mode, `input` is a graph file (`.csv`, `.graphml`, `.tetrad`, `.xdsl`,
  `.dsc`) and `output` is a directory where `_meta.json` will be written.
- IN CLI mode you can request multiple metrics by repeating the -m/00metric option e.g. "-m f1 -m shd"
- In workflows, `input` is a workflow cache (`.db`) and `output` is
  **prohibited** (UPDATE action pattern). The `filter` parameter can select
  specific cache entries.
- In workflows, `reference` can be another workflow cache (`.db`) whose
  entries contain reference graphs with the same key structure as the
  input cache. Each input entry is compared against the reference entry
  with identical matrix variable values.

---

## CLI Usage

### Basic Comparison

Compare a learned graph against a reference:

```bash
causaliq-analysis evaluate-graph -i learned.graphml -r ground_truth.graphml \
    -m f1 -m shd -o results/eval
```

This creates `results/eval/_meta.json` containing:

```json
{
  "f1": 0.7,
  "shd": 3
}
```

### All Metrics

Request all available metrics:

```bash
causaliq-analysis evaluate-graph -i learned.graphml -r ground_truth.graphml \
    -m f1 -m shd -m precision -m recall -m edge \
    -m equiv.f1 -m equiv.shd -m equiv.edge -o results/eval
```

### Equivalence Class Metrics

Compare equivalence classes (CPDAGs) rather than raw graphs:

```bash
causaliq-analysis evaluate-graph -i learned.graphml -r ground_truth.graphml \
    -m equiv.f1 -m equiv.shd -o results/eval
```

### Low-level Edge Counts

The `edge` metric expands to the nine low-level edge categories reported by
`pdag_compare`, plus `missing_matched` which completes the 2x2 confusion
matrix:

| Count | Meaning |
|-------|---------|
| `arc_matched` | Arc present with the same orientation in both graphs |
| `arc_reversed` | Arc present in both graphs but oppositely orientated |
| `edge_not_arc` | Undirected edge in the graph, arc in the reference |
| `arc_not_edge` | Arc in the graph, undirected edge in the reference |
| `edge_matched` | Undirected edge present in both graphs |
| `arc_extra` | Arc in the graph with no counterpart in the reference |
| `edge_extra` | Undirected edge in the graph with no counterpart |
| `arc_missing` | Arc in the reference with no counterpart in the graph |
| `edge_missing` | Undirected edge in the reference with no counterpart |
| `missing_matched` | Edges absent from both graphs (correctly rejected) |

```bash
causaliq-analysis evaluate-graph -i learned.graphml -r ground_truth.graphml \
    -m edge -o results/eval
```

This writes `results/eval/_meta.json` containing the counts:

```json
{
  "arc_matched": 2,
  "arc_reversed": 0,
  "edge_not_arc": 0,
  "arc_not_edge": 0,
  "edge_matched": 0,
  "arc_extra": 0,
  "edge_extra": 0,
  "arc_missing": 0,
  "edge_missing": 0,
  "missing_matched": 4
}
```

`missing_matched` is the number of edges absent from both graphs. It is derived
as the maximum possible number of edges minus the sum of the other counts, so
it is usually the largest of the counts.

`equiv.edge` reports the same counts computed after converting both graphs to
CPDAGs, exactly as `equiv.f1` and `equiv.shd` do. Its keys are prefixed with
`equiv.`:

```bash
causaliq-analysis evaluate-graph -i learned.graphml -r ground_truth.graphml \
    -m equiv.edge -o results/eval
```

```json
{
  "equiv.arc_matched": 0,
  "equiv.arc_reversed": 0,
  "equiv.edge_not_arc": 0,
  "equiv.arc_not_edge": 0,
  "equiv.edge_matched": 2,
  "equiv.arc_extra": 0,
  "equiv.edge_extra": 0,
  "equiv.arc_missing": 0,
  "equiv.edge_missing": 0,
  "equiv.missing_matched": 1
}
```

Because the counts are stored as flat metadata keys, they can be aggregated
directly with the [`summarise`](summarise.md) action:

```bash
causaliq-analysis summarise -i results/eval/_meta.json \
    -m arc_matched.mean -m equiv.missing_matched.sd -o results/summary.csv
```

---

## Workflow Usage

In a CausalIQ workflow, `evaluate_graph` operates as an UPDATE action:

```yaml
steps:
  - name: "Evaluate Graphs"
    uses: "causaliq-analysis"
    with:
      action: "evaluate_graph"
      input: "results/graphs.db"
      reference: "reference/asia_true.graphml"
      metric:
        - f1
        - shd
        - precision
        - recall
```

This computes metrics for each graph entry in the cache and adds them to the
entry's metadata.

### Workflow Cache Reference

Instead of a single ground-truth graph file, `reference` can point to another
workflow cache (`.db`) containing reference graphs. This enables comparing
graphs across caches that share identical cache keys, for example when
checking that causal discovery produces the same graphs as legacy BNSL code:

```yaml
steps:
  - name: "Compare against legacy BNSL graphs"
    uses: "causaliq-analysis"
    with:
      action: "evaluate_graph"
      input: "results/causaliq_graphs.db"
      reference: "results/legacy_bnsl_graphs.db"
      metric:
        - f1
        - shd
```

The reference cache must use the same key structure (matrix variable names) as
the input cache. Each input entry is evaluated against the reference entry
with identical matrix variable values (e.g. `network='asia', sample_size=100`).
If the key structures differ, no matching reference entry exists, or a
reference entry does not contain a graph, an error is reported.

---

## Supported Metrics

### Available Metrics Summary

| Metric | Description |
|--------|-------------|
| `f1` | F1 score from direct graph comparison |
| `shd` | Structural Hamming Distance |
| `precision` | Precision from direct comparison |
| `recall` | Recall from direct comparison |
| `equiv.f1` | F1 comparing equivalence classes (CPDAGs) |
| `equiv.shd` | SHD comparing equivalence classes (CPDAGs) |
| `edge` | Low-level edge comparison counts (see above) |
| `equiv.edge` | Low-level edge counts from CPDAG comparison |

### Metric Naming in CausalIQ

Many different structural metrics are used to evaluate graphs in causal
discovery. Common ones are F1, Precision, Recall and Structural Hamming
Distance (SHD), but others specific to causal discovery, such as Structural
Intervention Distance (SID), are also employed.

Critical differences in structural evaluation include:

- Whether the raw graphs (e.g., a learned DAG and a reference DAG) are
  compared, or whether the equivalence classes (CPDAGs or PAGs) to which they
  belong are compared. The former is generally more appropriate in causal
  discovery where orientation of arcs is critical.
- Many structural metrics are built upon true/false positive/negative counts,
  and different authors take different approaches to computing these counts
  for arcs which have an orientation property.
- Some authors report the raw metric but others normalise it (e.g., SHD
  divided by the number of variables or edges).

CausalIQ uses the following naming structure for metrics:

  `[<preprocessing>].<metric>.[<semantics>].[<postprocessing>].[<statistic>]`

| Element | Optional | Description | Supported Values |
|---------|----------|-------------|------------------|
| **`<preprocessing>`** | Yes | Preprocessing before comparison | `equiv` (convert to CPDAGs first) |
| **`<metric>`** | No | The basic metric | `f1`, `shd`, `precision`, `recall`, and the low-level edge counts (`arc_matched`, `arc_reversed`, `edge_not_arc`, `arc_not_edge`, `edge_matched`, `arc_extra`, `edge_extra`, `arc_missing`, `edge_missing`, `missing_matched`) |
| **`<scheme>`** | Yes | Alternative computation semantics | *not currently supported* |
| **`<postprocessing>`** | Yes | Postprocessing, e.g., normalisation | *not currently supported* |
| **`<statistic>`** | Yes | Statistic over multiple values | *see [`summarise`](summarise.md) action* |

---

### Legacy Support

The core module which provides structural comparisons between PDAGs (mixed
directed and undirected edge graphs, a superset of DAGs and CPDAGs) is
`pdag_compare` in `metrics.py`. It implements the comparison semantics used
consistently in CausalIQ papers and the legacy `discovery` repository.

### Comparison Semantics

To be completed — will describe in detail how the CausalIQ code computes the
confusion matrix counts that underlie the structural metrics.

## See Also

- [Summarisation Paradigm](../architecture/summarisation_paradigm.md) —
  Architecture for aggregation operations including filtering and weighting
- [PDG API Reference](../api/overview.md) — Full PDG class documentation
