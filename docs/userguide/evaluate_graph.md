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
| `reference` | `-r`/`--reference` | Yes      | Reference graph file (`.csv`, `.graphml`, `.tetrad`, `.xdsl`, `.dsc`) |
| `metric`    | `-m`/`--metric`    | Yes      | Metric(s) to compute (repeatable in CLI) |
| `output`    | `-o`/`--output`    | CLI only | Output directory for `_meta.json` file |
| `filter`    | —                  | No       | Filter expression for cache entries (workflow only) |

**Supported Metrics:** `f1`, `shd`, `precision`, `recall`, `equiv.f1`,
`equiv.shd`

**Notes:**

- In CLI mode, `input` is a graph file (`.csv`, `.graphml`, `.tetrad`, `.xdsl`,
  `.dsc`) and `output` is a directory where `_meta.json` will be written.
- IN CLI mode you can request multiple metrics by repeating the -m/00metric option e.g. "-m f1 -m shd"
- In workflows, `input` is a workflow cache (`.db`) and `output` is
  **prohibited** (UPDATE action pattern). The `filter` parameter can select
  specific cache entries.

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
    -m f1 -m shd -m precision -m recall -m equiv.f1 -m equiv.shd \
    -o results/eval
```

### Equivalence Class Metrics

Compare equivalence classes (CPDAGs) rather than raw graphs:

```bash
causaliq-analysis evaluate-graph -i learned.graphml -r ground_truth.graphml \
    -m equiv.f1 -m equiv.shd -o results/eval
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
| **`<metric>`** | No | The basic metric | `f1`, `shd`, `precision`, `recall` |
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
