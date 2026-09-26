# Support a new `edge` metric

Support new values `edge` and `equiv.edge` for the `metric` parameter of the 
`evaluate_graph` action of `causaliq-analysis`.

These will work the same way as existing metrics such as `f1` and `shd` metrics
but will output the nine edge metrics defined in lines 70 to 80 of pdag_compare 
method in @causaliq-analytics/metrics.py plus 'missing_matched' defined on line
110 of that function.

Analagously to f1 and equiv.f1, equiv.edge will convert
the graphs being compared to CPDAGs before the comparison is made.