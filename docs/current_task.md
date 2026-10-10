# **DIAGNOSE** why some legacy analysis tests are failing

Some causaliq-analysis functionality tests are failing on  the **legacy** monolithic code base.
The causaliq packages - e.g. causaliq-analysis - are an in-progress migration from the legacy 
monolithic code base as well as introducing new functionality.

I do not check these legacy tests after each commit so I do not know when they started failing.
I suspect it _could_ be due to the work that was done to support evaluation of PDGs - DAG/PDAG 
graph evaluation was changed to use PDG evaluation at that point; but it could be some other change.
The legacy tests now largely import code from the new causaliq packages, but the tests themselves
remain on the legacy repo; they therefore provide an extra check that the migration is correct.

The legacy repo has a different Python environment from the true causaliq packages, you run the 
failing tests with the following commands:

```bash
cd ../discovery
venv311/scripts/activate
pytest -v fileio/test/test_compare.py
```

The test failure output is:

```plaintext
============ short test summary info =============
FAILED fileio/test/test_compare.py::test_core_metrics_compare_all_d7a_no_know_old - AssertionError: assert False is True
FAILED fileio/test/test_compare.py::test_core_metrics_compare_all_d7at_old - AssertionError: assert False is True
FAILED fileio/test/test_compare.py::test_core_metrics_compare_all_d8atr_old - AssertionError: assert False is True
============ 3 failed, 7 passed in 13.21s ===============
```

Could you write a plan to **diagnose why** these tests are failing. It might be that it is some legacy functionality that we no longer need to support, so the tests could be removed. Alternatively, we may need to
fix the causaliq-analysis functionality so these tests pass.