# CausalIQ Analysis User Guide

## Overview

The causaliq-analysis package provides tools for analysing experimental
results from causal discovery workflows:

| Capability | Description |
|------------|-------------|
| **[Graph Merging](merge_graphs.md)** | Combine multiple DAGs/PDAGs/PDGs into a single PDG with edge probabilities |
| **Optimal Extraction** | Extract the "best" DAG or CPDAG from a PDG (planned) |
| **Structural Evaluation** | Compute F1, precision, recall vs true graph (planned) |
| **Graph Averaging** | Legacy edge probability calculation from Trace files |
| **Trace Migration** | Convert legacy Trace pickle files to modern format |

These capabilities follow a **summarisation paradigm** that provides
consistent patterns for aggregating experimental results across different
dimensions (e.g., network, sample size, algorithm).

---

## Graph Averaging (Legacy)

This provides a simple graph averaging capability which *initially* produces a table of edge probabilities from a set of individual structure learning experiments - for example, where graphs are learned from different sub-samples of a dataset. The feature provides the probability of the four possibilities between nodes A and B:

- probability of a directed edge from A to B
- probability of a directed edge from B to A
- probability of an undirected edge between A and B
- probablility of no edge between A and B

This feature will be extended to produce a result graph:

- using a simple thresholding and cycle resolution technique
- and/or integrating LLM knowledge through the causaliq-knowledge capability to resolve the most uncertain edges

### Function Signature

```python
from pandas import DataFrame
from causaliq_analysis.trace import Trace

average(trace: Trace, sample_size: int, pdag: bool, seeds: tuple) -> DataFrame:
  """
  Produce table of edge probabilities by averaging muliple graphs

  Args:
      trace (Trace): legacy format structure learning trace containing
                     learned graphs for different sample sizes and
                     random sub-sample seeds and a specific network
      sample_size (int): average graphs learnt from this sample size
      pdag (bool): whether learned graphs are converted to PDAGs
      seeds (tuple): use experiments with this range of seeds

  Returns
      DataFrame: of node pairs and respective probabilities for each directed
                 edges, undirected edge, and no edge

  """
  pass
```

### Invoking the feature

Graph averaging can be performed in custom Python code as follows:

```python
from causaliq_analysis.graph import average
from causaliq_analysis.trace import Trace

ROOT_DIR = "c:/dev/causaliq/discovery/experiments/"
SERIES = "TABU/SAMPLE/BASE"
NETWORKS = ["asia", "sports"]
SAMPLE_SIZES = [10000, 100000]
SEEDS = [0, 1]

for network in NETWORKS:
    trace = Trace.read(series=SERIES, root_dir=ROOT_DIR)
    for N in SAMPLE_SIZES:
        edges = average(trace=trace, N=N, pdag=True, seeds=SEEDS)
        print(f"Edge probabilites for network {network} and sample size "
              f"{N} are:\n{edges}")
```

Graph averaging can also be performed from the command line:

```shell
cqalys graph-average --network=asia --N=10k --seeds=0,1 --basis=pdag  --output=average.csv  --series=TABU/SAMPLE/BASE --root-dir=experiments
```

Most flexibly of all, the graph.py module will implement the CausalIQ Workflow Action interface
so that graph averaging can be included in causal discovery workflows. This supports
graph averaging over multiple networks, sample sizes etc.


```yaml
# graph_averaging.yaml
description: "Example graph-averaging workflow"
root_dir: "c:/dev/causaliq/discovery/experiments/"
series: "TABU/SAMPLE/BASE"

matrix:
  network: ["asia", "sports"]
  sample_size: ["10k", "100k"]
  seed: [0, 1]

steps:
 - name: "Graph averaging"
   uses: "causaliq-analysis"
   with:
     basis: "pdag"
     operation: "graph-average"
     traces: "{{series}}/{{network}}.pkl.gz"
     result: "{{series}}/{{network}}_{{sample_size}}.csv"

```

