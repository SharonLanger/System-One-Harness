# Supporting utility implementation evidence

Date: 2026-10-30. Base: `053af28fe76d732a2a843d9f6f4d1d8a9c7c64c3`.

The [approved contract/plan](supporting-utilities-plan.md) and [implemented API reference](../typescript-helper/README.md) are the main references. This work changes supporting utilities and their integration; core question preparation, enrichment, named rules, interpretation, model reuse and thresholds retain their existing behavior.

## Baseline and test-first evidence

The implementation used an isolated complete snapshot of current main: all 165 tracked files were materialized and verified against Git blob hashes, avoiding unrelated staged files in the earlier checkout. Its complete baseline Git tree is `f7aa513a9c96959e246eddfedb84a0f86fdbe435`, exactly matching the remote commit tree (including tracked paths and modes). TypeScript helper dependencies were present and `npm --prefix typescript-helper run build` passed before behavioral RED tests ran. No missing build/dependency failure is counted as evidence.

[Recorded RED output](testing/supporting-utilities-red.txt) contains the initial public outline, readable mapping and Python protocol failures, plus later receiver/header regression failures. Important observed failures:

- Public default invoice outline returned `calculateInvoiceTotal`, two anonymous callbacks, and `calculateInvoiceTotalWithAdjustment`; expected exactly the two outer functions.
- A nested-function/class/default fixture returned eight callables rather than only `outer` and `bound`.
- New call-list behavioral tests initially failed because the action/export did not exist; the same assertions subsequently verified resolved local/imported targets, nested-call scanning and internal-target omission.
- Existing Python `resolve_file('service1/invoice-service.ts', ...)` returned missing rather than the uniquely matching component suffix. New TS detector/resolver tests initially failed because exports did not exist; final tests assert presets, full filenames, exclusions, ambiguity, navigation and confinement.
- Method-selection payload exposed a SHA/range ID as the model choice key. The new test required a readable method identifier and a round-trip map to that internal ID. Final invoice assertions require the exact two method-name keys with signatures as descriptions.
- Constructor-injected/typed uninitialized field receivers initially returned `ok` with a concrete implementation; the regression requires partial diagnostics and no guessed target. Independent review also reproduced the direct injected-parameter case.
- Signature metadata initially exposed function bodies in default/computed headers; regression markers now remain only in extracted raw code, absent from all callable metadata.

No xfail, threshold reductions or expectation relaxation masked these failures. Old recursive discovery coverage now exercises the private exhaustive snapshot reader. Public outline tests assert the approved stopping boundary. A full-hook nested-selection fixture was updated to select/extract its outer callable, retaining the complete nested body.

## Implemented phases

A/B froze utility contracts and added tests before production changes. C added TS configurable detection, a generic confined component-suffix resolver, and public declaration-only outlines while retaining exact extraction/private discovery. D added checker-based called-callable navigation, including aliases/reexports, complete selected-block scanning, containment omission, explicit unsupported outcomes and extractor-compatible target identities. E integrated readable choice keys and a separate `label_map`, migrated default detection and generic resolution through bounded Python transport, and retained both lexical and canonical production-source gates. F retained only needed compatibility wrappers, updated examples/docs and verified existing collection budgets/coverage through regression tests.

The approved narrow compatibility exception retains caller-supplied Python regex semantics in `detect_file_references(text, pattern)`. New configured APIs and omitted-pattern/default flow use TS. A private omitted sentinel distinguishes omission from explicit `None` or explicit old default pattern. Default flow counts all `.ts` mentions before its production gate, preserving `multiple_files`/`excluded` outcomes. See the plan's decision appendix and API reference for flags/conditionals and migration details.

Readable criteria use unique method names; repeated names with different signatures use `name@line:column`. Identical signatures still produce `ambiguous_candidates` before inference. IDs/maps never enter model criteria or the optional fallback text.

One existing test fixture defect was independently reproduced on the current-main runtime structure: the disposable direct `laya_choice.py` test copied `support.py` but omitted the imported `summary.py`, causing `ModuleNotFoundError: summary`. The repair copies that required dependency into the temporary project; no production experiment behavior changed.

## Validation

Final stable candidate checks:

- `npm --prefix typescript-helper run build`: passed (TypeScript 5.9.3).
- `npm --prefix typescript-helper test`: **76 passed, 0 failed**.
- `python -m pytest -q`: **478 passed, 3 skipped, 0 failed** in 174.11 seconds. The three existing deferred cases concern duplicate-key configuration conventions and concurrent outside-project symlink replacement; no new skip/xfail was added.
- `git diff --check`: passed; all 20 JSON examples in the utility README parse, and its/root/method-selection documentation links resolve.
- Independent reviewer focused checks: **15 Node and 8 Python cases passed**, including injected receiver uncertainty, complete-block calls, exact invoice labels, mention gates, omitted/explicit-pattern compatibility and canonical target eligibility.

The final runs followed all production and fixture corrections; no behavioral edits were made during the stable Python run. Focused intermediate checks also exercised generic resolver/detector compatibility and the complete selection/flow pipeline.

The helper must be rebuilt after TypeScript edits. Tests use mock Laya boundaries only. No real Laya runtime/model was available on this host. Sharon's Mac rerun remains necessary to inspect submitted questions, confidence/rule decisions and resulting context; this implementation does not claim the earlier `method_undecided` behavior is fixed or lower any acceptance threshold to force success.
