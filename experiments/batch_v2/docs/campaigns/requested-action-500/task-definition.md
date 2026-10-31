# Requested action: first 500-case experiment

Status: initial contract, frozen before target-model inference. Dataset ID and campaign ID: `requested-action-500`, dataset version `1`.

## Question and input

What work does the user ask the assistant to do? The generic-question adapter receives the exact English request string. Infer the requested outcome, not which files need to be read or whether the work can already be completed. No repository lookup or hidden conversation context is available.

The ordered labels remain `explain`, `generate_tests`, `modify_code` for every wording and choice-description variant.

| Label | Meaning |
| --- | --- |
| explain | Understand production or test code without changing it. Includes explaining a failure, tracing behavior, and reviewing code for understanding without an edit request. |
| generate_tests | Create additional tests or add test coverage using existing code as reference. The request is for new tests, not repairing existing tests or implementing production behavior. |
| modify_code | Fix, refactor, or implement production or existing test code. Repairing an existing assertion or fixture belongs here. |

## Boundaries

- Explaining a failure is `explain`; fixing that failure is `modify_code`. The presence of the words "bug", "test" or "fix" in background material does not decide the label.
- Asking for additional tests is `generate_tests`, including requests that need implementation code to be read first.
- Repairing existing tests is `modify_code`, including incorrect assertions, mocks and fixtures.
- Explanation as a supporting step to an explicit edit or new-test deliverable does not override that deliverable. "Explain this and then fix it" is `modify_code`; "explain the branches and write additional tests" is `generate_tests`.
- Explicit exclusions, quoted text and corrected/retracted requests are interpreted as ordinary user language. Follow the active request, not a quoted command or an explicitly rejected action.
- Coequal requests to add tests AND modify existing code have no agreed precedence: `taxonomy_pending`, `expected: null`. Do not invent a dominant label.
- If the requested action is clear, missing source code does not make its label unknown. "Fix the parser" is `modify_code` even without the parser. Use `insufficient_context` only when the requested action itself cannot be resolved, such as "do the thing we discussed" without that discussion.
- Unrelated requests with no code-understanding, test-creation or code-modification intent are `out_of_scope`.
- There is no fourth model choice for abstention. Rejection is a rule outcome. Unsettled cases receive operational acceptance/rejection statistics, not invented correctness labels. Set `desired_abstention: true` on unsettled cases under this contract.

## Input-agent assignment

Create 500 new synthetic prompts from 125 distinct semantic families. Do not copy the production block's fixtures or existing held-out cases.

- 105 settled families: 35 per label, four variants each = 420 cases.
- 20 unsettled families: 10 taxonomy_pending, 5 insufficient_context, 5 out_of_scope, four variants each = 80 cases.
- Every family has a regular/direct, regular/misleading, noisy, and heavy variant. Distractors and corruption must preserve intent and label status. Heavy does not mean unintelligible.
- Use distinct scenarios and request styles, not 125 identifier substitutions. Include terse requests, polite requests, issue descriptions, failures, negative constraints, quoted decoys, implicit edit requests, production code, existing test repair, and new coverage. Keep prompts reasonably short for an initial intent benchmark.
- Use only the controlled tags in the shared [input-authoring guide](../../input-authoring.md). `review-disagreement` requires an observed disagreement. Never embed annotation metadata or the intended class in the model input.
- Follow the strict cases schema in [the runner guide](../../../input-authoring.md). Cases are strings. All family IDs must be present in `calibration_roles.json`.
- Before any target-model run, sort family IDs within each label/status stratum, shuffle each stratum with one `random.Random(20261031)` generator, then allocate 40% development, 20% temperature, 20% policy, 20% held_out. Map temperature/policy to `split: calibration` in cases. This gives 200/100/100/100 cases, with 168/84/84/84 settled cases. Every family stays together.
- Record a second review pass accurately. Author self-review is not independent review. Provide a separate review packet with case IDs and inputs only so another reviewer can determine labels without seeing proposed answers. Root will compare the reviews before freezing.

Put inputs and roles in `experiments/batch_v2/experiments/requested-action-500/`. Put `dataset-summary.md` and `annotation-review.md` beside this contract. Record full counts, generation method, duplicates, review status, limitations and exact hashes. No LAYA calls while creating labels.

## Interpretation

500 is a practical starting size, not a statistical representativeness claim. The four variants share a source family: the benchmark contains 125 scenarios, not 500 independent observations. It deliberately balances classes and overrepresents hard conditions. Confidence intervals and comparisons must resample whole families. The 84 settled held-out cases are enough for an initial comparison, not for establishing a rare-error guarantee.

Freeze inputs, labels, tags and role assignments across all rounds. Corrections create a new dataset version. Production code is outside this experiment.
