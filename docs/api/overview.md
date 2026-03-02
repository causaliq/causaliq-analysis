# CausalIQ Analysis API Reference

This is the entry point for the API documentation. Each module is documented
separately below.

## Modules

### [Merge](merge.md)

Functions for merging multiple graphs (DAG, PDAG, PDG) into a single
Probabilistic Dependency Graph (PDG) with weighted edge probabilities.

### [Metrics](metrics.md)

Functions for analysing and comparing causal graphs, including structural
metrics, Kullback-Leibler divergence calculations, and Bayesys compatibility
metrics.

### [Graph](graph.md)

Enumerations for describing changes made to causal graphs during structure
learning, including action types and detailed information recorded with each
trace entry.

### [Trace](trace.md)

Detailed tracing of structure learning processes, enabling researchers to
record, analyse, and compare the step-by-step evolution of causal graphs
during algorithm execution.

### [CLI](cli.md)

Command-line interface for causaliq-analysis operations.