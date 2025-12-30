# CausalIQ Analysis API Reference

This is the entry point for the API documentation. It is suggested to split the 
documentation by module, and briefly describe each module here, to ease navigation
of the API and avoid overlong pages.

## Modules

### [CLI](cli.md)

This provides a skeleton CLI implementation.

### [Metrics](metrics.md)

This module provides functions for analysing and comparing causal graphs, including structural metrics, Kullback-Leibler divergence calculations, and Bayesys compatibility metrics.

### [Graph](graph.md)

This module defines enumerations for describing changes made to causal graphs during structure learning, including action types and detailed information that can be recorded with each trace entry.

### [Trace](trace.md)

This module implements detailed tracing of structure learning processes, enabling researchers to record, analyze, and compare the step-by-step evolution of causal graphs during algorithm execution.