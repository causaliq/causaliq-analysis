# CausalIQ Analysis Plot

This package draws charts using matplotlib and Seaborn from a `summarise`
CSV output, migrated from the legacy `experiments/plot.py` module.

The public names are re-exported from `causaliq_analysis.plot`, so existing
imports are unchanged. Internally the package is split into:

- `causaliq_analysis.plot.properties` — chart property parsing;
- `causaliq_analysis.plot.axes` — axis styling and box/violin annotations;
- `causaliq_analysis.plot.charts` — the seaborn chart builders;
- `causaliq_analysis.plot.run` — the `run_plot` entry point and CSV helpers.

`SUPPORTED_KINDS` lists the plot kinds accepted by the `plot` action
(`line`, `regression`, `histogram`, `box`, `violin`, `bar` and `scatter`).

## Entry Point

::: causaliq_analysis.plot.run_plot
    options:
        show_root_heading: true
        show_source: false
        heading_level: 3

## Property Parsing

::: causaliq_analysis.plot.parse_properties
    options:
        show_root_heading: true
        show_source: false
        heading_level: 3

## Chart Builders

::: causaliq_analysis.plot.relplot
    options:
        show_root_heading: true
        show_source: false
        heading_level: 3

::: causaliq_analysis.plot.plot_scatter
    options:
        show_root_heading: true
        show_source: false
        heading_level: 3

::: causaliq_analysis.plot.plot_degree_distribution
    options:
        show_root_heading: true
        show_source: false
        heading_level: 3
