# causaliq-analysis

![Python Versions](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)

This repo provides tools for analysing and visualising learned causal graphs,
including structural metrics, stability assessment, significance tests, and
publication-ready tables and charts. It is part of the
[CausalIQ ecosystem](https://causaliq.org/) for intelligent causal discovery.

## Status

**Current Version**: v0.3.0

This repository is part of the [CausalIQ ecosystem](https://causaliq.org/) and
is in active development. Recent work has focused on graph merging
functionality and migration from the legacy
[discovery repo](https://github.com/causaliq/discovery).


## Features

✅ **Implemented Releases**

- **Release v0.3.0 - Graph Merging**: Merge multiple DAGs/PDAGs/PDGs into
  probabilistic dependency graphs (PDGs) with weighted edge probabilities.
  Trace migration to convert legacy traces to modern GraphML format.
- **Release v0.2.0 - Legacy Trace**: Support for reading and writing
  structure learning traces in legacy pickle format.
- **Release v0.1.0 - Foundation Metrics**: CausalIQ and Bayesys structural
  graph metrics and KL metric.

🛣️ **Upcoming Releases**

- **Release v0.4.0 - Optimal Extraction & Evaluation**: Extract best DAG/CPDAG
  from PDGs, structural evaluation metrics (F1, precision, recall) vs ground
  truth.


## Upcoming Key Innovations

### 🧠 LLM-assisted Graph Averaging
- **Uncertain or conflicting edges** - resolved using LLM queries

### 📊 Publication-ready chart generation
- **Seaborn charts** - flexible, but standardised publication-ready chart generation

### ▦ Publication-ready table generation
- **LaTeX tables** - converts tabular analysis data into publication-ready LaTeX tables

## Integration with CausalIQ Ecosystem

- 🔍 **CausalIQ Discovery** generates causal graphs which this package evaluates and visualises.
- 🤖 **CausalIQ Workflow** can access all features of this package (through the Action interface) so that analysis and visualisation are incorporated into CausalIQ workflows.
- 🧪 **CausalIQ Papers** uses the analysis, table and chart features of this package to generate published paper assets.

## LLM Support

The following provides project-specific context for this repo which should be provided after the [personal and ecosystem context](https://github.com/causaliq/causaliq/blob/main/LLM_DEVELOPMENT_GUIDE.md):

```text
I wish to migrate the code in legacy/core/metrics.py following all CausalIQ development guidelines
so that the legacy repo can use the migrated code instead. 
```

## Quick Start

```python
# to be completed
```

## Getting started

### Prerequisites

- Git 
- Latest stable versions of Python 3.9, 3.10. 3.11, 3.12 or 3.13


### Clone the new repo locally and check that it works

Clone the causaliq-analysis repo locally as normal

```bash
git clone https://github.com/causaliq/causaliq-analysis.git
```

Set up the Python virtual environments and activate the default Python virtual environment. You may see
messages from VSCode (if you are using it as your IDE) that new Python environments are being created
as the scripts/setup-env runs - these messages can be safely ignored at this stage.

```text
scripts/setup-env -Install
scripts/activate
```

Check that the causaliq-analysis CLI is working, check that all CI tests pass, and start up the local mkdocs webserver. There should be no errors  reported in any of these.

```text
causaliq-analysis --help
scripts/check_ci
mkdocs serve
```

Enter **http://127.0.0.1:8000/** in a browser and check that the 
causaliq-data documentation is visible.

If all of the above works, this confirms that the code is working successfully on your system.


## Documentation

Full API documentation is available at: **http://127.0.0.1:8000/** (when running `mkdocs serve`)

## Contributing

This repository is part of the CausalIQ ecosystem. For development setup:

1. Clone the repository
2. Run `scripts/setup-env -Install` to set up environments  
3. Run `scripts/check_ci` to verify all tests pass
4. Start documentation server with `mkdocs serve`

---

**Supported Python Versions**: 3.9, 3.10, 3.11, 3.12, 3.13  
**Default Python Version**: 3.11  
**License**: MIT

