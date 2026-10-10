# refactor cli.py according to module and method rules

Please generate a plan to refactor @src/causaliq_analysis/cli.py following the policies defined by the files listed in @.clinerules.

> This file previously described the `workflow_action.py` refactor, which is now
> complete (recorded in `docs/architecture/overview.md`, section "Action Classes
> and Registry", and in `docs/api/workflow_action.md`).
>
> The `cli.py` refactor described below is also now **complete**: `cli.py` was
> split into the `causaliq_analysis.cli` package — the `click` group and `main`
> in `cli/__init__.py`, shared helpers in `cli/common.py`, and one module per
> command in `cli/commands/` registered through `COMMANDS`. It is recorded in
> `docs/architecture/overview.md` (section "CLI Commands and Registry") and in
> `docs/api/cli.md`. The remaining legacy breaches listed below are left for
> later tasks.

## Context and current breaches

`cli.py` is 1,288 lines / **450 statements** and holds a `click` group plus six
commands and three module-level helpers. Measured with
`python scripts/check_code_rules.py`:

| Line | Object | Breach |
|------|--------|--------|
| 18 | `cli` (click group) | — |
| 80 | `migrate_trace_cmd` | depth 2, 18 statements |
| 202 | `merge_graphs_cmd` | depth 8, **127 statements** (over hard maximum) |
| 515 | `evaluate_graph_cmd` | depth 4, **86 statements** (over hard maximum) |
| 716 | `best_graph_cmd` | depth 2, 30 statements |
| 834 | `summarise_cmd` | depth 8, **120 statements** (over hard maximum) |
| 1150 | `plot_cmd` | (re-measure; currently within limits) |
| 1200 | `_print_summary_table` | depth 1, 18 statements |
| 1234 | `_flatten_metadata` | depth 6, 13 statements |
| 1261 | `_get_nested_value` | (small) |
| — | module | **450 statements** (target ~200) |

Duplication worth removing while extracting:

- `evaluate_graph_cmd` nests its own `_read_graph_file` and `_to_cpdag`
  (~L551-600) and imports metric helpers locally.
- `summarise_cmd` defines a local `SUPPORTED_STATS` (~L874) that duplicates
  `causaliq_analysis.validation.SUPPORTED_STATS`.
- `_flatten_metadata` / `_get_nested_value` (~L1234, L1261) duplicate helpers
  that already exist in `workflow_action/helpers.py`.
- The other remaining breach in the package is
  `causaliq_analysis/__init__.py:17 _parse_version` (depth 3) — fold in if cheap.

## Suggested steps

1. Step 1 (Foundation): convert `cli.py` into a `cli/` package whose
   `__init__.py` re-exports the `click` group `cli` and `main`, so
   `causaliq_analysis.cli:main` (the `[project.scripts]` entry points) and
   `causaliq_analysis.cli.cli` (patched by tests) keep resolving. Introduce a
   shared module for cross-command helpers (option parsing, metadata
   flattening, nested-value lookup, summary table). Keep it a pass-through so
   every existing CLI test passes unchanged before any command is moved.
2. Step 2 (single command slice): extract the smallest command first
   (`migrate_trace_cmd`, then `best_graph_cmd`) into
   `cli/commands/<name>.py`, register it on the group, and verify the CLI tests
   pass.
3. Step 3 (iterative extraction): move the remaining commands one at a time —
   `plot_cmd`, `evaluate_graph_cmd`, `summarise_cmd`, and finally
   `merge_graphs_cmd` — splitting each into helpers of **≤15 statements and
   depth ≤2** (hard maximum 30 statements) and reusing existing helpers instead
   of local copies. Run the gate set after each slice.
4. Step 4 (final cleanup): reduce the package to the group plus command
   registration (module ~≤200 statements), delete duplicated helpers, and
   update the docs (`docs/api/cli.md`, `mkdocs.yml` nav if the structure
   changes, and `docs/architecture/overview.md`).

## Constraints learned from the `workflow_action` refactor

- **CLI behaviour must stay byte-identical**: command names, option names,
  help text, output formatting, exit codes and error messages.
- **Preserve import binding sites** — tests patch or import by dotted path:
  - `tests/unit/test_cli.py:40` and `tests/functional/test_cli_main.py:30`
    monkeypatch `causaliq_analysis.cli.cli`;
  - `tests/unit/test_cli.py:366` patches `causaliq_analysis.cli.WorkflowCache`,
    even though `WorkflowCache` is imported *inside* functions today (~L273,
    ~L904) — verify what that test currently exercises before moving the code;
  - `tests/unit/test_cli.py` (~L2255-2282) and
    `tests/functional/test_cli_summarise.py` (~L893-920) import
    `_get_nested_value` from `causaliq_analysis.cli`;
  - functional CLI tests monkeypatch external namespaces
    (e.g. `causaliq_core.graph.io.read_graph`,
    `causaliq_core.graph.convert.pdag_to_cpdag`).
  Keep module-level imports where a test patches the module namespace, and keep
  function-local imports where a test patches the external namespace.
- **No behaviour-free bulk test rewrites**: add focused `pytest-mock` tests
  only where coverage gaps appear; keep the existing `unittest.mock` modules as
  they are (a mock-conversion sweep is a separate task).

## Commits

Stage the work as **two commits**:

1. **Code and tests** — `src/causaliq_analysis/cli/` (or the equivalent
   structure), any small `src/` edits it depends on, and the test changes.
2. **Documentation** — `docs/api/cli.md`, `mkdocs.yml`, and the
   `docs/architecture/overview.md` update, plus this task file.

Do not mix documentation-only changes into the code commit.

## Gates after each slice (as in `scripts/check_ci.ps1`)

`black --check src tests` · `isort --check-only src tests` ·
`flake8 src tests` · `mypy src/` ·
`python scripts/check_code_rules.py --strict src/causaliq_analysis/cli` ·
`python scripts/check_code_rules.py src/causaliq_analysis/` (advisory) ·
targeted CLI tests · full suite (`python -m pytest -q`) or `check_ci.ps1` ·
docs: `python -m mkdocs build --strict` (note: CI does not build the docs).
Maintain **100 % coverage** on the new modules.

## Test surface to watch

`tests/unit/test_cli.py` (large), `tests/functional/test_cli.py`,
`tests/functional/test_cli_main.py`,
`tests/functional/test_cli_migrate_trace.py`,
`tests/functional/test_cli_merge_graphs.py`,
`tests/functional/test_cli_evaluate_graph.py`,
`tests/functional/test_cli_best_graph.py`,
`tests/functional/test_cli_summarise.py`, `tests/functional/test_cli_plot.py`,
plus `tests/integration/test_workflow_integration.py`.

## Suggested final structure (consider alternatives if they are better)

```
causaliq_analysis/
└── cli/
    ├── __init__.py          # click group `cli`, `main`, public re-exports
    ├── common.py            # shared option parsing and metadata helpers
    └── commands/
        ├── __init__.py      # registers each command on the group
        ├── migrate_trace.py # migrate-trace command
        ├── merge_graphs.py  # merge-graphs command
        ├── evaluate_graph.py# evaluate-graph command
        ├── best_graph.py    # best-graph command
        ├── summarise.py     # summarise command
        └── plot.py          # plot command
```

## Remaining legacy breaches (later tasks)

After `cli.py`, the outstanding breaches are: `trace.py` (module 342;
`update_scores` 55, `diffs_from` 46), `plot.py` (module 238; `relplot` 61),
`metrics.py` (`pdg_compare` 57), `merge.py` (`merge_graphs` 45), `migrate.py`
(`run_migrate_trace` 27), `validation.py` (`parse_seed_workflow` 30),
`graph_io.py` (`read_graph_or_pdg_file` depth 3, 14).
