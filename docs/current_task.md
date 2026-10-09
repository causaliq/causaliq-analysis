# refactor workflow_acction.py according to module and method rules

Please generate a plan to refactor @src/causaliq_analysis/workflow_action/ following the policies defined by the files listed in @.clinerules.

Suggested steps are:
  1. Step 1 (Infrastructure Foundation): Create the workflow_action/ directory, set up types.py, helpers.py, and actions/base.py. Have __init__.py act as a pass-through so all existing tests pass unchanged.

  2. Step 2 (Single Action Slice): Extract the simplest action (e.g., plot.py or summarise.py) into actions/. Wire it up, update its specific test module, and verify pytest passes.

  1. Step 3 (Iterative Extraction): Migrate the remaining actions one by one (migrate_trace.py, evaluate_graph.py, etc.), verifying green test builds after each.

  1. Step 4 (Final Cleanup & Removal): Delete the old monolithic workflow_action.py once the package __init__.py fully replaces its public interface.  

A suggested **final** refactor structure might be (but consider alternatives if you
feel they might be better):
```
causaliq_analysis/
└── workflow_action/
    ├── __init__.py            # Provider class & public API re-exports
    ├── types.py               # Stub/Type-checking imports & shared data structures
    ├── helpers.py             # Cache parsing, metadata flattening, graph extraction
    └── actions/
        ├── __init__.py        # Registry mapping action names to action classes
        ├── base.py            # Abstract Base Action (validate & run contracts)
        ├── migrate_trace.py   # MigrateTraceAction (validate & run)
        ├── merge_graphs.py    # MergeGraphsAction (validate & run)
        ├── evaluate_graph.py  # EvaluateGraphAction (validate & run)
        ├── best_graph.py      # BestGraphAction (validate & run)
        ├── summarise.py       # SummariseAction (validate & run)
        └── plot.py            # PlotAction (validate & run)
```

## Status: complete

Steps 1-4 are done; the legacy monolith no longer exists and the package fully
replaces its public interface.

- `workflow_action/__init__.py` is now a thin provider: **40 statements**
  (down from 605) holding the parameter tables, `validate_parameters`,
  `run`/`_execute` and the public re-exports — no action logic.
- Seven action classes in `workflow_action/actions/`: `plot`,
  `migrate_trace`, `best_graph`, `evaluate_graph`, `merge_graphs`,
  `summarise`, plus the `AnalysisAction` base contract, all registered in
  `ACTION_CLASSES`.
- Shared infrastructure: `types.py` (31 statements) and `helpers.py`
  (195 statements — frozen close to the module limit).
- Code rules: `python scripts/check_code_rules.py` reports **0 breaches** for
  the whole `workflow_action` package in both advisory and `--strict` mode.
- Tests: full suite green (919 passed) with **100 % coverage** on every
  package module.

The remaining code-rule breaches in the repository are legacy CLI/core code
(`cli.py`, `trace.py`, `plot.py`, `merge.py`, `metrics.py`,
`validation.py`) and are candidates for a follow-on refactor, starting with
`cli.py`.