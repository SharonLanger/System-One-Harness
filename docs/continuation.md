# Implementation handoff after Phase 13

User authorized mock-first Phases01–19, public publication, direct main, no routine
approval gates. Phases01–13 are complete in this tree; continue14–19. Root will
assign a fresh sole implementation writer after Phase13 publication acknowledgment.
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
  helper=DEFAULT_HELPER,timeout=5.0,max_candidates=64,max_input_chars=16000)`:
  case-insensitive explicit `Explain`, one backtick-quoted production .ts path,
  colon, nonempty question. Requires exactly one lexical mention equal to target;
  default regex detects quoted spaces and plain extra file mentions. Filename only,
  output-only and incidental logs do not infer intent. Context result exactly
  {status:'context',reason:None,context:<extract dict plus coverage:'partial'>};
  no-op {status:'noop',reason:<reason>,context:None}. Flow uses real components,
  checks confinement before outline/extract and validates mapped path/hash/callable.
  Source/model failures are safe no-ops. Prompt/source unchanged. No dependencies
  collected; exact callable is useful but context explicitly partial.

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
```

Build/typecheck + all6 Node and272 Python tests pass at Phase13 candidate;
independent Luna reviewer reran all and returned VERIFIED. Final evidence is in
docs/phases/phase-13.md. Python suite
includes wheel build/resource-byte checks and isolated installed imports of both
blocks. Repeat fresh build and all suites at every phase; npm ci needed when
setting up/dependencies change. No repository-required formatter/linter/CI extras.

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
choices need no escalation. Root will hand14–19 to fresh Sol/medium after13 is
verified and published. Reusable agents currently /root/source_builder/phase_reviews and
/root/source_builder/source_repairs; root may reuse or assign fresh equivalents.

Git CLI has no remote credentials. /root/publisher owns authenticated GitHub API
publication to main. Send each verified local commit/test counts/verdict to root
and publisher, then WAIT exact-tree + local-HEAD sync acknowledgment before next
phase. Publisher creates server commit IDs, fetches and synchronizes clean main.
Never force push/discard files. Phase12 published62922776cfa00f6b9bf643252fd061c24c681362;
Phase13 follows in this commit; use git log after publication for server-assigned ID.

No AGENTS found in repo/ancestors by root; no old runner/framework added. Keep
model/SDK/harness evidence honest: mocks establish mechanics, never live support.

## Remaining authorized phases

14: bounded second round/multiple distinct block composition, max2 rounds, explicit
input budget; existing first round unchanged; changed-input fallback disabled by
default until separately evaluated. Require A/B/A reuse and correct policy binding.
15: only hooks/user_prompt_submit.py; official documented stdin/additionalContext
protocol, subprocess/mock Laya, safe no-op/errors, stdout purity. No activation.
16: complete isolated subprocess scenarios through actual helper/flow, mock only
Laya. Document enable/disable path without session/global changes. Actual Claude
context delivery remains unverified until supported final environment.
17: broaden callable forms with advertised fixture matrix and source fidelity;
small groups/subphases allowed, each independent planner/review/full-suite/commit.
18: symbol-aware bounded same-file dependencies, raw statements, explicit gaps.
19: project/tsconfig-aware cross-file resolution, boundary/budgets/side effects,
external/declaration/dynamic/missing config gaps; partial caller coverage honest.
20: BLOCKED on host, do not install/import/load/infer. Real checkpoints/settings,
model compatibility and actual harness delivery remain unverified separately.

Read docs/implementation-plan.md entire for exact tests/gates; don't redo01–13.
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
checked2026-10-29 for parser APIs/token starts/UTF16 positions. For15 reverify:
https://code.claude.com/docs/en/hooks (unversioned, root fetched2026-10-29).
UserPromptSubmit input session_id,cwd,hook_event_name,prompt; exit0 JSON
hookSpecificOutput:{hookEventName:'UserPromptSubmit',additionalContext:'...'};
exit0 empty stdout no-op. stderr logs only; errors must not unintentionally block.
No active Claude harness installed/tested; official protocol not actual delivery.
