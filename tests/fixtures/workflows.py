"""Test workflow definitions for integration testing."""

# Simple migrate_trace workflow for testing
SIMPLE_WORKFLOW = """
description: "Simple migrate_trace test workflow"
root_dir: "tests/data"
series: "TABU/STD"

steps:
  - name: "Migrate traces"
    uses: "causaliq-analysis"
    with:
      action: "migrate_trace"
      network: "asia"
      sample_size: "1k"
"""

# Matrix-based workflow for testing multiple configurations
MATRIX_WORKFLOW = """
description: "Matrix migrate_trace test workflow"
root_dir: "tests/data"
series: "TABU/STD"

matrix:
  network: ["asia", "cancer"]
  sample_size: ["1k", "10k"]

steps:
  - name: "Migrate traces"
    uses: "causaliq-analysis"
    with:
      action: "migrate_trace"
      traces: "{{series}}/{{network}}.pkl.gz"
"""

# Parameterized workflow for CLI override testing
PARAMETERIZED_WORKFLOW = """
description: "Parameterized migrate_trace workflow"
root_dir: "tests/data"
series: "TABU/STD"
network: null  # Must be provided via CLI
sample_size: "1k"  # Default value

steps:
  - name: "Migrate traces"
    uses: "causaliq-analysis"
    with:
      action: "migrate_trace"
      traces: "{{series}}/{{network}}.pkl.gz"
"""
