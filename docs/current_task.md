# refactor trace.py according to module and method rules

> **Status: COMPLETE (October 10, 2026).** Implemented as a `trace/` package
> (`__init__.py`, `compatibility.py`, `diffs.py`, `scores.py`, `trace.py`).
> Every `Trace` method now meets the module/method limits and
> `python scripts/check_code_rules.py --strict src/causaliq_analysis/trace`
> reports 0 breaches. All public names remain importable from
> `causaliq_analysis.trace`.


Please generate a plan to refactor @src/causaliq_analysis/trace.py following the policies defined by the files listed in @.clinerules.

> This file previously described the `workflow_action.py` and `cli.py` refactors,
> which are now complete (recorded in `docs/architecture/overview.md`, sections
> "Action Classes and Registry" and "CLI Commands and Registry", and in
> `docs/api/workflow_action.md` and `docs/api/cli.md`).
>
> The same approach is now to be applied to `trace.py`: split the module into a
> small package whose `__init__.py` re-exports the public names, keeping the
> `Trace` class and its methods thin by delegating to module-level helpers.

## Context and current breaches

`trace.py` is 1,184 lines / **342 statements** and holds the compatibility
unpickler, the `DiffType` enum and the `Trace` class. Measured with
`python scripts/check_code_rules.py`:

| Line | Object | Breach |
|------|--------|--------|
| 24 | `CompatibilityUnpickler` | — |
| 96 | `CompatibilityUnpickler.find_class` | depth 3, 9 statements |
| 124 | `load_with_compatibility` | — |
| 201 | `Trace.__init__` | depth 1, 20 statements |
| 365 | `Trace.update_scores` | depth 4, **55 statements** (over hard maximum) |
| 575 | `Trace._read_file` | depth 2, 19 statements |
| 684 | `Trace._blocked_same` | depth 4, 16 statements |
| 737 | `Trace._compare_entry` | depth 2, 21 statements |
| 862 | `Trace._merge_opposites` | depth 4, 14 statements |
| 904 | `Trace.diffs_from` | depth 4, **46 statements** (over hard maximum) |
| 1055 | `Trace._diffs_summary` | depth 3, 7 statements |
| — | module | **342 statements** (target ~200) |

Structure worth noting while extracting:

- `CompatibilityUnpickler` (with its nested `PlaceholderEnum` and `CLASS_MAPPING`)
  and `load_with_compatibility` are independent of `Trace` and can move to a
  compatibility module.
- `DiffType` and the comparison helpers (`_nums_diff`, `_blocked_same`,
  `_compare_entry`, `_update_diffs`, `_merge_opposites`, `_diffs_summary`) form a
  self-contained diff module; `diffs_from` is their orchestrator.
- `Trace.__init__` mixes argument validation, context-field validation and
  initialisation; `Trace.rename` nests a `_map` helper.
- `update_scores` and `diffs_from` are the only two over-hard-maximum methods;
  both mix orchestration with per-entry logic that can become module-level
  helpers.
- Module constants `CONTEXT_FIELDS` and the `ID_PATTERN` / `ID_ANTIPATTERN*`
  regexes are only used by the class validation paths.

## Suggested steps

1. Step 1 (Foundation): convert `trace.py` into a `trace/` package whose
   `__init__.py` re-exports `Trace`, `CompatibilityUnpickler`, `DiffType`,
   `load_with_compatibility` and `CONTEXT_FIELDS`, so
   `from causaliq_analysis.trace import ...` (used by `migrate.py` and the
   tests) and `CompatibilityUnpickler.CLASS_MAPPING`'s target
   `"causaliq_analysis.trace"` keep resolving. Keep it a pass-through so every
   existing trace test passes unchanged before any code is moved.
2. Step 2 (independent modules): move `CompatibilityUnpickler` (with its
   `PlaceholderEnum` and `CLASS_MAPPING`) and `load_with_compatibility` into
   `trace/compatibility.py`, re-exported from `__init__.py`, and verify the
   unpickler tests pass.
3. Step 3 (diff helpers): move `DiffType` and the comparison helpers
   (`_nums_diff`, `_blocked_same`, `_compare_entry`, `_update_diffs`,
   `_merge_opposites`, `_diffs_summary`) into `trace/diffs.py` as module-level
   functions; `Trace.diffs_from` becomes a thin method delegating to a
   `diffs_from(...)` helper. Flatten the moved functions to **≤15 statements
   and depth ≤2** (hard maximum 30 statements).
4. Step 4 (Trace class): keep the `Trace` class in `trace/trace.py` and split
   its over-limit methods — `__init__` (validation helper), `update_scores`
   (read/score/save helpers), `_read_file`, `_blocked_same`, `_compare_entry`,
   `_merge_opposites`, `_diffs_summary` — flattening and splitting inside the
   move so each function meets the limits.
5. Step 5 (final cleanup): reduce `trace/__init__.py` to re-exports only,
   remove any duplicated helpers, keep every module ≤~200 statements, and
   update the docs (`docs/api/trace.md`, `mkdocs.yml` nav if the structure
   changes, and `docs/architecture/overview.md`).

## Constraints learned from the `workflow_action` and `cli` refactors

- **Behaviour must stay byte-identical**: public names and signatures, error
  messages, `print` output and pickle round-trips.
- **Preserve import binding sites** — code and tests import or patch by dotted
  path:
  - `src/causaliq_analysis/migrate.py:26` does
    `from causaliq_analysis.trace import Trace`;
  - the tests import `Trace`, `CompatibilityUnpickler`, `DiffType` and
    `load_with_compatibility` from `causaliq_analysis.trace`:
    `tests/functional/test_trace.py`,
    `tests/functional/test_trace_edge_cases.py`,
    `tests/functional/test_trace_rename.py`,
    `tests/functional/test_trace_update_scores.py`,
    `tests/unit/test_trace_diffs.py`, `tests/functional/test_migrate.py`,
    `tests/unit/test_migrate.py` and
    `tests/functional/test_workflow_functional.py`;
  - `tests/functional/test_trace_edge_cases.py` monkeypatches `_nums_diff` on a
    `Trace` instance, so `_nums_diff` must remain a method invoked via `self.`;
  - `CompatibilityUnpickler.CLASS_MAPPING` maps `("learn.trace", "Trace")`,
    `("learn.trace", "CONTEXT_FIELDS")` and `("learn.trace", "DiffType")` to
    `"causaliq_analysis.trace"`, so those names must remain attributes of the
    package `__init__`.
  Re-export the public names from `trace/__init__.py` so all of the above keep
  resolving, and keep imports function-local where a test patches an external
  namespace.
- **No behaviour-free bulk test rewrites**: add focused `pytest-mock` tests
  only where coverage gaps appear; keep the existing `unittest.mock` modules as
  they are (a mock-conversion sweep is a separate task).

## Commits

Stage the work as **two commits**:

1. **Code and tests** — `src/causaliq_analysis/trace/` (or the equivalent
   structure), any small `src/` edits it depends on (e.g. `migrate.py`), and the
   test changes.
2. **Documentation** — `docs/api/trace.md`, `mkdocs.yml`, the
   `docs/architecture/overview.md` update, the `docs/roadmap.md` status, plus
   this task file.

Do not mix documentation-only changes into the code commit.

## Gates after each slice (as in `scripts/check_ci.ps1`)

`black --check src tests` · `isort --check-only src tests` ·
`flake8 src tests` · `mypy src/` ·
`python scripts/check_code_rules.py --strict src/causaliq_analysis/trace` ·
`python scripts/check_code_rules.py src/causaliq_analysis/` (advisory) ·
targeted trace tests · full suite (`python -m pytest -q`) or `check_ci.ps1` ·
docs: `python -m mkdocs build --strict` (note: CI does not build the docs).
Maintain **100 % coverage** on the new modules.

## Test surface to watch

`tests/functional/test_trace.py`,
`tests/functional/test_trace_edge_cases.py`,
`tests/functional/test_trace_rename.py`,
`tests/functional/test_trace_update_scores.py`,
`tests/unit/test_trace_diffs.py`, `tests/functional/test_migrate.py`,
`tests/unit/test_migrate.py`, `tests/functional/test_workflow_functional.py`,
plus `tests/integration/test_workflow_integration.py`.

## Suggested final structure (consider alternatives if they are better)

```
causaliq_analysis/
└── trace/
    ├── __init__.py       # public re-exports: Trace, CompatibilityUnpickler,
    │                     # DiffType, load_with_compatibility, CONTEXT_FIELDS
    ├── compatibility.py  # CompatibilityUnpickler + PlaceholderEnum + loader
    ├── diffs.py          # DiffType and the diff comparison helpers
    └── trace.py          # Trace class and context constants
```

## Remaining legacy breaches (later tasks)

After `trace.py`, the outstanding breaches are: `plot.py` (module 238;
`relplot` 61; `_convert_value` 25, `_set_axes_props` 23,
`_report_boxplot_values` 17, `plot_scatter` 27, `run_plot` 23), `metrics.py`
(`pdg_compare` 57; `_graph_to_pdg` depth 3, `bayesys_metrics` 21), `merge.py`
(`merge_graphs` 45; `_accumulate_sdg` depth 6, `_combine_noisy_or` 26,
`_merge_per_source` depth 3), `migrate.py` (`run_migrate_trace` 27,
`filter_traces` depth 5, `write_migrate_result` 16), `validation.py`
(`parse_seed_workflow` 30, `parse_sample_size` depth 4,
`validate_metric_specs` 20), and `graph_io.py` (`read_graph_or_pdg_file`
depth 3, 14).
