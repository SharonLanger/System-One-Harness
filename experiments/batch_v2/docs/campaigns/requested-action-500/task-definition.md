# Requested action: version 2 contract

Dataset `requested-action-500`, version `2`; campaign/results ID `requested-action-500-v2`.

Identify the requested action from the prompt alone. Every question uses these ordered labels:

| Label | Meaning |
| --- | --- |
| explain | Understand or explain existing production/test code without changing it. |
| generate_tests | Create additional tests or coverage. |
| modify_code | Fix, refactor or implement production code, or repair existing tests. |
| unclear | Cannot select one supported action: missing intent, competing actions with no primary action, or none of the other choices fits. Non-actionable. |

Classify the active request, not quoted or cancelled instructions. Explaining a failure is explain; fixing it is modify_code. Repairing existing assertions, mocks or fixtures is modify_code. Explanation supporting an explicit edit or additional-test deliverable does not override that deliverable. Missing source code or a filename alone does not make a clear requested action unclear.

When code modification and additional tests are both requested as deliverables without a single primary action, choose unclear. We do not introduce a modification-over-tests precedence. Unrelated requests also map to unclear; there is no other class.

Unclear is an actual model choice and a scored expected label. `undecided` is reserved for rejection by the confidence rule. An accepted unclear response and a rejected response both mean non-actionable for the proposed flow, but their metrics must remain separate. This experiment does not change production routing.

All 500 current labels are settled under this definition: 420 retain their action label and 80 previously unsettled prompts now expect unclear. Settled describes the annotation decision, not the clarity of the prompt. The obsolete desired_abstention flags are removed: correctly accepting unclear must count as a correct classification.

Keep all 500 prompt strings, IDs, order, noise levels, tags, source families and roles unchanged for this version. The split is 200 development, 100 temperature, 100 policy and 100 held-out. Family variants stay together. Any later correction requires another dataset version, with its reason and before/after evidence.

The original author/self-review and blind review are recorded in annotation-review.md and its version-1 ledger. The version-2 migration review is recorded separately in unclear-v2.md and unclear-v2-label-changes.json; do not claim a second blinded review or live-model accuracy.
