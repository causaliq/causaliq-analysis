"""Seaborn chart builders for the plot action.

The public chart functions stay thin, delegating the shared figure style,
per-kind figure construction and the figure/axes/legend post-processing to
module-level helpers.
"""

import re
from typing import Any, Dict, List, NamedTuple, Optional, Tuple

import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.patches import Patch
from pandas import DataFrame

from causaliq_analysis.plot.axes import (
    CONTEXT_PROPS,
    FACET_PROPS,
    SUBPLOT_ADJUST,
    VIOLIN_PROPS,
    SubplotInfo,
    _plot_violin_means,
    _report_boxplot_values,
    _set_axes_props,
)

# Plot types supported by the plot action.
SUPPORTED_KINDS = frozenset(
    {"line", "regression", "histogram", "box", "violin", "bar", "scatter"}
)

# Pattern matching the per-subplot titles assigned by seaborn.
_SUBPLOT_TITLE = re.compile(r"^subplot\s\=\s(.+)$")

__all__ = [
    "SUPPORTED_KINDS",
    "plot_degree_distribution",
    "plot_scatter",
    "relplot",
]


class _FigureStyle(NamedTuple):
    """Shared figure style derived from the chart properties."""

    palette: Optional[List[Any]]
    facet_kws: Dict[str, Any]
    col_wrap: Optional[int]
    aspect: Any
    rc_params: Dict[str, Any]
    sizes: Dict[str, Any]
    dashes: Dict[str, Any]


def relplot(
    data: DataFrame,
    props: Dict[str, Any],
    plot_file: str,
    info: Optional[Dict[str, SubplotInfo]] = None,
) -> None:
    """Plot a set of relational charts.

    Args:
        data: data in long form with the following columns: subplot
            (identifies the subplot), x_val (x values), y_var (y-variable
            on each subplot) and y_val (y values).
        props: customisable properties of the chart.
        plot_file: path of the output plot file.
        info: optional extra information to print on the chart.

    Raises:
        ValueError: If an unsupported subplot.kind is requested.
    """
    _print_properties(props)
    kind = _subplot_kind(props)
    style = _figure_style(props, data)

    with plt.rc_context(rc=style.rc_params):
        g = _build_figure(kind, data, props, style)
        _apply_figure_title(g, props)
        _apply_subplot_adjust(g, props)
        _apply_axes_with_annotations(g, props, kind, info)
        _apply_legend(g, props)
        _save_figure(g, props, plot_file, default_dpi=80)


def plot_scatter(
    data: DataFrame, props: Dict[str, Any], plot_file: str
) -> None:
    """Plot one or more scatter plots.

    Args:
        data: data in long form with the columns subplot, x_val, y_var
            and y_val.
        props: customisable properties of the chart.
        plot_file: path of the output plot file.
    """
    palette = _palette(props)
    facet_kws = _facet_params(props)
    col_wrap = _col_wrap(props)
    rc_params = _rc_params(props)

    with plt.rc_context(rc=rc_params):
        g = _build_scatter(data, palette, facet_kws, col_wrap)
        _apply_figure_title(g, props)
        _apply_subplot_adjust(g, props)
        _set_subplot_axes(g, props)
        _apply_scatter_legend(g, props)
        _save_figure(g, props, plot_file, default_dpi=600)


def plot_degree_distribution(dist: DataFrame, plot_file: str) -> None:
    """Plot node degree distributions for networks.

    Args:
        dist: data with network, metric and value columns.
        plot_file: path of the output plot file.
    """
    g = sns.FacetGrid(dist, col="network", hue="metric", col_wrap=5)
    g.map(sns.histplot, "value", discrete=True)
    g.add_legend()
    g.fig.subplots_adjust(top=0.9)  # adjust the figure
    g.fig.suptitle("Node degree distributions for networks", size=30)
    g.set_axis_labels(x_var="Number of nodes")
    g.set_axis_labels(y_var="Node in-degree or total degree")
    legend = g.fig.get_children()[-1]
    for label in legend.texts:
        text = label.get_text()
        label.set_text("In-degree" if text == "in" else "Total degree")
    g.fig.savefig(plot_file, dpi=600)


def _print_properties(props: Dict[str, Any]) -> None:
    """Print the chart properties in sorted order."""
    for p in sorted(props):
        print("{} = {}".format(p, props[p]))


def _subplot_kind(props: Dict[str, Any]) -> Optional[str]:
    """Return the requested subplot kind, if any."""
    return props["subplot.kind"] if "subplot.kind" in props else None


def _figure_style(props: Dict[str, Any], data: DataFrame) -> _FigureStyle:
    """Return the shared figure style derived from the properties."""
    y_vars = _unique_y_vars(data)
    sizes, dashes = _line_style(props, y_vars)
    return _FigureStyle(
        palette=_palette(props),
        facet_kws=_facet_params(props),
        col_wrap=_col_wrap(props),
        aspect=props["subplot.aspect"] if "subplot.aspect" in props else 1,
        rc_params=_rc_params(props),
        sizes=sizes,
        dashes=dashes,
    )


def _unique_y_vars(data: DataFrame) -> List[Any]:
    """Return the unique y_var values, printing them when present."""
    y_vars: List[Any] = []
    if "y_var" in data.columns:
        y_vars = list(data["y_var"].unique())
        print("Unique y_vars are: {}".format(y_vars))
    return y_vars


def _line_style(
    props: Dict[str, Any], y_vars: List[Any]
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Return the line sizes and dashes, defaulting per y_var."""
    sizes = (
        props["line.sizes"]
        if "line.sizes" in props
        else {y_var: 3 for y_var in y_vars}
    )
    dashes = (
        props["line.dashes"]
        if "line.dashes" in props
        else {y_var: (1, 0) for y_var in y_vars}
    )
    return sizes, dashes


def _palette(props: Dict[str, Any]) -> Optional[List[Any]]:
    """Return the RGB palette derived from hex colour properties."""
    if "palette" not in props:
        return None
    return [
        tuple(int(h[i : i + 2], 16) / 255 for i in (1, 3, 5))
        for h in props["palette"]
    ]


def _facet_params(props: Dict[str, Any]) -> Dict[str, Any]:
    """Return the facet parameters for the current properties."""
    return {p: props[k] for k, p in FACET_PROPS.items() if k in props}


def _col_wrap(props: Dict[str, Any]) -> Optional[int]:
    """Return the number of subplots per row, if configured."""
    return props["figure.per_row"] if "figure.per_row" in props else None


def _rc_params(props: Dict[str, Any]) -> Dict[str, Any]:
    """Return the rcParams derived from the chart properties."""
    return {p: props[k] for k, p in CONTEXT_PROPS.items() if k in props}


def _build_figure(
    kind: Optional[str],
    data: DataFrame,
    props: Dict[str, Any],
    style: _FigureStyle,
) -> Any:
    """Build the seaborn figure grid for the requested kind."""
    if kind == "line":
        return _build_line(data, style)
    if kind == "regression":
        return _build_regression(data, style)
    if kind == "histogram":
        return _build_histogram(data, style)
    if kind == "box":
        return _build_box(data, style)
    if kind == "violin":
        return _build_violin(props, data, style)
    if kind == "bar":
        return _build_bar(props, data, style)
    raise ValueError("relplot() bad arg values")


def _build_line(data: DataFrame, style: _FigureStyle) -> Any:
    """Build a line relplot grid."""
    return sns.relplot(
        data=data,
        x="x_val",
        y="y_val",
        hue="y_var",
        kind="line",
        sizes=style.sizes,
        col="subplot",
        size="y_var",
        facet_kws=style.facet_kws,
        col_wrap=style.col_wrap,
        style="y_var",
        palette=style.palette,
        dashes=style.dashes,
        aspect=style.aspect,
        errorbar="sd",
    )


def _build_regression(data: DataFrame, style: _FigureStyle) -> Any:
    """Build a regression lmplot grid."""
    return sns.lmplot(
        data=data,
        x="x_val",
        y="y_val",
        hue="y_var",
        col="subplot",
        facet_kws=style.facet_kws,
        col_wrap=style.col_wrap,
        palette=style.palette,
    )


def _build_histogram(data: DataFrame, style: _FigureStyle) -> Any:
    """Build a histogram displot grid."""
    return sns.displot(
        data=data,
        x="x_val",
        col="subplot",
        hue="y_var",
        col_wrap=style.col_wrap,
        kind="kde",
        weights="weight",
    )


def _build_box(data: DataFrame, style: _FigureStyle) -> Any:
    """Build a box catplot grid."""
    return sns.catplot(
        x="x_val",
        y="y_val",
        data=data,
        kind="box",
        col_wrap=style.col_wrap,
        col="subplot",
        aspect=style.aspect,
        whis=[0, 100],
        palette=style.palette,
    )


def _build_violin(
    props: Dict[str, Any], data: DataFrame, style: _FigureStyle
) -> Any:
    """Build a violin catplot grid."""
    kwargs = {
        VIOLIN_PROPS[arg]: value
        for arg, value in props.items()
        if arg in VIOLIN_PROPS
    }
    return sns.catplot(
        x="x_val",
        y="y_val",
        data=data,
        kind="violin",
        col_wrap=style.col_wrap,
        col="subplot",
        aspect=style.aspect,
        cut=0,
        palette=style.palette,
        **kwargs,
    )


def _build_bar(
    props: Dict[str, Any], data: DataFrame, style: _FigureStyle
) -> Any:
    """Build a bar catplot grid."""
    sharex = props["xaxis.shared"] if "xaxis.shared" in props else True
    sharey = props["yaxis.shared"] if "yaxis.shared" in props else True
    return sns.catplot(
        x="x_val",
        y="y_val",
        data=data,
        col_wrap=style.col_wrap,
        col="subplot",
        hue="y_var",
        kind="bar",
        aspect=style.aspect,
        sharex=sharex,
        sharey=sharey,
    )


def _build_scatter(
    data: DataFrame,
    palette: Optional[List[Any]],
    facet_kws: Dict[str, Any],
    col_wrap: Optional[int],
) -> Any:
    """Build a scatter lmplot grid."""
    return sns.lmplot(
        data=data,
        x="x_val",
        y="y_val",
        hue="y_var",
        col="subplot",
        facet_kws=facet_kws,
        col_wrap=col_wrap,
        palette=palette,
    )


def _apply_figure_title(g: Any, props: Dict[str, Any]) -> None:
    """Set the figure super-title when requested."""
    if "figure.title" not in props:
        return
    size = (
        props["figure.title_fontsize"]
        if "figure.title_fontsize" in props
        else 30
    )
    g.fig.suptitle(props["figure.title"], size=size)


def _apply_subplot_adjust(g: Any, props: Dict[str, Any]) -> None:
    """Adjust the figure subplot layout when requested."""
    adjust = {p: props[k] for k, p in SUBPLOT_ADJUST.items() if k in props}
    if len(adjust):
        g.fig.subplots_adjust(**adjust)


def _apply_axes_with_annotations(
    g: Any,
    props: Dict[str, Any],
    kind: Optional[str],
    info: Optional[Dict[str, SubplotInfo]],
) -> None:
    """Apply axes properties and box/violin annotations to each subplot."""
    for axes in g.axes.flat:
        subplot = _subplot_name(axes)
        _set_axes_props(axes, props, subplot)
        _annotate_axes(axes, props, kind, subplot, info)


def _set_subplot_axes(g: Any, props: Dict[str, Any]) -> None:
    """Apply axes properties to every subplot."""
    for axes in g.axes.flat:
        _set_axes_props(axes, props, _subplot_name(axes))


def _subplot_name(axes: Any) -> str:
    """Return the subplot name from the axes title."""
    title_match = _SUBPLOT_TITLE.match(axes.properties()["title"])
    return title_match.group(1) if title_match else ""


def _annotate_axes(
    axes: Any,
    props: Dict[str, Any],
    kind: Optional[str],
    subplot: str,
    info: Optional[Dict[str, SubplotInfo]],
) -> None:
    """Add the box/violin annotations for one subplot."""
    if kind == "box":
        _report_boxplot_values(
            axes, info=(None if info is None else info[subplot])
        )
    elif kind == "violin" and info is not None:
        _plot_violin_means(axes, info[subplot], props)


def _apply_legend(g: Any, props: Dict[str, Any]) -> None:
    """Apply legend title, labels and manual key to the grid legend."""
    legend = g._legend
    if legend is None and "legend.key" in props:
        legend = _build_manual_legend(props)
    _set_legend_title(legend, props)
    _set_legend_labels(legend, props)


def _apply_scatter_legend(g: Any, props: Dict[str, Any]) -> None:
    """Apply the scatter legend title and labels."""
    legend = g._legend
    _set_legend_title(legend, props, size=18)
    _set_legend_labels(legend, props)


def _build_manual_legend(props: Dict[str, Any]) -> Any:
    """Build a legend from the legend.key property."""
    loc = props["legend.loc"] if "legend.loc" in props else None
    ncol = props["legend.ncol"] if "legend.ncol" in props else 1
    artists = [
        Patch(fc=colour, ec="gray", label=key)
        for key, colour in props["legend.key"].items()
    ]
    return plt.legend(handles=artists, handlelength=1, ncol=ncol, loc=loc)


def _set_legend_title(
    legend: Any, props: Dict[str, Any], size: Optional[int] = None
) -> None:
    """Set the legend title, optionally at a fixed font size."""
    if legend is None or "legend.title" not in props:
        return
    if size is None:
        legend.set_title(props["legend.title"])
    else:
        legend.set_title(props["legend.title"], {"size": size})


def _set_legend_labels(legend: Any, props: Dict[str, Any]) -> None:
    """Apply the legend.labels mapping to the legend entries."""
    if legend is None or "legend.labels" not in props:
        return
    for label in legend.texts:
        metric = label.get_text()
        if metric in props["legend.labels"]:
            label.set_text(props["legend.labels"][metric])


def _save_figure(
    g: Any, props: Dict[str, Any], plot_file: str, default_dpi: int
) -> None:
    """Save the figure to a file at the configured dpi."""
    dpi = props["figure.dpi"] if "figure.dpi" in props else default_dpi
    g.fig.savefig(plot_file, dpi=dpi)
