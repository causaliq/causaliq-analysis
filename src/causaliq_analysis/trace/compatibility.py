"""Backward-compatible unpickling of legacy trace files.

The compatibility unpickler and its loader live here, independent of the
``Trace`` class and the diff machinery, so that legacy module paths can be
remapped without pulling in the analysis code.
"""

import gzip
import pickle
from typing import Any

__all__ = ["CompatibilityUnpickler", "load_with_compatibility"]


class CompatibilityUnpickler(pickle.Unpickler):
    """Custom unpickler that handles module path changes for backward
    compatibility.

    Maps specific classes that have been moved between modules.
    """

    # Mapping of (old_module, class_name) to new_module
    CLASS_MAPPING = {
        ("core.common", "EdgeMark"): "causaliq_core.graph",
        ("core.common", "EdgeType"): "causaliq_core.graph",
        ("core.common", "EnumWithAttrs"): "causaliq_core.utils",
        ("core.common", "rndsf"): "causaliq_core.utils",
        ("core.common", "ln"): "causaliq_core.utils",
        ("core.common", "BAYESYS_VERSIONS"): "causaliq_core.graph",
        ("core.common", "adjmat"): "causaliq_core.graph",
        ("core.common", "environment"): "causaliq_core.utils",
        ("core.common", "RandomIntegers"): "causaliq_core.utils.random",
        ("core.common", "Randomise"): "causaliq_core.utils.random",
        ("core.common", "stable_random"): "causaliq_core.utils.random",
        ("core.common", "init_stable_random"): "causaliq_core.utils.random",
        (
            "core.common",
            "generate_stable_random",
        ): "causaliq_core.utils.random",
        ("core.common", "random_generator"): "causaliq_core.utils.random",
        ("core.common", "set_random_seed"): "causaliq_core.utils.random",
        ("core.timing", "Timing"): "causaliq_core.utils.timing",
        ("core.timing", "MetaTiming"): "causaliq_core.utils.timing",
        ("core.timing", "TimeoutError"): "causaliq_core.utils.timing",
        ("core.timing", "run_with_timeout"): "causaliq_core.utils.timing",
        ("core.timing", "with_timeout"): "causaliq_core.utils.timing",
        # Graph class mappings for the modular refactoring
        ("core.graph", "SDG"): "causaliq_core.graph.sdg",
        ("core.graph", "PDAG"): "causaliq_core.graph.pdag",
        ("core.graph", "DAG"): "causaliq_core.graph.dag",
        ("core.graph", "NotDAGError"): "causaliq_core.graph.dag",
        ("core.graph", "NotPDAGError"): "causaliq_core.graph.pdag",
        # Trace class mapping for the import refactoring
        ("learn.trace", "Trace"): "causaliq_analysis.trace",
        ("learn.trace", "CONTEXT_FIELDS"): "causaliq_analysis.trace",
        ("learn.trace", "DiffType"): "causaliq_analysis.trace",
        # Add more specific class mappings as needed
    }

    class PlaceholderEnum:
        """Placeholder class for missing enum-like classes from legacy modules.

        This handles unpickling of enum instances that reference classes not
        available in the current environment (e.g., learn.hc_worker.Prefer).

        The issue: Legacy pickle files contain references to EnumWithAttrs
        classes from the 'learn' module that don't exist in standalone
        causaliq_analysis. When unpickling, Python tries to instantiate these
        enums with arguments, but a simple empty class fails with
        "takes no arguments" error.

        This placeholder accepts any arguments during construction to allow
        successful unpickling while maintaining compatibility with the
        discovery repo.
        """

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            # Accept any arguments during unpickling to avoid TypeError
            self.args = args
            self.kwargs = kwargs

        def __new__(cls, *args: Any, **kwargs: Any) -> Any:
            # Create instance that can be unpickled successfully
            return object.__new__(cls)

    def find_class(self, module: str, name: str) -> Any:
        """Override find_class to handle module path changes.

        Args:
            module (str): Original module name from pickle.
            name (str): Class name.

        Returns:
            The class object from the new location.
        """
        if (module, name) in self.CLASS_MAPPING:
            module = self.CLASS_MAPPING[(module, name)]
            return super().find_class(module, name)
        return self._find_learn_class(module, name)

    def _find_learn_class(self, module: str, name: str) -> Any:
        """Resolve a legacy ``learn.*`` class, with a placeholder fallback.

        Args:
            module (str): Original module name from pickle.
            name (str): Class name.

        Returns:
            The real class when importable, otherwise a placeholder type.
        """
        if not module.startswith("learn.") or module == "learn.trace":
            return super().find_class(module, name)
        try:
            return super().find_class(module, name)
        except ModuleNotFoundError:
            return type(name, (self.PlaceholderEnum,), {})


def load_with_compatibility(
    file_handle: Any, compression: str = "gzip", **kwargs: Any
) -> Any:
    """Load pickled data with module compatibility handling.

    Args:
        file_handle: File handle to read from.
        compression (str): Compression type.

    Returns:
        Unpickled object.
    """
    if compression == "gzip":
        # For gzip compressed files, we need to decompress first
        file_handle.seek(0)
        with gzip.GzipFile(fileobj=file_handle, mode="rb") as gz_file:
            return CompatibilityUnpickler(gz_file).load()
    # For uncompressed files
    file_handle.seek(0)
    return CompatibilityUnpickler(file_handle).load()
