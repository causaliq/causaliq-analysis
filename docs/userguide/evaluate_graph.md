# Evaluating Graphs

The `evaluate_graph` capability structurally evaluates a graph - PDAG, CPDAG or DAG - against a reference graph. Note that comparisons between general SDG graphs are not supported.

This is an `update` action (see [workflow patterns](introduction.md#workflow-action-patterns)) and so updates the metadata for an existing graph **in the input cache** with the requested metrics if used within a CausalIQ workflow.

## Parameters

| Parameter   | CLI  | Required | Default | Description |
|-------------|------|----------|---------|-------------|
| `input`     | `-i` | Yes      | None      | Input files (`.graphml` or `.db` cache). |
| `output`    | `-o` | No       | see notes | Output directory - CLI only |
| `metric`    | `-m` | No       | None      | List of graph structural metrics required |
| `reference` | `-r` | Yes      | None      | Reference graph for structural comparison<br/>A `.tetrad`, `.csv`, `.graphml`, `.xdsl` or `.dsc` file |
| `filter`    | `-f` | No       | None      | filter entries in input |

**Notes:**

- Input type is auto-detected by file extension:
  - `.graphml`: Read as GraphML file. This is only supported within the CLI.
  - `.db`: Read all entries from WorkflowCache database
- The `output` parameter can only be used in the CLI. The **updated** metadata
  containing the requested metrics will be placed in the output directory.
- In workflows, `evaluate_graph` is an update action: `output` and `matrix` are
  **prohibited**. The action processes all entries in the input cache.

## Supported Metrics

### Metric Naming in CausalIQ

Unfortunately, many different kinds of structural metrics are used to evaluate graphs in causal discovery. Common ones are F1, Precision, Recall and Structural Hamming Distance (SHD), but others which are more specific to causal discovery, for example, Structural Intervention Distance (SID) are also employed.

Moreover, there are other critical differences in structural evaluation:

- whether the raw graphs (e.g. a learned DAG and a reference DAG) are compared, or whether the equivalence classes (CPDAGS or PAGs) to which they belonf are compared. The former is generally more appropriate in causal discovery where orientation of arcs is critical, and the latter more generally relevant when evaluating the output of statistical structure learning algorithms if only observational data is used (since it is generally impossible to identify the orientation of all edges)
- many structural metrics are built upon true/false positive/negative counts, and different authors take different approaches to computing these counts for arcs which have an orientation property. See the section of comparison semantics below for further details.
- Some authors report the raw metric but others normalise it in some way. This mostly applies to the SHD metric which tends to scale with the size of the graph (number of nodes or edges). To facilitate comparison between SHD from graphs of different sizes, some authors normalise SHD by dividing it by the number of variables or edges in the reference graph.

In order to support all these variations we propose the follow naming structure for metrics throughout CausalIQ:

  `[<preprocessing>].<metric>.[<semantics>].[<postprocessing>].[<statistic>]`

where the elements of the name (separated by dots) are:

| Element                | Optional | Description | Supported Values |
|------------------------|----------|-------------|------------------|
| **`<preprocessing>`**  | Yes      | Preprocessing before comparison | **`equiv`** (convert to CPDAGs first) |
| **`<metric>`**         | No       | The basic metric                | **`f1`** and **`shd`** |
| **`<scheme>`**         | Yes      | Alternative computation semantics |  **not currently supported** |
| **`<postprocessing>`** | Yes      | Postprocessing of the metric, e.g. normalisation |  **not currently supported** |
| **`<statistic>`**      | Yes      | Statistic over multiple values, e.g. mean | **`summarise` action only** |

An example specifying metrics in a CausalIQ Workflow `evaluate_graph` step:

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
        - equiv.shd
```

This computes the F1 between the reference and evaluated graph, and the SHD
between CPDAGs to which the reference and evaluated graphs each belong.

### Legacy Support

The core module which provides structural comparsons between PDAG (mixed directed and undirected edge graphs which is a superset of DAGs and CPDAGs) is `pdag_compare` in module `metrics.py`. It implements the compairson semantics decsribed below and which have been used consistently in CausalIQ papers. It is also used extensively by the legacy code in the `discovery` repo. Therefore, this functionality **must be retained unmodified**.

This CausalIQ Analysis capability will provide a wrapper so that the friendlier metric names discussed above are supported.

### Comparison Semantics

To be completed - will describe in detail how the (legacy) CausalIQ code, which this capability will reuse, computes the confusion matrix counts that underly the structural metrics.

## See Also

- [Summarisation Paradigm](../architecture/summarisation_paradigm.md) —
  Architecture for aggregation operations including filtering and weighting
- [PDG API Reference](../api/overview.md) — Full PDG class documentation
