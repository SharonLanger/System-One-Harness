# Campaign records, evidence and handoffs

Use one campaign ID per fixed classification task and dataset version. Keep all human-facing knowledge under docs/campaigns/<campaign-id>/. Actual input/suite files and raw runner outputs use the locations below.

Paths in this document are relative to experiments/batch_v2/.

## Where each artifact belongs

- docs/campaigns/README.md: index of campaigns.
- docs/campaigns/<campaign-id>/README.md: current status, important links and next action.
- docs/campaigns/<campaign-id>/task-definition.md: frozen task, input rendering, labels, hypotheses and initial settings.
- docs/campaigns/<campaign-id>/dataset-summary.md and annotation-review.md: generation/review evidence.
- docs/campaigns/<campaign-id>/run-journal.md: chronological index of every attempt.
- docs/campaigns/<campaign-id>/rounds/001-<purpose>.md: plan, evidence, analysis and next decision for one round. Increment numbers without reuse.
- docs/campaigns/<campaign-id>/final-decision.md: frozen selected configuration, uncertainty and integration handoff.
- docs/campaigns/<campaign-id>/evidence/<run-id>/: compact shared evidence and its checksums.
- experiments/<campaign-id>/cases.json: the single frozen input file.
- experiments/<campaign-id>/calibration_roles.json: temperature/policy family map.
- experiments/<campaign-id>/protocol.json: research controller settings and role hashes, once implemented.
- experiments/<campaign-id>/rounds/001-<purpose>/suite.json: exact runnable suite for that round.
- results/<experiment-id>/<timestamp>__<unique-id>/: runner-owned raw artifacts, checkpoints and reports.

Keep suite experiment_id equal to the campaign ID across rounds; distinct launches already get unique result folders. Store the round ID in research records, not as an unsupported suite field. Use the same cases.json path and bytes for every round.

Current RV2 accepts explicit --cases and --suite paths, so a suite can live in a numbered round subdirectory. Run instructions remain in the existing runner README. No new command is claimed by this documentation.

## Dataset identity

Record dataset_id/version, full case-file SHA-256, role-map hash, source-family assignment and source commit. Changing labels, text or annotations requires a new version and campaign; preserve previous results. A suite change starts a new round/run, not a resume.

Research sidecar fields must not be injected into the strict current cases/suite schema. The input agent's role map divides split=calibration into two fixed roles.

## Before a run

1. Complete the task contract and input review; freeze input and role hashes.
2. Create the numbered round record from the template with status planned.
3. State the hypothesis, exact changes versus its parent, permitted analysis roles, metrics, tolerances and if/then branches.
4. Save complete question/rule/configuration definitions in the round suite.
5. Run validation/dry-run; record vector/case/inference counts, budgets and output.
6. Commit the authored files before inference where possible. Record commit and any dirty differences. Do not call an uncommitted working tree reproducible without preserving the diff.

## During and after a run

- Record command, start/end time, source revision, runtime/model identity, printed result directory, execution mode and rule mode.
- Keep runner manifest, raw responses, logs and checkpoints unchanged.
- Distinguish completed, partial, failed and cancelled attempts. A retry with new definitions is another attempt; resume preserves the original run ID.
- Use the role-filtered analysis report during tuning. The current runner's overall report includes held-out outcomes and must not drive selection.
- Record actual counts and exact metric denominators. Include per-class/noise/tag results, missing evidence and technical failures.
- Compare parent and candidate on matching case IDs and source-family roles.
- Fill the next-action section: retain/discard/branch/refine/stop, evidence, settings and reason.
- Update the journal and campaign README so another agent can continue without reading chat history.

A round can contain several runner invocations only when each is explicitly listed with its own run ID, purpose and mode. Never silently pool fixture/live evidence, different checkpoints or different label spaces.

## Durable evidence for the next agent

The runner's results/ directory is gitignored. A local path alone is not a shared handoff.

Default shared package under docs/campaigns/<campaign-id>/evidence/<run-id>/:
- evidence-manifest.json: original run ID, hashes, source commit, file inventory and analysis version.
- frozen case/suite/role hashes and references to their tracked files.
- compact per-inference predictions with full available probabilities, raw labels, statuses and source IDs.
- policy definitions and decisions, or a deterministic replay recipe with versioned helper hashes.
- role-filtered metrics and next-decision inputs.
- a compressed full raw-run archive when practical, or its durable shared artifact reference and checksum.

Do not include held-out prediction values in a tuning-facing evidence package. Preserve them separately, sealed for the final evaluator. Early packages identify withheld files by hash and role. Raw logs can contain held-out responses too; keep that archive sealed during tuning.

Choose a shared location accessible to the next agent. Small synthetic evidence can be committed with the campaign; larger bundles can be stored as shared artifacts with exact retrievable references in the manifest. Never assume ignored local results were uploaded by a git push. If required evidence is unreachable, mark the handoff incomplete.

Preserve the full originals even when the shared compact export excludes verbose logs. Exact hashes let an auditor connect the export to the original run. Export/sharing support is a Track A implementation task; no archive has been generated here.

## Journal conventions

Use one short chronological entry per round:
- round ID and status;
- hypothesis and parent;
- suite path and run IDs;
- principal observed changes and important regressions;
- selected next action and evidence reference.

Do not rewrite old conclusions when later evidence disagrees. Append a correction referencing the old entry. Separate observation ("accepted error changed") from interpretation ("we suspect wording helps noisy requests").

A planned entry has no results. Synthetic calculations are labeled illustrative and never entered as live evidence.

## Handoff to a building block

The final decision includes the exact question/choice definitions, rule/cutoff, requested and known effective model settings, input-rendering contract and evaluation evidence. Keep class labels and semantics stable.

A later production implementation must reproduce the evaluated payload and decision behavior. If its preparation, truncation, calibration or runtime differs, run a parity comparison before claiming the research result transfers. Pure helper functions can be considered for reuse only after their method is supported by evidence and the production change is separately reviewed.
