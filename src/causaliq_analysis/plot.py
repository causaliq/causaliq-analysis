"""
Plot charts from summarised experimental results.

This module migrates and restructures the legacy ``experiments/plot.py``
module from the ``causaliq-discovery`` repository so that figures such as
the variable-ordering CPDAG F1 chart can be replicated exactly from a
``summarise`` CSV output.
"""

import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.patches import Patch
from pandas import DataFrame, read_csv, to_numeric

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
    "violin.scale": "scale",  # scale: area, count or width
    "violin.width": "width",  # absolute width of violin
}

# Plot types supported by the plot action.
SUPPORTED_KINDS = frozenset(
    {"line", "regression", "histogram", "box", "violin", "bar", "scatter"}
)

# Type of the per-subplot info dictionary used for box/violin annotations.
SubplotInfo = Dict[str, Any]


def _convert_value(value: Optional[str]) -> Any:
    """Convert a string property value to its correct type.

    Supports blank values, ``True``/``False``, integers, floats, tuples
    ``(a, b)``, lists ``[a, b]`` and dictionaries ``{k, v, ...}``. The
    ``¬`` character converts to ``None`` (used to blank a property).

    Args:
        value: string value to convert, or None for a blank value.

    Returns:
        Value converted to the appropriate type.
    """
    if value is None:
        return ""
    if value == "¬":
        return None
    if value == "False":
        return False
    if value == "True":
        return True
    if value.startswith("(") and value.endswith(")"):
        return tuple(_convert_value(v) for v in value[1:-1].split(","))
    if value.startswith("[") and value.endswith("]"):
        return [_convert_value(v) for v in value[1:-1].split(",")]
    if value.startswith("{") and value.endswith("}"):
        items = [item.strip() for item in value[1:-1].split(",")]
        return {items[2 * i]: items[2 * i + 1] for i in range(len(items) // 2)}
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


def parse_properties(
    properties: Optional[Union[str, List[str]]],
) -> Dict[str, Any]:
    """Parse chart property strings into a typed dictionary.

    Each property is a string of the form ``<name>:<value>`` (e.g.
    ``"legend.title_fontsize:12"``). Values are converted to their correct
    types so ``"0.05"`` becomes a float and ``"True"`` becomes a boolean.

    Args:
        properties: list of property strings, a single string, or None.

    Returns:
        Dictionary of parsed property names to typed values.

    Raises:
        ValueError: If a property string is malformed.
    """
    parsed: Dict[str, Any] = {}
    if properties is None:
        return parsed
    if isinstance(properties, str):
        properties = [properties]
    for item in properties:
        name, _, value = item.partition(":")
        name = name.strip()
        if not name:
            raise ValueError(f"Malformed plot property: '{item}'")
        parsed[name] = _convert_value(value.strip() if value else None)
    return parsed


def _set_axes_props(
    axes: Any,
    properties: Dict[str, Any],
    subplot: Optional[str] = None,
) -> None:
    """Set up the properties of an individual axes object.

    Args:
        axes: matplotlib axes object to modify.
        properties: axis properties required.
        subplot: name of the subplot the axes belongs to, used to select
            subplot-specific values from dict properties.
    """
    params: Dict[str, Any] = {}
    current = axes.properties()
    for key, param in AXES_PROPS.items():
        if key in properties:
            if not isinstance(properties[key], dict):
                params.update({param: properties[key]})
            elif subplot and subplot in properties[key]:
                params.update({param: properties[key][subplot]})
            else:
                params.update({param: current[param]})
    axes.set(**params)

    # Set some properties not supported by the axes.set function.

    # Set custom x-axis tick labels.
    if "xaxis.tick_labels" in properties:
        axes.set_xticklabels(properties["xaxis.tick_labels"])

    # Rotation of x-axis tick labels.
    if "xaxis.ticks_rotation" in properties:
        axes.set_xticklabels(
            axes.get_xticklabels(), rotation=properties["xaxis.ticks_rotation"]
        )

    # Horizontal alignment of x-axis tick labels.
    if "xaxis.ticks_halign" in properties:
        axes.set_xticklabels(
            axes.get_xticklabels(),
            horizontalalignment=properties["xaxis.ticks_" + "halign"],
        )

    # Invert y-axis - used so that negative bars grow upwards.
    if (
        "yaxis.invert" in properties
        and subplot in properties["yaxis.invert"]
        and "yaxis.range" in properties
        and subplot in properties["yaxis.range"]
    ):
        for bar in axes.patches:
            bar.set_y(properties["yaxis.range"][subplot][0])
            bar.set_height(
                bar.get_height() - properties["yaxis.range"][subplot][0]
            )


def _report_boxplot_values(
    axes: Any, info: Optional[SubplotInfo] = None
) -> None:
    """Report and plot the boxplot values - percentiles, whiskers and extremes.

    Args:
        axes: matplotlib axes object for a subplot.
        info: information to add to box plots for the subplot.
    """
    if info is None:
        return
    plot_values = ["p25", "p75", "lo_whisker", "hi_whisker", "p50"]
    lines = axes.get_lines()
    x_labels = axes.get_xticklabels()

    data: List[Dict[str, Any]] = []
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

        axes.text(
            x_idx,
            info[x_label]["mean"],
            "{}".format(info[x_label]["mean"]),
            ha="center",
            va="center",
            fontweight="bold",
            size=9,
            color="white",
            bbox={"facecolor": "#445A64", "pad": 1, "alpha": 0.5},
        )

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


def _plot_violin_means(
    axes: Any, info: SubplotInfo, props: Dict[str, Any]
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
        axes.text(
            x_idx,
            info[x_label]["mean"],
            "{}".format(info[x_label]["mean"]),
            ha="center",
            va="center",
            fontweight="bold",
            size=size,
            color="white",
            bbox={"facecolor": "#445A64", "pad": 1, "alpha": 0.5},
        )


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
    for p in sorted(props):
        print("{} = {}".format(p, props[p]))

    # Get the unique y_var values.

    y_vars: List[Any] = []
    if "y_var" in data.columns:
        y_vars = list(data["y_var"].unique())
        print("Unique y_vars are: {}".format(y_vars))

    sizes = (
        props["line.sizes"]
        if "line.sizes" in props
        else {y_var: 3 for y_var in y_vars}
    )  # default width 3

    dashes = (
        props["line.dashes"]
        if "line.dashes" in props
        else {y_var: (1, 0) for y_var in y_vars}
    )  # default solid

    palette = (
        [
            tuple(int(h[i : i + 2], 16) / 255 for i in (1, 3, 5))
            for h in props["palette"]
        ]
        if "palette" in props
        else None
    )

    facet_kws = {p: props[k] for k, p in FACET_PROPS.items() if k in props}

    col_wrap = props["figure.per_row"] if "figure.per_row" in props else None

    rc_params = {p: props[k] for k, p in CONTEXT_PROPS.items() if k in props}

    kind = props["subplot.kind"] if "subplot.kind" in props else None
    aspect = props["subplot.aspect"] if "subplot.aspect" in props else 1

    with plt.rc_context(rc=rc_params):
        if kind == "line":
            g = sns.relplot(
                data=data,
                x="x_val",
                y="y_val",
                hue="y_var",
                kind=kind,
                sizes=sizes,
                col="subplot",
                size="y_var",
                facet_kws=facet_kws,
                col_wrap=col_wrap,
                style="y_var",
                palette=palette,
                dashes=dashes,
                aspect=aspect,
                ci="sd",
            )
        elif kind == "regression":
            g = sns.lmplot(
                data=data,
                x="x_val",
                y="y_val",
                hue="y_var",
                col="subplot",
                facet_kws=facet_kws,
                col_wrap=col_wrap,
                palette=palette,
            )
        elif kind == "histogram":
            g = sns.displot(
                data=data,
                x="x_val",
                col="subplot",
                hue="y_var",
                col_wrap=col_wrap,
                kind="kde",
                weights="weight",
            )
        elif kind == "box":
            g = sns.catplot(
                x="x_val",
                y="y_val",
                data=data,
                kind=kind,
                col_wrap=col_wrap,
                col="subplot",
                aspect=aspect,
                whis=[0, 100],
                palette=palette,
            )
        elif kind == "violin":
            kwargs = {
                VIOLIN_PROPS[arg]: value
                for arg, value in props.items()
                if arg in VIOLIN_PROPS
            }
            g = sns.catplot(
                x="x_val",
                y="y_val",
                data=data,
                kind=kind,
                col_wrap=col_wrap,
                col="subplot",
                aspect=aspect,
                cut=0,
                palette=palette,
                **kwargs,
            )
        elif kind == "bar":
            sharex = props["xaxis.shared"] if "xaxis.shared" in props else True
            sharey = props["yaxis.shared"] if "yaxis.shared" in props else True
            g = sns.catplot(
                x="x_val",
                y="y_val",
                data=data,
                col_wrap=col_wrap,
                col="subplot",
                hue="y_var",
                kind=kind,
                aspect=aspect,
                sharex=sharex,
                sharey=sharey,
            )
        else:
            raise ValueError("relplot() bad arg values")

        # Modify figure level properties.

        if "figure.title" in props:
            size = (
                props["figure.title_fontsize"]
                if "figure.title_fontsize" in props
                else 30
            )
            g.fig.suptitle(props["figure.title"], size=size)
        adjust = {p: props[k] for k, p in SUBPLOT_ADJUST.items() if k in props}
        if len(adjust):
            g.fig.subplots_adjust(**adjust)  # adjust the subplot area

        # Modify the properties of the axes of each subplot.

        title_pattern = re.compile(r"^subplot\s\=\s(.+)$")
        for axes in g.axes.flat:
            title_match = title_pattern.match(axes.properties()["title"])
            subplot = title_match.group(1) if title_match else ""
            _set_axes_props(axes, props, subplot)
            if kind == "box":
                _report_boxplot_values(
                    axes, info=(None if info is None else info[subplot])
                )
            elif kind == "violin" and info is not None:
                _plot_violin_means(axes, info[subplot], props)

        legend = g._legend

        # legend.key property used to manually define a legend.

        if legend is None and "legend.key" in props:
            loc = props["legend.loc"] if "legend.loc" in props else None
            ncol = props["legend.ncol"] if "legend.ncol" in props else 1
            artists = [
                Patch(fc=colour, ec="gray", label=key)
                for key, colour in props["legend.key"].items()
            ]
            legend = plt.legend(
                handles=artists, handlelength=1, ncol=ncol, loc=loc
            )

        if legend is not None and "legend.title" in props:
            legend.set_title(props["legend.title"])
        if legend is not None and "legend.labels" in props:
            for label in legend.texts:
                metric = label.get_text()
                if metric in props["legend.labels"]:
                    label.set_text(props["legend.labels"][metric])

        # Save the plot to a file.

        dpi = props["figure.dpi"] if "figure.dpi" in props else 80
        g.fig.savefig(plot_file, dpi=dpi)


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
    palette = (
        [
            tuple(int(h[i : i + 2], 16) / 255 for i in (1, 3, 5))
            for h in props["palette"]
        ]
        if "palette" in props
        else None
    )

    facet_kws = {p: props[k] for k, p in FACET_PROPS.items() if k in props}

    col_wrap = props["figure.per_row"] if "figure.per_row" in props else None

    rc_params = {p: props[k] for k, p in CONTEXT_PROPS.items() if k in props}

    with plt.rc_context(rc=rc_params):
        g = sns.lmplot(
            data=data,
            x="x_val",
            y="y_val",
            hue="y_var",
            col="subplot",
            facet_kws=facet_kws,
            col_wrap=col_wrap,
            palette=palette,
        )

        # Modify figure level properties.

        if "figure.title" in props:
            size = (
                props["figure.title_fontsize"]
                if "figure.title_fontsize" in props
                else 30
            )
            g.fig.suptitle(props["figure.title"], size=size)
        adjust = {p: props[k] for k, p in SUBPLOT_ADJUST.items() if k in props}
        if len(adjust):
            g.fig.subplots_adjust(**adjust)  # adjust the figure

        # Modify the axes of each subplot.

        title_pattern = re.compile(r"^subplot\s\=\s(.+)$")
        for axes in g.axes.flat:
            title_match = title_pattern.match(axes.properties()["title"])
            subplot = title_match.group(1) if title_match else ""
            _set_axes_props(axes, props, subplot)

        # Modify the legend.

        legend = g._legend
        if legend is not None and "legend.title" in props:
            legend.set_title(props["legend.title"], {"size": 18})
        if legend is not None and "legend.labels" in props:
            for label in legend.texts:
                metric = label.get_text()
                if metric in props["legend.labels"]:
                    label.set_text(props["legend.labels"][metric])

        dpi = props["figure.dpi"] if "figure.dpi" in props else 600
        g.fig.savefig(plot_file, dpi=dpi)


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


def run_plot(
    input_csv: str,
    output: str,
    kind: str = "line",
    subplot: str = "",
    group: str = "",
    x: str = "",
    y: str = "",
    properties: Optional[Union[str, List[str]]] = None,
    log_fn: Optional[Callable[[str], None]] = None,
) -> Dict[str, Any]:
    """Generate a chart from a ``summarise`` CSV output.

    The input CSV contains one row per subplot, x value and group
    combination (as produced by the ``summarise`` action). The chart is
    generated using the migrated legacy plotting functions.

    Args:
        input_csv: path of the input CSV file.
        output: path of the output chart file (e.g. ``.png`` or ``.jpg``).
        kind: type of plot required, e.g. ``line`` or ``bar``.
        subplot: column name defining the subplot.
        group: column name defining the groups shown in the legend.
        x: column name providing the x-axis values.
        y: column name providing the y-axis values.
        properties: list of chart property strings in
            ``<name>:<value>`` format.
        log_fn: optional callback used to log progress messages.

    Returns:
        Dictionary of metadata describing the chart generated.

    Raises:
        ValueError: If the kind, columns or input file are invalid.
    """
    if kind not in SUPPORTED_KINDS:
        raise ValueError(
            f"Unknown plot type '{kind}'. Supported types are: "
            f"{', '.join(sorted(SUPPORTED_KINDS))}"
        )

    if log_fn:
        log_fn(f"Plotting {kind} from {input_csv} to {output}")

    try:
        frame = read_csv(input_csv)
    except FileNotFoundError:
        raise ValueError(f"Input file not found: {input_csv}")

    # Normalise column names - some summarise outputs pad the headers.
    frame.columns = [str(col).strip() for col in frame.columns]

    # Check that the required columns are present in the input.

    missing = [c for c in (subplot, group, x, y) if c not in frame.columns]
    if missing:
        raise ValueError(
            f"Input CSV missing required column(s): {', '.join(missing)}"
        )

    # Build the long form data required by the plotting functions. The
    # subplot/group values are stripped of padding whitespace and the
    # y values are converted to numeric (non-numeric values become NaN).

    data = DataFrame(
        {
            "subplot": frame[subplot].astype(str).str.strip(),
            "x_val": frame[x],
            "y_var": frame[group].astype(str).str.strip(),
            "y_val": to_numeric(frame[y], errors="coerce"),
        }
    )

    # Merge user properties with the type parameter authoritative.

    props: Dict[str, Any] = parse_properties(properties)
    props["subplot.kind"] = kind

    if log_fn:
        for p in sorted(props):
            log_fn("{} = {}".format(p, props[p]))

    # Ensure the output directory exists.

    Path(output).parent.mkdir(parents=True, exist_ok=True)

    if kind == "scatter":
        plot_scatter(data, props, output)
    else:
        relplot(data, props, output)

    return {
        "input": str(input_csv),
        "output": str(output),
        "type": kind,
        "columns": {"subplot": subplot, "group": group, "x": x, "y": y},
    }
