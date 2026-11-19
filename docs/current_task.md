# Replicating the original pdg-merge charts - continued

### `summarise`

- Added Python-style conditional expressions and comparisons in formulas:

  - `a if condition else b`
  - `==`, `!=`, `<`, `<=`, `>`, `>=`
  - string literals
  - lazy evaluation of the selected branch

- Added `significance_detail: true` for paired Wins / Losses / Mean Δ columns alongside W and p.

- Added the `spearman-2-sided` significance test.

- Added the `sum` statistic and footer support.

- Extended `unique` to preserve and render text values, enabling `domain.unique` and `source_repository.unique`.

- Updated validation, action parameters, metadata and documentation.

- Added unit tests for all new behaviour.

### `evaluate_graph`

- Added an optional `context` JSON parameter.

- Added metrics:

  - `reference_arc_count`
  - `domain`
  - `source_repository`

- `domain` and `source_repository` are returned unchanged from the context/provenance, per your instruction.

- Added context reading and unit tests.

# Possible future work out of scope for this task

- __Per-input-group weights or a "require every input" guard in `merge_graphs`.__ Currently `weights` is a flat list over every graph read from every input cache; a missing subset makes the graph count and weight count disagree. A grouped form (`0.5` per input cache, distributed within the cache) plus a skip-if-input-empty rule would remove the barley guard and make fusion steps more robust. The two-stage subset ensemble design already handles this, so it is a convenience feature.

- Use `_aggregation_entries` instead of re-reading every cache per matrix job (the `O(groups × caches)` scan on the roadmap).

- retire the now-redundant `len(entries) != 1` checks inside `evaluate_graph`/`best_graph`

- Shared `ActionMetadata` builder across `best_graph`, `summarise`, `merge_graphs`, `plot`.

- Cross-repo refresh of `causaliq-workflow/docs/architecture/cache_type_model.md`.

- Decide the fate of `validation.validate_metric_specs`: it is public API but now has no caller inside `src` after `summarise` adopted its alias-aware parser.

- Optionally, apply `header`/`format`/`footer` to the CLI terminal table (`cli/common._print_summary_table`) so it matches the file outputs.

- __Cross-repo__ — refresh `causaliq-workflow/docs/architecture/cache_type_model.md` (it still shows `result.reference` and `result.evaluated_graph`).

- __Later audit__ — shared `ActionMetadata` builder once `best_graph`, `summarise`, `merge_graphs` and `plot` adopt the same contract.
