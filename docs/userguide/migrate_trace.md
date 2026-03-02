# Trace Migration

The `migrate-trace` command converts legacy Trace pickle files into portable
**GraphML format** with accompanying metadata. This enables integration with
modern causaliq workflows and third-party graph tools.

## Parameters

| Parameter | CLI | Action | Required | Description |
|-----------|-----|--------|----------|-------------|
| `network` | `--network` | `network` | Yes* | Network name to process |
| `series` | `--series` | `series` | Yes* | Series path (e.g., TABU/SAMPLE/BASE) |
| `traces` | — | `traces` | Yes* | Direct path pattern (action only) |
| `root_dir` | `--root-dir` | `root_dir` | No | Root directory (default: `experiments`) |
| `sample_size` | `--N` | `sample_size` | No | Filter by sample size (e.g., `10k`) |
| `seeds` | `--seeds` | `seeds` | No | Filter by seeds (comma-separated) |
| `output` | `--output` | — | CLI only | Output directory for files |

**Notes:**

- *Must provide either `network` + `series` OR `traces` pattern
- Sample size accepts integers or shorthand: `1k` = 1000, `10k` = 10000,
  `1m` = 1000000
- If `seeds` is omitted, all seeds are included
- CLI output defaults to `migrated/<series>/<network>/`

---

## How It Works

### Step 1: Load Trace Files

Trace files are loaded from the experiments directory based on the series
and network pattern. Each Trace contains:

- The learnt DAG from structure learning
- Algorithm parameters and configuration
- Sample size and random seed used
- Score metrics and iteration history

### Step 2: Extract Graph and Metadata

For each Trace, the migration extracts:

| Component | Description |
|-----------|-------------|
| Result DAG | Final learnt graph structure |
| Metadata | Algorithm, parameters, N, score, software version |

Traces without a valid result graph are skipped with a warning.

### Step 3: Convert to GraphML

The DAG is serialised to GraphML format, which:

- Preserves all nodes and directed edges
- Is readable by NetworkX, Gephi, Cytoscape, and other tools
- Includes graph-level metadata as GraphML data elements

---

## CLI Usage

### Example Commands

```powershell
# Migrate all traces for asia network from TABU/STD series
causaliq-analysis migrate-trace `
  --network=asia `
  --series=TABU/STD `
  --root-dir=experiments

# Migrate specific sample size and seeds
causaliq-analysis migrate-trace `
  --network=asia `
  --series=TABU/STD `
  --N=10k `
  --seeds=0,1,2 `
  --output=migrated/asia_10k

# Migrate from non-default root directory
causaliq-analysis migrate-trace `
  --network=alarm `
  --series=HC/SAMPLE/BASE `
  --root-dir=/data/experiments `
  --output=output/alarm_graphs
```

### Output Structure

```
migrated/TABU/STD/asia/
├── N1000.graphml        # Graph for N=1000, seed=0
├── N1000.json           # Metadata for N=1000
├── N1000_1.graphml      # Graph for N=1000, seed=1
├── N1000_1.json         # Metadata for N=1000, seed=1
└── ...
```

---

## Workflow Action

The `migrate_trace` action can be used in causaliq-workflow definitions
for batch migration across multiple networks.

### Example Workflow

```yaml
# migrate_experiments.yaml
description: "Migrate legacy traces to GraphML format"

matrix:
  network: [asia, alarm, insurance]
  series: [TABU/STD, HC/STD]

actions:
  migrate_trace:
    action: migrate_trace
    series: "{{series}}"
    network: "{{network}}"
    root_dir: experiments
```

This workflow migrates traces for all network/series combinations, storing
GraphML objects in the workflow cache for downstream actions.

### Action Outputs

| Output | Description |
|--------|-------------|
| `num_graphs` | Number of graphs successfully converted |
| `skipped` | Number of traces skipped (no result graph) |
| `status` | Execution status (`success`, `skipped`, `error`) |

The action also returns GraphML content as objects that can be:

- Stored in the workflow cache
- Passed to downstream actions (e.g., `merge_graphs`)
- Written to files via output configuration

---

## Output Formats

### GraphML

Standard XML-based graph format with directed edges:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<graphml xmlns="http://graphml.graphdrawing.org/xmlns">
  <graph id="G" edgedefault="directed">
    <node id="A"/>
    <node id="B"/>
    <node id="C"/>
    <edge source="A" target="B"/>
    <edge source="B" target="C"/>
  </graph>
</graphml>
```

### Metadata JSON

Accompanying metadata for each graph:

```json
{
  "id": "asia_N1000_0",
  "algorithm": "TABU",
  "params": {"max_parents": 4, "tabu_size": 10},
  "N": 1000,
  "score": -24531.42,
  "software_version": "1.3.0"
}
```

---

## See Also

- [Graph Merging](merge_graphs.md) — Combine migrated graphs into PDGs
- [Trace API Reference](../api/trace.md) — Trace class documentation
