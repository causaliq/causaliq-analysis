# Summarising Results

The `summarise` capability statistically summarises numerical results across experiments into publication-ready metrics such as means, standard deviations etc.

This is an `aggregate` action (see [workflow patterns](https://workflow.causaliq.org/userguide/action_patterns/)) and so aggregates results in the `input` cache and produces either a single tabular output or a metrics cache.

## Parameters

| Parameter | CLI             | Required | Description |
|-----------|-----------------|----------|-------------|
| `metric`  | `-m`/`--metric` | Yes      | Columns of the table: metric specifications or derived-column formulas |
| `input`   | `-i`/`--input`  | Yes      | Files containing raw results (`.json` or `.db` cache) |
| `output`  | `-o`/`--output` | Yes      | Tabular summary in `.csv`, `.tex` or `.md` format, or a `.db` metrics cache |
| `headers` | `--header`      | No       | Column headers for the visible columns, in order |
| `format`  | `--format`      | No       | Python format specifications for `.tex` and `.md` output; `null` hides the column |
| `footer`  | `--footer`      | No       | Footer row for the visible columns in `.tex` and `.md` output |
| `significance` | -          | No       | Paired significance tests over metric column aliases |
| `caption` | -               | No       | Heading of a significance table; empty suppresses it |
| `filter`  | `-f`/`--filter` | No       | Filter entries in the input |

**Notes:**

- In workflows, `summarise` is an aggregate action: `input`, `output`, and
  `matrix` are all **required**. The matrix controls output dimensionality.
- `metric` and `input` can be repeated in the CLI for multiple columns and
  inputs, and can use YAML list syntax in actions.
- `output` may be a `.csv`, `.tex` or `.md` table, or a `.db` workflow cache
  receiving one `metrics` object per matrix combination (see
  [Metrics-cache output](#metrics-cache-output)). `headers`, `format`,
  `footer`, `significance` and `caption` apply only to tables.

### `metric`

This specifies the columns of the table. Each entry selects a field in the
entry's JSON object (`metrics` objects in an evaluation cache) together with
the statistic to compute. So, for example, specifying `equiv.shd.mean`
indicates that the capability should compute the mean of the `equiv.shd`
field in the input.

The following statistics are supported:

- `mean` - the mean value
- `sd` - the standard deviation
- `count` - the number of non-null values used to compute the other statistics
- `min` - the smallest value
- `max` - the largest value
- `median` - the median value
- `bin` - the number of values inside a half-open range (see [Binned statistics](#binned-statistics))
- `pct` - the percentage of values inside a half-open range
- `unique` - the single distinct value of a field; conflicting values are rejected

A list-valued field, such as the per-pair `exist_agree` list written by
`evaluate_graph`, contributes every numeric element to the value pool. So
`exist_agree.count` is the number of pooled pairs, `exist_agree.mean` is the
mean agreement over all of them, and `exist_agree.pct(0.5, 0.65)` is the
percentage in that bucket. A scalar field contributes one value per entry.

A specification that is a bare alias, such as `value as copy`, copies the
earlier column. This is useful when a matrix dimension selects which computed
column becomes the output, for example `{{panel}} as y`.

A bare `<field>[<source>]` column reports the single distinct value of a
field, as if by a `unique` statistic: a field holding conflicting values is
rejected rather than silently summarised.

A specification of the form `<field>.argmax.<dimension>` reports the value of
a matrix dimension for the entry holding the largest `<field>` value. For
example, `f1.argmax.llm_temperature` reports the temperature of the best run
in each group, which is useful for hyper-parameter analysis. A group with no
numeric value for the field reports an empty cell.

Append a one-based element index to report one element of a list-valued
dimension. For example, with a `fusion_weights` matrix variable declared as
`[BNSL, LLM]`, `f1.argmax.fusion_weights{1}` reports the BNSL weight of the
best run and `f1.argmax.fusion_weights{2}` reports the LLM weight. An index
past the end of the list reports an empty cell.

### Binned statistics

A binned statistic names a half-open range in parentheses:

```text
<field>.bin(lo, hi)   count of values in the bin
<field>.pct(lo, hi)   percentage of values in the bin (0-100)
```

The range includes its lower bound and excludes its upper bound
(`lo <= value < hi`). A value of exactly 0.65 therefore falls in the
`(0.65, 0.75)` bucket, matching a `>= 0.65` boundary test; use `inf` as the
upper bound for the top bucket. A percentage over no values is an empty
cell rather than a division by zero.

```yaml
metric:
  - "exist_agree.pct(0.50, 0.65) as contested"
  - "exist_agree.pct(0.65, 0.75) as low"
  - "exist_agree.pct(0.95, inf) as consensus"
```

A binned statistic must be its own column: declare it with an alias and use
the alias in a later formula. `x.bin(0.1, 0.2) / x.count` is therefore an
error, while `x.bin(0.1, 0.2) as b` followed by `b / x.count` is valid.

### Metrics-cache output

An `output` ending in `.db` writes one `metrics` object per matrix
combination instead of a table, and `plot` reads that cache directly. The
matrix values become the chart columns, so no CSV reshaping is needed:

```yaml
matrix:
  network: [asia, alarm]
  stage: [bnsl, llm, fused]
  panel: [edge_recall, orientation_accuracy]

steps:
  - uses: "causaliq-analysis"
    with:
      action: "summarise"
      input: "results/intermediate/edge-metrics.db"
      output: "results/intermediate/edge-metrics-long.db"
      metric:
        - arc_matched.unique as matched
        - arc_reversed.unique as reversed
        - edge_not_arc.unique as undirected
        - arc_missing.unique as missing
        - >
          (matched + reversed + undirected) /
          (matched + reversed + undirected + missing) as edge_recall
        - "matched / (matched + reversed + undirected) as orientation_accuracy"
        - "{{panel}} as y"
```

The cache entry is keyed `{network, stage, panel}` and holds `y` (plus the
intermediate fields). A plot then names `subplot: panel`, `group: stage`,
`x: network` and `y: y`. Because the matrix value selects the field, every
cache entry can carry several computed columns while the chart plots one.

Table presentation options (`headers`, `format`, `footer`, `significance`,
`caption`) do not apply to a metrics cache and are rejected.

### Selecting entries with `where`

In workflow actions, a base column may add a `where <predicate>` clause
before its alias. The predicate selects which entries of an input cache
contribute to that column:

```yaml
      input:
        - results/ablation-solo.db
      metric:
        - f1.mean[1] where model == 'gemini' as gemini
        - f1.mean[1] where model == 'claude' as claude
```

The predicate is evaluated against the entry's reporting view, the same view
the step-level `filter` uses, so it can name matrix dimensions and metadata
fields. This lets one variant-keyed cache supply several columns without
writing one cache per variant. A column without `where` keeps the existing
behaviour and draws on every matching entry. Only base columns accept
`where`; a formula with a `where` clause is rejected.

### Significance tests

The `significance` parameter declares paired tests over the columns defined
by `metric`. Each entry names a registered test and the two column aliases
to compare:

```yaml
      metric:
        - f1.mean[1] as bnsl
        - f1.mean[2] as llm
        - f1.mean[3] as fusion
        - max(bnsl, llm) as best_solo
      significance:
        - wilcoxon-signed-rank-2-sided(fusion, bnsl) as "Fusion vs BNSL"
        - wilcoxon-signed-rank-2-sided(fusion, llm) as "Fusion vs LLM"
        - wilcoxon-signed-rank-2-sided(fusion, best_solo) as "Fusion vs best solo"
      output: "results/fusion-significance.md"
```

The initial test is `wilcoxon-signed-rank-2-sided`, the paired Wilcoxon
signed-rank test with a two-sided alternative. Arguments must name aliases
declared by `metric`; use `as <label>` to set the comparison label. The
label is optional and defaults to `<left> vs <right>`.

A significance table has four columns:

| Column | Default header | Default format |
|--------|----------------|----------------|
| Comparison label | `Comparison` | left |
| Statistic | `W` | `.1f` |
| p-value | `p` | `.4f` |
| Significance | `Significance` | left |

`headers` and `format` apply to these four columns exactly as they do to a
metric table. `format` takes one entry per declared column, so a `null`
entry hides that column from `.tex` and `.md` output; the column remains in
CSV output. `headers` takes one entry per visible column. `footer` is not
supported on a significance table.

The default caption is `STATISTICAL TESTS (<test title>)`, which renders as
`STATISTICAL TESTS (Wilcoxon signed-rank, two-sided)`. Use `caption` to
override it, or `caption: ""` to suppress it.

Rows are paired by the workflow grouping dimensions, so one network
contributes one pair. A row missing either value is left out of that test.
A test with fewer than two non-zero differences reports empty statistic
and p-value cells.

Significance tests are a workflow action feature: the CLI writes a
single-row metric table and has no grouping, so it cannot pair rows.


### Multiple inputs

A trailing one-based source index names the input file that supplies a
column, so one table can compare metrics computed from different caches:

```yaml
steps:
  - name: "summarise fusion metrics"
    uses: "causaliq-analysis"
    with:
      action: "summarise"
      input:
        - bnsl.db
        - llm.db
        - fusion.db
      metric:
        - node_count[1] as nodes
        - f1.mean[1] as bnsl
        - f1.mean[2] as llm
        - f1.mean[3] as fusion
        - fusion - max(bnsl, llm) as gain
      output: "tables/fusion.tex"
```

A column without a source index draws on **every** input cache, which is
the original union behaviour. A column with a source index takes its values
only from that cache, so `f1.mean[2]` is the mean of the F1 values recorded
in the second input file.

The caches are joined on the grouping dimensions. A metric that names its
input cache therefore requires every entry of that cache to carry every
grouping dimension: an entry without one would otherwise contribute to
every row, so it is rejected with an error naming the cache and the
dimension.

A bare `<field>[<source>]` reports the single distinct value of a field,
which is convenient for a value that does not vary across seeds, such as
`node_count[1]` for the number of nodes in a network. A field holding
conflicting values is rejected rather than silently summarised.

### Derived columns

An entry containing an operator or a function call is a derived column: an
arithmetic expression over the **aliases** of the columns that precede it,
written in Python syntax. A trailing `as <name>` gives a column its alias:

```yaml
      metric:
        - f1.mean[1] as bnsl
        - f1.mean[2] as llm
        - f1.mean[3] as fusion
        - fusion - max(bnsl, llm) as gain
        - round(gain * 100, 1) as gain_pct
```

- Operators are `+`, `-`, `*`, `/`, unary sign and parentheses; literals
  are ordinary numbers (`0.5`, `100`).
- Functions are `abs`, `max`, `min` and `round`.
- A formula refers to a column by its alias, never by its position, so a
  number is always a number and reordering the metrics cannot change what
  a formula means.
- References are backward only, so a formula can never form a cycle.
- An empty cell propagates: arithmetic over a missing value yields an
  empty cell, while `min` and `max` ignore empty cells.

### `headers`, `format` and `footer`

These parameters shape the presentation formats (`.tex` and `.md`).
`headers` and `footer` take one entry per visible column, in column order,
starting with the grouping dimensions. `format` takes one entry per
declared column, because it is also what hides a column:

```yaml
      metric:
        - node_count[1] as nodes
        - f1.mean[1] as bnsl
        - f1.mean[2] as llm
        - f1.mean[3] as fusion
        - fusion - max(bnsl, llm) as gain
      headers: [Network, Nodes, BNSL, LLM, Fusion, "F>best"]
      format: ["", "d", ".3f", ".3f", ".3f", "+.3f"]
      footer: ["AVERAGE", "", mean, mean, mean, mean]
```

- `headers` labels the visible columns. Headers are free text and
  independent of aliases: a header may be narrative or hold markup
  (`BNSL $F_1$`), and renaming one cannot break a formula. Without
  headers, a column's label is its alias, or its specification text when
  it has none.
- `format` holds Python format specifications, validated when the step
  starts. The type character also decides the alignment (`s` left, numeric
  right, an explicit `<`, `^` or `>` overrides it).
- `footer` holds blank cells, a statistic name or literal text. A
  statistic summarises the column's row values, so the footer of a derived
  column is the mean of the derived values.

### Hidden columns

A `null` entry in `format` hides that column from the `.tex` and `.md`
output. The column is still computed, so a later derived column can use it,
and it still appears in `.csv` output for a `plot` step:

```yaml
      metric:
        - node_count[2] as nodes
        - f1.mean[2] as fusion
        - f1.max[1] as oracle
        - f1.argmax.fusion_weights{1}[1] as bnsl_weight
        - oracle - fusion
        - f1.mean[3] as bnsl
        - f1.mean[4] as llm
        - oracle - max(bnsl, llm)
      headers: [Network, Nodes, 50/50 Fusion, Oracle Fusion, Optimal Weight,
                Oracle vs 50/50, Oracle vs best]
      format: ["", "d", ".3f", ".3f", ".2f", "+.3f", null, null, "+.3f"]
      footer: [AVERAGE, "", mean, mean, "", mean, mean]
```

The table above renders seven columns: the BNSL and LLM columns are hidden,
but `oracle - max(bnsl, llm)` still uses their values. `format` keeps one
entry per **declared** column because the nulls are what hide BNSL and LLM.
`headers` and `footer` hold one entry per **visible** column, so they have
seven entries rather than nine. In `.csv` output the hidden columns remain;
they keep their default label (the alias, or the specification text when
there is none). At least one column must remain visible. The CLI cannot
express a null entry, so hidden columns are a workflow action feature.

### `input`

In the CLI, this can be a list of `.json` files containing metadata which includes the requested metrics which are all scanned and the required summarisation metrics computed. In this case, the output would contain a single summarisation metric for each value in the `metric` parameter.

In a CausalIQ Workflow the input would typically be one or more workflow caches. Because `summarise` groups entries, a workflow `matrix` definition must be present. The `matrix` definition defines the groups of variable values that a separate summary statistic will be generated for - similar to the functionality of the "group by" feature in SQL and dataframe processing.

So for example, this workflow will create the mean and standard deviation of the F1 for each combination of `network` and `sample_size`:

```yaml
matrix:
  network: [asia, cancer]
  sample_size: [100, 1K]

steps:
  - name: "Summarise metrics"
    uses: "causaliq-analysis"
    with:
      action: "summarise"
      metric: 
        - f1.mean
        - f1.sd
      input: "results/metrics.db"
      output: "results/graph_accuracy.csv"
```

### `output`

`summarise` will produce tabular output with the requested summary statistics for
each combination of matrix variable values. The above workflow wil produce tabular output like this:

| network | sample_size | f1.mean | f1.sd |
|---------|-------------|---------|-------|
| asia    | 100         | 0.55    | 0.16  |
| asia    | 1K          | 0.65    | 0.07  |
| cancer  | 100 .......... |

The output extension selects the renderer:

| Extension | Output | `format`/`footer` applied |
|-----------|--------|---------------------------|
| `.csv` | Raw table | No |
| `.tex` | LaTeX `tabular` fragment | Yes |
| `.md`, `.markdown` | Markdown table | Yes |
| `.db` | Metrics cache, one `metrics` object per matrix combination | Not applicable |

CSV output always holds raw values, because a `plot` step reads the file
numerically; formatted cells or a footer row would deform the chart. Values
which cannot be computed, for example a SD based on one value, are left
empty. `headers` renames the CSV columns too, so a `plot` step reading the
file must name the headers rather than the metric specifications.

The presentation formats are fragments rather than documents: the `.tex`
file holds a `tabular` environment, ready to be `\input` inside a paper's
own `table` float, and the `.md` file holds the bare table. LaTeX output
escapes markup characters (including `_`, `%` and `>`) and rules the table
with `\hline` after the header and before the footer; Markdown output
escapes pipes and derives its alignment row from the `format` types.

Using the fusion example above, the tables render as:

```text
Network   & Nodes &  BNSL &   LLM & Fusion & F>best \\
\hline
alarm     &    37 & 0.804 & 0.653 &  0.866 & +0.062 \\
asia      &     8 & 0.750 & 0.842 &  1.000 & +0.158 \\
\hline
AVERAGE   &       & 0.777 & 0.748 &  0.933 & +0.110 \\
```

```markdown
| Network | Nodes | BNSL | LLM | Fusion | F>best |
| :--- | ---: | ---: | ---: | ---: | ---: |
| alarm | 37 | 0.804 | 0.653 | 0.866 | +0.062 |
| asia | 8 | 0.750 | 0.842 | 1.000 | +0.158 |
| AVERAGE |  | 0.777 | 0.748 | 0.933 | +0.110 |
```

The file is rewritten from scratch on every run: each run writes a complete
table with one row per matrix combination, so repeated runs cannot duplicate
or reorder rows. When a run is given pre-scanned entries but no input cache
it cannot group, and writes a single accumulated row.

### `filter`

`filter` can be used to filter input entries on the basis of metadata values or object fields. For example, one may wish to exclude results with long execution times, or include only entries with `f1 > 0.5`.

### CLI examples

```powershell
causaliq-analysis summarise -m f1.mean -m f1.sd -i cache.db -o table.csv
causaliq-analysis summarise -m f1.mean -m f1.sd -i cache.db -o table.md `
    --header BNSL --header SD --format .3f --format .3f
```

A CLI summary holds a single row, so `headers`, `format` and `footer` take
one entry per metric, and a `.tex` or `.md` output renders that row as a
table. `-o -` still prints the summary to the terminal.

## Conditional expressions and detailed comparisons

Formulas may use Python comparisons and conditional expressions in
addition to arithmetic:

```yaml
metric:
  - "b_gem if axis == 'LLM Model' else f_llm as value"
```

The selected branch is evaluated lazily. String literals are supported, so
a missing cell can be rendered as `'---'`.

`significance_detail: true` adds paired wins, losses and the mean
difference to a significance table:

```yaml
significance:
  - wilcoxon-signed-rank-2-sided(fusion, bnsl) as "Fusion vs. BNSL"
significance_detail: true
```

The `sum` statistic is supported alongside `mean`, `sd`, `count`, `min`,
`max` and `median`. The `unique` statistic preserves text values, which
allows metadata columns such as `domain.unique` and
`source_repository.unique`.

The registered significance tests are:

- `wilcoxon-signed-rank-2-sided` — paired Wilcoxon statistic and p-value.
- `spearman-2-sided` — Spearman rank correlation and two-sided p-value.

