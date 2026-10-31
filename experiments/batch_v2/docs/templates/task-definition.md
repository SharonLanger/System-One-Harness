# Task definition: <campaign-id>

Status: draft. This defines the classification problem before a production block exists.

## Goal

- User request or decision this classifier should understand:
- What a correct result enables:
- What is outside this task:
- Fixed question type:

## Input contract

- Exact text fields/context available to LAYA:
- Rendering order, delimiters and treatment of absent context:
- Language and relevant code language:
- Length/truncation policy:
- Information the model must not be assumed to have:

All case inputs are final nonblank strings for generic-question. Metadata and expected labels are excluded.

## Canonical classes

For each label, specify meaning, inclusion/exclusion boundaries and precedence for mixed requests. Record exact label order. Define insufficient-context/out-of-scope handling and which cases legitimately request abstention.

No class definition may change between wording variants.

## Questions and choices

- Q0 complete initial reference:
- Q1 concise instructions:
- Q2 clearer boundaries:
- C1 shorter choice descriptions:
- C2 clearer choice descriptions:

Wording variants preserve the criteria object. Description variants preserve instructions. Record the hypothesis for each and review semantic equivalence. Full executable definitions go in the suite, not only in prose.

## Rules and configurations

- R0 complete reference rule and rationale:
- Additional score/rule families:
- Model/checkpoint, language and known temperature bounds:
- Initial configuration list:
- Critical classes/noise/tag groups:
- Engineering tolerances and call/time budgets:
- Stable Q/R/configuration IDs:

## Inputs, evidence and analysis

- Dataset specification and source-family quotas:
- Fixed data roles and role-map policy:
- Input-authoring instructions and reviewer:
- Metrics and uncertainty conventions:
- Round-one hypothesis and expected possible outcomes:
- Explicit next step for each outcome:
- Held-out access policy:
- Source references and unresolved task-definition issues:

Agree this contract before generating real cases. Do not insert measured scores into a task definition before a run.
