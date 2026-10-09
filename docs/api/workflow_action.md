# Workflow Action

Workflow action interface for causaliq-workflow. A thin provider validates the
action and its parameters, then delegates to the action class registered in
`ACTION_CLASSES`; each action is a small class with its own `validate` and
`run` methods.

## Provider

::: causaliq_analysis.workflow_action
    options:
        show_root_heading: true
        show_source: false
        heading_level: 3
        inherited_members: false
        show_inheritance_diagram: false

## Action registry

::: causaliq_analysis.workflow_action.actions
    options:
        show_root_heading: true
        show_source: false
        heading_level: 3

## Base contract

::: causaliq_analysis.workflow_action.actions.base
    options:
        show_root_heading: true
        show_source: false
        heading_level: 3

## Action classes

- [Migrate Trace](workflow_action/migrate_trace.md)
- [Merge Graphs](workflow_action/merge_graphs.md)
- [Evaluate Graph](workflow_action/evaluate_graph.md)
- [Best Graph](workflow_action/best_graph.md)
- [Summarise](workflow_action/summarise.md)
- [Plot](workflow_action/plot.md)

## Shared types and helpers

`causaliq_analysis.workflow_action.helpers` holds the internal cache parsing,
metadata flattening and graph-extraction helpers shared by the action classes.
They are implementation details; the public API is the action classes listed
above.

`causaliq_analysis.workflow_action.types` re-exports the workflow types
(`ActionPattern`, `ActionResult`, `ActionValidationError`, and friends) from
`causaliq_core`, with minimal fallback stubs used when `causaliq-workflow` is
not installed.
