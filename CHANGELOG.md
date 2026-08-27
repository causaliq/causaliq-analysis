# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Plot Capability**: new `plot` CLI command and workflow action (NOCACHES
  pattern) which draws charts using matplotlib and Seaborn from a `summarise`
  CSV output
  - Migrated from the legacy `experiments/plot.py` module so figures such as
    the `ord_hc_f1` chart can be replicated exactly
  - Supports `line`, `regression`, `histogram`, `box`, `violin`, `bar` and
    `scatter` plot types
  - Chart properties specified as `name:value` strings (e.g.
    `legend.title_fontsize:12`)
  - Operates on plain files without workflow caches or the matrix, running
    once per workflow
  - Tests verify the output image exactly replicates a reference image
- **NOCACHES Action Pattern**: new `ActionPattern.NOCACHES` value (in
  `causaliq-core`) for actions that read/write plain files without workflow
  caches or the matrix; `causaliq-workflow` runs such steps once and skips
  the cache/matrix pattern validation
- **Graph Evaluation vs Workflow Cache**: `evaluate_graph` now accepts a
  workflow cache (`.db`) as its `reference` so graphs can be compared across
  caches with identical key structures (e.g. network and sample size)
  - Validates the reference cache key structure matches the input cache
  - Reports errors when reference entries do not contain graphs

### Changed
- Nothing yet

### Deprecated
- Nothing yet

### Removed
- Nothing yet

### Fixed
- **Cross-platform plot replication test**: `test_plot_exact_replication`
  now compares the plot CLI's SVG output with the `ord_hc_f1.svg`
  reference, which is byte-identical across platforms for a given
  matplotlib version, unlike rasterised PNG output.

### Security
- Nothing yet


## Evaluation & Summarisation [0.4.0] - 2026-04-10

### Added
- **Graph Evaluation**: `evaluate_graph` CLI command and workflow action
  (UPDATE pattern) to compute structural metrics vs ground truth
  - Standard metrics: F1, precision, recall, SHD
  - Equivalence class metrics: equiv.f1, equiv.shd (CPDAG comparison)
  - Support for multiple graph formats (GraphML, CSV, TETRAD, .xdsl, .dsc)
- **Optimal DAG Extraction**: `best_graph` CLI command and workflow action
  (UPDATE pattern) to extract optimal DAG from PDGs
  - Greedy algorithm with cycle avoidance
  - Configurable edge probability threshold
  - Alphabetical tie-breaking for direction ambiguities
- **Metric Summarisation**: `summarise` CLI command and workflow action
  (AGGREGATE pattern) to aggregate metrics across experiments
  - Summary statistics: mean, standard deviation, count
  - Metric specification format: `<field>.<stat>` (e.g., f1.mean, shd.sd)
  - Filter expressions for selective aggregation
  - CSV output format
- **Merge Strategies**: `noisy_or` and `max` merge strategies for graph
  merging in addition to the existing `average` strategy
- **Validation Module**: Shared validation utilities including
  `parse_sample_size()`, `parse_seed_cli()`, `validate_filter_expression()`,
  and `validate_metric_specs()`
- **Variable Name Corrections**: Automatic correction of known typos during
  trace migration (e.g., `HTshotOnTarget` → `HTshotsOnTarget`)

### Changed
- `merge-graphs` CLI enhanced with filter expressions (`--filter`),
  `random()` support, object type and strategy selection
- Template method pattern adopted for all workflow actions via
  `CausalIQActionProvider` base class
- Seed range support in CLI and workflow (e.g., `0-24`)

### Fixed
- Correct handling of PDAG extendability to CPDAG
- Division by zero handling in Bayesys metric computation
- Proper p_none computation in noisy-OR strategy


## Graph Merging [0.3.0] - 2026-03-02

### Added
- **Graph Merging**: `merge_graphs` function to combine multiple DAGs/PDAGs/PDGs
  into a single Probabilistic Dependency Graph (PDG) with weighted edge
  probabilities
  - Support for uniform weights (default) and custom weighting
  - Optional CPDAG conversion before merging (`cpdag=True`)
  - CLI command `merge-graph` for command-line access
  - Workflow action integration for batch processing
- **Trace Migration**: `migrate-trace` CLI command to convert legacy Trace
  pickle files to portable GraphML format
  - Filtering by sample size and seeds
  - Metadata extraction and JSON output
  - Workflow action for batch migration across networks
- **Summarisation Paradigm**: Architecture documentation for aggregation
  operations including filter expressions and metadata-driven weighting
- **API Documentation**: Complete documentation for merge module

### Changed
- Documentation restructured: detailed design moved from roadmap to
  architecture docs
- API overview reorganised with merge module as primary entry


## Legacy Trace [0.2.0] - 2025-12-30

### Added
- **Graph Module**: Enumerations for describing changes made to causal graphs during structure learning
  - `GraphActionDetail` enum for recording trace entry details (arcs, score deltas, statistics)
  - `GraphAction` enum for structure learning activities (INIT, ADD, DEL, REV, STOP, PAUSE, NONE)
- **Trace Module**: Comprehensive tracing of structure learning processes
  - `Trace` class for recording and analyzing causal graph evolution during algorithm execution
  - `DiffType` enum for comparing traces and identifying differences
  - `CompatibilityUnpickler` for backward compatibility with older module structures
  - Support for trace comparison, score updates, variable renaming, and statistical summaries
- **Enhanced Documentation**: Complete API documentation for all modules
  - Detailed documentation for graph and trace modules with usage examples
  - Updated API overview with descriptions of all available modules
  - Comprehensive coverage of key methods and integration patterns

### Changed
- **Documentation Structure**: Expanded API documentation to include graph and trace modules
- **Module Organization**: Better separation of concerns between graph actions and trace functionality


## Foundation Metrics [0.1.0] - 2025-12-27

### Added
- **PDAG Comparison**: Complete structural graph comparison with precision, recall, F1, SHD metrics
- **Bayesys Compatibility**: Half-match metrics, BSF, and DDM scores for Bayesys v1.3-v1.6 compatibility
- **KL Divergence**: Kullback-Leibler divergence calculation for probability distributions
- **100% Test Coverage**: Comprehensive test suite with full code coverage (76 tests)
- **CLI Interface**: Basic CLI with version reporting and greeting functionality
- **API Documentation**: Complete documentation for metrics module following mkdocs pattern
- **Sanity Check Validation**: Built-in consistency checks for metric calculations

### Changed
- Initial project structure and scaffolding with environment setup, CLI foundation, pytest testing and CI testing on github

### Fixed
- sentence describing first fix
