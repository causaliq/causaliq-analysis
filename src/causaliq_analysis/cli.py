"""Command-line interface for causaliq-analysis."""

from math import isnan
from pathlib import Path
from typing import Optional

import click
from pandas import DataFrame

from . import __version__
from .validation import parse_sample_size, parse_seeds_cli


def _interpret_correlation(corr: float) -> str:
    """Return interpretation label for a correlation coefficient."""
    abs_corr = abs(corr)
    if abs_corr >= 0.8:
        return "very strong"
    elif abs_corr >= 0.6:
        return "strong"
    elif abs_corr >= 0.4:
        return "moderate"
    elif abs_corr >= 0.2:
        return "weak"
    else:
        return "negligible"


def _report_entropy_correlations(df: DataFrame) -> None:
    """Report correlation between entropy measures and correctness."""
    # Existence correlation: h_exist vs exist_ok
    exist_data = df[["h_exist", "exist_ok"]].dropna()
    if len(exist_data) > 1:
        # Check for zero variance before computing correlation
        h_exist_var = exist_data["h_exist"].var()
        exist_ok_var = exist_data["exist_ok"].astype(float).var()

        if h_exist_var == 0 and exist_ok_var == 0:
            click.echo(
                "  h_exist vs exist_ok: cannot compute "
                "(no variance in h_exist or exist_ok)"
            )
        elif h_exist_var == 0:
            click.echo(
                "  h_exist vs exist_ok: cannot compute (h_exist variance = 0)"
            )
        elif exist_ok_var == 0:
            click.echo(
                "  h_exist vs exist_ok: cannot compute (exist_ok variance= 0)"
            )
        else:
            corr_exist = exist_data["h_exist"].corr(
                exist_data["exist_ok"].astype(float)
            )
            if not isnan(corr_exist):
                interp = _interpret_correlation(corr_exist)
                click.echo(
                    f"  h_exist vs exist_ok correlation: "
                    f"{corr_exist:.3f} ({interp})"
                )

    # Orientation correlation: h_orient vs orient_ok
    # Only for rows where orient_ok is not None (edge exists in both)
    orient_data = df[["h_orient", "orient_ok"]].dropna()
    if len(orient_data) > 1:
        # Check for zero variance before computing correlation
        h_orient_var = orient_data["h_orient"].var()
        orient_ok_var = orient_data["orient_ok"].astype(float).var()

        if h_orient_var == 0 and orient_ok_var == 0:
            click.echo(
                "  h_orient vs orient_ok: cannot compute "
                "(no variance in h_orient or orient_ok)"
            )
        elif h_orient_var == 0:
            click.echo(
                "  h_orient vs orient_ok: cannot compute "
                "(no variance in h_orient)"
            )
        elif orient_ok_var == 0:
            click.echo(
                "  h_orient vs orient_ok: cannot compute "
                "(no variance in orient_ok)"
            )
        else:
            corr_orient = orient_data["h_orient"].corr(
                orient_data["orient_ok"].astype(float)
            )
            if not isnan(corr_orient):
                interp = _interpret_correlation(corr_orient)
                click.echo(
                    f"  h_orient vs orient_ok correlation: "
                    f"{corr_orient:.3f} ({interp})"
                )


@click.group(name="causaliq-analysis")
@click.version_option(version=__version__)
def cli() -> None:
    """
    CausalIQ Analysis CLI - Tools for analysing and visualising causal graphs.
    """
    pass


@cli.command(name="graph-average")
@click.option("--network", required=True, help="Network name to process")
@click.option(
    "--N",
    "sample_size",
    required=True,
    help="Sample size (e.g., 10k, 100k, or integer)",
)
@click.option(
    "--seeds",
    default="",
    help="Comma-separated seed values (e.g., '0,1,2'). Empty means all seeds.",
)
@click.option(
    "--basis",
    type=click.Choice(["dag", "pdag"], case_sensitive=False),
    default="dag",
    help="Whether to use DAG or PDAG representation",
)
@click.option(
    "--output", required=True, type=click.Path(), help="Output CSV file path"
)
@click.option(
    "--series", required=True, help="Series path (e.g., TABU/SAMPLE/BASE)"
)
@click.option(
    "--root-dir",
    "root_dir",
    required=True,
    type=click.Path(exists=True),
    help="Root directory containing experiment traces",
)
@click.option(
    "--true-graph",
    "true_graph",
    default=None,
    type=click.Path(),
    help="Path to true graph (.xdsl or .dsc) relative to --root-dir. "
    "If provided, adds comparison columns to output.",
)
def graph_average_cmd(
    network: str,
    sample_size: str,
    seeds: str,
    basis: str,
    output: str,
    series: str,
    root_dir: str,
    true_graph: Optional[str],
) -> None:
    """
    Compute edge probabilities by averaging graphs across multiple experiments.

    Example:
        cqalys graph-average --network=asia --N=10k --seeds=0,1
                             --basis=pdag --output=average.csv
                             --series=TABU/SAMPLE/BASE --root-dir=experiments

        # With ground truth comparison:
        cqalys graph-average --network=asia --N=10k --seeds=0,1
                             --basis=pdag --output=average.csv
                             --series=TABU/SAMPLE/BASE --root-dir=experiments
                             --true-graph=networks/asia.xdsl
    """
    from causaliq_analysis.graph import (
        _validate_average_params,
        average,
        compare_to_truth,
    )
    from causaliq_analysis.trace import Trace

    # Parse sample size (handle formats like "10k", "100k", or plain integers)
    sample_size_int = parse_sample_size(sample_size)

    # Parse seeds
    seed_tuple = parse_seeds_cli(seeds)

    # Parse basis
    pdag = basis.lower() == "pdag"

    # Validate parameters using common validation
    try:
        _validate_average_params(sample_size_int, pdag, seed_tuple)
    except (TypeError, ValueError) as e:
        raise click.ClickException(str(e))

    # Read traces
    partial_id = f"{series}/{network}"
    try:
        traces = Trace.read(partial_id=partial_id, root_dir=root_dir)
        if traces is None:
            raise click.ClickException(
                f"No traces found for {partial_id} in {root_dir}"
            )
    except Exception as e:
        raise click.ClickException(f"Failed to read traces: {e}")

    # Filter traces to count how many will actually be used
    # (Same logic as in the average() function)
    matching_traces = {}
    for trace_id, trace in traces.items():
        # Check if trace has the right sample size
        if "N" not in trace.context or trace.context["N"] != sample_size_int:
            continue

        # Extract seed from trace ID (assuming format like "network_N1000_42")
        # If seeds tuple is empty, include all traces with matching sample size
        if len(seed_tuple) == 0:
            matching_traces[trace_id] = trace
        else:
            # Try to extract seed from trace_id
            parts = trace_id.split("_")
            for part in parts:
                try:
                    seed = int(part)
                    if seed in seed_tuple:
                        matching_traces[trace_id] = trace
                        break
                except ValueError:
                    continue

    if not matching_traces:
        raise click.ClickException(
            f"No traces found matching sample_size={sample_size_int} "
            f"and seeds={seed_tuple}"
        )

    # Compute average
    try:
        df = average(
            traces=traces,
            sample_size=sample_size_int,
            pdag=pdag,
            seeds=seed_tuple,
        )
    except Exception as e:
        raise click.ClickException(f"Failed to compute average: {e}")

    # Compare to ground truth if provided
    if true_graph:
        from causaliq_core.bn.io import read_bn

        true_graph_path = Path(root_dir) / true_graph
        if not true_graph_path.exists():
            raise click.ClickException(
                f"True graph file not found: {true_graph_path}"
            )
        try:
            true_dag = read_bn(str(true_graph_path)).dag
            df = compare_to_truth(df, true_dag)
            click.echo(f"Compared against true graph: {true_graph}")

            # Report correlation between entropy and correctness
            _report_entropy_correlations(df)
        except Exception as e:
            raise click.ClickException(
                f"Failed to load or compare true graph: {e}"
            )

    # Write output
    try:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output, index=False)
        click.echo(f"Edge probabilities written to {output}")
        click.echo(f"Averaged {len(matching_traces)} graphs")
    except Exception as e:
        raise click.ClickException(f"Failed to write output: {e}")


@cli.command(name="migrate_trace")
@click.option("--network", required=True, help="Network name to process")
@click.option(
    "--series", required=True, help="Series path (e.g., TABU/SAMPLE/BASE)"
)
@click.option(
    "--root-dir",
    "root_dir",
    default="experiments",
    type=click.Path(exists=True),
    help="Root directory containing experiment traces",
)
@click.option(
    "--N",
    "sample_size",
    default=None,
    help="Filter by sample size (e.g., 10k, 100k, or integer). "
    "Omit to include all sample sizes.",
)
@click.option(
    "--seeds",
    default="",
    help="Comma-separated seed values (e.g., '0,1,2'). Empty means all seeds.",
)
@click.option(
    "--output",
    default=None,
    type=click.Path(),
    help="Output directory for GraphML files. "
    "Defaults to migrated/<series>/<network>.",
)
def migrate_trace_cmd(
    network: str,
    series: str,
    root_dir: str,
    sample_size: Optional[str],
    seeds: str,
    output: Optional[str],
) -> None:
    """
    Migrate legacy Trace pickle files to GraphML format.

    Converts Trace files containing learnt graphs into portable GraphML format
    with accompanying metadata JSON files.

    Example:
        cqalys migrate_trace --network=asia --series=TABU/SAMPLE/BASE
                             --root-dir=experiments --N=10k --seeds=0,1
                             --output=migrated/asia
    """
    from causaliq_analysis.migrate import (
        run_migrate_trace,
        write_migrate_result,
    )

    # Build partial_id from series and network
    partial_id = f"{series}/{network}"

    # Parse optional sample_size
    sample_size_int = None
    if sample_size is not None:
        sample_size_int = parse_sample_size(sample_size)

    # Parse seeds
    seed_tuple = parse_seeds_cli(seeds)

    # Determine output directory
    if not output:
        output = f"migrated/{partial_id}"

    try:
        # Generate GraphML and metadata content
        result = run_migrate_trace(
            partial_id=partial_id,
            root_dir=root_dir,
            sample_size=sample_size_int,
            seeds=seed_tuple if seed_tuple else None,
            log_fn=click.echo,
        )

        # Write to files
        write_migrate_result(result, output, log_fn=click.echo)

        click.echo(
            f"Migration complete: {result.num_graphs} graphs "
            f"written to {output}"
        )
        if result.skipped:
            click.echo(f"Skipped {result.skipped} traces (no result graph)")
    except ValueError as e:
        raise click.ClickException(str(e))
    except Exception as e:
        raise click.ClickException(f"Migration failed: {e}")


def main() -> None:
    """Entry point for the CLI."""
    cli(prog_name="causaliq-analysis (cqalys)")


if __name__ == "__main__":  # pragma: no cover
    main()
