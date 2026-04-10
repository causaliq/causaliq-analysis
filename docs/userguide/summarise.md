# Summarising Results

The `summarise` capability statistically summarise numerical results across experiments into publication-ready metrics such as means, standard deviations etc.

This is an `aggregate` action (see [workflow patterns](https://workflow.causaliq.org/userguide/action_patterns/)) and so aggregates results in the `input` cache and produces a single tabular output.

## Parameters

| Parameter   | CLI             | Required | Description |
|-------------|-----------------|----------|-------------|
| `metric`    | `-m`/`--metric` | Yes      | List of summary metrics required, e.g. mean, standard deviation etc. |
| `input`     | `-i`/`--input`  | Yes      | List of files containing raw results (`.json` or `.db` cache). |
| `output`    | `-o`/`--output` | Yes      | Tabular summary in .csv format (see below) |
| `filter`    | —               | No       | filter entries in input |

**Notes:**

- In workflows, `summarise` is an aggregation action: `input`, `output`, and
  `matrix` are all **required**. The matrix controls output dimensionality.
- `-metric` and `-input` can be repeated in CLI for multiple metrics and inputs, and can use YAML list syntax in actions
- `-output` can only have a single value which must be a CSV file in both the CLI and action

### `metric`

This specifies a list of metrics that are to be summarised. The values specifed follow the metadata variable naming convention and so define both the variable to be summarised and the summary statistic to be computed. So, for example, specifying `equiv.shd.mean` indicates that the capability should compute the mean of the `equiv.shd` variables in the input.

The following summary statistics will be supported initially:

- `mean` - the mean value
- `sd` - the standard deviation
- `count` - the number of non-null values used to compute the other statistics

It is likely this will be extended to include other statistics such as mode, interquartile range, max etc. as well as significance statistics.

### `input`

In the CLI, this can be a list of `.json` files containing metadata which includes the requested metrics which are all scanned and the required summarisation metrics computed. In this case, the output would contain a single summarisation metric for each value in the `metric` parameter.

In a CausalIQ Workflow the input would typically be one or more workflow caches. The presence of an action with both an `input` and `output` parameter means that a workflow `matrix` definition must be present. The `matrix` definition defines the groups of variable values that a separate sumary statistic will be generated for - similar to the functionality of the "group by" feature in SQL and dataframe processing.

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
      input: "results/graphs.db"
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

Summary output like this is quite small and human-readable so it would be output as a CSV file. Values which cannot be computed, for example a SD based on just two values, will be displayed as None. This output file would often be used as input for a CausalIQ Analysis `table` or `plot` capability which will produce publication-ready LaTeX tables or charts respectively.

### `filter`

`filter` can be used to filter out some input entries on the basis of metadata values. For example, one may wish to exclude results with long execution times.

