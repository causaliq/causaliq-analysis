"""The ``plot`` command."""

from typing import Tuple

import click

__all__ = ["plot_cmd"]


@click.command(name="plot")
@click.option(
    "--input",
    "-i",
    required=True,
    type=click.Path(exists=True),
    help="Input CSV file produced by the summarise action.",
)
@click.option(
    "--output",
    "-o",
    required=True,
    type=click.Path(),
    help="Output chart file (e.g. a .png or .jpg image).",
)
@click.option(
    "--type",
    "plot_type",
    default="line",
    show_default=True,
    type=click.Choice(
        ["line", "regression", "histogram", "box", "violin", "bar", "scatter"]
    ),
    help="Type of plot required.",
)
@click.option(
    "--subplot",
    required=True,
    help="Column name in input which defines the subplot (e.g. network).",
)
@click.option(
    "--group",
    required=True,
    help="Column name in input which defines the legend groups (e.g. series).",
)
@click.option(
    "--x",
    "-x",
    required=True,
    help="Column name in input which provides the x-axis values.",
)
@click.option(
    "--y",
    "-y",
    required=True,
    help="Column name in input which provides the y-axis values.",
)
@click.option(
    "--property",
    "-p",
    "properties",
    multiple=True,
    help="Chart property in '<name>=<value>' format with a Python "
    "literal value (e.g. 'int.property=22', "
    "'dict.property={\"a\": 1}'). Can specify multiple.",
)
def plot_cmd(
    input: str,
    output: str,
    plot_type: str,
    subplot: str,
    group: str,
    x: str,
    y: str,
    properties: Tuple[str, ...],
) -> None:
    """
    Plot charts from a summarise CSV output.

    Draws a chart using matplotlib and Seaborn from information in a
    `.csv` file produced by the `summarise` action. The columns used
    for the subplot, groups, x-axis and y-axis are specified by the
    `--subplot`, `--group`, `--x` and `--y` options respectively.

    Example:
        causaliq-analysis plot -i summary.csv -o chart.png \\
            --type line --subplot network --group series \\
            --x sample_size --y f1.mean \\
            -p "xaxis.label=Sample size" \\
            -p "yaxis.label=F1"
    """
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    # Execute action
    action = AnalysisActionProvider()
    parameters = {
        "input": input,
        "output": output,
        "type": plot_type,
        "subplot": subplot,
        "group": group,
        "x": x,
        "y": y,
        "properties": list(properties),
    }
    try:
        status, metadata, _ = action.run("plot", parameters, mode="run")
    except Exception as e:
        raise click.ClickException(str(e))

    if status != "success":
        raise click.ClickException(f"Action failed: {metadata}")

    click.echo(f"Plot written to {metadata.get('output', output)}")
