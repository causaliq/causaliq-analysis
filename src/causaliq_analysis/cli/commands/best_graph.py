"""The ``best-graph`` command."""

import json
from pathlib import Path
from typing import Any, Dict, Tuple

import click

__all__ = ["best_graph_cmd"]


@click.command(name="best-graph")
@click.option(
    "--input",
    "-i",
    required=True,
    type=click.Path(exists=True),
    help="Path to PDG file (GraphML format).",
)
@click.option(
    "--output",
    "-o",
    required=True,
    type=click.Path(),
    help="Output directory for DAG and metadata files.",
)
@click.option(
    "--threshold",
    "-t",
    default=0.0,
    type=float,
    help="Minimum edge probability threshold (default: 0.0).",
)
def best_graph_cmd(
    input: str,
    output: str,
    threshold: float,
) -> None:
    """
    Extract optimal DAG from a PDG using greedy algorithm.

    Reads a Probabilistic Dependency Graph (PDG) and extracts the best
    DAG by greedily selecting high-probability edges while avoiding
    cycles. Undirected probability is split equally between forward
    and backward directions.

    For direction ties, alphabetical ordering is used (source -> target
    where source < target).

    Creates output directory containing dag.graphml and _meta.json.

    Example:
        causaliq-analysis best-graph -i merged.graphml -o results/optimal

        causaliq-analysis best-graph -i merged.graphml -o results/optimal \\
            --threshold=0.5
    """
    metadata, dag_obj = _run_best_graph_action(input, threshold)
    dag_path, meta_path = _write_best_graph_outputs(output, dag_obj, metadata)
    click.echo(f"Optimal DAG written to {dag_path}")
    click.echo(f"Metadata written to {meta_path}")


def _run_best_graph_action(
    input: str,
    threshold: float,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Run the best_graph action and return its metadata and DAG object.

    Args:
        input: Path to the PDG file.
        threshold: Minimum edge probability threshold.

    Returns:
        Tuple of (action metadata, DAG object).

    Raises:
        click.ClickException: If the action fails.
    """
    from causaliq_analysis.workflow_action import AnalysisActionProvider

    # Execute action
    action = AnalysisActionProvider()
    try:
        status, metadata, objects = action.run(
            "best_graph",
            {"input": input, "threshold": threshold},
            mode="run",
        )
    except Exception as e:
        raise click.ClickException(str(e))

    if status != "success":
        raise click.ClickException(f"Action failed: {metadata}")

    # Find DAG object
    dag_obj = next((o for o in objects if o["type"] == "dag"), None)
    if dag_obj is None:
        raise click.ClickException("No DAG object returned by action")

    return metadata, dag_obj


def _write_best_graph_outputs(
    output: str,
    dag_obj: Dict[str, Any],
    metadata: Dict[str, Any],
) -> Tuple[Path, Path]:
    """Write the extracted DAG and its metadata files.

    Args:
        output: Output directory.
        dag_obj: DAG object returned by the action.
        metadata: Action metadata to persist.

    Returns:
        Tuple of (DAG file path, metadata file path).
    """
    output_dir = _create_output_dir(output)
    dag_path = _write_dag_file(output_dir, dag_obj)
    meta_path = _write_best_graph_metadata(output_dir, metadata, dag_obj)
    return dag_path, meta_path


def _create_output_dir(output: str) -> Path:
    """Create the output directory if needed.

    Args:
        output: Output directory path.

    Returns:
        The created (or existing) output directory.

    Raises:
        click.ClickException: If the directory cannot be created.
    """
    output_dir = Path(output)
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise click.ClickException(f"Failed to create output directory: {e}")
    return output_dir


def _write_dag_file(output_dir: Path, dag_obj: Dict[str, Any]) -> Path:
    """Write the DAG GraphML object to disk.

    Args:
        output_dir: Output directory.
        dag_obj: DAG object returned by the action.

    Returns:
        Path to the written DAG file.

    Raises:
        click.ClickException: If the file cannot be written.
    """
    dag_path = output_dir / "dag.graphml"
    try:
        dag_path.write_text(dag_obj["content"], encoding="utf-8")
    except Exception as e:
        raise click.ClickException(f"Failed to write output: {e}")
    return dag_path


def _write_best_graph_metadata(
    output_dir: Path,
    metadata: Dict[str, Any],
    dag_obj: Dict[str, Any],
) -> Path:
    """Write the best-graph metadata file.

    Args:
        output_dir: Output directory.
        metadata: Action metadata to persist.
        dag_obj: DAG object returned by the action.

    Returns:
        Path to the written metadata file.

    Raises:
        click.ClickException: If the file cannot be written.
    """
    meta_path = output_dir / "_meta.json"
    meta_data = {
        "metadata": {"causaliq-analysis": {"best_graph": metadata}},
        "objects": {
            "dag": {
                "format": dag_obj["format"],
                "action": dag_obj["action"],
            }
        },
    }
    try:
        meta_path.write_text(json.dumps(meta_data, indent=2), encoding="utf-8")
    except Exception as e:
        raise click.ClickException(f"Failed to write metadata: {e}")
    return meta_path
