# LAYA token-budget research: results before design

Date: 2026-10-31  
Status: research completed where this environment permits; **detailed design held for discussion**.  
Scope: English text and TypeScript source. No product code changed. No model weights downloaded and no neural inference run.

## 1. Outcome and decisions to discuss

A centralized check is feasible. The existing shared prediction boundary already receives the complete prepared state and question definitions, and it knows which agent is selected. Building blocks do not need token arithmetic or recovery policies.

However, two assumptions need correcting before design:

1. **A total token count, or the SDK's existing `usage.truncated` flag, cannot establish that nothing was cut.** The SDK also trims individual options and instructions. Real-tokenizer experiments reproduced both while the state-truncation flag remained false. There is no inspected public method that returns a complete, untrimmed, all-boundary report.
2. **A JSON error returned as an ordinary prediction is incompatible with the current success contract.** Both the shared predictor and the new building-block runtime expect an `answers` mapping. An exception already travels through both block implementations, but the existing flow converts it to a generic `model_error`, and the logger does not serialize arbitrary exception attributes.

Recommended discussion outcome: use a typed exception carrying a JSON-serializable budget report internally; let it pass through blocks unchanged; catch it explicitly at the flow boundary. Keep valid prediction results unchanged. The flow would decide recovery later. This is a recommendation, not an approved design.

One implementation-boundary decision also remains: support the currently managed prediction path first, or support arbitrary SDK hooks/custom loaders immediately. SDK start hooks can change state, questions, and budgets after an outer preflight check. A guarantee for those cases requires checking after those changes and before encoding/inference, or explicitly refusing an unsupported configuration.

The actual installed SDK and resolved checkpoint on Sharon's Mac remain unverified. Source research and tokenizer experiments here cannot substitute for that inventory.

## 2. Evidence and reproducibility

### Pinned sources

| Component | Inspected revision | Version declared in source |
|---|---|---|
| SharonLanger/laya-context-router | `e4faa703d1572a88662e33f2bf8b53f339a5c8aa` | 0.1.0 |
| mizorewww/laya-mlx | `2159c6c9988e4cbfd6281db1888cef45de09cea9` | 0.6.0 |
| NandhaKishorM/laya | `55a19f7b7b56787e1a3e41063def9bb9a8737351` | 0.4.19 |
| aac6fef/laya-typed-decisions-mlx | `f9e501c2080cc57c13d6887820329758f5351125` | Checkpoint |
| tindang/laya-code | `f3d6bd2344e4750dd917f95d40ceacfa81bb81db` | Checkpoint |

These are the revisions actually fetched. Search snippets and mutable web pages can describe different versions; they were not used to override these pinned files.

The supplied handoff was read at `/workspace/scratch/aae8a6a84dee/requested-action-plan/laya-token-budget-handoff.md`. Its unresolved questions were investigated against the newer router snapshot above. The latest user instructions supersede its earlier narrower scope: strict rejection is required, English and TypeScript are the current scope, and character estimates are not wanted.

### What ran here

Linux x86_64, Python 3.12.14. An isolated research environment used tokenizers 0.23.3, numpy 2.5.4, and Transformers 5.22.1. LAYA and MLX neural runtimes were not installed.

Downloaded checkpoint files were restricted to configs, tokenizer files, model cards, licenses, and notices. Research probes executed the pinned MLX tokenizer wrapper, sequence-construction helpers, and prefix-cache implementation without loading neural weights. Separate probes loaded the checkpoint tokenizer through Transformers and exercised the existing router/block/flow error path with an injected exception.

The first attempt to import upstream `laya.common` directly failed because it imports PyTorch. It was not treated as a successful upstream runtime test. Instead, source AST comparisons checked six relevant function bodies, and a separate real Transformers-tokenizer comparison checked token IDs.

No production billing/building-block logs were available here. All numeric examples below are measured research fixtures, not claims about previous production requests.

## 3. Action-item results

| Action item | Result | Remaining work before implementation |
|---|---|---|
| 1. Identify every model/runtime limit | Checkpoint limits and inspected sequence cuts verified | Match the supported runtime versions to the actual Mac installation |
| 2. Decide static configuration and ownership | Static checkpoint budgets are appropriate; derived allowances belong in LAYA | Choose supported runtime/model revisions and unknown-profile behavior |
| 3. Find tokenizer/inspection API | Exact tokenizer is available; existing helpers expose only part of the needed diagnostics | Choose versioned adapter versus SDK extension for full inspection |
| 4. Locate the central check | Shared `laya/predict.py` covers both block implementations | Resolve SDK hooks and custom-loader metadata support |
| 5. Establish response information | Candidate report fields identified below | Confirm exception carrying JSON versus a wider return-type change |
| 6. Verify upward propagation | Executed: predictor and both block implementations preserve an exception unchanged | Flow must preserve the report instead of generic conversion |
| 7. Locate logging | Existing JSONL logger and prediction events inspected | Log report explicitly; custom exception attributes are not automatic |
| 8. Assess backward compatibility | Valid success shape can remain; strict rejection intentionally changes oversized requests | Update mock/decorator metadata support and any changed flow reason mapping |
| 9. Establish test direction | Real tokenizer/boundary/parity probes executed; acceptance categories identified | Full feature tests follow approved design; Mac neural verification still pending |

## 4. Verified model limits and licensing

| Value | Current MLX typed-decisions checkpoint | tindang/laya-code |
|---|---:|---:|
| `rl_agent_config.max_len` | 1,024 | 512 |
| `rl_agent_config.head_max_len` | 256 | 192 |
| Encoder `max_position_embeddings` | 8,192 | 8,192 |
| Tokenizer `model_max_length` | 8,192 | 8,192 |
| First rendered-option text cap in inspected runtime | 48 | 48 |

The 8,192 values are **not** the current request budget. The checkpoint's runtime configuration is smaller. Raising a limit to the encoder maximum would be a separate behavior/quality decision, not part of truncation prevention.

The 48-token option cap comes from runtime source, not the tokenizer vocabulary or checkpoint limit file. Its unit excludes the option's marker token. An additional shared-head rule can lower it.

These models score constrained decisions. There is no generated-answer token allowance to subtract as there would be for an autoregressive chat model. For several questions, the SDK constructs a separate sequence per question against the shared state; it does not combine all questions into one 1,024-token sequence.

The inspected inference construction does not use checkpoint `max_prefixes=6` as a six-question limit. Likewise, the typed checkpoint's `max_tokens_per_batch=4096` metadata must not be promoted to a request cap without an actual inference read of that field.

The tokenizer files are openly available. Hugging Face Tokenizers is Apache-2.0; the inspected checkpoint repositories declare Apache-2.0 and include LICENSE/NOTICE files. The code-model notice attributes the ModernBERT tokenizer. These findings support using the exact checkpoint tokenizer while preserving the applicable notices. There is no need to substitute a guessed tokenizer.

Both downloaded `tokenizer.json` files have this SHA-256:

`6c8aaa9a542084f2457eab775d4eeb51f92a70c0fd9de28d5edb0ddec3c08d30`

Their tokenizer configuration files differ, so tokenizer identity should include configuration as well as the main JSON file. Identical tokenization does not imply identical model budgets or prediction behavior.

### Static versus request-dependent values

Keep model identity, revision, runtime profile, and configured limits in LAYA-owned configuration. An immutable constants module is sufficient; a JSON registry is optional. Do not fetch Hub metadata on every request.

Verify the profile against the resolved agent/configuration when loaded. Effective per-call overrides, if supported, must be included in each inspection. State allowance and per-option allowance are computed from that request's actual normalized questions.

Keep lazy agent loading. Reuse the selected agent's tokenizer where possible. A tokenizer-only inspection can load metadata/tokenizer without weights, but that is a separate capability to expose deliberately. Parsing/loading a tokenizer is different from counting a new request; no cache of arbitrary prompt counts is required.

## 5. What the SDK actually assembles and cuts

The following describes the pinned sequence builder, not proposed application code.

1. Normalize a question into its type, instructions, and criteria.
2. Render each option. A choice description includes its label; score options include a level label; a boolean question has two rendered alternatives, including default descriptions where appropriate.
3. Replace literal mask-token text with a space in instructions, options, and serialized state.
4. Tokenize the instruction text with its type/question prefix, with automatic special tokens disabled.
5. Tokenize each rendered option with its leading space, initially retaining at most 48 text tokens. Prefix each option with a mask marker.
6. Allocate the shared head budget. If fewer than 16 tokens remain after the initial option spans, cap each span at `max(4, floor((head_max_len - 16) / option_count))`. This span includes its marker.
7. Recalculate the instruction allowance and keep at most `max(8, remaining_head_budget)` instruction tokens.
8. Add the head's classification/separator tokens.
9. Allow state tokens equal to `max(0, max_len - actual_assembled_head_length - 1)`. The final 1 reserves the closing state separator.
10. Assemble the sequence, apply the final `max_len` slice, and retain only option markers that survived.

This is why simply adding the token counts of raw JSON fields is wrong. The SDK adds labels, prefixes, leading spaces, and special tokens, and it tokenizes components separately. We should reproduce those exact operations within LAYA, not expose arithmetic to flows or blocks.

The head parameter is an allocation rule, not a literal ceiling on the finished head array. A measured typed-model head reached 259 tokens with `head_max_len=256`, because the enclosing head specials are additional. With extremely many options, minimum retained spans can produce a head that is longer than the total sequence ceiling. The final slice then matters too.

For string state, the SDK keeps the beginning when forced to trim. For conversation lists, it keeps the end. The router's normal prepared-block state is a string; supporting richer state forms should not be accidentally promised by this feature.

### Existing inspection facilities

| Facility | Useful for | Limitation |
|---|---|---|
| Checkpoint tokenizer / loaded `agent.tok` | Exact IDs for text under matching settings | Does not know LAYA's head allocation and sequence rules |
| `common.build_head` | Actual assembled head and option markers | Already applies option and instruction trimming |
| `common.state_room` | State allowance for an internal question | Uses an already-trimmed head; not an all-input safety test |
| `common.build_sequence` with truncation statistics | Actual token IDs and state dropped/used counts | Head text losses are not fully reported |
| `agent.prepare` | Normalized/prepared encoding without the prediction forward pass | Uses the trimming encoder; no complete untrimmed report; not proof of later hook parity |
| Response `usage` | Post-inference accounting and state-truncation diagnostics | Too late for prevention; not a full head-truncation report |

`usage.input_tokens` sums non-padding tokens across the question rows for a state. A two-question response can legitimately report more than the per-sequence context limit. It should not be compared directly to 1,024 or 512 as an overflow check.

The desired guarantee is conditional but precise: **for a supported, verified runtime profile, inspect the final effective request, detect every SDK cut, and reject if any content would be dropped before inference starts**. A logged scalar count alone cannot establish this. Nor does preventing truncation establish that the model's answer is semantically correct.

One central inspection location does not automatically mean one tokenization pass. Calling an external inspector and then public `predict` can tokenize again. Reusing the exact prepared IDs for inference would need a supported preparation/forward integration; this research did not establish a public API that both exposes all losses and consumes that inspected request unchanged. Keep that work inside the LAYA adapter.

### Existing approaches to small windows

The inspected SDK offers `predict_long`, which windows the state using the smallest available state allowance among the questions, then aggregates predictions. Its source also addresses retokenization and hook-induced changes to those budgets. Shortlisting and tournament helpers reduce large choice sets before a final decision. These approaches change which evidence or candidates contribute to the result and can add model calls. They are possible future flow policies, not substitutes for the requested rejection guard. No automatic chunking, summarization, or candidate elimination is recommended for this feature.

## 6. Measurements with the actual tokenizer

### Current fixed questions

The real repository question definitions were used unchanged. Test state: “Explain how this TypeScript function works.” It encoded to 9 state tokens.

| Question | Instruction tokens including prefix | Rendered option text tokens | Assembled head | Typed-model state allowance | Code-model state allowance |
|---|---:|---|---:|---:|---:|
| requested_action | 66 | 12, 13, 16 | 113 | 910 | 398 |
| context_scope | 59 | 15, 16, 17, 17 | 131 | 892 | 380 |

Neither question lost head content. Their complete sequences for the 9-token test state were 123 and 141 tokens respectively.

These are verified token allowances for these exact question definitions and configurations. They are not permanent building-block caps. Editing instructions/choices changes them. Dynamic method-selection criteria must be measured after candidates have been inserted.

The raw method-selection template was also measured: 51 head tokens. That template contains a placeholder criterion and **must not** be advertised as the deployed method-selection budget.

### Reproduced trimming cases

| Probe | Typed model | Code model | What it establishes |
|---|---|---|---|
| One long option | 83 raw text tokens became 48 | Same | A separate option cap applies even to a tiny request |
| Long instructions | 504 instruction tokens became 244 | 504 became 180 | Instruction text is independently cut |
| 30 options | Each 14-token option became 7 text tokens | Each became 4 | Shared head pressure can shrink options below 48 |
| 300 options, empty state | Head length 1,211; final sequence 1,024 | Head length 1,211; final sequence 512 | Final sequence/marker loss is another boundary |
| TypeScript function fixture | 51 state tokens; 75 complete tokens | Same | Exact code tokenization works without character estimates |

The long-option fixture required only 105 tokens before any trimming, yet 35 option tokens disappeared and the final sequence had 70. Its state-truncation flag was false. This is a direct counterexample to “under the total limit means nothing was truncated.”

All of these head-loss probes reported false in the helper's state-truncation field. In the 300-option case, the agent's subsequent marker-count guard would raise before the forward pass; the probe executed the builder, not neural inference. Existing marker checks cover that particular failure but not ordinary option/instruction shortening.

### Exact boundary probes

For each model, option lengths 47, 48, and 49 retained 47, 48, and 48. For instructions, typed-model lengths 243/244/245 with a 244 allowance retained 243/244/244; code-model lengths 179/180/181 with a 180 allowance retained 179/180/180. All had short, untrimmed state.

| Model/question | State counts tested | Tokens dropped |
|---|---|---|
| Typed / requested_action | 909, 910, 911 | 0, 0, 1 |
| Typed / context_scope | 891, 892, 893 | 0, 0, 1 |
| Code / requested_action | 397, 398, 399 | 0, 0, 1 |
| Code / context_scope | 379, 380, 381 | 0, 0, 1 |

Repeated “ hello” text was used only to produce exact state lengths verified by the tokenizer. These are packing tests, not semantic model tests.

### Parity and repeatability

- 16 cases across two model profiles produced identical token IDs, markers, option stats, and state stats through the plain builder and both cold/warm prefix-cache calls.
- 28 comparisons—7 text samples × 2 tokenization settings × 2 model directories—matched exact token IDs between the pinned MLX wrapper and Transformers' locally loaded tokenizer. Settings were unrestricted encoding and a 48-token cap, without automatic special tokens.
- Each model's TypeScript sample produced identical token IDs over 100 repeated encodings.
- Six upstream/MLX function bodies matched by AST after excluding docstrings: encoding, state serialization, option rendering, head construction, sequence construction, and state allowance. This is source parity, not execution of upstream PyTorch inference.

All of these checks passed. They establish concrete compatibility for the pinned artifacts and fixtures, not permanent equivalence across future releases.

## 7. The central check and routing findings

All Python source files under the router's inspected `src` tree were reviewed for prediction entry points. Both the legacy `QuestionBlock.run` and the newer `Block.run` call the shared `laya.predict.predict`. The live readiness command also uses it, with a capturing agent wrapper.

The central application location is therefore the shared prediction boundary, after complete preparation/normalization and model selection, before its prediction request proceeds. Building blocks need no separate tokenizer API. An optional externally callable preflight method could later delegate to the same inspector; it must not become a second implementation.

A check placed just before `agent.predict` is sufficient only if the request/configuration will not change inside the SDK. The pinned SDK supports installed and per-call start hooks that can change state/questions and `max_len`/`head_max_len`. It invokes those hooks before encoding. A guard implemented merely as a normal hook also needs care: `hooks_raise=False` can swallow hook exceptions.

The router's current ordinary RunConfig does not expose these SDK hooks. Thus a managed, explicitly supported path is a reasonable first scope. Arbitrary custom agents should not be silently declared safe. The guarantee must either cover them through a verified adapter or refuse inspection with a distinct error.

### Multi-model loading

The current real loader always imports `laya_mlx`. It does not choose `laya` versus `laya_mlx` based on model name. Registry reuse is currently keyed by model, temperature, and language.

A second package is **not yet proven necessary** for `tindang/laya-code`: the inspected MLX loader can resolve arbitrary model repositories, and its weight sanitizer maps upstream parameter names to MLX. That makes direct use plausible, but this investigation did not load the code-model weights or verify a full MLX prediction.

If different runtimes are needed, they can share a prediction interface without returning the same concrete Agent class. Runtime, revision, tokenizer, and effective budget identity must be explicit in profile selection and reuse; model-name substring guessing is insufficient.

The code model is specialized for code relevance. Tokenizer compatibility does not prove it is an appropriate replacement for requested-action or context-scope classification. Keep model/task routing separate from the input-budget guarantee.

## 8. Error information, propagation, and logging

### Executed propagation findings

A sentinel exception containing a JSON-compatible report was injected through the current SDK-facing interface:

| Layer | Observed behavior |
|---|---|
| Shared predictor | Reraised the same exception object and report |
| New Block runtime | Passed the same exception to its caller; reduction did not run |
| Legacy QuestionBlock | Passed the same exception to its caller |
| Existing file_method_context flow | Returned status noop, reason model_error, context null |
| Existing prediction error log | Included exception type/message/traceback; omitted its custom report attribute |

No recovery behavior was added. This experiment verifies the existing path, not the unimplemented token guard.

Consequently, a typed exception is the least invasive candidate for block transparency. Returning an error object as though it were ordinary SDK output would require coordinated changes to validation, both block paths, and consumers.

The flow already receives the exception: there is no architectural barrier preventing LAYA from informing the flow. The missing work is preserving/classifying that information. If a new flow reason is introduced, the hook integration's fixed reason mapping also needs updating; otherwise it can classify the result as invalid. Application hooks here are distinct from SDK prediction hooks.

### Candidate diagnostic fields for discussion

| Field/group | Purpose |
|---|---|
| Schema version and stable error code | Let flows distinguish budget overflow from unavailable inspection, malformed input, and inference failure |
| Request/attempt identity | Correlate boundary log, block invocation, and any flow retry |
| Model ID, resolved revision, runtime/version, tokenizer/config fingerprints | Explain exactly which rules were applied |
| Effective limits and profile provenance | Distinguish checkpoint values from explicit overrides |
| Inspection phase and inference_started=false | State that rejection occurred before request inference |
| Per-question measurements | Head size, state required/allowed, untrimmed full sequence length, and predicted retained length |
| Violations list | Include every detected failure, not just the first |
| Violation boundary, question ID, option key/index where relevant | Identify instruction, option, head allocation, state, or final sequence problem |
| Required tokens, limit tokens, would-drop tokens | Give the flow actionable measurements |
| Count unit and stage | Avoid confusing option text with marker-inclusive spans, or summed usage with per-sequence length |

A report should distinguish “would drop” before inference from “did drop” after inference. It should not mark a request retryable merely because it overflowed; retrying identical input accomplishes nothing, and shortening state cannot fix an oversized option.

For the measured long-option example, an illustrative report would identify the choice, report 83 option-text tokens against 48, and predict a 35-token loss. It would separately show that the total untrimmed 105-token sequence fits. This is an illustrative diagnostic, not an existing production log.

### Logging recommendation

Create the report once at the shared boundary and attach that same data explicitly to its ERROR log and propagated exception. Accepted requests may log per-question measurements at DEBUG. Existing JSONL fields already include time, process IDs, component, event, and details.

Do not rely on exception string formatting to preserve structured numbers. Avoid adding full prompt/source copies to the new budget report; existing debug events already contain payload text. Logging failures must not turn a rejected request into an allowed one. Logs describe the decision; they do not enforce it.

## 9. Compatibility and risks

| Risk | Assessment | Consequence for later design |
|---|---|---|
| Only checking total/state usage | High; reproduced | Check option, instruction, shared-head, state, and final sequence losses |
| Checker differs from actual runtime/version | High | Pin/verify profiles and compare prepared IDs; unsupported profiles cannot report safe |
| SDK hook changes input after check | High when such hooks are allowed | Guard after mutation or explicitly restrict supported path |
| Raw error dict enters success parsing | High; current contracts reject it | Prefer typed exception or approve a wider return-contract change |
| Flow/log strips structured details | Confirmed | Explicit flow classification and explicit report logging |
| Mocks/decorators expose only predict | Confirmed in tests/live-check source | Budget-inspection capability must be injectable/forwarded; do not require hidden attributes accidentally |
| Dynamic candidates alter head | High relevance | Measure final criteria after preparation, never template-only counts |
| Lazy loading lost through global imports | Avoidable | Keep dependencies/tokenizer access at the existing lazy boundary |
| Reusing agent with wrong runtime/revision | Moderate | Extend identity when those config dimensions become supported |
| Extra tokenization cost | Unmeasured on Mac | Share prepared data where supported, or measure duplicated encoding; no count cache needed initially |
| Concurrent tokenizer use | Sequential probes do not establish concurrency behavior | Preserve SDK locking; test inspection alongside prediction, especially Transformers truncation settings |
| Assumed safe percentage/character cap | Does not solve demonstrated failures | Exact checking is preferred; 90% total utilization still allows option truncation |

“Backward compatible” can mean unchanged results and schemas for valid supported requests. It cannot also preserve success for requests that the user now explicitly wants rejected. That strict change is intentional.

Existing character caps in method selection are independent early resource controls. They neither prove token fit nor need to be removed for this feature. Changing them should be a separate decision.

The present custom-loader contract only requires an object with `predict`. Adding unconditional access to `agent.tok` or `agent.cfg` would break existing mocks and the live-check capturing wrapper. This is concrete compatibility work for the design, not a reason to put counting into blocks.

A first invalid request may still incur lazy model-loading cost if the inspector uses the loaded agent. “No request inference” does not automatically mean “no weights loaded.” Optional compile warmup is another distinction for nondefault loaders. Tokenizer-only preflight avoids weights but needs matched metadata and an explicit adapter.

## 10. Direction for the later test plan

This is an outline of acceptance evidence, not the detailed implementation test plan.

| Area | What the feature must eventually demonstrate |
|---|---|
| Every token boundary | Below/at/above option, instruction, shared-head, state, and final-sequence limits |
| Complete refusal | Any overflow rejects the whole request before any question's forward pass; no partial answers |
| Actual tokenizer/assembler parity | Same normalized text, special tokens, option rendering/order, cached and uncached behavior |
| Multiple questions | Check each independent sequence; report every violation; never mistake aggregate usage for context length |
| Propagation | LAYA → both block paths → flow retains the same structured diagnostic; no reducer/recovery inside blocks |
| Logging | ERROR report matches propagated report, valid JSON, correct units/model/revision; logging failure cannot bypass rejection |
| Compatibility | Valid results unchanged; explicit mocks supported; lazy reuse preserved; no unconditional heavy imports |
| Model/config changes | Switching models, revisions, head/total overrides, and unsupported metadata cannot reuse wrong limits |
| Input mutation | Supported SDK hooks covered after mutation or clearly rejected; no swallowed enforcement failure |
| English and TypeScript | Fixed questions, dynamic signatures, long identifiers, punctuation, comments, and mixed English/code text |
| Regression on formerly truncated fixtures | They now fail deliberately; do not weaken the guard to preserve old success expectations |

A neural forward spy can establish zero inference for rejected requests once the guard exists. A later controlled Mac run should establish parity against the actual installed agent, including effective limits and resolved model revision. These feature tests were not claimed as run here.

## 11. Remaining evidence and design gate

Before claiming support for Sharon's live setup, capture installed LAYA/MLX/tokenizers versions, actual model snapshot revision/path, tokenizer fingerprints, effective agent config, and any hooks/custom wrappers. The repository's existing live-check command provides some identity observations but does not currently inventory all effective token limits.

Before promising code-model execution through MLX, run a small, explicit load/predict check on the intended Mac using a pinned revision. If it requires the upstream runtime, verify that adapter separately. No full-weight download or Mac inference was performed in this research.

The decisions to resolve now are:

1. **Internal failure contract:** accept a typed exception carrying the JSON report, leaving blocks transparent, or require an ordinary error return object and accept broader caller changes?
2. **Initial guarantee scope:** start with managed, verified model/runtime profiles at the shared boundary, or include arbitrary mutating SDK hooks/custom loaders from the first version?

Recommendation: the typed exception and managed verified profiles. Preserve the current success interface; add only the boundary inspection/reporting, capability support where needed, and the flow handling required to preserve diagnostics. Do not silently truncate, retry, expand limits, or bypass inspection for unknown real agents.

The detailed design and implementation plan are intentionally not included because the user asked to discuss changed assumptions first.

## 12. Primary-source index

The following links identify the evidence needed to recheck this report. Pinned code/configuration takes precedence over mutable descriptions.

- [Router snapshot](https://github.com/SharonLanger/laya-context-router/tree/e4faa703d1572a88662e33f2bf8b53f339a5c8aa)
- [Shared prediction boundary](https://github.com/SharonLanger/laya-context-router/blob/e4faa703d1572a88662e33f2bf8b53f339a5c8aa/src/laya_context_router/laya/predict.py)
- [RunConfig](https://github.com/SharonLanger/laya-context-router/blob/e4faa703d1572a88662e33f2bf8b53f339a5c8aa/src/laya_context_router/laya/config.py)
- [Agent registry](https://github.com/SharonLanger/laya-context-router/blob/e4faa703d1572a88662e33f2bf8b53f339a5c8aa/src/laya_context_router/laya/registry.py)
- [New block runtime](https://github.com/SharonLanger/laya-context-router/blob/e4faa703d1572a88662e33f2bf8b53f339a5c8aa/src/laya_context_router/block_runtime/runtime.py)
- [Legacy QuestionBlock](https://github.com/SharonLanger/laya-context-router/blob/e4faa703d1572a88662e33f2bf8b53f339a5c8aa/src/laya_context_router/blocks.py)
- [Flow error handling](https://github.com/SharonLanger/laya-context-router/blob/e4faa703d1572a88662e33f2bf8b53f339a5c8aa/src/laya_context_router/flows/file_method_context.py)
- [Flow-to-hook mapping](https://github.com/SharonLanger/laya-context-router/blob/e4faa703d1572a88662e33f2bf8b53f339a5c8aa/src/laya_context_router/hooks/user_prompt_submit/prompt_context_enrichment.py)
- [JSONL logger](https://github.com/SharonLanger/laya-context-router/blob/e4faa703d1572a88662e33f2bf8b53f339a5c8aa/src/laya_context_router/log_utils.py)
- [Current question definitions](https://github.com/SharonLanger/laya-context-router/tree/e4faa703d1572a88662e33f2bf8b53f339a5c8aa/src/laya_context_router/defaults/questions)
- [MLX tokenizer wrapper](https://github.com/mizorewww/laya-mlx/blob/2159c6c9988e4cbfd6281db1888cef45de09cea9/laya_mlx/tokenizer.py)
- [MLX sequence construction](https://github.com/mizorewww/laya-mlx/blob/2159c6c9988e4cbfd6281db1888cef45de09cea9/laya_mlx/common.py)
- [MLX agent, checkpoint load, marker checks](https://github.com/mizorewww/laya-mlx/blob/2159c6c9988e4cbfd6281db1888cef45de09cea9/laya_mlx/agent.py)
- [MLX hooks, preparation, prediction and usage](https://github.com/mizorewww/laya-mlx/blob/2159c6c9988e4cbfd6281db1888cef45de09cea9/laya_mlx/runtime.py)
- [MLX prefix cache](https://github.com/mizorewww/laya-mlx/blob/2159c6c9988e4cbfd6281db1888cef45de09cea9/laya_mlx/prepared.py)
- [MLX weight-name conversion](https://github.com/mizorewww/laya-mlx/blob/2159c6c9988e4cbfd6281db1888cef45de09cea9/laya_mlx/model.py)
- [Upstream sequence construction](https://github.com/NandhaKishorM/laya/blob/55a19f7b7b56787e1a3e41063def9bb9a8737351/laya/common.py)
- [Upstream tokenizer loading and prediction](https://github.com/NandhaKishorM/laya/blob/55a19f7b7b56787e1a3e41063def9bb9a8737351/laya/agent.py)
- [Typed checkpoint config](https://huggingface.co/aac6fef/laya-typed-decisions-mlx/blob/f9e501c2080cc57c13d6887820329758f5351125/rl_agent_config.json)
- [Code checkpoint config](https://huggingface.co/tindang/laya-code/blob/f3d6bd2344e4750dd917f95d40ceacfa81bb81db/rl_agent_config.json)
- [Typed checkpoint tokenizer files](https://huggingface.co/aac6fef/laya-typed-decisions-mlx/tree/f9e501c2080cc57c13d6887820329758f5351125/tokenizer)
- [Code checkpoint tokenizer files](https://huggingface.co/tindang/laya-code/tree/f3d6bd2344e4750dd917f95d40ceacfa81bb81db/tokenizer)
- [Typed checkpoint license](https://huggingface.co/aac6fef/laya-typed-decisions-mlx/blob/f9e501c2080cc57c13d6887820329758f5351125/LICENSE)
- [Code checkpoint license](https://huggingface.co/tindang/laya-code/blob/f3d6bd2344e4750dd917f95d40ceacfa81bb81db/LICENSE)
- [Code checkpoint attribution](https://huggingface.co/tindang/laya-code/blob/f3d6bd2344e4750dd917f95d40ceacfa81bb81db/NOTICE)
- [Hugging Face Tokenizers license](https://github.com/huggingface/tokenizers/blob/main/LICENSE)

