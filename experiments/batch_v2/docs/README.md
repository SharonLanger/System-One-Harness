# Experiment handbook — start here

Define a classification use case, test alternative questions/choices/rules through Runner V2, and use the best tested configuration to design a building block afterward.

This folder is the shared entry point for the experiment designer, input author/reviewer, implementation agent, operator and results analyst. A production building block is not required to run the research.

Status: the runner is merged; the additional analysis helpers are planned. This handbook contains instructions and blank record templates. It contains no real experiment cases or measured results.

## Read in this order

1. [Workflow](workflow.md): rounds, decision branches, temperature refinement and stopping.
2. [Scoring](scoring.md): model metrics, acceptance-rule metrics, probabilities and DOCTOR.
3. [Records and handoffs](records-and-handoffs.md): exact locations, run history, evidence and sharing.
4. [Implementation plan](implementation-plan.md): Track A prepares the tooling; Track B defines and runs a real use case.
5. [Input-agent instructions](input-authoring.md): generation, fixed tags, labels, review and family splits.
6. [Research notes](research-notes.md): why these methods were selected and their limits.

For executable runner commands and schemas, read [Runner V2 usage](../README.md) and [the JSON authoring guide](../input-authoring.md). The handbook does not redefine their interfaces.

## Instructions by role

- **Implementation agent:** finish Track A in a separate PR. Keep changes inside experiments/batch_v2/. New scoring helpers must be reusable pure functions. Record actual tests and any remaining Mac-only checks.
- **Experiment designer:** after tooling preparation, complete the task-definition template. Define the input/label contract independently of existing block code. Keep decision boundaries fixed while testing phrasing.
- **Input author and reviewer:** receive that completed contract plus input-authoring.md. Generate expected labels from the contract, not from LAYA predictions. Review and freeze the dataset.
- **Operator:** validate the suite, inspect call counts, record exact commands/settings, execute and preserve the printed run folder. Resume only unchanged runs.
- **Results analyst:** use permitted development/calibration roles during selection. Fill the result and next-step sections after each round; keep uncertainty and competing hypotheses visible.
- **Next agent:** start with the campaign README and journal, follow evidence references, and continue only the recorded next action. Do not infer success from an unchecked box or missing error log.

## Templates

Copy these into one campaign's folder when the specific use case is agreed:
- [Campaign README](templates/campaign-readme.md)
- [Task definition](templates/task-definition.md)
- [Run journal](templates/run-journal.md)
- [Round plan, result and next decision](templates/run-record.md)
- [Final configuration decision](templates/final-decision.md)

[Campaign index](campaigns/README.md) will link actual campaigns. None has been created by this documentation change.

## What stays fixed and what changes

Keep the same input cases, expected labels, annotations and source-family roles throughout a campaign. Change only the declared question/choice wording, rule or configuration axes. New label meanings or corrected case text require a new dataset/campaign version.

Each round records what was changed, the hypothesis, observations and the next proposed comparison. Keep both alternatives when evidence does not resolve them. A "best tested" configuration is not proof of a global optimum.

Expected labels/tags never go to the model. Held-out evidence never guides the next experiment. Technical failures are not wrong labels. No experimental helper is promoted into production automatically.

## Immediate next work

Implement and verify [Track A](implementation-plan.md), then review/merge that implementation. Afterward, define the first concrete question, choice alternatives and task boundaries with Sharon using Track B. Case generation and real model runs follow that definition.

The documents in this folder are the repository's operational handbook. Earlier standalone research notes are background; when instructions differ, follow this handbook's generic-task scope and the current runner schema.
