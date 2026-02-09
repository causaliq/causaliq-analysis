"""
causaliq-analysis: Tools for analysing and visualising causal graphs
"""

__version__ = "0.2.0"
__author__ = "CausalIQ"
__email__ = "info@causaliq.com"

# Package metadata
__title__ = "causaliq-analysis"
__description__ = "Tools for analysing and visualising causal graphs"

__url__ = "https://github.com/causaliq/causaliq-analysis"
__license__ = "MIT"

# Version tuple for programmatic access
VERSION = tuple(map(int, __version__.split(".")))

# Import main functions
from causaliq_analysis.graph import (  # noqa: E402, F401
    _validate_average_params,
    average,
)

# Import workflow action for auto-discovery (if causaliq-workflow is installed)
try:
    from causaliq_analysis.workflow_action import (  # noqa: E402, F401
        CausalIQAnalysisAction,
    )

    __all__ = [
        "__version__",
        "__author__",
        "__email__",
        "VERSION",
        "average",
        "_validate_average_params",
        "CausalIQAnalysisAction",
    ]
except ImportError:
    # causaliq-workflow not installed, skip workflow integration
    __all__ = [
        "__version__",
        "__author__",
        "__email__",
        "VERSION",
        "average",
        "_validate_average_params",
    ]
