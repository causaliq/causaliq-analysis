# CausalIQ Analysis Graph

This module defines enumerations and classes for describing changes made to causal graphs during structure learning. These are primarily used for tracing and recording the evolution of graphs through learning algorithms.

⚠️ NOTE: these classes will be migrated to the [graph module](https://causaliq.github.io/causaliq-core/api/graph/) of the [causaliq_core package](https://causaliq.github.io/causaliq-core/).

## Core Enumerations

::: causaliq_analysis.graph.GraphActionDetail
    options:
        show_root_heading: true
        show_source: false
        heading_level: 3

Enumeration of details that can be recorded with each trace entry, such as arcs changed, score deltas, and statistical information.

::: causaliq_analysis.graph.GraphAction
    options:
        show_root_heading: true
        show_source: false
        heading_level: 3

Enumeration of activities that can be recorded in a structure learning trace, with associated labels, mandatory details, and priority ordering.

## Overview

### Graph Action Details

The `GraphActionDetail` enum defines the types of information that can be captured when recording changes to a causal graph:

- **ARC**: The specific arc (edge) that was modified
- **DELTA**: Score change resulting from the modification
- **ACTIVITY_2, ARC_2, DELTA_2**: Information about the second-highest scoring alternative
- **MIN_N, MEAN_N, MAX_N**: Statistical information about contingency table cell counts
- **LT5**: Number of contingency table cells with counts less than 5
- **FPA**: Free parameters in contingency tables
- **KNOWLEDGE**: Prior knowledge constraints used
- **BLOCKED**: List of changes that were blocked during the iteration

### Graph Actions

The `GraphAction` enum defines the types of modifications that can be made to graphs during structure learning:

- **INIT**: Initialize the learning process
- **ADD**: Add an arc to the graph
- **DEL**: Delete an arc from the graph  
- **REV**: Reverse the direction of an arc
- **STOP**: Stop the search process
- **PAUSE**: Pause the search process
- **NONE**: No change made in this iteration

Each action has associated metadata including human-readable labels, mandatory detail fields that must be provided, and priority ordering for display purposes.

### Integration with Tracing

These enumerations are designed to work closely with the tracing functionality to provide detailed records of how causal graphs evolve during structure learning algorithms. They enable researchers to:

- Track the sequence of modifications made to graphs
- Understand why specific changes were made (through score deltas)
- Identify alternative modifications that were considered
- Record statistical constraints and prior knowledge influences
- Debug and analyze the behavior of learning algorithms