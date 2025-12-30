# CausalIQ Analysis Trace

This module implements detailed tracing of structure learning processes, allowing researchers to record, analyze, and compare the step-by-step evolution of causal graphs during algorithm execution.

⚠️ NOTE: these functionality will be superseded by a more open format based on csv and GraphML standards.

## Core Classes

::: causaliq_analysis.trace.Trace
    options:
        show_root_heading: true
        show_source: false
        heading_level: 3

Main class for recording and managing structure learning traces with detailed context, iteration-by-iteration recording, and comparison capabilities.

::: causaliq_analysis.trace.DiffType
    options:
        show_root_heading: true
        show_source: false
        heading_level: 3

Enumeration defining the different types of differences that can be detected when comparing traces.

::: causaliq_analysis.trace.CompatibilityUnpickler
    options:
        show_root_heading: true
        show_source: false
        heading_level: 3

Custom unpickler for handling backward compatibility when loading trace files with module path changes.

## Utility Functions

::: causaliq_analysis.trace.load_with_compatibility
    options:
        show_root_heading: true
        show_source: false
        heading_level: 3

Load trace files with backward compatibility support for older module structures.

## Overview

### Structure Learning Tracing

The `Trace` class provides comprehensive functionality for recording and analyzing causal graph structure learning:

**Recording Capabilities:**
- **Context Management**: Store learning algorithm parameters, data characteristics, and environment information
- **Iteration Tracking**: Record each step of the learning process with detailed action information
- **Result Storage**: Capture final learned graphs and search statistics
- **Flexible Storage**: Support for compressed file formats and cross-platform compatibility

**Analysis Features:**
- **Trace Comparison**: Compare two traces to identify differences in learning paths
- **Score Updates**: Retroactively update or recalculate scores using different metrics
- **Variable Renaming**: Handle variable name changes across different datasets
- **Statistical Summaries**: Generate summaries of learning algorithm behavior

### Key Methods

**Creation and Management:**
- `__init__()`: Initialize a new trace with optional context information
- `add()`: Record a new iteration with action details and graph state
- `read()`: Load trace data from files with compatibility support
- `save()`: Save trace data to compressed files

**Analysis and Comparison:**
- `diffs_from()`: Compare this trace with another to identify differences
- `update_scores()`: Recalculate scores using different scoring functions
- `get()`: Export trace data as a pandas DataFrame for analysis
- `rename()`: Apply variable name mappings throughout the trace

**Results and Context:**
- `set_result()`: Set the final learned graph
- `set_treestats()`: Add tree search statistics
- `context_string()`: Generate human-readable context descriptions

### Trace Differences

The tracing system can identify several types of differences between learning runs:

- **MISSING/EXTRA**: Iterations present in one trace but not another
- **ACTION**: Different actions taken at corresponding iterations  
- **ARC**: Different arcs modified in corresponding actions
- **SCORE**: Different scores recorded for the same actions
- **DETAILS**: Differences in recorded action details

### File Compatibility

The module includes robust backward compatibility features:

- **Module Migration**: Handles changes in module structure over time
- **Class Mapping**: Automatically maps old class locations to new ones
- **Version Tracking**: Records software versions for reproducibility
- **Compressed Storage**: Efficient storage using gzip compression

### Integration with Graph Actions

Traces work seamlessly with the graph action enumerations to provide detailed records of:

- Which specific arcs were added, deleted, or reversed
- Score changes resulting from each modification
- Alternative actions that were considered but not taken
- Statistical constraints and prior knowledge influences
- Debugging information for algorithm development

This comprehensive tracing capability is essential for:

- Algorithm development and debugging
- Reproducible research in causal discovery
- Performance analysis and optimization
- Comparative studies of different learning approaches
- Educational demonstrations of structure learning behavior