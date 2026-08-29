# Plotting Results

The `plot` capability draws charts using matplotlib and Seaborn from
information in a `.csv` file produced by the `summarise` action. It is a
`nocaches` action which operates directly on plain files: it reads a CSV
file and produces a publication-ready image file such as a `.png` or
`.jpg`, without using workflow caches or the workflow matrix. Such
actions run once per workflow regardless of any matrix definition.

The plotting code is migrated from the legacy `experiments/plot.py`
module in the `causaliq-discovery` repository, so figures such as the
variable-ordering CPDAG F1 chart can be replicated exactly.

## Parameters

| Parameter    | CLI      | Required | Description |
|--------------|----------|----------|-------------|
| `input`      | `-i`/`--input` | Yes | Input `.csv` file produced by `summarise` |
| `output`     | `-o`/`--output` | Yes | Output chart file, e.g. a `.png` or `.jpg` image |
| `type`       | `--type` | No | Type of plot required: `line`, `regression`, `histogram`, `box`, `violin`, `bar` or `scatter` (default `line`) |
| `subplot`    | `--subplot` | Yes | Column name which defines the subplot, e.g. `network` |
| `group`      | `--group` | Yes | Column name which defines the legend groups, e.g. `series` |
| `x`          | `-x`/`--x` | Yes | Column name which provides the x-axis values, e.g. `sample_size` |
| `y`          | `-y`/`--y` | Yes | Column name which provides the y-axis values, e.g. `f1.mean` |
| `property`   | `-p`/`--property` | No | Chart property in `name=value` format with a Python literal value, repeatable |

## Input

The input file is a `.csv` produced by the `summarise` action with one row
per subplot, x-value and group combination. For example:

| network | series         | sample_size | f1.mean |
|---------|----------------|-------------|---------|
| asia    | BNLEARN/HC_STD | 100         | 0.14    |
| asia    | BNLEARN/HC_STD | 1000        | 0.27    |
| asia    | BNLEARN/HC_OPT | 100         | 0.25    |
| sports  | BNLEARN/HC_OPT | 1000        | 0.48    |

## CLI Example

This command replicates the `ord_hc_f1` figure with one subplot per
network, a line per series, a log-scale x-axis and the publication fonts:

```bash
causaliq-analysis plot -i results/summary.csv -o figures/ord_hc_f1.png \
    --type line --subplot network --group series \
    --x sample_size --y f1.mean \
    -p "figure.title=" \
    -p "subplot.aspect=1.05" \
    -p "figure.subplots_left=0.04" \
    -p "figure.subplots_right=0.86" \
    -p "figure.subplots_top=0.98" \
    -p "figure.subplots_hspace=0.22" \
    -p "subplot.grid=True" \
    -p "subplot.grid_colour=lightgray" \
    -p "subplot.background=white" \
    -p "xaxis.scale=log" \
    -p "xaxis.label=Sample size" \
    -p "yaxis.label=F1 (CPDAG)" \
    -p "legend.title=variable ordering" \
    -p "palette=['#66bd63','#d73027','#000000']"
```

## Workflow Example

```yaml
steps:
  - name: "Plot CPDAG F1"
    uses: "causaliq-analysis"
    with:
      action: "plot"
      input: "results/graph_accuracy.csv"
      output: "figures/ord_hc_f1.png"
      type: "line"
      subplot: "network"
      group: "series"
      x: "sample_size"
      y: "f1.mean"
      properties:
        - "xaxis.label=Sample size"
        - "yaxis.label=F1 (CPDAG)"
```

## Properties

Properties use the names from the legacy plotting module. Each property
is a string of the form `<name>=<value>` where `<value>` is written in
Python literal syntax, so the full range of Python types can be
specified:

- `int.property=22` sets the integer `22`
- `float.property=0.23` sets the float `0.23`
- `string.property='string value'` sets the string `string value`
- `tuple.property=(2, 'dad')` sets the tuple `(2, 'dad')`
- `list.property=['a', 1, 2.3]` sets the list `['a', 1, 2.3]`
- `dict.property={'key1': 1, 'key2': 'me'}` sets a dict
- `set.property={1, 'two'}` sets the set `{1, 'two'}`
- `bool.property=True` sets `True`, and `none.property=None` sets
  `None`

Values which are not valid Python literals (e.g. `lightgray` or
`Sample size`) are treated as plain strings, and a blank value (e.g.
`figure.title=`) sets an empty string. The `¬` character sets `None`.
Strings may also be quoted: `figure.title='Test Figure'` is equivalent
to `figure.title=Test Figure`.

> **YAML note**: a dict value contains `: ` (colon-space), which ends a
> YAML plain scalar, so dict properties must be double-quoted in the
> workflow file, e.g. `- "dict.property={'key1': 1, 'key2': 'me'}"`.

Supported property names include:

- Figure: `figure.title`, `figure.title_fontsize`, `figure.dpi`,
  `figure.per_row`, `figure.background`
- Subplot: `subplot.kind`, `subplot.aspect`, `subplot.title`,
  `subplot.title_fontsize`, `subplot.axes_fontsize`, `subplot.background`,
  `subplot.grid`, `subplot.grid_colour`
- Axes: `xaxis.label`, `xaxis.range`, `xaxis.scale`, `xaxis.ticks`,
  `xaxis.ticks_fontsize`, `xaxis.shared`, `yaxis.label`, `yaxis.range`,
  `yaxis.scale`, `yaxis.ticks`, `yaxis.ticks_fontsize`, `yaxis.shared`
- Figure layout: `figure.subplots_top`, `figure.subplots_left`,
  `figure.subplots_right`, `figure.subplots_bottom`,
  `figure.subplots_hspace`, `figure.subplots_wspace`
- Legend: `legend.title`, `legend.title_fontsize`, `legend.fontsize`,
  `legend.labels`, `legend.outside`, `legend.key`, `legend.loc`,
  `legend.ncol`
- Lines: `line.sizes`, `line.dashes`
- Other: `palette`, `violin.scale`, `violin.width`
