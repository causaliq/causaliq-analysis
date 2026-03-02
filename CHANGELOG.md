# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Nothing yet

### Changed
- Nothing yet

### Deprecated
- Nothing yet

### Removed
- Nothing yet

### Fixed
- Nothing yet

### Security
- Nothing yet


## [0.3.0] - 2026-03-02

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


## [0.2.0] - 2025-12-30

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


## [0.1.0] - 2025-12-27

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
