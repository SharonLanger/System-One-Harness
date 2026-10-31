# Annotation review: requested-action-500

Status: input authoring and label-blind review completed; pre-freeze clarifications applied. Dataset version 1 is frozen before target-model inference. No LAYA prediction, probability, or acceptance result was used to set labels, tags or roles.

## Who reviewed what

The input-authoring agent `/root/requested_action_inputs` authored 125 distinct semantic bases and 125 custom misleading variants, then generated controlled noisy/heavy variants. Its second pass checked the base/decoy intent, transformation rules, label/status invariance and structural validation. This is author self-review, not independent evidence.

The root agent `/root` received only 500 shuffled opaque IDs and input strings, with no proposed labels, notes, family IDs or roles. It manually assigned all 500 judgments and saved those judgments before opening the author's annotations. Author and reviewer share model lineage. The review is independent of the proposed labels, but it is not independent human truth or a guarantee of correctness.

Initial agreement was 498/500. Two disagreements concerned one family, described below. The compact [per-case review ledger](annotation-review.json) preserves the original author label/status, blinded reviewer judgment, final label/status, disposition and final input hash. It also preserves every input that changed during pre-freeze review, including original and final text. Do not describe the final clarified dataset as having 100% independently measured agreement: the two revised prompts were clarified as the reviewer requested, rather than subjected to a new complete blinded evaluation.

## Observed disagreement and resolution

`case-272` and `case-476`, family-063, originally asked to "Write a test matrix" for cache eviction limits. The author intended new executable tests (`generate_tests`). The blind reviewer marked `insufficient_context`: a test matrix could mean a test plan rather than test implementation.

Before any target run, both inputs were clarified to "Write table-driven tests". The noisy variant retains `evicton` and its surrounding spaces. Final expected label is `generate_tests`. Only these two actually disputed cases receive `review-disagreement`; the other two family variants already clearly asked for additional tests and agreed. No labels were changed to match a model prediction.

The root reviewer then checked all nine final before/after revisions against the contract and confirmed that the intended labels are preserved, including `generate_tests` for both clarified cases. This was a focused post-clarification check, not a second blinded review of all 500 inputs.

Final texts:

- case-272: `Write table-driven tests for cache eviction under maximum item count and maximum total size.`
- case-476: `  Write table-driven tests for cache evicton under maximum item count and maximum total size.  `

## Author corrections before freeze

Two noisy variants initially had no typo and became duplicates of the direct wording after whitespace normalization. Author self-review and the root reviewer both identified the duplication. Adding the recoverable substitutions `integration` -> `integraiton` and `eviction` -> `evicton` fixed it. Because the same deterministic substitution list is used consistently, the typo additions affected eight noisy/heavy inputs in total, including disputed case-476. Together with the two test-matrix clarifications, nine distinct inputs changed; the complete before/after inventory is in the ledger. IDs, family assignments, expected labels and status remained fixed.

The blind review packet was regenerated once during review for those typo fixes, with unchanged IDs and ordering, and the reviewer was notified. These are disclosed as pre-freeze corrections, not hidden replacements of already evaluated data. The final packet was not overwritten after the test-matrix clarification; the ledger preserves that original review evidence through before/after text and recorded judgments.

During author self-review, inherited tags were removed from direct/noisy variants when only their misleading counterpart had the corresponding negation, mixed intent, or correction/retraction. The final tags describe each actual prompt. No `review-disagreement` tags were manufactured for the intentionally difficult cases.

## Decision boundaries checked

- Test explanation versus existing-test repair versus additional test creation.
- A failing test does not automatically imply a repair request.
- Explanation supporting an explicit change or new-test deliverable does not override that deliverable.
- Quoted text, filenames, issue titles and cancelled requests do not override the active request.
- Missing source code does not remove a clear requested action.
- Coequal new-test and implementation/repair requests have `taxonomy_pending`, with no invented precedence.
- Unresolved references to earlier discussions have `insufficient_context` because the action itself is unavailable.
- Non-code writing, translation, arithmetic, meals and astronomy are `out_of_scope`, even when they use words such as explain or contain a programming-related decoy.

Unsettled cases intentionally remain unresolved for one-label correctness. All 80 have null expected labels and an explicit abstention goal. They can be counted for acceptance behavior, but must not be assigned a fabricated "correct class" for accuracy or calibration.

## Duplicates and source families

All 500 final input strings are distinct, both exactly and after Unicode NFKC normalization, case folding and whitespace collapse. Each source family has exactly four variants and stays in one role.

A character-sequence similarity screen (`difflib.SequenceMatcher`) on the 125 direct scenario texts flagged seven cross-family pairs at a 0.55 threshold. The highest ratio was 0.6043. This is a lexical screen, not proof of semantic independence. The author checked the flagged pairs:

| Families | Ratio | Why kept separate |
| --- | ---: | --- |
| 108 / 109 | 0.6043 | Token-store refactor plus eviction tests versus mock-server repair plus a new rejection test. |
| 050 / 065 | 0.5680 | Repeated command-line flags versus negative export amounts/missing currency. |
| 037 / 065 | 0.5570 | Failed upload chunk retry versus financial export edge cases. |
| 037 / 069 | 0.5556 | Chunk retry versus fallback-font selection. |
| 037 / 050 | 0.5548 | Upload retry versus repeated command-line flags. |
| 018 / 029 | 0.5538 | Mock call order versus snapshot timestamp/fake-clock behavior. |
| 056 / 059 | 0.5526 | TLS certificate validation versus binary frame length-prefix fuzz tests. |

Shared request grammar alone does not make these the same scenario. No cross-family derived counterfactuals were knowingly created. Related topics such as tests, retries and parsers still recur; the synthetic generation style and common wrappers can create dependence beyond the explicit families. Treat family-level uncertainty as exploratory, and do not claim these are 500 independent production observations.

## Validation and limits

The final inputs validate against the actual RV2 schema/runtime checks and first-round suite. Family roles validate with `research.protocol.role_ids`. Counts, tag distributions and frozen hashes are in [dataset-summary.md](dataset-summary.md). No production fixtures were reused, no cases changed role during review, and no target-model inference has been run.

This first set stresses controlled distinctions with clear active-request markers and short prompts. It does not measure long-context robustness, multilingual requests, production prevalence, or every possible noise form. The label-blind review resolved the one observed wording ambiguity; future real-user failure analysis may reveal other gaps. Any correction after a target run must create a new dataset version and preserve version-1 evidence.
