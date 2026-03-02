# Summarisation Paradigm

## Overview

The **summarisation paradigm** provides a consistent architecture for
aggregating experimental results across different dimensions. This pattern
is used by `merge_graphs` and future actions like accuracy metrics
aggregation, score summarisation, and statistical significance testing.

The design draws terminology from BI software (Power BI/dbt) and CI
workflows (GitHub Actions) to provide familiar concepts for users.

## Core Concepts

| Concept | Parameter | Purpose |
|---------|-----------|---------|
| Grouping dimensions | `matrix` | Workflow `matrix` definition specifies output granularity—one output per unique combination |
| Workflow cache | `input` | Provides entries (each with metadata and objects like graphs) to aggregate |
| Input filtering | `filter` | Restricts inputs by metadata values before grouping |
| Output elements | (action-specific) | Metrics/values produced (e.g., F1, SD, merged_graph) |

## Workflow vs Action Separation

### causaliq-workflow Responsibilities

**Implicit matrix parameters**: Matrix variables are automatically passed to
actions without explicit parameter declarations:

```yaml
matrix:
  network: [asia, sports]

actions:
  merge_graphs:
    input: discovery_results.db
    # network: {{network}}  ← NOT NEEDED, implicit from matrix
```

**Aggregation detection**: When an action has both a `matrix` definition and
an `input` parameter specifying a workflow cache, causaliq-workflow
automatically treats this as an aggregation operation.

**Two-phase execution**:

1. **Scan phase** — Assemble cache entry keys for each matrix combination,
   applying any `filter` expression. Log statistics: number of combinations,
   groups found, min/mean/max group sizes.

2. **Execute phase** — Call the action's `run()` method for each group,
   passing the resolved cache entries for aggregation.

### Action Responsibilities

Actions implementing aggregation operations must:

- Raise an error if no matrix is specified (aggregation requires grouping)
- Process a `List[CacheEntry]` of input entries
- Return results with provenance metadata

## Filter Expression Syntax

The `filter` parameter uses Python expression syntax, evaluated safely using
the `simpleeval` library.

**Supported operators:**

- Comparison: `==`, `!=`, `>`, `<`, `>=`, `<=`
- Boolean: `and`, `or`, `not`
- Membership: `in`
- Grouping: parentheses `()`

**Examples:**

```yaml
# Simple equality
filter: network == 'asia'

# Numeric comparison
filter: sample_size >= 1000

# Boolean combination
filter: network == 'asia' and sample_size > 500

# Complex expression with grouping
filter: (network == 'asia' or network == 'alarm') and status == 'completed'

# Membership test
filter: algorithm in ['pc', 'fci', 'ges']
```

Metadata field names are used directly as variables. String literals must be
quoted; numeric literals are unquoted.

## Weights Specification

Weights enable metadata-driven weighting where entries receive different
influence based on their characteristics.

**Specification format:**

```yaml
weights:
  action:
    generate_graph: 1.0
    migrate_trace: 0.5
  algorithm:
    pc: 1.0
    fci: 0.8
```

**Weight computation:**

- Final weight = product of all matching field-value weights
- Default weight is 1.0 for unspecified values
- Example: `action=migrate_trace` + `algorithm=fci` → `0.5 × 0.8 = 0.4`

## Metadata Handling

### Input Requirements

Every input entry must have metadata. Entries without required matrix
variables in their metadata are skipped.

### Output Metadata

Every output entry receives metadata comprising:

| Field | Description |
|-------|-------------|
| Matrix values | Values for each grouping dimension (e.g., `network`, `sample_size`) |
| `source_count` | Number of input entries aggregated |
| `source_caches` | List of input cache filenames |
| `filter` | Filter expression applied (if any) |
| `action` | Action that produced this entry |
| `timestamp` | ISO 8601 timestamp of execution |
| Action-specific | Additional metadata (e.g., `weights_applied`, `cpdag_conversion`) |

## Workflow Example

```yaml
# merge_graphs workflow example
matrix:
  network: [asia, alarm]
  sample_size: [500, 1000]

actions:
  merge_graphs:
    input:
      - discovery_results.db
      - legacy_traces.db
    filter: status == 'completed'
    cpdag: true
    weights:
      action:
        generate_graph: 1.0
        migrate_trace: 0.5
    output: merged_graphs.db
```

This produces one merged graph for each `network × sample_size` combination
(4 outputs total), filtering to completed entries and weighting by action
type.

## See Also

- [Graph Merging User Guide](../userguide/merge_graphs.md) — Practical usage
- [causaliq-workflow documentation](https://causaliq.org/projects/causaliq-workflow/)
