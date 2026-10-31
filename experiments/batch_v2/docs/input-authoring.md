# LAYA input-authoring agent handoff

Date: 2026-10-31
Status: instructions for a future author/reviewer; no agent has been launched and no case list is included.

Use with the [workflow blueprint](workflow.md) and the completed task-definition document from [the template](templates/task-definition.md). Schema reference: [RV2 input-authoring guide](../input-authoring.md).

## 1. Your assignment

Create a fixed, diverse labeled dataset for one classification use case. It will be evaluated through the generic-question adapter before a production building block is selected or designed. Author prompts whose intended answer follows the task contract; do not claim that LAYA will necessarily produce that answer.

Expected means the reviewed correct class, not a prediction, confidence, or acceptance threshold. You do not assign model probabilities or tune acceptance rules. Noise is an enum describing textual condition, not a numeric model threshold.

Use the exact task contract, canonical labels and boundary policies from the campaign's task-definition.md. Examples of label sets from earlier work, not a restriction on new experiments:
- Requested action: explain, generate_tests, modify_code.
- Context scope: method_only, called_methods, calling_methods, both_directions.

Those lists are orientation only. Read the campaign task contract before interpreting mixed requests, tests versus test repair, relationships or missing context. Do not invent a policy merely to fill a quota.

Prepare independent datasets if assigned different classification tasks. Different tasks have different expected labels; do not force their case lists to be identical.

## 2. Input schema

Each case contains:
- id: stable lowercase identifier.
- input: the exact nonblank string accepted by generic-question; no expected answer or annotation embedded.
- expected: one canonical label for settled cases, otherwise null.
- label_status: settled, taxonomy_pending, insufficient_context or out_of_scope.
- noise_level: regular, noisy, heavy or unspecified.
- tags: unique lowercase strings, possibly empty.
- source_family_id: required by this campaign, linking every paraphrase/corruption derived from one semantic scenario.
- split: development, calibration or held_out.
- notes: review rationale and any ambiguity.
- desired_abstention: optional boolean when the task contract explicitly calls for rejection.

For generic experiments, never pass the existing block adapters' object shapes as input. If prior action or other context is part of the question, include it through the exact rendering contract defined in task-definition.md. Keep that rendered text unchanged across variants. Block adapters are reserved for later integration parity checks. Do not add code, relationships or context absent from the task contract just to make an answer easy.

The schema vocabulary is already decided. These fields are independent: a regular input can be misleading; a heavy-noise input can still have settled ground truth.

## 3. Controlled tags

Use these exact tags when applicable:
- simple
- misleading
- negation
- mixed-intent
- missing-context
- typos
- irrelevant-text
- boundary-case
- reviewer-challenging
- review-disagreement

reviewer-challenging is an author judgment that careful reasoning is needed. review-disagreement means disagreement was actually observed during independent review; record the alternatives and resolution. Do not write "Claude cannot solve this" without a recorded evaluation supporting that statement.

Do not retag inputs based on the target LAYA experiment's mistakes. Any later failure-derived grouping belongs in a separate analysis annotation, not the frozen input metadata.

Use English prompts initially. Realistic TypeScript identifiers and paths may appear when the task supports them; language tags are unnecessary for an English-only campaign.

Noise meanings:
- regular: no deliberate corruption; distractors can still be grammatical and misleading.
- noisy: moderate typos, formatting issues or distracting text with recoverable intent.
- heavy: substantial corruption/distraction, still recoverable for a settled label.
- unspecified: missing annotation. Resolve these before the research dataset is accepted.

If corruption removes the facts needed to answer, mark insufficient_context rather than preserving a guessed label.

## 4. Starting dataset specification

Engineering starting target for a three- or four-class use case: 1,200 cases, based on 300 source families. This is an exploratory benchmark size, not a statistical guarantee. For another label count, choose an explicitly recorded family count divisible by the number of labels and split allocation; preserve the protocol rather than forcing these example counts.

Settled pool:
- 240 independent semantic families, four meaning-preserving variants each: 960 cases.
- Balance semantic families across labels: 80 per label for the three-class task; 60 per label for the four-class task.
- Four variants: regular/direct; regular/misleading; noisy; heavy.
- Add applicable tags, including negation and mixed-intent where the contract resolves the answer.
- Cover every relevant decision boundary, not just repeated changes of method names.

Unsettled pool:
- 60 independent semantic families, four variants each: 240 cases.
- 20 families for each of taxonomy_pending, insufficient_context and out_of_scope.
- expected=null for every such case.
- Vary wording/noise without accidentally resolving the missing information or changing status.
- Keep behavior goals separate from correctness. desired_abstention is set only when justified.

If a task has no legitimate examples of one unsettled status, report that fact and reallocate before freezing; never manufacture ambiguity contrary to a clear contract. If a proposed corruption changes meaning, revise or reclassify it and replace the lost settled example before freeze. Do not add semantically empty filler merely to hit 1,200.

The design intentionally overrepresents hard conditions. Its overall accuracy and calibration describe this benchmark, not an estimated production frequency. Provide separate clean/noise/tag reports; do not call the mixture representative traffic.

## 5. Fixed source-family splits

Assign complete families, never individual paraphrases:
- Development: 40%.
- Temperature calibration: 20%.
- Policy calibration: 20%.
- Held-out: 20%.

Use the same proportions within each settled label and unsettled status. With the starting target, this means 120/60/60/60 families and 480/240/240/240 cases across the four roles.

In cases.json, both calibration roles use split=calibration because that is the current RV2 enum. In calibration_roles.json, map each calibration source_family_id to temperature or policy. Do not add a new role field to cases.json.

Freeze deterministic assignment before running LAYA. For reproducibility, sort family IDs, use recorded seed 20261031 to shuffle within each label/status stratum, then allocate the declared counts. Generation seed, if the generation system supports one, is separate; do not pretend an LLM used a seed it cannot enforce.

All tuning rounds receive the same case file. Family-role assignments and text remain unchanged. Held-out labels are available to the final evaluator, not to question/temperature/rule selection.

## 6. Authoring and review procedure

1. Read the task contract and enumerate each class boundary and priority rule.
2. Draft independent semantic scenarios across realistic user intents.
3. Decide expected/status from the contract before adding noise. Record the governing rule in notes.
4. Create variants. Check that misleading cues are background and do not actually reverse the request.
5. Have a second review pass determine label/status from input and contract without seeing the proposed answer first. Record reviewer identity/model and whether the review was independent.
6. Compare reviews. Resolve disagreements with the contract and evidence. Mark review-disagreement only when observed.
7. If the contract cannot resolve a disagreement, use taxonomy_pending with expected=null; missing facts mean insufficient_context. A reviewer mistake does not make a settled input ambiguous.
8. Check exact/near duplicates. Reworded copies remain one source family, not new independent families. Link counterfactual variants derived from the same scenario to the same family; if this changes label-stratification counts, preserve family integrity over exact quotas.
9. Validate schema, class counts, noise/tag counts, family counts and role assignments.
10. Freeze dataset version, hashes and review report. Later corrections create a new dataset version; never change old experiment evidence.

Independent review can be another model/reviewer. Agreement is useful evidence, not automatic proof of correctness. If the only available review is a second pass by the author, label it self-review and keep independent review as an outstanding task before final benchmark acceptance.

Do not run or inspect target LAYA predictions while assigning expected labels. Do not adjust labels or difficulty tags to improve reported accuracy.

## 7. Required deliverables

- cases.json: complete runner-valid inputs and annotations.
- calibration_roles.json: fixed temperature/policy family assignments.
- annotation-review.md: task boundaries, review process, observed disagreements, unresolved issues and exclusions.
- dataset-summary.md: class/status/noise/tag distributions, family and role counts, duplicate checks and exact dataset hash.

No suite settings, calibrated thresholds or probability targets belong in these deliverables. The experiment designer supplies question/rule/configuration arrays separately.

Validation must confirm:
- Every settled expected value is canonical; every unsettled expected is null.
- No metadata is inserted into input.
- Every case has an explicit noise level and consistent tags.
- Every family remains in one role.
- Every canonical label appears in every settled role.
- Expected label stays invariant across equivalent question variants.
- No unresolved reviewer disagreement is disguised as settled ground truth.
- Dataset count deviations have written reasons rather than hidden filler.

Handoff ends with counts, review status and the exact files. It does not claim LAYA accuracy, prove a model will answer as expected or authorize production changes.

## Storage and handoff

Follow [records-and-handoffs.md](records-and-handoffs.md). Store the fixed cases and role map under experiments/batch_v2/experiments/<campaign-id>/; store review and distribution notes under docs/campaigns/<campaign-id>/. Commit the accepted dataset and notes together before a real run. Link exact paths, dataset version/hash and source commit in the campaign README. Do not create a first-run result entry before a run exists.
