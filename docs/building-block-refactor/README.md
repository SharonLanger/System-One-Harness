# Reusable question blocks: design and implementation plan

Status: DESIGN ONLY. No implementation or test execution authorized by this document alone.
This plan is for a reliable hackathon demo, with a small reusable interface.

## Read in this order

1. This file: scope, repository baseline, phases, compatibility and completion gates.
2. [design.md](design.md): exact configuration, inputs, preparation, runtime, outputs and flow examples.
3. [test-plan.md](test-plan.md): concrete test cases and the evidence required before migration.

## Outcome

A flow calls a block with validated input and model configuration. The block uses
its default questions and one named rule per question, unless the caller supplies
an override. Questions may be shared definitions or block-owned inline definitions.
Input preparation can construct method choices or call existing utilities. The
common runtime validates the prepared questions, calls Laya once, enriches each
answer once, applies one compatible rule per question, and returns decisions.

Keep existing blocks available throughout migration. Introduce the new runtime
and sibling block packages; compare old and new behavior using the same mock raw
responses. Switch callers only after parity passes. Do not delete the legacy
runtime or block packages in this work.

## Reviewed repository baseline

Reviewed remote main at `92191d3837f4efd0f839270e83b8bd436b0e1009`.
Implementation must fetch current main again: other agents are actively changing
hook gateway/dispatcher code. This local checkout is older than remote main.
Do not publish its whole tree or overwrite newer remote flow changes.

- `src/laya_context_router/blocks.py`: QuestionBlock loads questions.json and
  rules.json; accepts dynamic question payloads with matching names; returns decisions.
- `answers/rules.py`: RulesConfig has conditions and conditions_by_type. It does
  not explicitly constrain the compatible question type. Missing type-specific
  conditions currently contribute no additional checks: this must not become a
  silent compatibility mechanism for new named rules.
- `answers/interpret.py`: validates, enriches, checks rules and extracts answers.
  Keep its legacy behavior; reuse its primitives without enriching twice.
- `questions/models.py`: supports choice, noul and score. Preserve SDK spelling
  `noul`, not null. Reuse these validators for fully prepared questions.
- Existing blocks: ticket_triage and method_selection. Their entry points accept
  config and registry; method selection additionally accepts an outline and budgets.
- `flows/file_method_context.py` currently supports opt-in fallback and
  resolve_from_project_root. Preserve both, along with reasons and source identity checks.
- `laya/config.py` and registry.py already handle model/temperature/language and
  agent reuse per `(model, temperature, language)` within one invocation.
- Existing wheel test verifies block resources; new shared JSON must be included
  in package data and tested from an isolated installed wheel.

### Current policy behavior to preserve

Method selection: answer_confidence >= 0.5 AND probability_gap >= 0.15.
Multiple-relevant noul: answer_confidence >= 0.5; do not restore the previously
removed distance_from_boundary condition.
Ticket department: answer_confidence >= 0.9 AND probability_gap >= 0.5.
Ticket churn: distance_from_boundary >= 0.1.
Re-read these files at implementation time; if main changed, preserve the newer
intent rather than copying these historical values over it.
Sharon will provide additional defaults. Until then use exact typed copies of
existing rules; illustrative examples in design.md are not new calibrated policy.

## Deliberate scope limits

No multiple policies per question in one run, rule comparison engine, workflow
DSL, inheritance tree, plugin loader, automatic retry, global agent cache, dynamic
Python imports from JSON, or persistent prediction store. No new Laya questions
or threshold tuning required for migration. No changes to TypeScript extraction.
No promised live accuracy from mock tests. No new hooks installed or activated.

## Phases: small commits on a feature branch

0. **Fresh baseline and characterization.** Start from current remote main in an
   isolated branch/worktree. Read applicable AGENTS.md. Run current relevant tests
   and record existing failures separately. Capture both old block inputs,
   exact SDK payloads, decisions, no-selection reasons and representative flow
   results using fixed raw responses. Commit characterization tests first.
1. **Typed shared catalogs.** Add validated named rules and shared question loading,
   exact existing policy copies, duplicate/missing-name errors and package-data
   coverage. Keep old block files untouched. Tests first, then implementation.
2. **New runtime and simple block.** Implement one execution path with input/output
   validation, injected preparation, per-call question/rule overrides, one-time
   enrichment and config/registry reuse. Add ticket_triage_v2 beside the old block.
   Demonstrate defaults and one overridden rule without involving TypeScript.
3. **Method selection sibling.** Add method_selection_v2 with the same input
   outline, candidate labels/maps, budgets and two-question reduction. Extract
   only small reusable preparation helpers if parity tests prove no legacy change.
   Test real outlines with fake SDK responses. Add explicit optional preparation
   callback; avoid making filesystem reads mandatory for the existing outline API.
4. **Flow rehearsal.** Exercise a small Python flow using the new blocks, a utility,
   a conditional second block, and an alternate RunConfig. Test early stop,
   mixed/undecided answers and errors. Test the existing file-method flow using an
   explicit test seam selecting old/new implementations before production switch.
5. **Caller migration.** After parity passes, route existing public block entry
   points through thin adapters to V2 while preserving signatures and returned
   dictionaries. Existing flow imports stay usable. Preserve legacy implementations
   at an explicit old path so a revert is straightforward. Update experiments only
   where required by the new optional parameters; no behavior changes by default.
6. **Documentation and independent verification.** Run complete relevant suites,
   isolated wheel check and offline experiment smoke. Map every required test-plan
   case to test names/results. Verify reviewer findings before declaring complete.
   Prepare a PR, compare latest main, resolve conflicts and rerun affected suites.

Commit each completed phase on the feature branch. Use a PR because other agents
are working concurrently. Do not merge stale local main over remote changes.
Before merge, show exact changed files, parity results, skips and remaining gaps.
No legacy deletion phase is included. Rollback is reverting caller-migration
commit while keeping the additive runtime/catalog work available.

## Gates and honest reporting

A new feature test should fail for the missing behavior before implementation.
Characterization tests for correct legacy behavior should pass immediately.
Keep meaningful assertions; never weaken tests to make migration pass. Test names
must describe behavior, not simply restate a function name. Run targeted tests
while developing, then relevant regressions once the phase is stable. Run all
Python tests and the TypeScript suite at final integration to catch accidental
cross-layer regressions; real model execution remains Sharon's manual gate.

A green total count is not proof that the plan is covered. Maintain a case-to-test
checklist. Required cases remain open until implemented or explicitly accepted as
deferred by Sharon. If a change in semantics or significant redesign is needed,
use Astra reasoning review, document the decision and stop on a major unresolved
issue rather than repeatedly patching symptoms. Use Sol for implementation and a
low-cost independent verifier for final coverage review, as requested previously.

## Definition of done

- Existing blocks and default flow outputs are equivalent on characterized inputs.
- Named defaults and per-call overrides work without mutating shared definitions.
- Rule/question mismatch logs ERROR and fails before loading or calling Laya.
- Dynamic inputs, invalid model responses and likely configuration mistakes are covered.
- All required test-plan cases have evidence, including packaging and flow composition.
- README explains how to add and use one block without reading runtime internals.
- No automatic retries, live model calls, hidden rule selection or hook changes.
