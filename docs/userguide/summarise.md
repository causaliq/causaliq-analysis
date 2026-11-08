# Summarising Results

The `summarise` capability statistically summarises numerical results across experiments into publication-ready metrics such as means, standard deviations etc.

This is an `aggregate` action (see [workflow patterns](https://workflow.causaliq.org/userguide/action_patterns/)) and so aggregates results in the `input` cache and produces a single tabular output.

## Parameters

| Parameter | CLI             | Required | Description |
|-----------|-----------------|----------|-------------|
| `metric`  | `-m`/`--metric` | Yes      | Columns of the table: metric specifications or derived-column formulas |
| `input`   | `-i`/`--input`  | Yes      | Files containing raw results (`.json` or `.db` cache) |
| `output`  | `-o`/`--output` | Yes      | Tabular summary in `.csv`, `.tex` or `.md` format |
| `headers` | `--header`      | No       | Column headers, in column order |
| `format`  | `--format`      | No       | Python format specifications for `.tex` and `.md` output |
| `footer`  | `--footer`      | No       | Footer row for `.tex` and `.md` output |
| `filter`  | `-f`/`--filter` | No       | Filter entries in the input |

**Notes:**

- In workflows, `summarise` is an aggregate action: `input`, `output`, and
  `matrix` are all **required**. The matrix controls output dimensionality.
- `metric` and `input` can be repeated in the CLI for multiple columns and
  inputs, and can use YAML list syntax in actions.
- `output` can only have a single value, which must be a `.csv`, `.tex` or
  `.md` file in both the CLI and the action.
- `headers`, `format` and `footer` each take one entry per table column:
  the grouping dimensions first, then one entry per metric.

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

A bare `<field>[<source>]` column reports the single distinct value of a
field, as if by a `unique` statistic: a field holding conflicting values is
rejected rather than silently summarised.

A specification of the form `<field>.argmax.<dimension>` reports the value of
a matrix dimension for the entry holding the largest `<field>` value. For
example, `f1.argmax.llm_temperature` reports the temperature of the best run
in each group, which is useful for hyper-parameter analysis. A group with no
numeric value for the field reports an empty cell.

Significance testing is not yet available.

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

These parameters shape the presentation formats (`.tex` and `.md`). Each
takes one entry per table column, in column order, starting with the
grouping dimensions:

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

- `headers` labels the columns. Headers are free text and independent of
  aliases: a header may be narrative or hold markup (`BNSL $F_1$`), and
  renaming one cannot break a formula. Without headers, a column's label
  is its alias, or its specification text when it has none.
- `format` holds Python format specifications, validated when the step
  starts. The type character also decides the alignment (`s` left, numeric
  right, an explicit `<`, `^` or `>` overrides it).
- `footer` holds blank cells, a statistic name or literal text. A
  statistic summarises the column's row values, so the footer of a derived
  column is the mean of the derived values.

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

