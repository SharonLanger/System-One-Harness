# Mock-only token-budget unit tests

The latest user instruction replaces the former real-tokenizer/SDK fixture strategy. Unit tests must not load real tokenizer assets or import the tokenizer/MLX SDK to perform tokenization.

`tests/token_budget_support.py` supplies controlled token IDs and a mock runtime lock/encoding boundary. Tests cover rendered input and ordering, below/at/above limits, an explicitly scripted 83-token option within a 105-token request, state retention direction, marker positions, final slicing, all-question refusal, stable reports, timeout/logging behavior, configuration mutations, block propagation and caller snapshots. Hand-specified assembly expectations replace copied-SDK comparisons. These tests do not establish real-tokenizer accuracy or upstream SDK parity; actual runtime qualification is not claimed by this suite.

The copied SDK source, tokenizer/model configurations, bundled notices/licenses, prepared vocabulary, and preparation script have been removed. The test extra requires pytest only. `ExactTokenizer` remains production code because actual loaded-agent verification still calls it; it is not used by these unit tests. Production logic and experiments are unchanged by this cleanup.

Run unit tests with `python -m pytest -q tests/test_token_budget*.py`. No asset preparation or network access is required. Regression checks for this cleanup exclude experiment tests and do not launch experiments. Raw execution output is not committed; concise results are recorded in implementation-progress.md. Earlier research/verification documents are historical, not current test qualification claims.

Unpublished increment 11, experiment cleanup, runtime/hash simplification, and any main integration remain outside this cleanup. The pull request remains open and unmerged.
