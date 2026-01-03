"""Test workflow definitions for integration testing."""

# Simple graph averaging workflow for testing
SIMPLE_WORKFLOW = """
description: "Simple graph averaging test workflow"
root_dir: "tests/data"
series: "TEST/SAMPLE/BASE"

steps:
  - name: "Graph averaging"
    uses: "causaliq-analysis"
    with:
      operation: "graph-average"
      network: "test_network"
      sample_size: "1k"
      basis: "pdag"
      seeds: "0,1"
      result: "test_output.csv"
"""

# Matrix-based workflow for testing multiple configurations
MATRIX_WORKFLOW = """
description: "Matrix graph averaging test workflow"
root_dir: "tests/data"
series: "TEST/SAMPLE/BASE"

matrix:
  network: ["asia", "cancer"]
  sample_size: ["1k", "10k"]

steps:
  - name: "Graph averaging"
    uses: "causaliq-analysis"
    with:
      operation: "graph-average"
      basis: "pdag"
      seeds: "0,1"
      traces: "{{series}}/{{network}}.pkl.gz"
      result: "{{series}}/{{network}}_{{sample_size}}_average.csv"
"""

# Parameterized workflow for CLI override testing
PARAMETERIZED_WORKFLOW = """
description: "Parameterized graph averaging workflow"
root_dir: "tests/data"
series: "TEST/SAMPLE/BASE"
network: null  # Must be provided via CLI
sample_size: "1k"  # Default value

steps:
  - name: "Graph averaging"
    uses: "causaliq-analysis"
    with:
      operation: "graph-average"
      basis: "pdag"
      seeds: "0,1"
      traces: "{{series}}/{{network}}.pkl.gz"
      result: "{{series}}/{{network}}_{{sample_size}}_average.csv"
"""
