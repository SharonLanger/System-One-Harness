# LAYA first method-context flow — detailed test plan

Date: 2026-10-31  
Status: non-token first-flow coverage implemented; sandbox cleanup authorized and executed.
Design: [First-flow design and Sol handoff](https://chatgpt.com/library?file_id=libfile_8162b9ed215c8191a1c195013523bfe0&account_id=personal).

The original plan lists 61 case IDs, including future tokenizer proposals. Current first-flow coverage is implemented as 122 tests with mocked public building blocks and real deterministic utilities. Token-specific cases remain separate future work, not acceptance requirements for this cleanup. Existing test edits are authorized for sandbox retirement and migration of useful shared hook checks.

## 1. Test boundary and files

Test the new flow's orchestration. Replace both public LAYA building-block calls with fixed results or declared exceptions:

- `building_blocks.questions.requested_action.block.run`
- `building_blocks.questions.method_selection_v2.block.run`

Do not invoke their real preparation, questions, rules, inference, or confidence interpretation. Do not mock the model SDK as a substitute for mocking these block boundaries. The suite must not load a model or download weights.

Run the real deterministic detector, resolver, outline, extractor, and outgoing navigator. Exercise real hook dispatchers and serialization in integration cases. Narrow fault injection is permitted only when a named case requires a failure that cannot be produced reliably by a fixture; restore the original function afterward. Do not replace utility success paths with canned dictionaries.

Use only new files, for example:

| New location | Purpose |
|---|---|
| `tests/first_flow/conftest.py` | Temporary fixture copies, block-result builders, call recording, model tripwires |
| `tests/first_flow/test_flow.py` | Setup, root gates, routing, extraction/navigation |
| `tests/first_flow/test_formatting.py` | Literal output, source fidelity, budget boundaries |
| `tests/first_flow/test_token_handling.py` | Existing token-result/error consumption |
| `tests/first_flow/test_hook_integration.py` | Exact payload logging and actual hook chain |
| `tests/fixtures/first_flow_project/` | Independent copy of the connected example project |
| `tests/fixtures/first_flow_expected/` | Independently authored expected strings and flow-specific edge data |

Do not modify top-level test configuration, shared conftest files, old test helpers, old snapshots, experiment tests, or example runners. Test support must not globally affect tests outside this new directory.

Ask Astra for focused mitigation only when an unexpected unresolved issue needs judgment.

## 2. Fixture setup and independent oracles

Copy the source fixture once during implementation:

```text
experiments/fixtures/connected_project/
    -> tests/fixtures/first_flow_project/
```

The source of the copy is read-only. Preserve imports, directory structure, and tsconfig. Record origin path and commit in the copied README. Every test uses a fresh temporary copy of this new test-owned fixture; tests must not read from experiments at runtime.

Reviewed origin commit: `223b83b90c7c8f3b397c17f80f48908b579a8556`.

Baseline literal expectations:

| Item | Expected |
|---|---|
| Selected file | `src/billing/invoice-service.ts` |
| Selected method | `calculateInvoiceTotalWithAdjustment` |
| Selected definition | Lines 21–24 |
| Direct callee | `calculateInvoiceTotal`, same file, lines 6–19 |
| Direct callee | `roundToCents`, `src/utils/rounding.ts`, lines 1–3 |
| Full expected payload | The literal example in design section 7 |

Setup may call the real outline to obtain the selected opaque ID for the known fixture method. Reset counters before the flow call. The block stub returns that ID and the existing result shape. Do not hardcode a hash-derived ID, choose a different method during the stub, or use the formatter under test to construct the expected output.

Author the golden text independently. Check exact method bytes against the source fixture and the golden string. Add temporary variants for duplicate method names, repeated calls, no calls, excluded files, decoys, Unicode/CRLF, oversize methods, and missing/changed sources. These variants belong only under the new test area.

Record block call counts/arguments and use pass-through spies for real utilities when a case needs ordering. A normal success calls action once, selection once, extraction once, navigation once, and outline twice inside the flow. The second outline checks the selected snapshot. Reset setup calls out of this count.

Redirect existing log destinations to a temporary absolute path in tests; do not alter production logging settings or create tracked output artifacts.

## 3. S — Setup, ownership, and isolation (4 cases)

| ID | Setup and action | Required assertions |
|---|---|---|
| S01 | Run a successful flow and a skipped flow on temporary copies of the test fixture. Snapshot file bytes before/after. | Project files and committed test fixtures remain unchanged; the original experiment fixture is not a write target. No source is imported or executed. |
| S02 | Run the new suite with experiment runners/imports unavailable and the test-owned fixture available. | Fixture setup and flow execution succeed without runtime access to `experiments/`. No test imports an experiment helper. |
| S03 | Install tripwires on real model loading and prediction, then execute every supported route and the gateway success case. | No tripwire fires. Both block calls are intercepted at their public boundaries; no network/model access occurs. A deliberately unmocked block is detected by the tripwire in a focused harness check. |
| S04 | Deep-copy request/config, supplied outline and fake block result objects; invoke adapter and flow. | Inputs remain unchanged, including relative config input and block metadata. No global registry/logger/token state is introduced. |

## 4. P — Explicit root and file gates (10 cases)

| ID | Setup and action | Required assertions |
|---|---|---|
| P01 | Prompt references the baseline root-relative production file. Supply an explicit absolute root. | Resolver receives root mode and root for both lookup-base/root parameters; emitted source and paths belong to that root. |
| P02 | Parameterize process cwd and valid event cwd as project subdirectory and an unrelated directory containing a same-named decoy file. | Identical selected source/payload for all variants; decoy is never read or selected. Cwd does not determine config/source lookup. |
| P03 | Parameterize root as absent, relative, nonexistent, or a regular file. Invoke the adapter. | Existing failure contract; no config/source/block read; no cwd or upward-search fallback. |
| P04 | Provide a relative config filename in the configured root and a different file of the same name in process cwd. Also test an explicit absolute config path. | Relative config loads from root, explicit absolute config remains explicit; incoming args are unchanged. Invalid root prevents either config read. |
| P05 | Parameterize a blank prompt, no file reference, and unsupported-extension-only prompt. | Noop; neither LAYA block runs; no selection/extraction/navigation occurs. |
| P06 | Parameterize `.spec.ts`, `.test.ts`, `.d.ts`, and an apparently production-named symlink to an excluded target within root. | No enrichment and no LAYA block call. Both lexical and canonical eligibility apply. |
| P07 | Mention the same production file repeatedly, including two supported spellings resolving to its canonical path. | One eligible file, one action call, one selection call; no duplicate source context. |
| P08 | Mention two distinct recognized TypeScript files, including production+test and valid+missing variants. | No context; the flow never discards the second recognized reference to enrich the first. Neither block runs. |
| P09 | Parameterize missing file and ambiguous basename/suffix against real fixture variants. | Resolver's outcome is honored; no arbitrary candidate chosen, no block calls, no context. |
| P10 | Parameterize an outside-root absolute source, traversal escape, and symlink escape. Also test an in-root symlink to a valid production file. | Escapes yield no context and no outside source extraction; the permitted target is canonicalized/deduplicated and rendered relative to root. |

## 5. R — Block routing and orchestration (10 cases)

| ID | Setup and action | Required assertions |
|---|---|---|
| R01 | Fixed action `explain`; fixed baseline selected ID. Run full flow. | Context with exact expected method/list; normal call counts/order; original prompt forwarded unchanged to both blocks. |
| R02 | Same fixture, fixed action `generate_tests`. | Same enrichment policy and utility sequence as explanation; no test-generation implementation occurs inside this flow. |
| R03 | Fixed action `modify_code`. | Noop after action; outline, selection, extraction, navigation never run. |
| R04 | Parameterize requested-action undecided and explicit block skip. | Honor the result once; no confidence-based reinterpretation, retry, fallback, or selection. |
| R05 | Fixed explain action; real fixture with no callable candidates. | Noop after real outline; selection/extraction/navigation not called. |
| R06 | Parameterize selection no-single-match, method-undecided, multiple-relevant, and explicit budget/other declared skips. | Preserve authoritative nonselection; no extraction/navigation; no second selection or fallback flow. |
| R07 | Fixed accepted action/selection results with irrelevant or contradictory confidence fields where the existing result contract permits them. | Accepted semantic answers control routing. Flow never invokes rules or re-scores a decision. |
| R08 | Use real outline with duplicate method names, but distinct valid IDs; select the predetermined second identity. | Exactly that implementation is extracted. No name-based reselection, guessed line match, or additional LAYA call. |
| R09 | Parameterize malformed selected identity and unknown action value supplied by a deliberately invalid fake result. | Contract failure with no context; never choose a substitute. This tests boundary handling, not block correctness. |
| R10 | At each LAYA block boundary inject an ordinary exception, then `TimeoutError` in a separate parameter. | Ordinary errors become failure at the correct stage; timeout propagates to gateway handling. No downstream calls or retries. |

## 6. N — Real extraction and one-hop navigation (7 cases)

| ID | Setup and action | Required assertions |
|---|---|---|
| N01 | Baseline selected method with both real direct callees. | Full exact implementation plus both expected signatures, paths, and definition ranges. Do not use invocation-site ranges. |
| N02 | Real fixture where a direct callee calls a further helper; add a separate incoming caller. | Output lists direct callees only; no transitive helper or incoming caller; navigation invoked once; no callee implementation bodies. |
| N03 | Real fixture calls the same target multiple times and has a target in another file. | One row per target identity, preserving utility order; no duplication from call sites. |
| N04 | Real fixture method has no project callees. | Keep full method and fixed “No project methods were reported.” line; do not invent targets. |
| N05 | Produce a partial navigation result with a targeted fixture; use narrow fault injection only if the helper cannot reliably produce that condition. | Retain reported valid entries and exact partial note. Diagnostics do not imply exhaustive runtime-call coverage. |
| N06 | Inject only an ordinary navigation failure/error result, with the selected source unchanged; separately inject gateway `TimeoutError`. | Ordinary failure gives method-only context plus fixed unavailable note. Timeout gives no context. Existing utility-wrapped errors keep their existing semantics. |
| N07 | In temporary copies, edit the source after initial outline/before extraction, and after real navigation/before final outline; also remove the selected file. | Stale/missing selected source yields no context. Do not reselect, retry, or emit an outdated implementation with fresh locations. |

## 7. O — Exact presentation and output cap (10 cases)

All size cases use independently measured complete candidate strings. Tests may call private pure presentation helpers in the new flow module. Do not expose a new production framework solely for testability.

| ID | Setup and action | Required assertions |
|---|---|---|
| O01 | Baseline success against independently authored golden text. | Exact equality of title, metadata order, line ranges, blank lines, implementation, ordered call rows, and footer. No code fences or extra prose. |
| O02 | Parameterize tabs, trailing spaces, comments, backticks, Unicode, CRLF/CR/LF and supported Unicode line separators in extracted source. | Implementation substring/encoded bytes remain exact; only section separators are added outside it. Selected line range uses inclusive line-break semantics, including trailing terminators. |
| O03 | Use a multiline signature/control characters in metadata, with valid utility output. | Each navigation item remains one physical line using visible escapes. Implementation is untouched; paths remain root-relative. |
| O04 | Construct complete outputs of 7,999, 8,000, and 8,001 UTF-16 units where all rows are otherwise desired. | First two fit. Third never exceeds cap: omit complete rows if possible, otherwise no context. No method/row truncation. |
| O05 | Method plus mandatory presentation alone exceeds cap. | Noop output-budget refusal; full code is never cut or summarized; navigation need not run after this lower-bound failure. |
| O06 | Method fits but only a prefix of call rows fits. | Largest valid complete prefix; exact omitted count and note included in sizing; stable ordering; no shortened signatures. |
| O07 | Method fits but no navigation row can fit alongside required omission/status notes. | Emit method with zero-row representation only if the entire candidate fits; otherwise noop. No uncounted note appended afterward. |
| O08 | Construct an edge where the zero-row omission notice is longer than the full short list, so zero rows overflow but full list fits. | Flow evaluates candidate representations and emits the fitting full list; no premature rejection based only on the zero-row candidate. |
| O09 | Parameterize emoji/supplementary Unicode and configured limits below/above 8,000. | Count two UTF-16 units for supplementary characters; smaller valid limit respected; larger config cannot raise hard cap. Invalid Unicode yields formatting failure. |
| O10 | Combine partial/unavailable navigation, budget omission where applicable, and fixture-specific excluded-content markers. | Required notes/footer all count toward final cap. No callee bodies, unrelated declarations, internal IDs, scores, token reports, log prefixes, or raw errors leak into payload. |

## 8. T — Separate tokenizer follow-up

T01–T05 and metadata-present variants of T06–T07 are future tokenizer-integration proposals, outside this task. T06 unavailable-metadata behavior and ordinary block-local refusal variants of T07 are covered now. No placeholder skips or live tokenizer calls are added. H03 token variants and optional-token L05 variants likewise remain future work.

## 9. L — Reused logging and exact enrichment (5 cases)

| ID | Setup and action | Required assertions |
|---|---|---|
| L01 | Successful adapter call with capturing logger, then serialize using the existing gateway. | Exactly one flow `enrichment_prepared` payload event; logged `additional_context == Context.text == decoded hook additionalContext`. No independently regenerated log text. |
| L02 | Exercise existing JSONL logger redirected to a temporary absolute destination with tabs, CRLF, Unicode and quotes in context. | Decode the log record and compare exact string/UTF-8 bytes. JSON escapes on disk do not alter source. No new plaintext writer or per-invocation payload artifact. |
| L03 | Parameterize skip, block failure, extraction failure, and output-budget refusal. | Compact outcome/reason diagnostics; no enrichment payload event; token/internal diagnostic fields never appear in hook response. |
| L04 | Inject an ordinary logger failure, then `TimeoutError` separately. | Ordinary logging failure does not corrupt valid context or write to stdout. Timeout retains gateway deadline behavior; never log “delivered” on preparation alone. |
| L05 | Execute two invocations with different IDs, sources, and optional token reports. | Correct existing correlation and distinct final payload records; no cross-invocation mutable state, duplicate body logs from the flow, or shared last-token report. |

Only the new flow's additional records are counted for the “once” assertion; existing utility logs are outside this change. Do not rewrite global logging to satisfy the test.

## 10. H — Actual hook integration (8 cases)

At this level, invoke the actual gateway, common dispatcher, event dispatcher and default handler. Patch only the two block boundaries plus explicitly named failure dependencies. Do not inject a replacement feature handler in the primary route test.

For subprocess cases, a small test-local bootstrap may install the block fakes before invoking the existing CLI/gateway. It must not alter routing, launch the legacy handler, modify production entry points, or bypass the actual default route.

| ID | Setup and action | Required assertions |
|---|---|---|
| H01 | Invoke actual default UserPromptSubmit chain with valid envelope/root, fixed blocks and real utilities. | New flow reached exactly once; both dispatchers remain active; exactly one JSON object with `hookSpecificOutput.hookEventName` and `additionalContext`; exact golden context. |
| H02 | Parameterize no-file, unsupported action, no selection, and output overflow through gateway. | Exit follows existing nonblocking behavior; stdout exactly zero bytes, not `{}`, a blank line, or empty-context JSON. |
| H03 | Parameterize block exception, selected-source failure, and established tokenizer refusal/inspection failure through gateway. | No diagnostic text in stdout; zero-byte no-enrichment response; appropriate existing log/stderr outcome. Token variants remain dependency-bound. |
| H04 | Fake block writes Python stdout noise and fd 1 noise before returning a fixed success. | Existing gateway isolation contains noise outside protocol output; stdout parses as exactly the one expected response with no prefix/suffix noise. |
| H05 | Inject deterministic deadline expiry during a block and during final payload logging. | Existing gateway handles deadline; zero context output; no downstream flow work or retry. Avoid timing-sensitive sleeps. |
| H06 | Supply invalid event/prompt/common fields rejected by existing dispatchers; test existing `--real` opt-in absence. | Existing validation remains authoritative; new flow/blocks do not run when inappropriate; no added common-dispatcher logic required. |
| H07 | Use valid project root with process/event cwd elsewhere, decoy source/config, and source read-only snapshots. | Full hook uses configured root and emits root-relative paths; config/source snapshots remain unchanged. Missing root never falls back to cwd. |
| H08 | Exercise the event dispatcher's existing injected-handler seam separately, plus the unmodified default route with fake blocks. | Injection still works for its current tests; default registration points to the new flow. Legacy exact-output regression conflicts are surfaced, not hidden by injecting the old handler into existing tests. |

## 11. Execution and scope review

Use tests/first_flow plus focused shared-hook/component groups during migration, followed by one full Python run. Retire sandbox-only tests; preserve meaningful infrastructure and utility assertions. Do not hide failures using exclusions, xfails or new skips. The small compatibility re-export keeps existing experiment imports usable. Record retired/adapted/retained coverage and actual results in the PR. No generated evidence framework or repeated broad test loop is needed.

## 12. Acceptance evidence and limits

Provide one offline successful hook response with its matching decoded log payload, and one skipped response proving zero stdout. Clearly label the LAYA answers as mocked. Report focused/regression commands and results, any baseline failures, and the tokenizer dependency state.

Offline flow tests prove routing, reuse, source handling, formatting and transport. They do not prove model answer quality, tokenizer correctness, live Claude consumption, or end-to-end live latency. Existing component tests and an optional later live check cover those areas.

Report implementation and test results accurately. Tokenizer remains separate work. Normal checkout/CI confirmation and Sharon's merge review remain outstanding; no merge is performed by this cleanup.
