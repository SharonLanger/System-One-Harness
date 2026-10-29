# API and implementation status through Phase 19

Phases01–19 are implemented and independently verified for the documented
bounded scope with the Laya SDK boundary mocked.
Phase20 live integration is blocked: the verification environment is Linux x86_64
without MLX or laya_mlx. No real model loading, inference or Claude activation has
been performed. Mock results establish pipeline behavior, not live compatibility,
selection accuracy, policy calibration or token savings.

## Current API contracts

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
  question_payloads=None)`: default reads questions/rules, one adapter invocation,
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
  locations 1-based. Runtime implementation bodies are discovered recursively:
  functions, arrows/function expressions, methods/constructors/accessors, object
  and class members, callbacks, async/generator forms, overload implementations,
  anonymous defaults and computed members. Member names retain source spelling;
  declared function names retain semantic identifier names. IDs distinguish scope.
  Binding-aware signatures include immediate variable/property headers and
  transparent wrappers; raw ranges/code remain the callable expression alone.
  Bodyless runtime declarations and destructuring-bound expressions remain
  explicit diagnostics. Type-only signatures are not implementation candidates.
  Computed names are never evaluated. Binding inference never crosses calls,
  conditional/binary expressions or arbitrary ancestors. Unbound anonymous names
  use <anonymous@line:column>; anonymous default functions use <default>.
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
- Phase18A `typescript.collect_local_context(path,callable_id,max_depth=2,
  max_dependency_chars=12000,node=...,helper=...,timeout=5.0)` adds same-file
  semantic dependencies to exact selected extraction, with `coverage:'partial'`,
  raw dependency units, declaration-based `symbol_ids`, explicit gaps and source
  accounting. Same-read isolated checker never loads imports/libraries/configs.
  Module statements/types/functions/classes and same-class members are eligible;
  outer locals are closure gaps. BFS admission, source-order presentation and
  whole-unit depth/size omissions are deterministic. Dependency budget counts
  UTF16 units in dependency code only, including overlaps; selected code and
  metadata are excluded. Depth0–20, positive budget<=1,000,000. External/runtime
  state, callers and other module initialization remain partial. Phase18B integrates
  this collector into the flow/hook with independent model/final-render budgets.
- Phase19A `typescript.collect_project_context(path,callable_id,
  repository_root=...,max_depth=2,max_dependency_chars=12000,node=...,helper=...,
  timeout=5.0)` adds confined project context as a separate API. TypeScript parses
  the nearest tsconfig and resolves Classic/Node10 relative/path aliases and
  named/default/star/local reexport routes by requested name plus symbol identity.
  Modern modes, missing/broken config and project mismatch retain local context
  with explicit gaps. Per-file path/hash/ranges qualify units/symbols and gaps;
  project metadata records consumed JSON configuration/module metadata hashes.
  Canonical confinement covers config/source/module/reference/symlink origins;
  package implementations are never loaded, including internal package symlinks.
  Namespace/property dispatch, ambiguity, declarations, ambient state, callers,
  libraries, referenced projects and module effects remain partial gaps. Graph
  loading separately caps64 unique source attempts (including failures),4,000,000
  cumulative foreign pre-read bytes and1,000,000 admitted foreign UTF16 units.
  Source emission retains whole-unit depth/size bounds. Phase19B integrates this
  collector into flow/hook; direct local/extract APIs remain available.
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
  fallback_config=None,fallback_max_input_chars=16000,
  max_dependency_depth=2,max_dependency_chars=12000)`:
  case-insensitive explicit `Explain`, one backtick-quoted production .ts path,
  colon, nonempty question. Requires exactly one lexical mention equal to target;
  default regex detects quoted spaces and plain extra file mentions. Filename only,
  output-only and incidental logs do not infer intent. Context result exactly
  {status:'context',reason:None,context:<project context dict with coverage:'partial'>};
  no-op {status:'noop',reason:<reason>,context:None}. Flow uses real components,
  checks confinement before outline/collection and validates mapped path/hash/callable.
  Source/model failures are safe no-ops. Prompt/source unchanged. Invalid dependency
  limits no-op before source/model work. Complete selected code plus bounded
  semantic project dependencies/configuration gaps remain explicitly partial.
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
  stdout and synchronous file-descriptor-1 output redirect to stderr. Tests
  cover simulated native writes; actual backend output remains unverified.
  --max-dependency-depth defaults2 (0–20); --max-dependency-chars defaults12,000
  (1–1,000,000 UTF16 source units), separate from final Unicode rendering. Invalid
  limits no-op before SDK loading. Final overflow never retries with fewer units.
  --deadline defaults10s, explicit finite >0<=300s; helper remains5s. Default and
  max are administrative bounds, not measured Laya latency. SIGALRM covers Python
  stdin/import/load/flow path but cannot guarantee interrupting native C. Future
  outer harness timeout must exceed explicit deadline with grace (example+5s).
  Fast mocked calls cover explicit21/300-second bounds and invalid
  finite/nonfinite values. Live cold load,
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

## Reproduce the mock validation

Verified environment: Python3.12.14, pytest9.2.0, Node24.22.1 and npm11.9.0.
The helper pins TypeScript5.9.3 and @types/node24.10.1 in its lockfile.
Run from the repository root:

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

Run dependency installation, builds and suites sequentially when sharing one
checkout, because reinstalling dependencies during validation can remove files
being tested. A fresh build is required before the Python-to-Node integration
suite. The Python suite includes isolated wheel/resource checks for both blocks.
No required mock test is skipped or xfailed.

Phase17A: fresh build/typecheck, Node10/10 and Python354/354 passed, including an
exact-budget hook scenario for an async class method. Phase17B: fresh build,
Node14/14 and Python356/356 passed. Independent verification reran those suites
and reviewed the implementation and test matrix; its Phase17B Python run took
92.22seconds. Phase17C independently verified the complete advertised17A/B/C
matrix with fresh build/typecheck, Node19/19 and Python358/358 in74.94seconds;
zero failures/skips/xfail. See [17A](phases/phase-17a.md),
[17B](phases/phase-17b.md) and [17C](phases/phase-17c.md).

Phase18B independently verified fresh build/typecheck, Node26/26 and Python395/395
in102.12s. Phase19A independently verified Node53/53 and Python408/408 in102.88s;
Phase19B independently verified Node53/53 and Python415/415 in112.86s, each with
a fresh build/typecheck and zero failures/skips/xfail. See [18A](phases/phase-18a.md),
[18B](phases/phase-18b.md), [19A](phases/phase-19a.md) and
[19B](phases/phase-19b.md) for source/budget contracts and known gaps.

Example prompt:

```text
Explain `tests/fixtures/typescript/basic.ts`: how does greet work?
```
The offline example explicitly configures a mock to select the fixture's first
candidate. It returns exact source/provenance with partial coverage; it does not
infer an answer in the mock or establish actual model-selection accuracy.

## Source coverage and continuing constraints

Phase17 callable discovery is complete for the advertised matrix. Preserve
source hash:start:end identity, UTF16 positions, exact
raw slices, separate display text, parser-error failure and explicit unsupported
diagnostics. Existing unsupported-form expectations may change only when replaced
with positive source-fidelity coverage for the deliberately promoted form.

Phase18 provides bounded same-file context using TypeScript symbol identity
rather than spelling matches. Preserve raw dependency statements, deterministic order,
deduplication, depth/size bounds and explicit gaps for closures, mutable state,
side effects and unresolved/dynamic references. Keep selected code intact.

Phase19 provides documented Classic/Node10 project resolution and hook delivery
for relative paths, aliases and proven reexports. Modern resolution modes and
unproven foreign dispatch remain explicit gaps. Enforce repository boundaries and identify external,
declaration-only, missing-config/module and dynamic/inherited gaps. Do not execute
project modules or load arbitrary package implementations. Caller coverage remains
explicitly partial where it cannot be established reliably.

Keep three budgets separate: model question input, source/dependency collection,
and the final rendered hook additionalContext string. Deliver complete selected
code or the documented no-op. Never truncate code or silently imply omitted
dependencies were included. Exercise final rendering with oversized local and
cross-file bundles, provenance and gap metadata.

Each implementation increment requires independent preimplementation test
planning, tests-first missing-behavior checks, a complete fresh build and all
accumulated suites, then independent diff review and a separate full rerun.
Required skips/xfails do not satisfy the gate. Preserve these gates when modifying
source coverage. The full roadmap and phase criteria are in
[implementation-plan.md](implementation-plan.md).

## Live integration and harness evidence still needed

Phase20 requires a supported runtime and compatible checkpoints/settings. Verify
actual SDK response compatibility and independently calculate processing results
from actual returned data; different valid model answers are allowed. Record
observed model/settings metadata and its limits separately from requested values.
Missing prerequisites remain blocked checks, never substituted mock successes.

Actual Claude delivery needs a separate isolated harness check. Record version,
commit, exact command/settings, registration and debug parsing/timeout/overflow
evidence. A fresh unpredictable hook-only marker and a disabled-hook control in
a fresh session test delivery without alternate source/tool access. Remove the
diagnostic marker path afterward. Report mock protocol, mock full flow, actual
Claude receipt and live Laya compatibility separately; delivery does not prove
selection accuracy or use of every code line. No such harness check has run.

## Fixture provenance and protocol reference

Fixtures preserve the supplied request/raw-response JSON and separate enriched
output, with provenance recorded in their README. Synthetic TypeScript fixtures
and raw variants are labelled; original captures remain unchanged. The captured
requested model aac6fef/laya-mlx differs from the source default deliberately.
The raw label laya-rl-agent does not prove checkpoint identity; SDK/revision
metadata remain unknown. Private archives and project source are not fixtures.

The documented hook contract was checked against the official hooks reference
on2026-10-29: https://code.claude.com/docs/en/hooks . UserPromptSubmit emits exit0
JSON with hookSpecificOutput.hookEventName and string additionalContext, or
exit0 with empty stdout for no-op. Diagnostics use stderr. The reference and
subprocess tests are protocol evidence, not proof of actual harness delivery.
