"""
causaliq-analysis: Tools for analysing and visualising causal graphs
"""

from typing import Optional

__version__ = "0.5.0.dev1"
__author__ = "CausalIQ"
__email__ = "info@causaliq.org"

# Package metadata
__title__ = "causaliq-analysis"
__description__ = "Tools for analysing and visualising causal graphs"

__url__ = "https://github.com/causaliq/causaliq-analysis"
__license__ = "MIT"


def _parse_version(version_str: str) -> tuple:
    """Parse version string to tuple, handling pre-release identifiers.

    Extracts numeric parts from version strings like "0.3.0" or "0.3.0.dev1".
    Pre-release identifiers (dev, alpha, beta, rc) are ignored for the tuple.

    Args:
        version_str: Version string (e.g., "0.3.0.dev1").

    Returns:
        Tuple of integers (e.g., (0, 3, 0)).
    """
    parts = []
    for part in version_str.split("."):
        value = _try_int(part)
        if value is None:
            # Non-integer part (e.g., "dev1") - stop parsing
            break
        parts.append(value)
    return tuple(parts)


def _try_int(value: str) -> Optional[int]:
    """Return the integer value of a version part, or None.

    Args:
        value: A single dot-separated version part (e.g. "3" or "dev1").

    Returns:
        The integer value, or None when the part is not an integer.
    """
    try:
        return int(value)
    except ValueError:
        return None


# Version tuple for programmatic access
VERSION = _parse_version(__version__)

# Import main functions
from causaliq_analysis.merge import merge_graphs  # noqa: E402, F401
from causaliq_analysis.plot import run_plot  # noqa: E402, F401

# Import workflow action for auto-discovery (if causaliq-workflow is installed)
try:
    from causaliq_analysis.workflow_action import (  # noqa: E402, F401
        ActionProvider,
        AnalysisActionProvider,
    )

    __all__ = [
        "__version__",
        "__author__",
        "__email__",
        "VERSION",
        "merge_graphs",
        "run_plot",
        "ActionProvider",
        "AnalysisActionProvider",
    ]
except ImportError:
    # causaliq-workflow not installed, skip workflow integration
    __all__ = [
        "__version__",
        "__author__",
        "__email__",
        "VERSION",
        "merge_graphs",
        "run_plot",
    ]
