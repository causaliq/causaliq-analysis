"""Plot charts from summarised experimental results.

This package replaces the legacy ``causaliq_analysis.plot`` module and
re-exports its public names so existing imports keep resolving:

- ``run_plot`` from ``plot.run``;
- ``parse_properties`` from ``plot.properties``;
- ``relplot``, ``plot_scatter``, ``plot_degree_distribution`` and
  ``SUPPORTED_KINDS`` from ``plot.charts``;
- the axes helpers from ``plot.axes``.

The code is split so each part stays within the code limits: property
parsing in ``plot.properties``, axis styling and annotations in
``plot.axes``, the seaborn builders in ``plot.charts`` and the entry
point in ``plot.run``.
"""

from causaliq_analysis.plot.axes import (  # noqa: F401
    AXES_PROPS,
    CONTEXT_PROPS,
    FACET_PROPS,
    SUBPLOT_ADJUST,
    VIOLIN_PROPS,
    SubplotInfo,
    _plot_violin_means,
    _report_boxplot_values,
    _set_axes_props,
)
from causaliq_analysis.plot.charts import (
    SUPPORTED_KINDS,
    plot_degree_distribution,
    plot_scatter,
    relplot,
)
from causaliq_analysis.plot.properties import (  # noqa: F401
    _NOT_A_LITERAL,
    _convert_value,
    _split_property,
    parse_properties,
)
from causaliq_analysis.plot.run import run_plot

__all__ = [
    "SUPPORTED_KINDS",
    "parse_properties",
    "plot_degree_distribution",
    "plot_scatter",
    "relplot",
    "run_plot",
]
