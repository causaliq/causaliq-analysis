"""Axis styling and per-subplot annotation helpers for plot charts.

The style maps translate the legacy chart property names into
matplotlib/Seaborn parameters, and the helpers apply them to an axes
object or annotate a subplot with box/violin statistics.
"""

from typing import Any

from matplotlib.ticker import FixedLocator
from pandas import DataFrame

# Matplotlib/Seaborn properties which can be modified in format
# {plot property name: Matplotlib/Seaborn param name}

# Individual properties set explicitly:
#   figure.title
#   figure.title_fontsize
#   line.sizes
#   line.dashes
#   palette
#   subplot.kind
#   subplot.aspect

# Properties set on an individual axis set.
AXES_PROPS = {
    "xaxis.label": "xlabel",
    "xaxis.range": "xlim",
    "xaxis.scale": "xscale",
    "xaxis.ticks": "xticks",
    "yaxis.label": "ylabel",
    "yaxis.range": "ylim",
    "yaxis.scale": "yscale",
    "yaxis.ticks": "yticks",
    "subplot.title": "title",
}

# Properties set through rcParams (font sizes, colours etc).
CONTEXT_PROPS = {
    "legend.fontsize": "legend.fontsize",
    "legend.title_fontsize": "legend.title_fontsize",
    "subplot.title_fontsize": "axes.titlesize",
    "subplot.axes_fontsize": "axes.labelsize",
    "xaxis.ticks_fontsize": "xtick.labelsize",
    "yaxis.ticks_fontsize": "ytick.labelsize",
    "subplot.background": "axes.facecolor",
    "subplot.grid": "axes.grid",
    "subplot.grid_colour": "grid.color",
    "figure.background": "figure.facecolor",
}

SUBPLOT_ADJUST = {
    "figure.subplots_top": "top",
    "figure.subplots_left": "left",
    "figure.subplots_right": "right",
    "figure.subplots_bottom": "bottom",
    "figure.subplots_hspace": "hspace",
    "figure.subplots_wspace": "wspace",
}

FACET_PROPS = {
    "xaxis.shared": "sharex",
    "yaxis.shared": "sharey",
    "legend.outside": "legend_out",
}

VIOLIN_PROPS = {
    "violin.scale": "density_norm",  # density_norm: area, count or width
    "violin.width": "width",  # absolute width of violin
}

# Type of the per-subplot info dictionary used for box/violin annotations.
SubplotInfo = dict[str, Any]

# Position and default size of the panel tags, in axes coordinates.
TAG_X = -0.02
TAG_Y = 1.02
TAG_FONTSIZE = 16


def _set_axes_props(
    axes: Any,
    properties: dict[str, Any],
    subplot: str | None = None,
) -> None:
    """Set up the properties of an individual axes object.

    Args:
        axes: matplotlib axes object to modify.
        properties: axis properties required.
        subplot: name of the subplot the axes belongs to, used to select
            subplot-specific values from dict properties.
    """
    _apply_axis_params(axes, properties, subplot)
    _apply_tick_labels(axes, properties)
    _apply_tick_rotation(axes, properties)
    _apply_tick_halign(axes, properties)
    _apply_title_weight(axes, properties)
    _apply_subplot_tag(axes, properties, subplot)
    _invert_axis_bars(axes, properties, subplot)
    _apply_bar_alpha(axes, properties)


def _apply_axis_params(
    axes: Any,
    properties: dict[str, Any],
    subplot: str | None,
) -> None:
    """Apply the properties supported by the axes ``set`` method."""
    params: dict[str, Any] = {}
    current = axes.properties()
    for key, param in AXES_PROPS.items():
        if key in properties:
            params[param] = _axis_param_value(
                properties[key], subplot, current[param]
            )
    axes.set(**params)


def _axis_param_value(value: Any, subplot: str | None, current: Any) -> Any:
    """Select the value for a subplot, or the current axes value."""
    if not isinstance(value, dict):
        return value
    if subplot and subplot in value:
        return value[subplot]
    return current


def _apply_tick_labels(axes: Any, properties: dict[str, Any]) -> None:
    """Set custom x-axis tick labels with a fixed locator."""
    if "xaxis.tick_labels" not in properties:
        return
    _fix_xtick_locator(axes)
    axes.set_xticklabels(properties["xaxis.tick_labels"])


def _apply_tick_rotation(axes: Any, properties: dict[str, Any]) -> None:
    """Rotate the x-axis tick labels."""
    if "xaxis.ticks_rotation" not in properties:
        return
    for label in axes.get_xticklabels():
        label.set_rotation(properties["xaxis.ticks_rotation"])


def _apply_tick_halign(axes: Any, properties: dict[str, Any]) -> None:
    """Set the horizontal alignment of the x-axis tick labels."""
    if "xaxis.ticks_halign" not in properties:
        return
    for label in axes.get_xticklabels():
        label.set_horizontalalignment(properties["xaxis.ticks_halign"])


def _fix_xtick_locator(axes: Any) -> None:
    """Fix the x-axis tick positions before setting tick labels."""
    axes.xaxis.set_major_locator(FixedLocator(axes.get_xticks()))


def _invert_axis_bars(
    axes: Any, properties: dict[str, Any], subplot: str | None
) -> None:
    """Invert the y-axis so that negative bars grow upwards."""
    if not _has_invert_range(properties, subplot):
        return
    for bar in axes.patches:
        bar.set_y(properties["yaxis.range"][subplot][0])
        bar.set_height(
            bar.get_height() - properties["yaxis.range"][subplot][0]
        )


def _has_invert_range(properties: dict[str, Any], subplot: str | None) -> bool:
    """Return True when the subplot has an inverted, ranged y-axis."""
    return (
        "yaxis.invert" in properties
        and subplot in properties["yaxis.invert"]
        and "yaxis.range" in properties
        and subplot in properties["yaxis.range"]
    )


def _apply_bar_alpha(axes: Any, properties: dict[str, Any]) -> None:
    """Set the opacity of the bar patches."""
    alpha = properties.get("bar.alpha")
    if alpha is None:
        return
    for bar in axes.patches:
        bar.set_alpha(alpha)


def _apply_title_weight(axes: Any, properties: dict[str, Any]) -> None:
    """Set the font weight of the subplot title."""
    weight = properties.get("subplot.title_fontweight")
    if not weight:
        return
    axes.title.set_fontweight(weight)


def _apply_subplot_tag(
    axes: Any, properties: dict[str, Any], subplot: str | None
) -> None:
    """Draw a panel tag (e.g. ``A``) in the top-left corner of a subplot.

    Args:
        axes: matplotlib axes object for a subplot.
        properties: axis properties holding an optional ``subplot.tag``
            and ``subplot.tag_fontsize``.
        subplot: name of the subplot the axes belongs to.
    """
    tags = properties.get("subplot.tag")
    if not tags:
        return
    tag = _axis_param_value(tags, subplot, "")
    if not tag:
        return
    size = properties.get("subplot.tag_fontsize", TAG_FONTSIZE)
    axes.text(
        TAG_X,
        TAG_Y,
        tag,
        transform=axes.transAxes,
        fontsize=size,
        fontweight="bold",
        va="bottom",
    )


def _report_boxplot_values(axes: Any, info: SubplotInfo | None = None) -> None:
    """Report and plot the boxplot values - percentiles, whiskers and extremes.

    Args:
        axes: matplotlib axes object for a subplot.
        info: information to add to box plots for the subplot.
    """
    if info is None:
        return
    data = _collect_boxplot_values(axes, info)
    frame = DataFrame(data)
    frame = frame[
        [
            "comparing",
            "min",
            "lo_whisker",
            "p25",
            "p50",
            "p75",
            "hi_whisker",
            "max",
        ]
    ]
    print("\nBox plot values are:\n{}\n".format(frame))


def _collect_boxplot_values(
    axes: Any, info: SubplotInfo
) -> list[dict[str, Any]]:
    """Collect the boxplot statistics and annotate each subplot mean."""
    plot_values = ["p25", "p75", "lo_whisker", "hi_whisker", "p50"]
    lines = axes.get_lines()
    x_labels = axes.get_xticklabels()

    data: list[dict[str, Any]] = []
    for x_idx in axes.get_xticks():
        x_label = x_labels[x_idx].get_text()
        print("Data for {} is {}".format(x_label, info[x_label]))
        values = {
            key: round(list(lines[6 * x_idx + i].get_ydata())[0], 3)
            for i, key in enumerate(plot_values)
        }
        outliers = list(lines[6 * x_idx + 5].get_ydata())
        values.update(
            {
                "min": (
                    round(min(outliers), 3)
                    if len(outliers) and min(outliers) < values["lo_whisker"]
                    else None
                ),
                "max": (
                    round(max(outliers), 3)
                    if len(outliers) and max(outliers) > values["hi_whisker"]
                    else None
                ),
                "comparing": x_label,
            }
        )
        data.append(values)
        _add_mean_label(axes, x_idx, info[x_label]["mean"], 9)
    return data


def _add_mean_label(axes: Any, x_idx: Any, mean: Any, size: Any) -> None:
    """Add a centred mean label to a plot."""
    axes.text(
        x_idx,
        mean,
        "{}".format(mean),
        ha="center",
        va="center",
        fontweight="bold",
        size=size,
        color="white",
        bbox={"facecolor": "#445A64", "pad": 1, "alpha": 0.5},
    )


def _plot_violin_means(
    axes: Any, info: SubplotInfo, props: dict[str, Any]
) -> None:
    """Display the means on violin plots.

    Args:
        axes: matplotlib axes object for a subplot.
        info: information to add to the violin plot.
        props: customisable properties of the chart.
    """
    x_labels = axes.get_xticklabels()
    for x_idx in axes.get_xticks():
        x_label = x_labels[x_idx].get_text()
        print("Data for {} is {}".format(x_label, info[x_label]))
        size = props["violin.fontsize"] if "violin.fontsize" in props else 9
        _add_mean_label(axes, x_idx, info[x_label]["mean"], size)
