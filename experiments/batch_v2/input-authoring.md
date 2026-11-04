# Authoring RV2 experiment inputs

Status: RV2 input schema and authoring instructions, aligned with the runner design (historical material; see docs/cleanup-local-files.md). See [README](README.md) for commands and verification (historical material; see docs/cleanup-local-files.md) for tested behavior and remaining live/browser checks.

## 1. Define the classification task first

Write down the task, one question type and the canonical label meanings. Decide how to handle mixed requests and inputs outside the supported task before labeling cases. Keep those meanings constant across all question variants. A question rephrasing must not change the correct label for an input.

The generic example below classifies whether text identifies an edible fruit or anything else. Labels are `fruit` and `other`, in that order. Apple-the-company is a settled `other` example. It is not an out-of-scope case because the task explicitly defines a catch-all label.

## 2. Who assigns label_status, and who uses it?

The dataset author or reviewer assigns `expected` and `label_status` before running the experiment. An LLM can draft or independently review annotations, but its answer is not automatically the truth. Review disagreements using the task definition and available evidence. The RV2 collector uses the status to decide whether correctness can be scored; the classifier never receives it.

`settled` means the expected answer is agreed under the task's definition. It does not mean the input is easy, and it does not mean Claude, LAYA or another model will always answer correctly. A difficult, noisy or misleading input can still be settled. If a model makes a mistake, keep the agreed label; do not retrospectively relabel the case as uncertain just because it was missed.

| Status | Plain meaning | expected | Accuracy treatment |
| --- | --- | --- | --- |
| `settled` | We have an agreed expected class | One canonical label | Eligible for correctness scoring when execution/evidence is valid |
| `taxonomy_pending` | The class definitions or priority between classes do not yet resolve this input | null | Run and report behavior; exclude from correctness metrics |
| `insufficient_context` | Required facts are missing from the input | null | Run and report behavior; exclude from correctness metrics |
| `out_of_scope` | The input is outside the defined task and has no valid class under its policy | null | Run and report behavior; exclude from correctness metrics |

"Taxonomy" simply means the set of classes and their definitions. For an action-classification experiment, "explain this and fix it" could be taxonomy_pending if no mixed-action priority exists. Once a clear policy resolves it, it may become settled. "Do the same thing as before" may have insufficient_context when the previous request is absent. A weather question may be out_of_scope for a code-action task that defines no fallback class.

Model disagreement is a review signal, not a separate ground-truth status. If evidence resolves the disagreement, retain settled. If the task's labels are genuinely ambiguous, use taxonomy_pending and explain why in `notes`. You may add a `review-disagreement` tag only when such disagreement was actually observed during annotation review; this is independent of noise level and is not a difficulty score.

If the task deliberately defines an `other` or `unknown` class with a valid expected answer, use settled plus that class. Do not turn ordinary negative examples into out_of_scope cases. `expected: null` is not a request for the model to output JSON null, and `undecided` is normally a rule-rejection outcome rather than an expected class. Use optional `desired_abstention: true` to separately annotate behavior you want for unanswerable cases; the initial report still reports their observed acceptance/abstention without inventing correctness labels.

## 3. Add noise levels and tags

Each case gets exactly one `noise_level`:

- `regular`: no deliberate textual corruption or distracting additions.
- `noisy`: moderate typos, broken formatting or irrelevant text; the intended meaning remains recoverable.
- `heavy`: substantial corruption/distraction; keep a settled expected label only if reviewers can still recover the meaning.
- `unspecified`: not annotated; the report must display this group rather than silently treating it as regular.

Noise measures the input's textual condition, not difficulty or correctness. Clear grammatical wording can be misleading. If corruption destroys required information, use insufficient_context, expected=null and a note instead of guessing ground truth.

`tags` is an array of unique lowercase strings; `[]` is valid. Start with a small consistent vocabulary:

- `simple`: direct, unambiguous wording.
- `misleading`: plausible surface cues point toward the wrong class.
- `negation`: the intended answer depends on words such as "not" or "without".
- `mixed-intent`: the input mentions multiple requested actions.
- `missing-context`: required context is absent.
- `typos`: deliberate spelling corruption.
- `irrelevant-text`: extra material unrelated to the task.

Additional language tags such as `language-he` are optional. Use identical spelling everywhere; `typo` and `typos` would otherwise become separate groups. Tag each case based on its content before measuring results. Do not use the same run's failures to define the original noise groups.

Tags overlap. An input may be noisy and tagged both misleading and negation. It counts once in the noisy row, once in the misleading row and once in the negation row; overlapping tag counts are not added to form a dataset total.

## 4. Complete cases.json example

Save this as `experiments/batch_v2/experiments/fruit-smoke/cases.json`. This small dataset demonstrates the file format; it is not a calibrated benchmark.

```json
{
  "schema_version": 1,
  "dataset_id": "fruit-smoke",
  "dataset_version": "1",
  "cases": [
    {
      "id": "case-01",
      "input": "I ate an apple.",
      "expected": "fruit",
      "label_status": "settled",
      "noise_level": "regular",
      "tags": ["simple"],
      "source_family_id": "apple-food",
      "split": "development"
    },
    {
      "id": "case-02",
      "input": "I ate an aple.",
      "expected": "fruit",
      "label_status": "settled",
      "noise_level": "noisy",
      "tags": ["typos"],
      "source_family_id": "apple-food",
      "split": "development"
    },
    {
      "id": "case-03",
      "input": "Apple released a laptop.",
      "expected": "other",
      "label_status": "settled",
      "noise_level": "regular",
      "tags": ["misleading"],
      "source_family_id": "apple-company",
      "split": "development"
    }
  ]
}
```

Required fields are id, input, expected, label_status, noise_level and tags. Source-family and split fields are optional but useful for larger datasets. Keep a clean case and its noisy paraphrases in the same split to avoid near-duplicate leakage into held-out evaluation. Optional notes preserve annotation reasoning; desired_abstention, when supplied, is a boolean.

The generic adapter accepts a string input. For the requested-action adapter, the input value is an object such as `{"prompt":"Explain calculateTotal."}`. For context-scope, it can be `{"prompt":"Explain calculateTotal and its callers.","requested_action":"explain"}`. Those blocks require their own fixed labels/questions; do not pass these objects to the generic example or reuse fruit labels for the blocks. Only the input value reaches the selected execution path.

## 5. Complete matching suite.json example

Save this as `experiments/batch_v2/experiments/fruit-smoke/suite.json`. The settings below are illustrative plumbing values, not recommendations for a temperature sweep or calibrated acceptance thresholds. Use a model already installed locally. Null temperature requests the SDK default; it does not establish that the effective temperature differs from 1.0.

```json
{
  "schema_version": 1,
  "experiment_id": "fruit-smoke",
  "dataset_id": "fruit-smoke",
  "dataset_version": "1",
  "adapter": "generic-question",
  "question_type": "choice",
  "labels": ["fruit", "other"],
  "questions": [
    {
      "id": "q-baseline",
      "variant_kind": "baseline",
      "definition": {
        "name": "subject",
        "type": "choice",
        "instructions": "Does this text identify an edible fruit? Classify fruit references as fruit and everything else as other. Apple technology is other.",
        "criteria": {
          "fruit": "The text identifies an edible fruit, including an apple as food.",
          "other": "Everything else, including Apple technology and text that does not identify fruit."
        }
      }
    },
    {
      "id": "q-wording",
      "variant_kind": "wording",
      "definition": {
        "name": "subject",
        "type": "choice",
        "instructions": "Classify whether the text identifies an edible fruit. Use fruit for fruit references and other otherwise. Apple technology belongs to other.",
        "criteria": {
          "fruit": "The text identifies an edible fruit, including an apple as food.",
          "other": "Everything else, including Apple technology and text that does not identify fruit."
        }
      }
    }
  ],
  "rules": [
    {
      "id": "r-baseline",
      "definition": {
        "name": "smoke-gap",
        "conditions": [{"field": "probability_gap", "op": "gte", "value": 0.15}]
      }
    },
    {
      "id": "r-strict",
      "definition": {
        "name": "smoke-gap-strict",
        "conditions": [{"field": "probability_gap", "op": "gte", "value": 0.3}]
      }
    }
  ],
  "configurations": [
    {"id": "sdk-default", "model": "aac6fef/laya-typed-decisions-mlx", "temperature": null, "lang": "en"},
    {"id": "explicit-one", "model": "aac6fef/laya-typed-decisions-mlx", "temperature": 1.0, "lang": "en"}
  ],
  "baseline": {
    "question_id": "q-baseline",
    "rule_id": "r-baseline",
    "config_id": "sdk-default"
  }
}
```

Dataset ID/version must match cases.json. Question definitions use the same name, type, label IDs, order and meanings. This wording-only variant preserves the complete criteria object. A choice-description variant instead preserves instructions and edits descriptions while retaining the class meanings. Rules reuse the runtime's condition syntax. Configuration IDs distinguish requested settings; the manifest separately records effective settings when observable.

This suite creates 8 vectors and 24 logical case outcomes. Without exclusions it uses 12 shared inferences in verified replay mode or 24 inferences in direct mode. All questions/rules/configurations live in arrays; adding another compatible entry expands the matrix without new runner code.

## 6. A repeatable annotation workflow

1. Define labels and boundary/mixed-request policies. Write a few clean cases for every label.
2. Give each case a stable ID. Set expected and label_status from independent reasoning/review, with notes for unresolved cases.
3. Make noisy or misleading variants deliberately. Preserve expected only when their meaning still supports it; record shared source-family IDs.
4. Add one noise level and applicable tags. Include relevant combinations, not only easy cases. Inspect counts per expected label, noise level and tag before running.
5. If an LLM generates cases or labels, review them. Stronger models also make errors; agreement alone is not proof. Record actual reviewer disagreements in notes or the optional review-disagreement tag, then resolve what can be resolved before freezing inputs.
6. Assign splits by source family when using development/calibration/held-out evaluation. Do not tune rules using the held-out results.
7. Freeze the files and run validation/dry-run using the README commands. Bump dataset_version when correcting labels, annotations or content after a run; preserve the prior run's frozen snapshot. Start a new run rather than altering old results.

## 7. How annotations affect the summary

Every vector receives the same cases. Only settled cases with a valid expected class and valid prediction evidence enter the correct/wrong accounting. Pending, missing-context and out-of-scope cases remain in the export and operational reports, with observed acceptance/abstention, status and timing. The report must state why cases are unscored.

For each scored subgroup, count correct accepted, wrong accepted, correct rejected and wrong rejected. Correct/wrong rejected are the two parts of abstention. This exposes correct LAYA answers lost to a conservative rule as well as wrong answers the rule successfully filtered.

Noise-level rows use their own eligible subgroup denominator. Tag rows do the same and may overlap. In this example the planned distribution is regular=2, noisy=1, simple=1, typos=1 and misleading=1. Those counts describe the inputs regardless of which predictions the model makes. Read operational counts alongside accuracy whenever a subgroup contains unscored or failed cases.

