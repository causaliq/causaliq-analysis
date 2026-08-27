# Add a new `plot` action to `causaliq-analysis`

This will use matplotlib and Seaborn libraries to draw charts using information in a `.csv` file produced by the `summarise` action.

The goal of this task is to be able to *exactly replicate* the figure c:/dev/discovery/experiments/analysis/series/ord_hc_f1.png by migrating the legacy code in c:/dev/discovery/experiments/plot.py into `causaliq-analysis`, restructuring where appropriate and making `plot` available as a workflow action and CLI command.

The following parameters will be supported:

* `input`: specifies the input `.csv` file
* `output`: specifies the output chart as an image e.g. a `.png` or `.jpg` file
* `type`: type of plot required, e.g. `line`, `bar` etc. (was called 'kind' in legacy code)
* `subplot`: specifies the column name in `input` which defines the subplot - for the chart we are trying to replicate the value would be `network`
* `group`: specifies the column name in `input` which specifies how we group data points into e.g. a particular line or colour in a chart, and which is tyically shown in a legend. For the initial plot this is `series`.
* `x`: specifies the column in `input` which provides the x-axis values, `sample_size` in the initial graph
* `y`: specifies the column in `input` which provides the y-axis values, `f1.mean` in th first target chart
* `properties`: is a list of chart properties, such as title, size, colours, fonts etc. Each item in the list will be a string of the format "_<property_name>_:_<property_value>_" e.g. "legend.title.font_size:12". This allows multiple properties to be specified on the command line, or in a list in a workflow action. The property names should be based on those in the legacy plot.py module.

Create some tests input files to check that figures such as `ord_hc_f1.png` can be generated, for example

| network | series         | sample_size | f1.mean |
|---------|----------------|-------------|---------|
| asia    | BNLEARN/HC_STD | 100         | 0.14    |
| asia    | BNLEARN/HC_STD | 1000        | 0.27    |
| asia    | BNLEARN/HC_OPT | 100         | 0.25    |
| asia    | BNLEARN/HC_OPT | 1000        | 0.48    |
| sports  | BNLEARN/HC_STD | 100         | 0.07    |
| .....   |                |             |         |

Tests should include checking that the output image file exactly replicates a reference image file.