"""
Common validation utilities for causaliq-analysis.

This module contains shared validation functions used across CLI and
workflow_action modules to avoid code duplication.
"""

from typing import Any, Tuple, Union


def parse_sample_size(size_input: Union[str, int]) -> int:
    """Parse sample size from various input formats.

    Args:
        size_input: Sample size as string (e.g., '10k', '100k') or integer

    Returns:
        int: Parsed sample size

    Raises:
        ValueError: If format is invalid

    Examples:
        >>> parse_sample_size("10k")
        10000
        >>> parse_sample_size("1.5k")
        1500
        >>> parse_sample_size("2m")
        2000000
        >>> parse_sample_size(1000)
        1000
    """
    if isinstance(size_input, int):
        return size_input

    if not isinstance(size_input, str):
        raise ValueError(f"Invalid sample size type: {type(size_input)}")

    size_str = str(size_input).strip().lower()

    if size_str.endswith("k"):
        try:
            return int(float(size_str[:-1]) * 1000)
        except ValueError:
            raise ValueError(f"Invalid sample size format: {size_str}")
    elif size_str.endswith("m"):
        try:
            return int(float(size_str[:-1]) * 1000000)
        except ValueError:
            raise ValueError(f"Invalid sample size format: {size_str}")
    else:
        try:
            return int(size_str)
        except ValueError:
            raise ValueError(f"Invalid sample size format: {size_str}")


def parse_seeds_cli(seeds_str: str) -> Tuple[int, ...]:
    """Parse seed string to tuple of integers (CLI format).

    CLI format treats comma-separated values as ranges if exactly 2 values.

    Args:
        seeds_str: Seeds string from CLI

    Returns:
        Tuple of seed integers

    Raises:
        ValueError: If format is invalid

    Examples:
        >>> parse_seeds_cli("")
        ()
        >>> parse_seeds_cli("5")
        (5,)
        >>> parse_seeds_cli("0,2")
        (0, 1, 2)
    """
    if not seeds_str or seeds_str.strip() == "":
        return ()

    try:
        parts = [int(s.strip()) for s in seeds_str.split(",")]

        if len(parts) == 1:
            # Single seed
            return tuple(parts)
        elif len(parts) == 2:
            # Range: start to end inclusive
            start, end = parts
            if start > end:
                raise ValueError(
                    f"Invalid range: start ({start}) > end ({end})"
                )
            return tuple(range(start, end + 1))
        else:
            raise ValueError(
                "Seeds should be either a single value or a range (start,end)"
            )

    except ValueError as e:
        if "invalid literal" in str(e):
            raise ValueError(f"Invalid seeds format: {seeds_str}")
        else:
            raise


def parse_seeds_workflow(seeds_input: Any) -> Tuple[int, ...]:
    """Parse seeds from various input formats (workflow format).

    Workflow format treats comma-separated values as explicit lists.

    Args:
        seeds_input: Seeds as string, list, tuple, or None

    Returns:
        Tuple of seed integers

    Raises:
        ValueError: If format is invalid

    Examples:
        >>> parse_seeds_workflow("")
        ()
        >>> parse_seeds_workflow("1,2,3")
        (1, 2, 3)
        >>> parse_seeds_workflow([1, 2, 3])
        (1, 2, 3)
    """
    if isinstance(seeds_input, tuple):
        return seeds_input

    if isinstance(seeds_input, list):
        return tuple(seeds_input)

    if not seeds_input or str(seeds_input).strip() == "":
        return ()

    if isinstance(seeds_input, str):
        try:
            seeds = tuple(int(s.strip()) for s in seeds_input.split(","))
            return seeds
        except ValueError:
            raise ValueError(f"Invalid seeds format: {seeds_input}")

    raise ValueError(f"Invalid seeds type: {type(seeds_input)}")
