# CausalIQ Analysis User Guide

## Overview

The causaliq-analysis package is part of the CausalIQ [CausalIQ ecosystem](https://causaliq.org/) for intelligent causal discovery and inference. CausalIQ Analysis provides the following capabilities for analysing experimental results from causal discovery and inference workflows:

| Capability | Pattern | Description |
|------------|-------------|-------------|
| **`best_graph`** | Create | Extract the "best" DAG or CPDAG from a PDG using threshold-based methods (COMING IN v0.5.0)|
| **[`evaluate_graph`](evaluate_graph.md)** | Update | Compute F1, precision, recall vs true graph |
| **`evaluate_pdg`** | Update | Compute stability measures of PDG (COMING IN v0.5.0)|
| **[`merge_graphs`](merge_graphs.md)** | Aggregate | Combine multiple DAGs/PDAGs/PDGs into a single PDG with edge probabilities |
| **[`migrate_trace`](migrate_trace.md)** | Create | Convert legacy Trace pickle files to open-standards formats used by CausalIQ e.g. GraphML and JSON |
| **`plot`** | Create | Publication-ready charts (COMING IN V0.6.0) |
| **[`summarise`](summarise.md)** | Aggregate | Statistically summarise numerical results across experiments into publication-ready metrics |
| **`table`** | Create | Publication-ready LaTeX tables (COMING IN V0.6.0) |

## Command Line, Workflow or Programmatic Access

As with all CausalIQ packages, users may access the capabilities of CausalIQ Analysis in three ways:

- **Command Line Interface (CLI)** provides an easy introduction to performing analysis from the command line. This is primarily orientated to analysing a single result and thus gain an initial understanding of how to use the capability. However, one could use native scripting languages e.g. `bash` to construct more elaborate workflows using the CLI.

- **CausalIQ Workflows** allows users to include CausalIQ Analysis steps within workflows which can combine learning graphs from data or LLMs, performing inference, analysing results, through to generating publication tables and charts.

- **Programmatic Access** using the [Python API](../api/overview.md) for complete flexibility over the processing logic.

The CLI and workflow routes use the same command or action name respectively, which in turn matches the capability name in the table above. Parameters are named identically, and as far as practical, the capability behaviour is the same, in the CLI and workflow interfaces.

## Common parameters

There are a number of parameters which are common to many capabilities which we document here to avoid repetition in the sections describing individual capabilities.

### `input` parameter

This specifies the input(s) to the capability. Generally, this is a list of either:

- **individual files** on the filesystem with an appropriate format for the capability being used. For example, the `evaluate_graph` capability expects GraphML files. Specifying files would be the more usual approach when using the CLI to initially explore the functionality of the capability.
 
- **CausalIQ Workflow caches** are lightweight sql-lite databases that typically contain large numbers of results from CausalIQ packages and so are a key element of production workflows where one may wish to generate and analyse thousands of graphs. Individual entries in a cache typically contain an object e.g. a graph, or summary of results, together with associated metadata giving the provenance of that object. Workflow actions would generally use workflow caches as input.

### `output` parameter

This specifies where the output from the capability should be placed. The
output from a capability is typically one or more objects appropriate to the
analysis capability, together with metadata describing the analysis
undertaken. This is generally either a:

- **filesystem directory** is the location where the output files — typically
  a metadata JSON file and one or more object files — will be placed. This is
  usually the more appropriate choice when using the CLI.

- **CausalIQ Workflow cache** would be the typical output destination in a
  workflow setting. Creation and aggregation actions write new entries to the
  output cache.

Note that **update actions** (e.g., `evaluate_graph`) do not use an output
parameter in workflows — they modify entries in the input cache directly.
See [Workflow Action Patterns](#workflow-action-patterns) below.

### `filter` parameter

As the name implies, the `filter` parameter allows the user to restrict the input objects that the capability is applied to. `filter` expression use Python syntax with the following supported operators:

| Category | Operators |
|----------|-----------|
| Comparison | `==`, `!=`, `>`, `<`, `>=`, `<=` |
| Boolean | `and`, `or`, `not` |
| Membership | `in` |
| Grouping | `()` |

Allowed functions: `len`, `str`, `int`, `float`, `bool`, `abs`, `min`, `max`

Any metadata variable can be included in the filter expression, providing a powerful tool to define the data which one wishes to analyse. Some examples might be:

```yaml
filter: "sample_size < 1000 and network in ['asia', 'sports']"
```


## Workflow Action Patterns

CausalIQ workflow actions follow one of three patterns, determined by their
`input` and `output` parameters. Understanding these patterns is key to
building correct workflows.

### Pattern 1: Creation (output only)

**Actions that create new cache entries.**

| Parameter | Requirement |
|-----------|-------------|
| `input` | Not used (or refers to data files, not caches) |
| `output` | Required (workflow cache) |
| `matrix` | Required |

The `matrix` defines the combinations of parameter values for which entries
are created. Each matrix combination produces one entry in the output cache.

```yaml
# Example: Structure learning creates graphs
matrix:
  network: [asia, cancer]
  sample_size: [100, 1000]

steps:
  - name: "Learn Graphs"
    uses: "causaliq-core"
    with:
      action: "learn_structure"
      output: "results/graphs.db"
```

This creates 4 entries (2 networks × 2 sample sizes).

### Pattern 2: Update (input only)

**Actions that add analysis results to existing cache entries.**

| Parameter | Requirement |
|-----------|-------------|
| `input` | Required (workflow cache) |
| `output` | Not allowed |
| `matrix` | Not allowed |

The action processes **all** entries in the input cache (subject to any
`filter`), adding its results to each entry's metadata and objects. This
ensures analysis is applied consistently to all entries without risk of
accidentally filtering via a mismatched matrix definition.

```yaml
# Example: Evaluate all graphs in a cache
steps:
  - name: "Evaluate Graphs"
    uses: "causaliq-analysis"
    with:
      action: "evaluate_graph"
      input: "results/graphs.db"
      true_graph: "reference/asia_true.graphml"
```

Update actions add metadata and objects but never remove or alter existing
ones. Results are stored under an action-specific key in the entry metadata.

### Pattern 3: Aggregation (input and output)

**Actions that combine multiple entries into new summary entries.**

| Parameter | Requirement |
|-----------|-------------|
| `input` | Required (workflow cache) |
| `output` | Required (workflow cache) |
| `matrix` | Required |

The `matrix` controls the **output dimensionality** — entries from the input
cache are grouped by matrix variable values and aggregated into new entries
in the output cache.

```yaml
# Example: Merge graphs per network
matrix:
  network: [asia, cancer]

steps:
  - name: "Merge by Network"
    uses: "causaliq-analysis"
    with:
      action: "merge_graphs"
      input: "results/graphs.db"
      output: "results/merged.db"
```

If `graphs.db` contains entries for multiple sample sizes per network, this
produces 2 entries in `merged.db` — one merged PDG per network.

### Summary

| Pattern | Input | Output | Matrix | Example Actions |
|---------|-------|--------|--------|-----------------|
| Creation | — | required | required | `learn_structure` |
| Update | required | prohibited | prohibited | `evaluate_graph` |
| Aggregation | required | required | required | `merge_graphs`, `summarise` |

## Conservative Execution

CausalIQ workflows support **conservative execution** — skipping work that
has already been completed. The behaviour depends on the action pattern:

### Creation actions

An entry is created only if it does not already exist. If an entry with
matching matrix values exists in the output cache, the action is skipped
for that combination.

### Update actions

An action is applied to an entry only if the entry exists **and** the
action has not yet been performed on it. The presence of the action's
metadata section indicates completion.

| Entry exists? | Action metadata exists? | Behaviour |
|---------------|------------------------|-----------|
| No | — | Skip (nothing to update) |
| Yes | No | **Run** |
| Yes | Yes | Skip (already done) |

### Aggregation actions

An output entry is created only if it does not already exist in the output
cache.

### Re-running actions

To re-run an action that has already completed:

- use **`--mode=force`** to bypass all conservative execution checks
- or, for **creation/aggregation** use a fresh output cache

See the
[architecture documentation](../architecture/summarisation_paradigm.md) for
additional details.

