# Replicate pdg-merge analysis charts

### `evaluate_graph`

- `reference` is now __optional__: without it the action describes the graph, writing list-valued `exist_agree` / `dir_agree` metrics (with `present_threshold` and `direction_threshold`, default 0.0).
- New `threshold` parameter: both graphs are reduced to deterministic edge states (`p_exist < t → none`, dominant direction otherwise) before comparison, so `metric: [edge]` returns integer counts.
- New `causaliq_analysis/edge_analysis.py` with `threshold_graph`, `pdg_edge_agreement`, and a public `graph_to_pdg` wrapper in `metrics.py`.
- Provider metadata (`workflow_action/__init__.py`) documents the new parameters and description metrics.
- No new derived metric names: `edge_recall` / `orientation_accuracy` are workflow formulas over the ten counts.

### `summarise`

- __`.db` output__: writes one `metrics` object per matrix combination; `plot` reads it directly, so no CSV reshaping is needed. Table outputs are unchanged; table-only options are rejected with a `.db` path.
- __List-valued fields__ are flattened into the value pool: `count` is the pooled value count, `mean`/`median`/… operate over the pool.
- __`bin(lo, hi)` / `pct(lo, hi)`__: half-open lower-inclusive ranges, `inf` allowed for the top bucket; empty pools give empty cells.
- __Bare alias references__ (`"{{panel}} as y"`) copy a preceding column, letting a matrix dimension select which computed column becomes the plot's `y`.

### `plot`

- `scatter.connect=True` draws connectors between the two hue groups at each x (scatter no longer adds a regression line).
- Bar charts now honour `palette` and `legend.outside`.
- `legend.loc` moves the existing legend in place (no duplicate legend).
- Fixed a latent bug where applying `xaxis.ticks_rotation` blanked categorical tick labels.



# Possible future work out of scope for this task

- the `evaluate_graph` → `analyse_graph` rename and the wider cache consolidation remain separate tasks, as agreed.

- __Per-input-group weights or a "require every input" guard in `merge_graphs`.__ Currently `weights` is a flat list over every graph read from every input cache; a missing subset makes the graph count and weight count disagree. A grouped form (`0.5` per input cache, distributed within the cache) plus a skip-if-input-empty rule would remove the barley guard and make fusion steps more robust. The two-stage subset ensemble design already handles this, so it is a convenience feature.

- Use `_aggregation_entries` instead of re-reading every cache per matrix job (the `O(groups × caches)` scan on the roadmap).

- retire the now-redundant `len(entries) != 1` checks inside `evaluate_graph`/`best_graph`

- Shared `ActionMetadata` builder across `best_graph`, `summarise`, `merge_graphs`, `plot`.

- Cross-repo refresh of `causaliq-workflow/docs/architecture/cache_type_model.md`.

- Decide the fate of `validation.validate_metric_specs`: it is public API but now has no caller inside `src` after `summarise` adopted its alias-aware parser.

- Optionally, apply `header`/`format`/`footer` to the CLI terminal table (`cli/common._print_summary_table`) so it matches the file outputs.

- __Cross-repo__ — refresh `causaliq-workflow/docs/architecture/cache_type_model.md` (it still shows `result.reference` and `result.evaluated_graph`).

- __Later audit__ — shared `ActionMetadata` builder once `best_graph`, `summarise`, `merge_graphs` and `plot` adopt the same contract.

