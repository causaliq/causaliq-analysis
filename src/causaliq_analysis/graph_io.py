#
#   Graph file input helpers shared by the CLI and workflow actions
#

from typing import Any


def is_pdg_graphml(content: str) -> bool:
    """Return True if GraphML content represents a PDG.

    PDGs are serialised with probability data keys (p_forward etc.) which
    are absent from deterministic DAG/PDAG/CPDAG GraphML files.

    Args:
        content: GraphML document text.

    Returns:
        True if the content carries PDG probability keys.
    """
    return '<key id="p_forward"' in content


def _read_text(path: str) -> str:
    """Return the text of a file, or an empty string when unreadable.

    Args:
        path: Path to the file to read.

    Returns:
        The file contents, or "" when the file cannot be read.
    """
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    except OSError:
        return ""


def read_graph_or_pdg_file(path: str) -> Any:
    """Read a graph file, auto-detecting PDG GraphML and other formats.

    GraphML files carrying PDG probability keys are read as PDGs; all
    other supported formats are read as deterministic graphs.

    Args:
        path: Path to a graph file (.csv, .graphml, .tetrad, .xdsl, .dsc).

    Returns:
        Parsed graph (SDG/PDAG/DAG) or PDG.
    """
    from causaliq_core.bn.io import read_bn
    from causaliq_core.graph.io import graphml, read_graph

    suffix = path.lower().split(".")[-1]
    if suffix in ("xdsl", "dsc"):
        return read_bn(path).dag
    if suffix == "graphml" and is_pdg_graphml(_read_text(path)):
        return graphml.read_pdg(path)
    return read_graph(path)
