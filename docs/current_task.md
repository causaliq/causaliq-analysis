# `summarise` supports hidden columns

Please devise a plan for `summarise` to be able to not display selected columns
in the .md and .tex output. My suggestion is that I can indicate this by
specifying a null as the format specifier for this column. Please feel free
to suggest alternative approaches.

An example of where I would want to do this is @causaliq-research /papers/pdg-merge/workflows/04_weighting/04_summarise-weighting-results.yml - I want to compute
`oracle - max(bnsl, llm)` as the final column but don't want to include the
llm and bnsl in the final table.

# Possible future work out of scope for this task

- Use `_aggregation_entries` instead of re-reading every cache per matrix job (the `O(groups × caches)` scan on the roadmap).

- retire the now-redundant `len(entries) != 1` checks inside `evaluate_graph`/`best_graph`

- Shared `ActionMetadata` builder across `best_graph`, `summarise`, `merge_graphs`, `plot`.

- Cross-repo refresh of `causaliq-workflow/docs/architecture/cache_type_model.md`.

- Decide the fate of `validation.validate_metric_specs`: it is public API but now has no caller inside `src` after `summarise` adopted its alias-aware parser.

- Optionally, apply `header`/`format`/`footer` to the CLI terminal table (`cli/common._print_summary_table`) so it matches the file outputs.

- __Cross-repo__ — refresh `causaliq-workflow/docs/architecture/cache_type_model.md` (it still shows `result.reference` and `result.evaluated_graph`).

- __Later audit__ — shared `ActionMetadata` builder once `best_graph`, `summarise`, `merge_graphs` and `plot` adopt the same contract.

