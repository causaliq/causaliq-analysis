"""Significance tests over the columns of a summarise table.

A significance test is a table-level operation: it pairs the values of two
columns across the rows of a table and reports one statistic and one
p-value. Tests are declared separately from metric columns because a paired
test needs two samples and produces a single result for the whole table.

The registry maps a test name to its implementation and presentation
metadata, so a new test is added without changing the parser or renderers.
"""

from dataclasses import dataclass
from statistics import mean
from typing import Any, Callable, Sequence

from scipy.stats import spearmanr, wilcoxon

__all__ = [
    "SIGNIFICANCE_TESTS",
    "SignificanceSpec",
    "SignificanceTest",
    "_default_caption",
    "_paired_values",
    "_paired_summary",
    "_significance_rows",
    "_significance_stars",
    "_statistic_format",
    "_statistic_label",
]

# One table row: grouping values and computed column values
_Row = tuple[dict[str, Any], dict[str, Any]]


@dataclass(frozen=True)
class SignificanceTest:
    """One significance test available to ``summarise``.

    Attributes:
        name: Registry name used in a significance specification.
        title: Human-readable name used in the default caption.
        statistic_label: Symbol of the test statistic (for example ``W``).
        format_spec: Python format specification for the statistic.
        arity: Number of samples the test consumes.
        run: Callable returning the statistic and p-value, or None when
            the test cannot be computed.
    """

    name: str
    title: str
    statistic_label: str
    format_spec: str
    arity: int
    run: Callable[
        [Sequence[float], Sequence[float] | None],
        tuple[float, float] | None,
    ]


@dataclass(frozen=True)
class SignificanceSpec:
    """One declared significance test.

    Attributes:
        text: Specification text, without any label.
        test: Registered test implementation and metadata.
        left: Alias of the first sample column.
        right: Alias of the second sample column, or None for a
            one-sample test.
        label: Comparison label of the result row.
    """

    text: str
    test: SignificanceTest
    left: str
    right: str | None
    label: str


def _wilcoxon_signed_rank_2_sided(
    left: Sequence[float],
    right: Sequence[float] | None,
) -> tuple[float, float] | None:
    """Return the Wilcoxon signed-rank statistic and two-sided p-value.

    A two-sample call is the paired test: the differences are the values
    handed to SciPy. A one-sample call tests the values against zero.
    Fewer than two non-zero differences cannot produce a useful test and
    report no result.

    Args:
        left: First sample, or the sample tested against zero.
        right: Second sample, or None for a one-sample test.

    Returns:
        Tuple of (W statistic, two-sided p-value), or None when there are
        fewer than two non-zero differences.
    """
    differences = _differences(left, right)
    if sum(1 for value in differences if value != 0) < 2:
        return None
    result = wilcoxon(differences, alternative="two-sided")
    return float(result.statistic), float(result.pvalue)


def _differences(
    left: Sequence[float],
    right: Sequence[float] | None,
) -> list[float]:
    """Return paired differences, or the sample itself for one sample.

    Args:
        left: First sample.
        right: Second sample, or None for a one-sample test.

    Returns:
        Differences in sample order.
    """
    if right is None:
        return list(left)
    return [first - second for first, second in zip(left, right)]


def _spearman_2_sided(
    left: Sequence[float],
    right: Sequence[float] | None,
) -> tuple[float, float] | None:
    """Return the Spearman rank correlation and two-sided p-value.

    Args:
        left: First sample.
        right: Second sample.

    Returns:
        Tuple of (rho, two-sided p-value), or None when the correlation
        cannot be computed.

    """
    if right is None or len(left) < 3 or len(right) < 3:
        return None
    result = spearmanr(left, right)
    statistic = float(result.statistic)
    p_value = float(result.pvalue)
    if statistic != statistic or p_value != p_value:  # NaN guard
        return None
    return statistic, p_value


SIGNIFICANCE_TESTS: dict[str, SignificanceTest] = {
    "wilcoxon-signed-rank-2-sided": SignificanceTest(
        name="wilcoxon-signed-rank-2-sided",
        title="Wilcoxon signed-rank, two-sided",
        statistic_label="W",
        format_spec=".1f",
        arity=2,
        run=_wilcoxon_signed_rank_2_sided,
    ),
    "spearman-2-sided": SignificanceTest(
        name="spearman-2-sided",
        title="Spearman rank correlation, two-sided",
        statistic_label="rho",
        format_spec=".3f",
        arity=2,
        run=_spearman_2_sided,
    ),
}


def _paired_values(
    spec: SignificanceSpec,
    rows: Sequence[_Row],
) -> tuple[list[float], list[float] | None]:
    """Return the two samples of a test, paired by table row.

    Args:
        spec: Significance specification naming the sample aliases.
        rows: Grouping values and computed column values per row.

    Returns:
        Tuple of the left sample and the right sample; the right sample is
        None for a one-sample test.
    """
    left: list[float] = []
    right: list[float] = []
    for group, results in rows:
        pair = _row_pair(spec, {**group, **results})
        if pair is None:
            continue
        left.append(pair[0])
        if spec.right is not None:
            right.append(pair[1])
    return left, right if spec.right is not None else None


def _row_pair(
    spec: SignificanceSpec,
    values: dict[str, Any],
) -> tuple[float, float] | None:
    """Return the paired values of one table row.

    Args:
        spec: Significance specification naming the sample aliases.
        values: Grouping and computed column values of the row.

    Returns:
        Tuple of the two numeric values, or None when either is missing.
    """
    first = _numeric_value(values.get(spec.left))
    if first is None:
        return None
    if spec.right is None:
        return first, 0.0
    second = _numeric_value(values.get(spec.right))
    if second is None:
        return None
    return first, second


def _numeric_value(value: Any) -> float | None:
    """Return a numeric cell value, or None for a missing cell.

    Args:
        value: Cell value to convert.

    Returns:
        Numeric value, or None when the cell is missing or not numeric.
    """
    if value is None or isinstance(value, bool) or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _significance_row(
    spec: SignificanceSpec,
    rows: Sequence[_Row],
) -> dict[str, Any]:
    """Compute one significance result row.

    Args:
        spec: Significance specification.
        rows: Grouping values and computed column values per row.

    Returns:
        Result row holding the comparison label, statistic, p-value and
        significance stars.
    """
    left, right = _paired_values(spec, rows)
    result = spec.test.run(left, right) if left else None
    statistic, p_value = result if result is not None else (None, None)
    wins, losses, mean_delta = _paired_summary(left, right)
    return {
        "comparison": spec.label,
        "wins": wins,
        "losses": losses,
        "mean_delta": mean_delta,
        "statistic": statistic,
        "p_value": p_value,
        "significance": _significance_stars(p_value),
    }


def _paired_summary(
    left: Sequence[float],
    right: Sequence[float] | None,
) -> tuple[Any, Any, Any]:
    """Return wins, losses and mean difference of a paired sample.

    A win is a positive difference, a loss a negative difference and a tie
    is neither. The values are empty when the sample is empty.

    Args:
        left: First sample.
        right: Second sample, or None for a one-sample test.

    Returns:
        Tuple of (wins, losses, mean delta).

    """
    if not left:
        return "", "", ""
    if right is None:
        differences = list(left)
    else:
        differences = [first - second for first, second in zip(left, right)]
    wins = sum(1 for value in differences if value > 0)
    losses = sum(1 for value in differences if value < 0)
    return wins, losses, mean(differences)


def _significance_rows(
    specs: Sequence[SignificanceSpec],
    rows: Sequence[_Row],
) -> list[_Row]:
    """Compute one significance result row per declared test.

    Args:
        specs: Significance specifications in declaration order.
        rows: Grouping values and computed column values per row.

    Returns:
        Result rows in declaration order, each with empty grouping values.
    """
    return [({}, _significance_row(spec, rows)) for spec in specs]


def _significance_stars(p_value: float | None) -> str:
    """Return the significance stars for a p-value.

    Args:
        p_value: Two-sided p-value, or None when the test was not computed.

    Returns:
        ``***`` below 0.001, ``**`` below 0.01, ``*`` below 0.05, else blank.
    """
    if p_value is None:
        return ""
    if p_value < 0.001:
        return "***"
    if p_value < 0.01:
        return "**"
    if p_value < 0.05:
        return "*"
    return ""


def _default_caption(specs: Sequence[SignificanceSpec]) -> str:
    """Return the default caption of a significance table.

    Args:
        specs: Significance specifications in declaration order.

    Returns:
        A caption naming the test when every row uses the same test.
    """
    titles = {spec.test.title for spec in specs}
    if len(titles) == 1:
        return f"STATISTICAL TESTS ({next(iter(titles))})"
    return "STATISTICAL TESTS"


def _statistic_label(specs: Sequence[SignificanceSpec]) -> str:
    """Return the statistic column label of a significance table.

    Args:
        specs: Significance specifications in declaration order.

    Returns:
        The test's statistic symbol when every row shares it.
    """
    labels = {spec.test.statistic_label for spec in specs}
    if len(labels) == 1:
        return next(iter(labels))
    return "Statistic"


def _statistic_format(specs: Sequence[SignificanceSpec]) -> str:
    """Return the statistic format of a significance table.

    Args:
        specs: Significance specifications in declaration order.

    Returns:
        The test's format specification when every row shares it.
    """
    formats = {spec.test.format_spec for spec in specs}
    if len(formats) == 1:
        return next(iter(formats))
    return ".4g"
