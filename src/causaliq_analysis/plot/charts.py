"""Seaborn chart builders for the plot action.

The public chart functions stay thin, delegating the shared figure style,
per-kind figure construction and the figure/axes/legend post-processing to
module-level helpers.
"""

import re
from typing import Any, Iterator, NamedTuple

import matplotlib.pyplot as plt
import seaborn as sns
from pandas import DataFrame

from causaliq_analysis.plot import legend as legend_helpers
from causaliq_analysis.plot import style as style_helpers
from causaliq_analysis.plot.axes import (
    CONTEXT_PROPS,
    FACET_PROPS,
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

# Default style of the scatter connectors.
CONNECT_COLOUR = "#888888"
CONNECT_WIDTH = 0.8

__all__ = [
    "SUPPORTED_KINDS",
    "plot_degree_distribution",
    "plot_scatter",
    "relplot",
]


class _FigureStyle(NamedTuple):
    """Shared figure style derived from the chart properties."""

    palette: list[Any] | None
    facet_kws: dict[str, Any]
    col_wrap: int | None
    aspect: Any
    rc_params: dict[str, Any]
    sizes: dict[str, Any]
    dashes: dict[str, Any]


def relplot(
    data: DataFrame,
    props: dict[str, Any],
    plot_file: str,
    info: dict[str, SubplotInfo] | None = None,
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
        subplots = _subplot_axes(g)
        style_helpers.apply_figure_size(g, props)
        style_helpers.apply_figure_title(g, props)
        style_helpers.apply_layout_or_adjust(g, props)
        _apply_axes_with_annotations(subplots, props, kind, info)
        legend_helpers.apply_legend(g, subplots, props)
        style_helpers.save_figure(g, props, plot_file, default_dpi=80)


def plot_scatter(
    data: DataFrame, props: dict[str, Any], plot_file: str
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
        g = _build_scatter(data, props, palette, facet_kws, col_wrap)
        subplots = _subplot_axes(g)
        style_helpers.apply_figure_size(g, props)
        style_helpers.apply_figure_title(g, props)
        style_helpers.apply_layout_or_adjust(g, props)
        if props.get("scatter.connect"):
            _connect_scatter(g, data, props, subplots)
        _set_subplot_axes(subplots, props)
        legend_helpers.apply_scatter_legend(g, subplots, props)
        style_helpers.save_figure(g, props, plot_file, default_dpi=600)


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


def _print_properties(props: dict[str, Any]) -> None:
    """Print the chart properties in sorted order."""
    for p in sorted(props):
        print("{} = {}".format(p, props[p]))


def _subplot_kind(props: dict[str, Any]) -> str | None:
    """Return the requested subplot kind, if any."""
    return props["subplot.kind"] if "subplot.kind" in props else None


def _figure_style(props: dict[str, Any], data: DataFrame) -> _FigureStyle:
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


def _unique_y_vars(data: DataFrame) -> list[Any]:
    """Return the unique y_var values, printing them when present."""
    y_vars: list[Any] = []
    if "y_var" in data.columns:
        y_vars = list(data["y_var"].unique())
        print("Unique y_vars are: {}".format(y_vars))
    return y_vars


def _line_style(
    props: dict[str, Any], y_vars: list[Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
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


def _palette(props: dict[str, Any]) -> list[Any] | None:
    """Return the RGB palette derived from hex colour properties."""
    if "palette" not in props:
        return None
    return [
        tuple(int(h[i : i + 2], 16) / 255 for i in (1, 3, 5))
        for h in props["palette"]
    ]


def _facet_params(props: dict[str, Any]) -> dict[str, Any]:
    """Return the facet parameters for the current properties."""
    return {p: props[k] for k, p in FACET_PROPS.items() if k in props}


def _col_wrap(props: dict[str, Any]) -> int | None:
    """Return the number of subplots per row, if configured."""
    return props["figure.per_row"] if "figure.per_row" in props else None


def _rc_params(props: dict[str, Any]) -> dict[str, Any]:
    """Return the rcParams derived from the chart properties."""
    params = style_helpers.theme_rc_params(props)
    params.update(
        {p: props[k] for k, p in CONTEXT_PROPS.items() if k in props}
    )
    return params


def _build_figure(
    kind: str | None,
    data: DataFrame,
    props: dict[str, Any],
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
    props: dict[str, Any], data: DataFrame, style: _FigureStyle
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
    props: dict[str, Any], data: DataFrame, style: _FigureStyle
) -> Any:
    """Build a bar catplot grid."""
    return sns.catplot(
        x="x_val",
        y="y_val",
        data=data,
        col_wrap=style.col_wrap,
        col="subplot",
        hue="y_var",
        kind="bar",
        aspect=style.aspect,
        palette=style.palette,
        **style_helpers.catplot_kwargs(props, style.facet_kws),
    )


def _build_scatter(
    data: DataFrame,
    props: dict[str, Any],
    palette: list[Any] | None,
    facet_kws: dict[str, Any],
    col_wrap: int | None,
) -> Any:
    """Build a scatter lmplot grid without a fitted regression line."""
    return sns.lmplot(
        data=data,
        x="x_val",
        y="y_val",
        hue="y_var",
        col="subplot",
        facet_kws=facet_kws,
        col_wrap=col_wrap,
        palette=palette,
        markers=style_helpers.scatter_markers(props),
        scatter_kws=style_helpers.scatter_kws(props),
        fit_reg=False,
    )


def _connect_scatter(
    g: Any,
    data: DataFrame,
    props: dict[str, Any] | None = None,
    subplots: list[tuple[Any, str]] | None = None,
) -> None:
    """Connect the two hue groups at each x value on every subplot.

    Args:
        g: Seaborn figure grid holding the scatter subplots.
        data: Long-form data with subplot, x_val and y_val columns.
        props: chart properties holding the connector style.
        subplots: pairs of axes and subplot name; read from the titles
            when not supplied.
    """
    props = props or {}
    targets = subplots if subplots is not None else _subplot_axes(g)
    for axes, subplot in targets:
        subset = data[data["subplot"] == subplot]
        _connect_axes(axes, subset, props)


def _connect_axes(
    axes: Any, subset: DataFrame, props: dict[str, Any] | None = None
) -> None:
    """Draw one vertical connector per paired group of values.

    Args:
        axes: Matplotlib axes of one subplot.
        subset: Long-form data belonging to that subplot.
        props: chart properties holding the connector style.
    """
    props = props or {}
    colour = props.get("scatter.connect_colour", CONNECT_COLOUR)
    width = props.get("scatter.connect_linewidth", CONNECT_WIDTH)
    for x_val, values in _connector_pairs(subset):
        axes.plot(
            [x_val, x_val],
            values,
            color=colour,
            linewidth=width,
            zorder=1,
        )


def _connector_pairs(subset: DataFrame) -> Iterator[tuple[Any, list[Any]]]:
    """Yield the x value and two y values of each paired group.

    Rows are grouped by the scatter.connect_key column when it is
    present, so repeated x values stay paired by their source row.
    """
    key = "row_key" if "row_key" in subset.columns else "x_val"
    for _, rows in subset.groupby(key, sort=False):
        values = [value for value in rows["y_val"] if value == value]
        if len(values) == 2:
            yield rows["x_val"].iloc[0], values


def _apply_axes_with_annotations(
    subplots: list[tuple[Any, str]],
    props: dict[str, Any],
    kind: str | None,
    info: dict[str, SubplotInfo] | None,
) -> None:
    """Apply axes properties and box/violin annotations to each subplot."""
    for axes, subplot in subplots:
        _set_axes_props(axes, props, subplot)
        _annotate_axes(axes, props, kind, subplot, info)


def _set_subplot_axes(
    subplots: list[tuple[Any, str]], props: dict[str, Any]
) -> None:
    """Apply axes properties to every subplot."""
    for axes, subplot in subplots:
        _set_axes_props(axes, props, subplot)


def _subplot_axes(g: Any) -> list[tuple[Any, str]]:
    """Return each axes with its subplot name, before retitling."""
    return [(axes, _subplot_name(axes)) for axes in g.axes.flat]


def _subplot_name(axes: Any) -> str:
    """Return the subplot name from the axes title."""
    title_match = _SUBPLOT_TITLE.match(axes.properties()["title"])
    return title_match.group(1) if title_match else ""


def _annotate_axes(
    axes: Any,
    props: dict[str, Any],
    kind: str | None,
    subplot: str,
    info: dict[str, SubplotInfo] | None,
) -> None:
    """Add the box/violin annotations for one subplot."""
    if kind == "box":
        _report_boxplot_values(
            axes, info=(None if info is None else info[subplot])
        )
    elif kind == "violin" and info is not None:
        _plot_violin_means(axes, info[subplot], props)
