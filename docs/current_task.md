# refactor plot.py according to module and method rules

> This file previously described the `plot.py` refactor, which is now
> complete (committed as `refactor: plot to meet causaliq guidelines` and
> `docs: document refactored plot API`, and recorded in
> `docs/architecture/overview.md`, section "Plot Package", and in
> `docs/api/plot.md`).
>
> `plot.py` is now the `plot/` package (`properties`, `axes`, `charts` and
> `run`) whose `__init__.py` re-exports the public names. The remaining
> legacy breaches, listed at the end of this file, are the candidates for
> the next refactoring task.

## Context and current breaches

`plot.py` is the module migrated from the legacy `experiments/plot.py`. It is
749 lines / **238 statements** and holds the chart property parsing, the
axis-styling helpers and the seaborn chart builders (`relplot`,
`plot_scatter`, `plot_degree_distribution`) plus the `run_plot` entry point.
Measured with `python scripts/check_code_rules.py`:

| Line | Object | Breach |
|------|--------|--------|
| 93 | `_convert_value` | depth 2, 25 statements |
| 137 | `_split_property` | — |
| 163 | `parse_properties` | — |
| 195 | `_set_axes_props` | depth 4, 23 statements |
| 258 | `_report_boxplot_values` | depth 1, 17 statements |
| 327 | `_plot_violin_means` | — |
| 355 | `relplot` | depth 7, **61 statements** (over hard maximum) |
| 558 | `plot_scatter` | depth 4, 27 statements |
| 632 | `plot_degree_distribution` | — |
| 653 | `run_plot` | depth 2, 23 statements |
| — | module | **238 statements** (target ~200) |

Structure worth noting while extracting:

- `_convert_value`, `_split_property` and the public `parse_properties` form a
  self-contained property-parsing group; `run_plot` and the workflow action
  both import `parse_properties` and `SUPPORTED_KINDS`.
- The style maps (`AXES_PROPS`, `CONTEXT_PROPS`, `SUBPLOT_ADJUST`,
  `FACET_PROPS`, `VIOLIN_PROPS`, `SubplotInfo`) and the axis helpers
  (`_set_axes_props`, `_report_boxplot_values`, `_plot_violin_means`) form an
  axes/styling group.
- `relplot` mixes per-kind figure construction (line, regression, histogram,
  box, violin, bar) with figure-level, axes-level and legend post-processing;
  it is the only over-hard-maximum function.
- `plot_scatter` repeats elements of the `relplot` palette/facet/rcParams and
  legend handling and can share module-level helpers.
- `run_plot` mixes kind validation, CSV reading, long-form data shaping,
  property merge/logging and dispatch to `plot_scatter`/`relplot`.

## Suggested steps

1. Step 1 (Foundation): convert `plot.py` into a `plot/` package whose
   `__init__.py` re-exports every name currently importable — including the
   private helpers the tests import (`_set_axes_props`,
   `_report_boxplot_values`, `_plot_violin_means`) plus `SUPPORTED_KINDS`,
   `parse_properties`, `plot_degree_distribution`, `plot_scatter`, `relplot`
   and `run_plot`. Keep it a pass-through so `tests/unit/test_plot.py` and
   `tests/functional/test_cli_plot.py` pass unchanged before any code is
   moved.
2. Step 2 (properties): move `_convert_value`, `_split_property`,
   `parse_properties` and `_NOT_A_LITERAL` into `plot/properties.py`,
   splitting `_convert_value` so it meets ≤15 statements and depth ≤2.
3. Step 3 (axes/styling): move the style maps and `SubplotInfo` plus
   `_set_axes_props`, `_report_boxplot_values` and `_plot_violin_means` into
   `plot/axes.py`, splitting `_set_axes_props` and `_report_boxplot_values`
   inside the move.
4. Step 4 (charts): move `relplot`, `plot_scatter`, `plot_degree_distribution`
   and `SUPPORTED_KINDS` into `plot/charts.py`; decompose `relplot` into a
   per-kind figure helper (line, regression, histogram, box, violin, bar) plus
   `_apply_figure_props`, `_apply_axes`, `_apply_legend` and `_save_figure`
   helpers, and split `plot_scatter` similarly.
5. Step 5 (runner): keep `run_plot` in `plot/run.py`, splitting it into
   kind validation, CSV reading, long-form data shaping and dispatch helpers.
6. Step 6 (final cleanup): reduce `plot/__init__.py` to re-exports only,
   remove duplicated helpers (e.g. the shared palette/facet/rcParams lookups
   used by both `relplot` and `plot_scatter`), keep every module ≤~200
   statements, and update the docs (`docs/api/plot.md`,
   `docs/architecture/overview.md` — whose Module Structure tree currently
   omits `plot.py` — and `docs/roadmap.md`).

## Constraints learned from the `workflow_action`, `cli` and `trace` refactors

- **Behaviour must stay byte-identical**: public names and signatures, error
  messages, `print` output and — critically — the rendered chart. The
  functional test
  `tests/functional/test_cli_plot.py::test_plot_exact_replication` compares the
  produced SVG byte-for-byte with `tests/data/functional/ord_hc_f1.svg`, so the
  seaborn/matplotlib calls, their order, the rcParams handling and the saved
  dpi must not change.
- **Preserve import binding sites** — code and tests import or patch by dotted
  path:
  - `src/causaliq_analysis/__init__.py:61` does
    `from causaliq_analysis.plot import run_plot`;
  - `src/causaliq_analysis/workflow_action/actions/plot.py` imports `run_plot`
    at module level and imports `SUPPORTED_KINDS` and `parse_properties`
    function-locally;
  - `tests/unit/test_plot.py:19` imports `SUPPORTED_KINDS`,
    `_plot_violin_means`, `_report_boxplot_values`, `_set_axes_props`,
    `parse_properties`, `plot_degree_distribution`, `plot_scatter`, `relplot`
    and `run_plot` from `causaliq_analysis.plot`;
  - `tests/unit/test_action_plot.py` patches
    `causaliq_analysis.workflow_action.actions.plot.run_plot` (the action
    module's binding), so keep that module's top-level import;
  - `tests/unit/test_plot.py` patches `seaborn.catplot` (external namespace),
    so keep the seaborn calls resolving through the `seaborn` module attribute.
  Re-export the names from `plot/__init__.py` so all of the above keep
  resolving; do not change the function-local imports in the workflow action.
- **No behaviour-free bulk test rewrites**: add focused `pytest-mock` tests
  only where coverage gaps appear; keep the existing `unittest.mock`
  (`from unittest.mock import patch`) usage in `tests/unit/test_plot.py` as it
  is (a mock-conversion sweep is a separate task).

## Commits

Stage the work as **two commits**:

1. **Code and tests** — `src/causaliq_analysis/plot/` (or the equivalent
   structure), any small `src/` edits it depends on, and the test changes.
2. **Documentation** — `docs/api/plot.md`, the
   `docs/architecture/overview.md` update (including adding `plot/` to the
   Module Structure tree and a "Plot Package" design note), the
   `docs/roadmap.md` status, plus this task file.

Do not mix documentation-only changes into the code commit.

## Gates after each slice (as in `scripts/check_ci.ps1`)

`black --check src tests` · `isort --check-only src tests` ·
`flake8 src tests` · `mypy src/` ·
`python scripts/check_code_rules.py --strict src/causaliq_analysis/plot` ·
`python scripts/check_code_rules.py src/causaliq_analysis/` (advisory) ·
targeted plot tests (`tests/unit/test_plot.py`,
`tests/unit/test_action_plot.py`, `tests/functional/test_cli_plot.py`) ·
full suite (`python -m pytest -q`) · docs: `python -m mkdocs build --strict`
(note: CI does not build the docs).
Maintain **100 % coverage** on the new modules and keep the `ord_hc_f1` SVG
replication test green.

## Test surface to watch

`tests/unit/test_plot.py` (imports the private helpers directly),
`tests/unit/test_action_plot.py` (patches the action's `run_plot` binding),
`tests/functional/test_cli_plot.py` (SVG replication and CLI behaviour),
`tests/functional/test_workflow_functional.py` and
`tests/integration/test_workflow_integration.py`.

## Suggested final structure (consider alternatives if they are better)

```
causaliq_analysis/
└── plot/
    ├── __init__.py     # public re-exports (run_plot, parse_properties,
    │                   # SUPPORTED_KINDS, relplot, plot_scatter,
    │                   # plot_degree_distribution, _set_axes_props, ...)
    ├── properties.py   # _convert_value, _split_property, parse_properties
    ├── axes.py         # style maps, SubplotInfo, _set_axes_props,
    │                   # _report_boxplot_values, _plot_violin_means
    ├── charts.py       # relplot (+ per-kind helpers), plot_scatter,
    │                   # plot_degree_distribution, SUPPORTED_KINDS
    └── run.py          # run_plot and CSV/data helpers
```

## Remaining legacy breaches (later tasks)

After `plot.py`, the outstanding breaches are: `metrics.py` (`pdg_compare` 57;
`_graph_to_pdg` depth 3, `bayesys_metrics` 21), `merge.py` (`merge_graphs` 45;
`_accumulate_sdg` depth 6, `_combine_noisy_or` 26, `_merge_per_source`
depth 3), `migrate.py` (`run_migrate_trace` 27, `filter_traces` depth 5,
`write_migrate_result` 16, `get_trace_metadata` depth 3), `validation.py`
(`parse_seed_workflow` 30, `parse_sample_size` depth 4, `parse_seed_cli` 19,
`validate_metric_specs` 20), and `graph_io.py` (`read_graph_or_pdg_file`
depth 3, 14).
