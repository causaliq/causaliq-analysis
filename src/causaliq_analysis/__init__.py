"""
causaliq-analysis: Tools for analysing and visualising causal graphs
"""

__version__ = "0.3.0.dev1"
__author__ = "CausalIQ"
__email__ = "info@causaliq.com"

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
        # Try to parse as integer, stop at first non-integer part
        try:
            parts.append(int(part))
        except ValueError:
            # Non-integer part (e.g., "dev1") - stop parsing
            break
    return tuple(parts)


# Version tuple for programmatic access
VERSION = _parse_version(__version__)

# Import main functions
from causaliq_analysis.merge import merge_graphs  # noqa: E402, F401

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
    ]
