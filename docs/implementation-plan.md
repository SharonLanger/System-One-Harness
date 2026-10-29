# Laya Context Router: small, tested implementation steps

Prepared for Sharon · 29 October 2026

**Execution status: implementation authorized on 29 October 2026; Phases 01–19 use mocks. Phase 20 remains blocked on a supported real environment. Original planning status follows for provenance.**

**Original status: plan only. No implementation, model execution, commits, repository creation, or pushes have been performed for this plan.** Sharon will supply the remote repository later. Give the implementing agent this file, the original `LAYA.zip`, and the earlier `laya-context-router-handoff.zip`.

**Latest decision: mock Laya first; real Laya inference is Phase 20, the final stage.** This replaces the earlier requirement for real model calls before every early commit. Implement the production adapter from the supplied code, but do not load weights or call a real model during Phases 01–19. Sharon will supply complete question/request and raw-response JSON examples for the mock fixtures. Independent test planning, pre-commit verification, and full regression runs remain required.

## The destination

Build reusable Python blocks that define questions, call the existing Laya model, enrich predictions, apply extraction rules, and return answers. A Python flow combines those blocks with ordinary code. Later, one hook entry script connects the flow to Claude Code, and a TypeScript helper supplies source outlines and context.

Start with one trivial question through the real adapter code and a mocked SDK boundary. Do not create the entire proposed folder structure in the first commit. Create each module when its phase needs it. Every phase should leave a working increment that can be understood, tested, and reverted on its own.

The first useful method-selection flow does not need a complete dependency graph. Deliver exact selected-method context with honest limitations first; expand context in later commits.

## The path at a glance

- **01:** implement the Laya adapter and test one mocked question/response.
- **02–07:** add settings/reuse, JSON questions, enrichment, rules, answer extraction, then one complete reusable block; all Laya calls remain mocked.
- **08–12:** detect and resolve a file, extract a small supported outline and exact code, then select a method using a mocked Laya response.
- **13–14:** combine the pieces into an offline flow and a bounded multi-block/second-round flow.
- **15–16:** add one hook script and test complete hook scenarios through subprocesses, without activating a real session.
- **17–19:** broaden callable coverage and add bounded same-file/cross-file context.
- **20:** enable real Laya calls, run the prepared contract tests against actual models/settings, and perform authorized real-harness validation if in scope.

Every numbered phase ends with the full accumulated tests required at that stage, independent review, and one focused commit. Phases 07, 13, and 16 are useful stopping points: reusable decision core, working offline flow, and tested hook protocol. These milestones prove behavior with controlled model responses; real model compatibility is verified only in Phase 20.

## Decisions this plan makes explicit

These incorporate the discussion after the original handoff and supersede its conflicting layout suggestions:

- Python continues to run `laya_mlx`. Do not replace it with another runtime during extraction.
- Keep the SDK import/load lazy and the dependency boundary small. Early tests inject a fake loader/agent; ordinary examples explicitly use mock mode. Real mode is explicit, never an accidental fallback. Importing the package or running the mock suite must not load weights, require MLX, or contact a model service.
- Each script invocation starts fresh. Agents load on first use and are reused only within that invocation, keyed by model and load settings.
- One block may ask multiple named questions. Its folder contains `questions.json`, `rules.json`, `block.py`, and `README.md`.
- Every block rules file uses `rules_by_question`, even if there is only one question. The existing `RulesConfig.from_dict()` reads each inner policy; its existing `from_file()` cannot read this new outer envelope unchanged.
- There is one hook adapter: `hooks/user_prompt_submit.py`. No second hooks package is needed initially.
- The flow defines order, branching, model settings, and calls to ordinary code. There is no general workflow engine or new configuration language for flows.
- Initial source work targets production TypeScript. `.spec.ts` is Sharon's test convention; declaration files are classified separately. Test extraction comes later.
- No old experiment runner, `TestCase`, result-directory orchestration, report engine, `Scenario/Results/Report` framework, or threshold-sweep CLI is copied. Small tests and direct examples are sufficient.

## One rules format throughout

Example block `questions.json` is a list of complete question definitions. Each definition has a unique `name`. A method block could ask `method` and `multiple_relevant`.

Its `rules.json` always has this shape:

```json
{
  "rules_by_question": {
    "method": {
      "name": "method-selection",
      "conditions": [
        {"field": "answer_confidence", "op": "gte", "value": 0.3}
      ],
      "conditions_by_type": {
        "choice": [
          {"field": "probability_gap", "op": "gte", "value": 0.1}
        ]
      }
    },
    "multiple_relevant": {
      "name": "multiple-methods",
      "conditions": [
        {"field": "distance_from_boundary", "op": "gte", "value": 0.15}
      ]
    }
  }
}
```

These thresholds illustrate the format, not a calibrated production policy. The outer keys bind policies to question names and Laya answer keys. Inner `name` identifies the policy. It does not select the question. One question means one entry in this same envelope, not a different format.

Definitions go to Laya. Rules do not. Expected test answers never become runtime inputs. A block returns named decisions with an answer, `decided`, and a reason. A flow may then ask another block, run normal Python, or finish.

## How every phase is executed

Use this process for every numbered phase below. These are engineering completion checks, not a request for Sharon to approve every routine step.

1. **Establish the starting point.** Inspect the repository instructions, working tree, previous phase record, and current public contracts. Run the complete existing test suite before editing. For Phase 01, there are no project tests yet; record that rather than calling an empty suite a pass. Preserve unrelated user changes.
2. **Have a separate agent write the phase test plan before implementation.** Give it the phase requirement, existing contracts and regression tests, and relevant original source. Ask it to identify positive, negative, boundary, parity, and integration checks. It should not invent expected results by copying the new implementation. The implementing agent should not silently replace this independent planning step with self-review.
3. **Record the scope and tests.** Use one short `docs/phases/phase-NN.md` for the scope, independent test plan, expected outputs, and eventual verification evidence. Keep a short `docs/progress.md` linking these records. No additional management framework is needed.
4. **Write the planned tests, then the smallest implementation.** New behavior tests should fail for the missing behavior before the implementation makes them pass. Tests documenting behavior already present may pass immediately. Keep tests focused on observable contracts, not internal method choreography unless exact SDK arguments are the contract.
5. **Run focused checks while developing.** Fix the implementation when a regression exposes a real defect. Do not weaken assertions, alter fixtures, or exclude difficult cases to obtain green output.
6. **Run the complete accumulated validation suite on the final candidate.** Include all previous tests, the new tests, complete mock-based contract/integration checks, and TypeScript/build checks once introduced. Real Laya checks become mandatory only in Phase 20. A subsequent change affecting code, tests, fixtures, dependencies, runtime configuration, or test discovery requires another complete run before the phase is finished. Evidence-only documentation updates need review, not another test run.
7. **A separate verification agent checks completion before the commit.** It must be independent of the implementing agent; it may be the earlier test-planning agent. It reviews the requirement, actual implementation, final diff, test coverage, and execution evidence. It must map every phase requirement to implemented behavior and relevant executed tests, check that tests were not weakened or silently skipped, and verify the declared execution mode: Phases 01–19 use mocked Laya; Phase 20 must include genuine model execution. A passed mock test is never evidence of a real model call. It cannot approve based only on the implementer's summary or a green test count. It independently reruns the full suite on the final candidate when it has access to the required environment. If it cannot, its verdict must explicitly distinguish independently inspected execution evidence from tests it reran; missing or unverifiable required evidence blocks completion. Resolve blockers; any behavior- or validation-affecting change requires Step 6 and another verification pass.
8. **Make one focused commit.** Include implementation, its tests, usage notes, and the completed phase record. Report the resulting SHA in the external handoff/status message; include it in the next phase's already-planned progress update if useful. Do not leave a post-commit edit just to record a commit's own SHA. Stop before the next phase if a required check failed or was not run.

A phase can be split into smaller commits/phases if it proves too large, but each completed increment follows the same test process. Do not combine several unverified phases into one commit. Revert a faulty committed phase with a normal revert when appropriate; do not rewrite unrelated history or discard user work.

If no independent agent is available, report the missing review and leave the phase's independent-review check pending. Do not claim another agent reviewed it. During this planning task, an independent agent reviews the test strategy only; that does not substitute for the later per-phase reviews.

## What “run all tests” means

During development, a quick subset is fine. At phase boundaries, a subset of the required tests is not enough.

- **From Phase 01:** run every Python unit and mock-based contract/integration test. Use ordinary pytest, not the old runner. The suite must work without MLX, model weights, a compatible GPU, or model-service access.
- **From Phase 02:** include mocked model A/B/A and temperature T1/T2/T1 combinations, default settings, exact SDK arguments, identity, and object reuse. These prove configuration routing and reuse, not actual checkpoint loading.
- **From Phase 10:** also compile/type-check the TypeScript helper, run its entire suite, and run Python-to-Node integration tests against a fresh build. The source helper is real code, not a canned outline response in the main integration tests.
- **From Phases 15–16:** include all hook subprocess/protocol and scenario tests with the Laya boundary mocked. No real Claude session is required to complete these phases.
- **In Phase 20:** run all existing tests plus actual model integration tests. Required real execution that cannot run is reported as blocked for Phase 20; it does not retroactively invalidate earlier verified mock-based phases.
- Include formatter, linter, type-check, and CI checks required by repository instructions. Do not add a large tooling stack merely to create a phase.

Document exact commands once the project exists. For example, early validation can run `python -m pytest tests/unit tests/contract tests/integration`; the final phase adds `tests/real` to the complete invocation. Directories are created when needed, and the actual command must include every accumulated required test. Future real tests are explicitly outside the early phase scope, not silently skipped tests counted as passing. If real tests are drafted early, keep their explicit opt-in entry separate from the default mock suite and record them as deferred.

Record passed, failed, skipped, and not-run counts, test identity changes, execution mode, environment versions, and reviewer conclusions. Unexpected skips, `xfail`, or disabled required tests do not satisfy a gate. Do not reduce coverage because tests take time. A test missing its required environment blocks that phase; real-model hardware is not an early-phase requirement. A deliberate operational-timeout test is different from abandoning a slow suite.

## Mock boundary and fixtures

### Implement the adapter, replace only the external call

The production adapter can be implemented immediately from the supplied `RunConfig` and prediction code. It imports `laya_mlx` lazily, calls `laya.load(model, **kwargs)`, then calls the returned agent's `predict(text, questions, **kwargs)`. A small injected loader or test monkeypatch is sufficient; no provider/plugin framework is needed.

For Phases 01–19, replace that loader with a fake returning a controlled agent. The fake records the actual arguments, exposes explicitly simulated identity/settings where a test needs them, and returns a fresh copy of a raw response fixture. It can also raise planned load/predict errors. Never return a precomputed final decision from the fake: question construction, JSON ingestion, enrichment, rules, answer extraction, blocks, source extraction, and flows must execute their real code.

Mocks should validate expected requests and select fixtures explicitly; do not make the fake infer the answer by parsing the prompt. For multi-call flows, configure an expected request/response sequence so a wrong question, model, temperature, or call order fails clearly. Deep-copy response data on each call so enrichment or caller mutation cannot contaminate later tests. Test that an attempted unconfigured real load fails immediately in mock mode rather than contacting the SDK. Never fall back from failed real mode to a fake success.

The package and mock examples must run without the real SDK installed. Keep real-SDK dependencies optional until the final setup stage. Once written, label the real adapter **implemented, not yet verified against live Laya**.

### What Sharon's examples need to contain

Start with **one complete choice-question request/response pair** to establish the first supported contract. For each example retain:

- Exact input text and named question dictionary sent to `predict`, with the question definition used to produce it if available.
- Requested model ID, temperature (including omitted/default), language, and SDK version/revision when known. Unknown metadata is labelled unknown, not guessed.
- Complete raw response before enrichment, rules, or extraction. Keep every JSON field and distinguish absent fields from explicit nulls.
- Any existing enriched response or interpreted answer as a separate artifact, clearly identified as downstream output.

Use a small `tests/fixtures/laya/` folder with request/config JSON, unchanged raw-response JSON, and a short provenance note. Keep independently specified expected enrichment/decisions in the test or a separate expected fixture, never in the model request. Sanitize sensitive source text before committing, documenting any transformations; retain the unsanitized example only in its authorized private location.

To cover all planned question types, eventually obtain examples of **choice, noul, and score**, plus a **multi-question response** showing the answer-name mapping. One multi-question example can cover several types. Obtain another example whenever a supported model/SDK actually has a different response shape; not every temperature needs a different fixture merely because probabilities vary. Missing fields, rejected rules, exceptions, ties, malformed data, and numerical boundaries can be covered with clearly labelled synthetic fixtures.

Examples are sufficient for the current scope when they cover every supported question/response shape and every field used by its rules/extraction, the full fixture response can be parsed without guessing, and all deterministic contract tests pass. Tell Sharon when that point is reached and request only specific missing cases. This establishes fixture-backed compatibility, not proof that every model behaves identically. Until actual samples arrive, labelled synthetic fixtures can support implementation; record which contracts remain provisional. Do not fabricate a captured Laya response or claim its provenance is real.

### The integration tests Sharon described

These are full-pipeline tests with a mocked Laya boundary. They are useful now and prepare the same contracts for real execution later:

1. Build the actual named question payload from input and definitions; assert exact text, question shape, model, temperature, and language arguments at the SDK boundary.
2. Receive the configured raw response and check the supported version's required fields, names, types, and numerical values. Required versus optional metadata is grounded in supplied samples and source, not invented.
3. Serialize to strict JSON and parse it again, preserving relevant data and keys. If runtime numeric values later need explicit conversion, test that conversion instead of stringifying the entire response.
4. Run the actual enrichment, load the named rules, evaluate acceptance, and extract the answer or an explicit undecided/error result.
5. Check that the block/flow consumes that result correctly, with no ground-truth labels or rules leaking into the model request. Extend to source and hook subprocess paths as those features arrive.

Validate the `answers` mapping and requested names; supported prediction type; choice membership/probability keys; finite noul values in range; score/legend consistency; and fields used by each selected rule. Probability tolerance and numeric ranges must match the established schema. Reject malformed/non-finite required data, or return the documented safe undecided/error result; never accept it as usable context. Add negative cases even if real responses rarely contain those faults.

**Mock tests have exact expected outcomes.** A fixed raw response must produce the independently calculated enrichment, accepted answer, rejection reason, or no-op. Do not call production extraction code to generate its own expected answer. Use fixtures for accepted decisions, alternate labels, abstention, missing data, and different confidence patterns. Clear prompts make examples readable; the fake's answer is fixture data, not a claim about model accuracy.

**Final real tests must allow different valid model answers.** Reuse the request/response/ingestion contracts with a real loader, then independently calculate the correct downstream result from the response actually returned. Do not require “apple” merely because a mock fixture returned “apple.” A valid alternative label can pass; an unsupported label, missing required field, or wrong rule calculation cannot. A legitimate policy rejection must remain undecided. Guarantee acceptance-path coverage with deterministic fixtures; do not weaken production rules to force a real response through them. Semantic accuracy is a separate later evaluation, not this integration gate.

### Agent settings and evidence

Early tests use simulated metadata and exact load/predict argument assertions for model A/B/A, default versus explicit temperatures, T1/T2/T1, and language. Verify same-key object identity, distinct objects for different configurations, failed-load recovery, no mutation leakage, and fresh registries/processes. These do not prove real model identity or effective temperature.

In Phase 20, inspect metadata on actual returned agents. The supplied source reads `model_id`, `model_dir`, `revision`, and `temperature`; verify their actual availability and meaning then. Compare requested and resolved IDs/settings, allowing explicit documented alias mappings. Do not write metadata onto an agent to make a test pass or treat wrapper-echoed settings as proof. If a setting is not exposed, investigate the real loader/configuration path and record the evidence or unresolved limitation.

Before every phase-finalizing commit, the separate verifier inspects command, exit status, test IDs/counts, fixture provenance, execution mode, settings combinations, JSON/decision outcomes, candidate code identity, and unresolved gaps. A compact phase record suffices. Its verdict is **VERIFIED for the stated phase scope** or **BLOCKED**. Phases 01–19 may be verified while real compatibility is explicitly deferred. Phase 20 cannot claim real verification using cached fixtures or mocks.

## Keep existing tests

Tests accumulate as the project grows. Existing regression tests should remain unchanged by default.

- A refactor preserves behavior, so its contract tests and expectations should still hold. Mechanical import updates may be necessary, but cannot weaken what the test asserts.
- A deliberate behavior change may require a test change. Record the old contract, new requirement, affected test, and why the old expectation no longer applies. The independent reviewer checks that explanation.
- A demonstrably incorrect test can be corrected with evidence; do not force correct code to preserve a mistaken oracle. Retain coverage of the original scenario and record the correction.
- Removing a feature does not justify silently deleting its safety coverage. Replace it with a test of the new supported behavior or explicit unsupported result.
- Never change deterministic fixture expectations simply to make a failure pass, loosen numerical tolerances after seeing a failure, or regenerate snapshots blindly. Real integration tests do not require a fixed semantic label; any later model-accuracy dataset keeps its separate, independently defined labels.
- New bug fixes should add a reproducing regression case. Test renames and moves should preserve traceability; do not rely on total test counts alone to detect lost coverage.

## Preserve the existing Laya contract

Preserve the supplied source behavior for valid inputs:

- Default model: `aac6fef/laya-typed-decisions-mlx`.
- `temperature=None` means no load override. A supplied temperature becomes `lang_temperatures={lang: {"temperature": [t, t, t]}}`.
- The original prediction path sends `lang` only when temperature is supplied. Preserve this while extracting; investigate any change separately.
- Prediction uses `agent.predict(text, questions, **kwargs)` and reads the named entries under `answers`.
- Both choice and score receive gap/entropy enrichment. Noul receives distance from `0.5`. Derived fields round to four decimals.
- Score answer extraction uses Python `round(score)`, clamping, and a zero-based string-key legend lookup. It is not argmax or generic high/low classification.
- The acceptance helper returns `(bool, reason)`. Always unpack it; the tuple itself is truthy even when its first member is false.

During Phases 01–19, compare exact request arguments and deterministic processing of the same raw response between the original reusable functions and the new code. Preserve input text, question definitions, candidate order, settings, rounding, and extraction semantics. This is request/post-processing parity, not proof of equal real predictions or model accuracy. Do not import the old runner to gain this coverage.

Record SDK/Python versions and model revisions from Sharon's examples when available; missing live environment metadata does not block early implementation. The original test-case definitions and raw run datasets are absent from the ZIP. Recover the working method question when available, or explicitly establish a provisional new definition. Do not label illustrative handoff JSON as the original tested question. Final real execution verifies the established contract with the supported model/SDK; cross-model answer equality is not required.

## Before Phase 01: repository and fixture check

This happens later, after Sharon supplies the repository and asks implementation to begin. It is a preflight, not an empty scaffold commit.

- Confirm repository, branch, local instructions, and existing files. Preserve existing project structure and unrelated changes.
- Obtain the original ZIP and identify reusable source. Do not restore cached bytecode or copy the runner package wholesale.
- Inventory supplied request/raw-response examples and record their provenance. Start with a choice pair when provided; use labelled synthetic fixtures for missing examples without claiming live compatibility.
- Set up the portable Python test environment. No model weights, MLX host, download, live SDK import, or inference is required. Node/TypeScript setup comes when the extractor is added.
- The plan grants no instruction to push now. Later pushes target the repository and branch Sharon supplies and preserve its review/CI workflow.

## Phase 01 — one question through a mocked Laya call

**Goal:** implement and test the smallest call contract before building abstractions.

**Build:** minimal Python package/test setup, one small prediction adapter based on the supplied code, and a direct example using an explicit mock loader. Use the existing default model setting and an inline choice question, such as identifying a fruit. The fake returns a complete raw fixture, not an already extracted answer. No blocks, rules, registry, AST, or hooks yet. Keep the SDK import inside the real load path so package import is portable.

**Files introduced:** `pyproject.toml`, `laya/predict.py`, `examples/basic_question.py`, initial tests/fixtures, README, and phase/progress records. Package paths live under `src/laya_context_router/`. Follow the repository's existing dependency conventions; no mandatory MLX install for mock tests.

**Tests before completion:** exact model ID/input/question/kwargs captured by a fake loader/agent; raw response preserved; named answer and required initial shape usable; strict JSON round-trip; missing/invalid response and load/predict errors explicit; fake responses isolated between calls; package import and mock example work without `laya_mlx`; accidental real access fails instead of loading. The example and tests call the same adapter.

**Completion:** full mock-based Python suite plus independent verification. Record captured versus synthetic fixture coverage and the real adapter's unverified status. No real call is required or claimed. **Commit:** `feat: add Laya adapter with mocked contract tests`.

## Phase 02 — model settings and reuse within one run

**Goal:** support model/temperature changes and verify routing and object reuse without loading a model.

**Build:** extract the existing `RunConfig`; add a small registry owned by one invocation and reuse agents by `(model, temperature, lang)`. Keep the simple Phase 01 call available. No service or persistent worker.

**Tests before completion:** mocked A/B/A identities and load counts; same-key object identity; T1/T2/T1; language and default settings; exact original load/predict kwargs; `None` versus explicit zero as a forwarding/cache test, without claiming zero is supported by real inference; failed-load recovery; separate registry/process lifetimes; stale-config and global-state leakage protection. Return controlled raw JSON at different settings and verify it remains ingestible. Simulated metadata must be labelled as such.

**Completion:** complete accumulated mock suite, original-argument parity, and independent verification. No second real model, live metadata, or MLX host is required. Actual model/settings verification remains in Phase 20. **Commit:** `feat: reuse configured Laya agents per invocation`.

## Phase 03 — question definitions from JSON

**Goal:** move the same verified question out of inline code without changing its model payload.

**Build:** selected question classes and loader in `questions/models.py` and `questions/load.py`. Remove the old `evaluate()` methods. Support the existing single-definition/list loader inputs; block `questions.json` files will consistently use a list.

**Tests before completion:** choice/noul/score round-trips; exact `to_predict_dict()` payloads; name as outer response key rather than model-body field; ordered criteria preserved; duplicate names and invalid types/criteria rejected; missing file/malformed JSON; independent instances do not accidentally share mutable candidate lists. The JSON-loaded form produces the same exact SDK request and fixture-derived result as the inline Phase 01 form, with Laya mocked.

**Completion:** full suite; no question wording change hidden in serialization. **Commit:** `feat: load typed question definitions from JSON`.

## Phase 04 — enrich predictions

**Goal:** add the existing derived fields without changing inference.

**Build:** reuse `answers/enrich.py`. Preserve its mathematics; enrich a copy where the caller also retains raw data. Define explicit invalid-data handling at the boundary.

**Tests before completion:** choice and score gap/entropy for concentrated, uniform, tied, zero-probability, and near-threshold distributions; noul values at zero, one, and `0.5`; four-decimal rounding; missing and singleton distributions; raw response unchanged; malformed/non-finite inputs produce explicit errors rather than trusted answers. Compare valid-input results to the original enrichment functions and hand-calculated examples.

**Completion:** full suite and unchanged raw fixture responses. **Commit:** `feat: enrich Laya predictions with confidence signals`.

## Phase 05 — shared rule evaluation

**Goal:** reuse rule conditions and per-type acceptance without a test evaluator.

**Build:** `answers/conditions.py` and `answers/rules.py` using existing `OPS`, field lookup, `RulesConfig`, and acceptance evaluation. At this phase test inner policy objects directly. Do not introduce a competing block file format; the canonical outer loader arrives in Phase 07.

**Tests before completion:** every operator; nested dictionary paths; universal AND type-specific conditions; first-failure reason; absent type-specific entries; explicitly empty conditions; unknown operators; missing versus explicit-null behavior; failed upper-bound conditions still use the legacy reason name; correct tuple unpacking. Document the old `eq`/null behavior and reject malformed configurations at the new boundary rather than claiming all missing fields always fail.

**Completion:** full suite and compatibility on the supplied valid v2 policy objects. **Commit:** `feat: apply shared and type-specific answer rules`.

## Phase 06 — extract decisions without expected answers

**Goal:** turn model predictions into usable runtime decisions.

**Build:** reuse only `extract_answer()` from the evaluator; add a small interpreter composing enrichment, rule evaluation, and answer mapping. Iterate requested questions, not the old `expect` map. Validate response type, choice membership, and score legend before accepting data.

**Tests before completion:** choice labels; noul just below/at/above `0.5`; score rounding at `1.5` and `2.5`, bounds, and legend lookup; policy rejection; missing answers; mismatched/unknown prediction types; invalid legends; accepted `none_or_unclear` distinct from policy `undecided`; all requested questions returned when there is no ground truth; raw data preserved. Verify numerical boundary cases after four-decimal enrichment rounding.

**Completion:** full suite; no dependency on `TestCase`, expected labels, or reports. **Commit:** `feat: interpret named predictions without ground truth`.

## Phase 07 — one reusable block with multiple questions

**Goal:** finish the reusable block contract on a tiny example before code routing.

**Build:** one small example block with `questions.json`, `rules.json`, `block.py`, and `README.md`. Implement the `rules_by_question` loader by calling existing `RulesConfig.from_dict()` for each inner value. Use the same envelope for one or multiple questions. The block receives input, model settings, and the invocation registry; matching questions share one model call.

**Tests before completion:** one-question and multiple-question files use the same schema; exact question-name binding; missing/unknown policy keys rejected; duplicate JSON mapping keys detected rather than silently overwritten; inner policy names need not equal question names; policy conditions apply only to their named answer; request contains no rules/expected answers; one failed decision does not overwrite another; two calls reuse the configured agent. Run the complete two-question path with mocked models/settings, validate raw JSON through final decisions, and compare exact SDK arguments to the original call contract. Include independently calculated accepted, rejected, and mixed outcomes; do not mock the interpreter.

**Completion:** full suite and a README showing exact input/output. **Commit:** `feat: add reusable multi-question blocks with named rules`.

## Phase 08 — detect code-file mentions

**Goal:** extract candidate references without reading files or asking Laya.

**Build:** `building_blocks/file_reference_utils.py`, accepting text and an external regex with a documented path capture. Return all references in order with filename/path-as-written and a lexical kind. Do not assume every mention is a read target.

**Tests before completion:** no references; basename/relative/absolute paths; backticks, quotes, punctuation, line suffixes; multiple mentions and duplicates; `.spec.ts` versus `.ts`; declaration files; non-code extensions; configurable patterns; invalid pattern/capture; paths with spaces where supported. If syntax is unsupported, report or reject it explicitly rather than incorrectly resolving a partial path. A filename inside a log remains a mention, not proof of task intent.

**Completion:** full suite; no filesystem reads in this detector. **Commit:** `feat: detect explicit code references with configurable regex`.

## Phase 09 — resolve one production file

**Goal:** resolve candidates deterministically and avoid selecting the wrong file.

**Build:** `building_blocks/resolve_file.py` with explicit cwd and repository root. Exact path first; basename lookup only when needed. Keep code reads within the configured repository boundary for the initial flow. Missing, ambiguous, excluded, and inaccessible results remain distinguishable.

**Tests before completion:** nested cwd; unique/duplicate basenames; exact relative/absolute paths; missing files/directories; `.spec.ts`/declaration exclusions; traversal and symlink escape; Unicode/spaces; no arbitrary first match; repository unchanged. Use temporary fixtures, not Sharon's real repository.

**Completion:** full suite; ambiguous inputs produce no selected file. **Commit:** `feat: resolve production files with ambiguity handling`.

## Phase 10 — smallest TypeScript extractor and Python bridge

**Goal:** prove Python can ask Node for an outline and receive valid JSON.

**Build:** pinned TypeScript helper dependencies, a JSON CLI, and `building_blocks/typescript.py`. Initially support a documented subset: ordinary named function implementations in a fixture file. Flag unsupported callable forms; do not label the outline comprehensive yet. Parse source without importing or executing it.

**Tests before completion:** function names/signatures/locations; empty file and parser errors; unsupported class/arrow forms reported; Python-to-Node request/response fidelity; spaces in paths; nonzero exit, malformed stdout, missing Node/build, and bounded process timeout. Pass subprocess arguments as an array, not a shell-built command. Stdout is protocol JSON; diagnostics use stderr.

**Completion:** complete Python suite, fresh TypeScript build/type-check, complete TypeScript suite, and bridge integration checks. **Commit:** `feat: extract basic TypeScript outlines through a JSON helper`.

## Phase 11 — retrieve the exact selected function

**Goal:** return original source text for a supported callable, not reconstructed code.

**Build:** a callable-ID/source-range lookup and an initial context result containing exact raw code, file path, location, and explicit coverage limitations. Define whether attached comments/decorators are included; retain precise raw ranges either way. Line-numbered display text is a separate field, never inserted into raw `code`.

**Tests before completion:** source-slice equality; LF/CRLF; Unicode before/inside the function; same-named functions in separate supported fixture files; invalid/outdated IDs; file changed between outline and extraction; comment boundaries; empty/unsupported implementation; no writes. Scoped duplicate-name tests use only forms already supported by Phase 10; other forms assert an explicit unsupported diagnostic until Phase 17. Handle TypeScript UTF-16 offsets and Python indexing deliberately rather than assuming they are interchangeable.

**Completion:** full accumulated suite; source text round-trips exactly. **Commit:** `feat: return exact callable source with provenance`.

## Phase 12 — method-selection block

**Goal:** replace the toy decision with Sharon's first useful code question.

**Build:** `building_blocks/questions/method_selection/` with the same four-file block contract. Build dynamic candidate IDs/criteria from the outline. Start with the working signature representation; keep an explicit no-single-match choice. Preserve a candidate-to-source map outside the model payload. If the original working definition is unavailable, document the new baseline instead of claiming equivalence.

**Tests before completion:** dynamic criteria assembled correctly; empty candidate list does not call Laya; duplicate names have distinct IDs; selected ID maps to the right range; unknown selected IDs rejected; abstention preserved; caller's question templates are not mutated; long-input/candidate-budget handling is explicit, not silent truncation. Add fixed prompt/request/response cases for a clear match, noise, no match, and multiple plausible methods. Mock only the Laya response and verify candidate mapping and policy behavior exactly. Keep expected decisions outside inference inputs; compare original request formatting where exact definitions are available. This does not establish real method-selection accuracy.

**Completion:** full suite with request and deterministic post-processing parity; real model accuracy remains unmeasured. **Commit:** `feat: select methods from dynamic source candidates`.

## Phase 13 — first ordinary Python flow

**Goal:** run detection → resolution → outline → Laya → selected code without hooks.

**Build:** `flows/file_method_context.py` and a direct example. Restrict the first flow to a documented explanation request for one explicit production file. Return a context result or a reasoned no-op. Do not infer read intent merely from a filename. Start with an explicit narrow trigger/eligibility contract; a general role classifier is later work.

**Tests before completion:** complete fixture flow with controlled model responses; no file, several files, ambiguous basename, test/declaration file, output-only request, incidental log mention, malformed extractor output, undecided choice, and stale source; no mutation of input or repository; a real temporary source-file path through the actual Node helper and Python flow, with only the Laya SDK boundary mocked. The original Phase 01 contract tests remain in the full suite.

**Completion:** full suite and a useful offline example. The returned bundle clearly states that dependency context is not yet complete. **Commit:** `feat: compose the first file-method context flow`.

## Phase 14 — multiple blocks and a bounded second round

**Goal:** prove that a flow can branch between questions and ordinary code without building a workflow framework.

**Build:** one explicit second-round branch. For example, a decided multi-method signal can return a no-op; an undecided first selection may trigger one fixed fallback representation and one further call. Use at most two rounds with an explicit input budget. Keep the first-round baseline unchanged. Different model/config selections use the same registry interface.

**Tests before completion:** accepted first round makes no second call; explicit negative/ambiguous outcomes are not overridden accidentally; second-round input reflects the intended code transformation; separate question policies stay associated with the correct answers; A/B/A reuse verified with controlled agent objects and SDK-boundary spies; exceptions/abstention terminate; no unbounded retries. Include at least one composition test using two distinct block identities and independently bound policies, not merely two calls to the same block. Reuse the existing example block or a tiny second fixture block for this check; do not duplicate shared inference code. Run the actual flow with different configured mock models/settings for successive calls. Verify full request/response sequences and branch termination. Keep a fallback that changes the model input representation disabled by default until separately evaluated; mock success proves mechanics, not improved answer quality.

**Completion:** full suite. A fallback without evidence of benefit remains disabled, with its bounded composition contract tested. **Commit:** `feat: support bounded multi-question flow branches`.

## Phase 15 — hook adapter, tested without installing it

**Goal:** make the existing flow callable through a Bash-launched Python script.

**Build:** only `hooks/user_prompt_submit.py`. At implementation time, verify the target harness version's documented stdin/output contract; a local harness installation is not required for this phase. Parse input, invoke the flow, serialize supported additional context or a no-op. Do not install into Sharon's normal session yet. Do not assume arbitrary prompt replacement or tool-output interception is supported.

**Tests before completion:** subprocess stdin-to-stdout integration; missing/invalid hook fields; nested cwd; unsupported events if relevant; original prompt preserved; exact JSON output shape; no debug/model-loading text on stdout; stderr diagnostics; bounded failure behavior; source/model errors do not block the user's prompt unintentionally. Use a temporary repository and captured/synthetic protocol fixtures checked against current documentation. Use mocked Laya load/predict calls in every subprocess; no real model or harness activation is required.

**Completion:** full suite and protocol-correct script behavior, with no real harness activation. **Commit:** `feat: add a tested prompt hook adapter`.

## Phase 16 — complete isolated hook scenarios with mocked Laya

**Goal:** prove the hook script carries the complete flow through the documented protocol in a disposable fixture repository.

**Build:** a small subprocess-based scenario example and enable/disable instructions for later actual use. Extend Phase 15 from protocol boundaries to complete source-to-context scenarios. Do not install hooks in Sharon's session or start a real harness as a requirement here.

**Tests before completion:** supply a realistic hook input; run the actual adapter, flow, TypeScript helper, question construction, enrichment, rules, and extraction with only Laya mocked; check exact output context or documented no-op. Cover supported explanation, unmatched prompt, rejected prediction, model/extractor failure, stdout purity, independent invocation lifetimes, and unchanged tracked source fixtures. Test disable/config instructions where possible without claiming observed Claude behavior.

**Completion:** full accumulated mock/contract/source/hook suite and independent review. Report protocol behavior as verified and actual Claude delivery as unverified. Real-harness delivery belongs to the final environment stage if authorized and available. **Commit:** `test: cover complete hook scenarios with mocked Laya`.

**Post-16 hook hardening (handoff correction, separate verified commit):** retain the
existing additive `hookSpecificOutput.hookEventName` plus string
`additionalContext` contract. Isolate both Python and native file-descriptor-1
progress output during synchronous SDK work, then emit exactly one JSON response
or empty stdout/exit 0. Test native writes in load and predict, success and
failure; missing/ambiguous files; unrelated event fields; load/predict deadline
and whole-rendered-context budgets including Unicode and metadata. Document
synthetic stdin/output/no-op examples, actual required CLI arguments, project-local
synchronous command settings, and the unverified harness boundary. No real
model or Claude activation is required for this follow-up.

## Phase 17 — broader production callable coverage

**Goal:** extend outline/extraction beyond the initial function subset.

**Build:** recursive callable discovery in small groups. If needed, split this phase into 17a classes, 17b expressions/objects, and 17c nested/special forms; each group is its own verified commit using the full process.

**Tests before completion:** instance/static/private methods; constructors; getters/setters; async/generator functions; class-field arrows; variable-bound functions; object methods/function properties; nested functions/callbacks; anonymous defaults; class expressions; computed names; overload signatures distinguished from implementation bodies. Test duplicate names, scope identity, abstract/declaration-only forms, parser diagnostics, and source fidelity for every supported form. Unsupported forms remain visible diagnostics.

**Completion:** full suite at every subphase; do not claim “all methods” until the advertised fixture matrix passes. **Commit:** `feat: expand production callable extraction coverage` (or focused commits per group).

## Phase 18 — imports, constants, and same-file dependencies

**Goal:** give useful surrounding context without overstating completeness.

**Build:** symbol-aware references to relevant imports, module constants/types, class fields, and direct same-file callees. Preserve original statements. Mark unresolved/dynamic calls and bounded omissions. Continue to return the selected method even when the surrounding context is incomplete, clearly labelled as partial.

**Tests before completion:** aliasing, shadowed identifiers, same-spelling unrelated symbols, mutable globals, closure captures, constructors/fields, cycles, computed/dynamic calls, side-effect imports, stable deduplication, depth/size limits, deterministic order, raw-text fidelity. Test inclusion and exclusion with manually reviewed dependency fixtures; string-name matching alone is not sufficient evidence of resolution.

**Completion:** full suite including mock-based hook scenarios; manually inspect dependency context against the fixture source, without claiming model explanation quality or universal sufficiency. **Commit:** `feat: include bounded local method dependencies`.

Keep three budgets distinct: model question input, source/dependency collection,
and final hook `additionalContext` rendering. Carry complete selected code or
refuse output; never cut a method mid-code or silently imply omitted dependencies
were included. Exercise final hook output with oversized dependency bundles and
explicit partial-coverage/gap information. Deterministic omission of complete
dependency units is allowed only when the resulting context labels those gaps.

## Phase 19 — cross-file context and explicit gaps

**Goal:** resolve dependencies where the original report suggested enrichment may help most.

**Build:** project-aware resolution using the actual TypeScript configuration; direct project-file callees, with bounded caller context if reliable. Missing configs, external packages, declarations without implementations, unresolved dispatch, and budget limits remain explicit gaps. Do not load arbitrary package implementations by default or execute project modules.

**Tests before completion:** relative imports, aliases/re-exports, path mappings, missing modules/configuration, external declaration-only dependencies, inherited/dynamic targets, cycles, shared dependencies, module side effects, repository boundary enforcement, partial caller coverage, and stable budgets. Verify that omitted/unresolved references do not become “no dependencies.”

**Completion:** full accumulated mock-based suite; same-file and cross-file context fixtures reviewed for correct source coverage and explicit omissions. Model explanation quality is not an early gate. **Commit:** `feat: add bounded cross-file context resolution`.

Repeat hook-level rendering tests with cross-file bundles, re-exports and
unresolved references. Stay below the configured final context ceiling or emit
the documented no-op; no automatic overflow/file offload may count as full inline
method delivery. Keep exact selected source and provenance in successful output.

## Phase 20 — final integration with actual Laya

**Goal:** after the supporting code, reusable blocks, flows, source helper, and hook protocol work with mocks, verify the same contracts using real model calls.

**Build:** enable the existing real loader on a supported environment and add the final real-test entry point using the shared contract checks. No replacement of the pipeline or new runner is needed. Confirm actual model IDs, SDK version, settings, and fixture compatibility; preserve the earlier mock suite. Explicit real mode must fail clearly if the runtime or weights are unavailable, never silently return a fixture.

**Tests before completion:**

- Execute a real request and ingest the complete response. Confirm named questions, required fields/types, strict JSON round-trip, enrichment, named-rule evaluation, extraction, and usable accepted/undecided/error handling. For a valid response, independently compute the expected processing result from the returned values; do not insist on a preselected model label.
- Cover the supported choice/noul/score contracts and at least one multi-question call. Use easy, readable questions; their intended semantic answers may be recorded for observation, but are not integration pass/fail labels.
- Retain the requested configuration coverage: two distinct compatible real checkpoints, each with default settings and at least two supported explicit temperatures. Confirm actual IDs/settings before running; do not invent model B, assume arbitrary temperatures are supported, or count two aliases of the same checkpoint as distinct models. Different valid predictions across models or temperatures are allowed.
- Inspect actual agent identity/settings and run real A/B/A and T1/T2/T1 reuse checks in one invocation. Ask the original agent again after other configurations to expose leakage. Verify a new invocation loads its own object. Record metadata limitations instead of echoing requested configuration as proof.
- Run a real block and flow through the actual source helper. If selection is valid and accepted, verify exact selected source; if rules reject or no single method is selected, verify the correct no-op. Deterministic mock tests continue to guarantee all branches are covered.
- Run the complete accumulated mock, TypeScript, subprocess, and real suites before the finalizing commit. Time alone is not a reason to omit required cases. Do not regenerate captured fixtures or adjust rules solely to accommodate a surprising real answer.

If a real response differs structurally from the established schema, add a version/model-specific fixture and make an explicit reviewed compatibility fix. Preserve previous fixtures and tests. Re-run all required checks after any code or validation change. Missing runtime, a second compatible checkpoint, or unverifiable required settings leaves this final real-verification milestone blocked or partially executed; it does not turn prior mock results into failures or authorize fake substitutions.

Actual Claude harness delivery is authorized as an isolated project-local check
in a disposable repository after backend compatibility is established. Record
candidate commit, date, `claude --version`, exact command/settings and debug-log
location. Inspect `/hooks` registration and debug evidence of hook execution,
JSON parsing or rejection, timeout and overflow behavior. The protocol subprocess
test alone is not proof that Claude received the string. In a diagnostic-only
path, generate a fresh unpredictable marker inside the hook and retain the
expected value outside the model-visible prompt, conversation and readable
source. Ask the matching prompt to return the marker without tools, inspect
the transcript for alternate reads, then repeat with the hook disabled in a
fresh session and another fresh marker. Record exact matches and controls,
unmatched/no-op behavior, unchanged tracked source, and any unresolved access
path. Remove the diagnostic path before normal use. A marker match supports
context availability, not proof that Claude used every code line or that Laya
selected correctly; a mismatch requires diagnosis. Report four outcomes
separately: mock protocol, mock full flow, actual Claude delivery, and real Laya
compatibility. Missing harness access or real model support stays explicitly
blocked/unrun, never reported as a pass. Normal/global hook activation remains
outside this isolated check.

**Completion:** all required accumulated suites pass, the separate verifier confirms genuine model execution and response handling, and any in-scope harness check has its own verified outcome. Record the supported models/settings and remaining gaps. This proves implementation compatibility, not fixed answers, equal accuracy across models, policy calibration, or token savings. **Commit:** `test: verify Laya integration with actual models`.

## Work deliberately left for later

Full method bodies as Laya candidate input, broad source/output-role classification, test-file extraction, automatic policy tuning, model-accuracy benchmarks, extensive caller analysis, tool manipulation, and persistent agents are separate features/experiments. They do not block a useful first version. The earlier report's weak reference-role results are not fixed merely by changing thresholds.

When experimenting with full method bodies, keep the signature baseline and tests intact. Add a separately named representation with paired cases and input-budget checks. Do not change the default under a refactoring commit. Mock tests establish request construction and processing; deciding whether the new representation improves selection needs a separate real-model evaluation after real integration is available.

## Compact phase record template

Each `docs/phases/phase-NN.md` should contain:

```text
Phase and objective:
Starting commit / environment:
Independent test-planning agent:
Independent final verification agent:
Scope and observable contracts:
Tests to add, including boundaries and failures:
Expected results and their source:
Existing tests or expectations changed, with reason:
Implementation files changed:
Full-suite commands and actual results:
Passed / failed / skipped / not-run:
Model/SDK and harness versions where applicable:
Execution mode: mocked SDK boundary or actual model:
Fixture provenance and contracts still provisional:
Executed model/settings combinations (simulated or actual):
Requested versus observed identity/settings; evidence limitations:
JSON, enrichment, rule, and extraction outcomes:
Real Laya compatibility: deferred until Phase 20 / verified / blocked:
Candidate code identity and evidence timestamps:
Independent review findings and resolutions:
Verifier verdict: VERIFIED for stated phase scope or BLOCKED
Decision: COMPLETE or BLOCKED
Known limitations carried forward:
```

Keep test evidence small and reviewable. Do not commit model weights, local caches, credentials, private repository source copied into fixtures, or long raw session transcripts. Use purpose-built synthetic TypeScript fixtures for shared tests.

## Autonomous work and recommended Sharon checkpoints

Once Sharon authorizes implementation for the supplied repository, the implementing agent can independently inspect code, extract the agreed helpers, create fixtures, write tests, run the complete required suite with Laya mocked through Phase 19, fix in-scope defects, coordinate the independent test/verification agents, update phase notes, and make the agreed local phase commits. All of this remains subject to repository instructions and the verification checks. Long runtime alone is not a reason to stop the tests or ask for permission again.

Do not stop for approval on every internal file or ordinary test addition. The following are recommended product-review checkpoints; they do not silently create new mandatory approval requirements. Sharon can choose which to use when implementation begins.

1. **After Phase 02 — adapter/settings and fixture contract.** Show the exact request, raw mock response, simulated settings/reuse evidence, fixture provenance, and full-suite result. Confirm Sharon’s examples are represented correctly and identify any missing schema cases. Do not present simulated metadata as actual model evidence.
2. **After Phase 07 — the block contract.** Show one block's four files, a multi-question input, matching rules, and the final named decisions. Confirm that adding a question or selecting different rules is as simple as Sharon expects before building many blocks.
3. **After Phase 13 — the first useful offline flow.** Show the prompt, resolved production file, candidates, method chosen by a controlled response, exact returned code, and no-op behavior. Let Sharon inspect the output format and context; make clear that selection accuracy is not yet evaluated.
4. **Before enabling hooks in Sharon's normal development repository/session.** First show the tested adapter, exact supported output, failure/no-op behavior, and a simple disable path. Phase 16 proves subprocess behavior, not actual session delivery. An isolated real-harness check is deferred to the final environment stage; passing it does not authorize changing global settings or activating the hook everywhere.
5. **After Phase 19 / before Phase 20 — readiness for real calls.** Review the completed mock-based system, same-file/cross-file context, fixture coverage, and remaining schema gaps. Confirm the supplied real environment and compatible model/settings choices before entering the final stage. This is the main recommended handoff checkpoint; do not infer permission to start real calls from completion of an early phase. If Sharon has already authorized the full implementation including Phase 20 and its model/setup scope, proceed when prerequisites pass without asking again.

At each chosen checkpoint, present the working result, commit identifier, relevant test evidence, and remaining limitations. Ask about a concrete result, not a hypothetical design before doing the authorized work. If Sharon already authorized activation or pushing to a specified branch, do not ask again merely because a checkpoint is listed here.

Separately surface genuine scope decisions: changing the public JSON contract, replacing the Laya runtime, changing baseline questions or score semantics, enabling a new fallback policy by default, introducing cost/resource commitments beyond the agreed setup, or weakening the required tests. Technical failures first trigger an in-scope repair attempt; an unresolved requirement is reported as blocked rather than bypassed. Missing real-model hardware or checkpoints is relevant to Phase 20, not a reason to block Phases 01–19.

## Where to stop and report

Stop promotion when a regression remains, the current phase’s required environment is unavailable, a deterministic fixture expectation or numerical tolerance would need an unexplained change, or independent review finds a blocker. In Phase 20, unsupported response structure or incorrect processing is a defect; a different valid semantic model answer alone is not. Report the exact failing check and the smallest proposed correction. Continue fixing within the current phase; do not start the next feature to work around it.

Once a phase is fully verified, the later implementation can proceed to the next authorized phase without a routine approval question. This current request authorizes writing the plan only. Repository implementation and pushing begin after Sharon supplies the repository and instructs that work to start.

## Evidence and review status

This roadmap is based on the inspected ZIP, the prior handoff's `02-project-design.md` and `05-next-agent-checklist.md`, and the subsequent discussion refining blocks and hooks. It is a plan, not a record of completed product tests. The source contains reusable config/question/enrichment/rule/extraction pieces; the new adapter boundary, blocks/flows, and TypeScript helper still need implementation.

The initial independent test-strategy review was incorporated. Sharon then superseded live-first execution with mock-first implementation and final-stage real integration. The current revision keeps independent pre-commit verification, distinguishes mock evidence from real evidence, and permits variable real answers while requiring correct JSON ingestion and rule-derived outcomes.

**Independent review of the complete mock-first revision is complete.** The reviewer found no mock-first sequencing blockers. Clarifications were incorporated so early hook work does not require an installed harness and previously authorized final-stage work does not trigger another permission request. Final multi-model/temperature coverage retains Sharon's preceding explicit request, deferred to Phase 20. Document validation checked phase numbering, required phase fields, code-fence balance, and JSON examples. These are planning/document checks only; no future project tests or real models were executed.
