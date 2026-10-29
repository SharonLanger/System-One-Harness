# Implementation handoff after Phase 16

User authorized mock-first Phases01–19, public publication, direct main, no routine
approval gates. Phases 01–16 are complete in this tree; continue 17–19. Root will
assign a fresh sole implementation writer after Phase 16 exact-tree publication
acknowledgment. Do not redo the completed phases or write concurrently with the
new owner. The outgoing sole writer is /root/flow_builder.
Do not stop the overall task here. Phase20 remains blocked: Linux x86_64, no mlx or
laya_mlx (stdlib discovery only). No SDK imports, installs, weights, downloads,
model calls or real harness activation are authorized on this host. All inference
boundaries so far are explicit mocks; every supporting pipeline layer executes.

## Exact current contracts

- `laya.predict.predict(text,named_payloads,model=DEFAULT_MODEL,loader=None,
  real=False,config=None,registry=None)` deep-copies raw JSON after membership,
  type/numeric/legend validation. Mock mode requires explicit loader. Lazy live
  adapter is implemented, not verified. Errors propagate; no fake fallback.
- `laya.config.RunConfig(model='aac6fef/laya-typed-decisions-mlx',temperature=None,
  lang='en')` immutable; explicit temperature sends original load temperature map
  and predict lang. None and zero differ. `AgentRegistry(loader=...,real=False)`
  invocation-owned cache keyed model/temperature/lang; caches successful loads.
- `questions.models.Question.from_dict`, `.to_dict`, `.to_predict_dict` (excludes
  name, copies criteria); `questions.load.load_questions` single/list JSON, exact
  duplicate-key/name rejection. No evaluate/runner dependencies.
- `answers.enrich.enrich_prediction/enrich_response` copy and preserve original
  four-decimal mathematics. Missing/empty/singleton distribution is not usable.
- `answers.rules.RulesConfig.from_dict`; accepts returns `(bool,reason)`, unpack.
  Universal then type-specific conditions. Legacy absent/null both None; eqNone
  passes both, failed upper bounds retain below_threshold reason.
  `load_named_rules(path,question_names)` requires exact rules_by_question envelope.
- `answers.interpret.interpret(raw,payloads,policies)` returns each requested name
  with answer/decided/reason; preserves raw. Rejections undecided; accepted
  none_or_unclear distinct. Score uses Python round, clamp, zero-based legend.
- `blocks.QuestionBlock(directory).run(text,config=...,registry=...,
  question_payloads=None)`: default reads questions/rules, one real adapter call,
  real interpreter. Optional dynamic override requires exact same names, validates
  through Question.from_dict and copies payloads. Errors propagate to flow.
- `building_blocks.file_reference_utils.detect_file_references(text,pattern)`:
  external string/compiled text regex with named path capture, complete path alone
  excluding delimiters/suffixes. Frozen FileReference(path,filename,kind,start,end),
  exact capture spans/order/duplicates; no filesystem/intent. Case-sensitive kind:
  declaration .d.ts, test_code .spec.ts/.test.ts, production_code .ts/.tsx/.js/.jsx,
  otherwise non_code. Backslash/control captures explicitly reject. Regex owns
  complete space-path syntax; no implicit path grammar in this utility.
- `building_blocks.resolve_file.resolve_file(reference,cwd=...,repository_root=...)`:
  FileReference or string; canonical absolute Resolution(status,selected_path,
  candidates tuple). Case-sensitive production .ts only, including canonical
  symlink targets. Exact path wins; only bare missing basename scans. Sorted
  deduplicated canonical candidates; ambiguity never selects. Status resolved,
  missing, ambiguous, excluded, not_file, inaccessible, outside_repository. Search
  skips .git/node_modules/symlink directories; scan errors suppress selection.
- `building_blocks.typescript.outline(path,node='node',helper=DEFAULT_HELPER,
  timeout=5.0)`: subprocess argv JSON request {action:'outline',path}. Schema1 dict:
  canonical path, source_hash SHA256 decoded UTF8, callables each id/name/signature/
  start/end/location, diagnostics list(code/message/start/end), limitations list.
  IDs are hash:start:end. Ranges/end exclusive/columns are UTF16 code units;
  locations 1-based. Only ordinary named top-level implementations supported.
  Nested/class/arrow/expression/async/generator/overload forms explicit diagnostics.
  Parser errors fail, never trust recovery outlines. No source import/execute.
- `typescript.extract_callable(path,callable_id,node=...,helper=...,timeout=5.0)`:
  JSON extract action with id; same one-read snapshot supplies hash/outline/code.
  JS slice uses UTF16 offsets (Python never indexes them). Returns schema1 path,
  source_hash, callable metadata, exact raw code, separate display_code, diagnostics,
  limitations. Leading attached/trailing comments excluded; body comments retained.
  Raw LF/CRLF preserved; display numbered lines use LF. Invalid/stale IDs fail.
  Python bridge validates schema/provenance/range length and raises TypeScriptError
  for startup/build/nonzero/JSON/schema/timeout errors. Timeout >0 and <=60sec.
  Default helper supports source checkout; installed callers must supply built
  helper path with its pinned dependency. No wheel compiler bundling claimed.
- `building_blocks.questions.method_selection.block.run(text,source_outline,
  config=...,registry=...,max_candidates=64,max_input_chars=16000)` returns
  selected_id/reason/decisions/candidate_map. Four files questions/rules/block/README
  same contract as ticket_triage; installed-wheel resources tested for both.
  method dynamic choices map opaque IDs to signatures plus none_or_unclear;
  multiple_relevant noul independently bound. Only accepted method plus accepted
  multiple=no selects. Sentinel/multi/rejections no-op; unknown choice adapter error.
  Source map path/hash/ranges stays outside payload. No candidates/budget overflow
  avoids loader and never truncates. Budget = text Unicode chars + compact question
  JSON chars, not tokens. New provisional baseline, original working definition
  unavailable. Accuracy and policy calibration unmeasured.
- `flows.file_method_context.run(prompt,cwd=...,repository_root=...,config=...,
  registry=...,reference_pattern=DEFAULT_REFERENCE_PATTERN,node='node',
  helper=DEFAULT_HELPER,timeout=5.0,max_candidates=64,max_input_chars=16000,
  fallback_config=None,fallback_max_input_chars=16000)`:
  case-insensitive explicit `Explain`, one backtick-quoted production .ts path,
  colon, nonempty question. Requires exactly one lexical mention equal to target;
  default regex detects quoted spaces and plain extra file mentions. Filename only,
  output-only and incidental logs do not infer intent. Context result exactly
  {status:'context',reason:None,context:<extract dict plus coverage:'partial'>};
  no-op {status:'noop',reason:<reason>,context:None}. Flow uses real components,
  checks confinement before outline/extract and validates mapped path/hash/callable.
  Source/model failures are safe no-ops. Prompt/source unchanged. No dependencies
  collected; exact callable is useful but context explicitly partial.
- Phase 14 opt-in `fallback_config` only triggers when method is policy-rejected
  and multiple_relevant is accepted `no`. Appends a fixed snapshot ID/signature
  summary to the original text, unchanged question choices. Independent positive
  fallback input budget counts Unicode text plus compact questions JSON; refuses
  without truncation. Invalid second budget no-ops before work. Max two model
  calls, no exceptions/explicit no-match/multi/unclear-multi/second rejection retry.
  Default None disables changed-input fallback; no benefit/accuracy evaluation.
  Actual method_selection + ticket_triage blocks compose with independently bound
  policies and registry A/B/A object reuse in test_flow_branches.py.
- `hooks/user_prompt_submit.py` is the only adapter, standalone POSIX command.
  Required `--repository-root` absolute path, optional `--config` using RunConfig,
  `--real` explicit lazy opt-in. Omit --real => safe no-op, no SDK import. No
  runtime mock mode; tests supply child-only sitecustomize fake laya_mlx.load.
  stdin object requires string hook_event_name/cwd/prompt, exact UserPromptSubmit;
  different events silently no-op. Cwd must canonicalize to existing directory
  within root. Duplicate JSON keys reject. Unknown extra event fields preserved
  outside pipeline; only prompt goes to flow unchanged. Session_id is not needed
  by this adapter. stdin max65,536 Unicode chars, additionalContext max8,000
  (lower with --max-context-chars); refuses, never truncates. Accepted output is
  exactly {hookSpecificOutput:{hookEventName:'UserPromptSubmit',
  additionalContext:<HEADER + compact JSON context string>}}. HEADER is
  'Selected TypeScript context (partial):\n'. Safe no-op/errors exit0 empty
  stdout and stderr diagnostics; argparse errors never exit2. Pipeline Python
  stdout redirects to stderr; native SDK stdio remains unverified.
  --deadline defaults10s, explicit finite >0<=300s; helper remains5s. Default and
  max are administrative bounds, not measured Laya latency. SIGALRM covers Python
  stdin/import/load/flow path but cannot guarantee interrupting native C. Future
  outer harness timeout must exceed explicit deadline with grace (example+5s).
  Astra high reviewed this pre-implementation before relaxing the old20s cap;
  21/300 quick mocks and invalid finite/nonfinite bounds covered. Live cold load,
  inference and cancellation need Phase20 observations. No activation happened.
- Phase 16 `examples/user_prompt_submit_scenario.py` creates a disposable source
  fixture and SDK shim, launches real hook via Bash/Python, validates fixed mock
  request/response, emits actual protocol JSON. No Claude/settings writes.
  `docs/hook-usage.md` gives a future manual project-local settings recipe after
  live prerequisites; tests parse it and run its command only with fake SDK,
  including omission of --real as opt-out. Actual reload/delivery/disable behavior
  remains unverified. Scenarios cover actual tracked basic.ts greet/twice in
  distinct invocations, exact source/provenance/partial context, stdout purity,
  rejected/abstained/malformed/model-error no-ops and deliberate temp-source edit
  after accepted selection causing real extractor_error. Tracked fixture and
  request fixture bytes remain unchanged; only SDK is mocked.

## Commands and execution evidence

Source checkout: Python3.12.14/pytest9.2.0; Node24.22.1/npm11.9.0. Helper package
pins TypeScript5.9.3 and @types/node24.10.1 with package-lock.json.

```bash
python -m pip install -e '.[test]'
npm --prefix typescript-helper ci --ignore-scripts --no-audit --no-fund
npm --prefix typescript-helper run build
npm --prefix typescript-helper test
python -m pytest -q
PYTHONPATH=src python examples/basic_question.py
PYTHONPATH=src python examples/file_method_context.py
PYTHONPATH=src python examples/user_prompt_submit_scenario.py
```

Build/typecheck + all 6 Node and 345 Python tests pass at Phase 16 candidate;
independent Luna reviewer final evidence is recorded in docs/phases/phase-16.md.
No required test is skipped or xfailed. Phase 15 published fac696fa3ddca2e1aa477dacf2705ba396d1f5ee;
Phase 16 follows in this commit; use git log after publication for its API SHA. Python suite
includes wheel build/resource-byte checks and isolated installed imports of both
blocks. Repeat fresh build and all suites at every phase; npm ci needed when
setting up/dependencies change. Serialize all dependency/build/suite operations
between implementer and reviewer. A concurrent npm ci in Phase14 temporarily
removed shared node_modules, causing MODULE_NOT_FOUND failures; Astra independently
diagnosed the environmental race. Serial reruns passed without source/test/timeout
changes. Never run npm ci or a build while another agent validates the shared tree. No repository-required formatter/linter/CI extras.

Offline example prompt: Explain `tests/fixtures/typescript/basic.ts`: how does greet
work? Mock explicitly selects first fixture candidate; output exact greet source,
raw provenance and coverage partial. It does not infer an answer from prompt or
claim actual selection accuracy. All original163 tests preserved through extensions.

## Mandatory workflow and publication

Each next phase: separate low-cost planner BEFORE implementation; baseline all
suites; TDD missing-behavior red; smallest implementation; final full accumulated
suite; independent verifier rereads actual diff and reruns all; VERIFIED before
focused commit including phase/progress/README. No required skips/xfail. Unexpected
bugs or review blockers require heavy reasoning diagnose+fix, then full re-run and
re-review. Expected TDD reds are planned. User explicitly requested low-cost easy
agents: gpt-6-luna/medium fork-none planner/reviewer; gpt-6-astra/high fork-none
repair. If a substantive change to the agreed phase design, public contract, test
gate or scope is needed, Astra/high must reason through it BEFORE implementation;
preserve roadmap unless justified change is documented. Routine implementation
choices need no escalation. Root will hand17–19 to fresh Sol/medium after16 is
verified and published. Reusable agents currently /root/flow_builder/phase_reviews
(Luna medium) and /root/flow_builder/source_repairs (Astra high); root may reuse
or assign fresh equivalents.

Git CLI has no remote credentials. /root/publisher owns authenticated GitHub API
publication to main. Send each verified local commit/test counts/verdict to root
and publisher, then WAIT exact-tree + local-HEAD sync acknowledgment before next
phase. Publisher creates server commit IDs, fetches and synchronizes clean main.
Never force push/discard files. Phase12 published62922776cfa00f6b9bf643252fd061c24c681362;
Phase13 published8a46ea56ea75dad5ed4ad37e2566d5ec58123da6;
Phase14 published01a29ac69a2a53d0ade128fea2f150723e2a930e;
Phase15 publishedfac696fa3ddca2e1aa477dacf2705ba396d1f5ee. Phase16 was
independently verified in local candidate f44e7dd; check remote main for its
server-assigned ID. A handoff-driven hook hardening increment follows Phase16;
check progress and git log before starting 17.

No AGENTS found in repo/ancestors by root; no old runner/framework added. Keep
model/SDK/harness evidence honest: mocks establish mechanics, never live support.

## Remaining authorized phases

17: broaden callable forms with advertised fixture matrix and source fidelity;
small groups/subphases allowed, each independent planner/review/full-suite/commit.
18: symbol-aware bounded same-file dependencies, raw statements, explicit gaps.
19: project/tsconfig-aware cross-file resolution, boundary/budgets/side effects,
external/declaration/dynamic/missing config gaps; partial caller coverage honest.
20: BLOCKED on host, do not install/import/load/infer. Real checkpoints/settings,
model compatibility and actual harness delivery remain unverified separately.
The final isolated Claude check must capture version, commit, actual command and
settings, `/hooks` registration, debug parsing/timeout/overflow evidence, and
a fresh unpredictable hook-only marker returned without alternate tool/source
access plus a disabled-hook control in a fresh session. The marker test is a
diagnostic path, removed afterward; report actual Claude receipt separately
from actual Laya response compatibility and mock protocol/full-flow results.
Missing MLX/SDK or harness access is a blocked/unrun check, never mock success.

Read docs/implementation-plan.md entire for exact tests/gates; don't redo01–16.
Initial source subset deliberately narrow; no broad dependency completeness claim.

## Provenance and research

Original read-only source outside repo:
/workspace/scratch/aae8a6a84dee/laya-source/LAYA/code/runner/.
Reusable pure helpers extracted, never old workflow/TestCase/report engine.
Uploaded script AST-literal-extracted, never executed. Fixtures retain full supplied
request/raw JSON, choice pair, separate enrichment from original pure helper with
SHA in fixture README. Requested captured model aac6fef/laya-mlx differs from source
default deliberately; raw label laya-rl-agent is not proven checkpoint identity.
SDK/revision unknown; no private archive/source committed. Synthetic TS fixtures
and raw variants clearly labelled, original captures unchanged.

Official TypeScript Compiler API wiki/Architectural Overview and compiler source
checked2026-10-29 for parser APIs/token starts/UTF16 positions. Hook protocol
reverified by implementer and independent planner on2026-10-29:
https://code.claude.com/docs/en/hooks (unversioned, root fetched2026-10-29).
UserPromptSubmit input session_id,cwd,hook_event_name,prompt; exit0 JSON
hookSpecificOutput:{hookEventName:'UserPromptSubmit',additionalContext:'...'};
exit0 empty stdout no-op. stderr logs only; errors must not unintentionally block.
No active Claude harness installed/tested; official protocol not actual delivery.
The handoff at /workspace/scratch/c0679bf67556/laya-hook-integration-handoff.md
clarifies additional context versus prompt replacement, complete rendered-budget
behavior, native stdout isolation, and separate delivery evidence. The hook
hardening increment adds regression cases for native fd1 output, missing and
ambiguous files, extra input fields, load/predict deadlines, Unicode and metadata
budget, and a tested synthetic usage example. Preserve these when expanding
source context in 17–19; test the final hook budget with new dependency bundles.

## Fresh builder entry checklist after publication

1. Confirm remote main/local HEAD exact tree and clean worktree with root/publisher.
2. Read this handoff and full implementation-plan; inspect TypeScript helper,
   bridge validation and accumulated tests. No code owner overlaps.
3. Have separate Luna medium plan Phase17 or17a BEFORE tests/implementation; run
   complete baseline (fresh TS build/typecheck, all Node, all Python), serialized.
4. Advertise exact callable fixture matrix. Preserve old unsupported-form regression
   expectations unless the documented phase intentionally promotes those forms;
   replace with positive source-fidelity coverage and explicit remaining gaps.
   Broad AST discovery must retain hash:start:end identities, UTF16 ranges, parser
   error failure, exact raw slices and separate display text. Group17a/17b/17c
   if useful, each its own verified/published commit.
5. Phase18 needs real TypeScript symbol identity, not text/name matching. Bound
   depth/size/order and disclose closures, mutable/side-effect/dynamic omissions.
6. Phase19 needs actual tsconfig-aware program/module resolution, aliases and
   reexports; repository boundary, budgets, external/declaration gaps explicit.
   Preserve selected callable even when dependencies partial. Do not execute
   project modules or load arbitrary external implementations. Partial caller
   coverage must stay honest.
7. Design/public-contract/gate changes or unexpected failures: Astra high reasoning
   BEFORE implementation; planned TDD red is expected. Every final candidate gets
   independent Luna diff inspection + full rerun after implementer full suite.
8. Commit focused code/tests/README/progress/phase evidence then send SHA to root
   and publisher. WAIT exact-tree remote/local sync ACK before next increment.
9. Root reports after19; do not silently stop before19. Phase20 remains blocked
   on current host; no live SDK install/import/weights/inference/harness activation.
