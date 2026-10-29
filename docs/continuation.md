# Implementation handoff after Phase 07

User authorized the entire mock-first plan through Phase19, public repository
publication, merging to main, and continuing directly on main as sole writer.
Do not stop at the reusable-core milestone. Phase20 is blocked on this host:
Linux x86_64; `laya_mlx` and `mlx` absent (stdlib discovery only). No models have
been loaded, imported, downloaded or executed. Do not install MLX or call models.
No hook has been activated. Root coordinates publication and remaining phases.

## Current public contracts

- `laya.predict.predict(text, named_question_payloads, *, model=DEFAULT_MODEL,
  loader=None, real=False, config=None, registry=None)` returns a deep-copied raw
  JSON response after shape/type/membership/numeric/legend validation. Default
  mode requires an explicit injected loader. Live loader imports SDK lazily and
  is implemented but unverified. SDK errors propagate; no fake fallback.
- `laya.config.RunConfig` is immutable: model default
  `aac6fef/laya-typed-decisions-mlx`, temperature None, lang en. Only explicit
  temperature sends `lang_temperatures={lang:{temperature:[t,t,t]}}` at load and
  `lang=lang` at predict. None and zero differ. `.to_dict/.from_dict/load_config`
  preserve source valid settings. `.load_kwargs/.predict_kwargs` return fresh data.
- `laya.registry.AgentRegistry(loader=..., real=False)` is invocation owned, keyed
  `(model,temperature,lang)`, caches successful agents only. No global state.
- `questions.models.Question.from_dict` returns choice/noul/score classes.
  `.to_dict` includes name; `.to_predict_dict` excludes name and copies criteria.
  No evaluate method. `questions.load.load_questions(path)` supports single/list,
  duplicate names/JSON keys rejected, empty list returns empty mapping.
- `answers.enrich.enrich_prediction` and `enrich_response` copy data and preserve
  original four-decimal math. Missing/empty/singleton distributions and absent/null
  noul receive no derived fields. Those are not trusted as usable predictions.
- `answers.rules.RulesConfig.from_dict` loads inner policies; `conditions_for` is
  universal conditions then type-specific. `accepts` returns `(bool,reason)`;
  always unpack. Operators gt/gte/lt/lte/eq. Legacy missing/null both resolve None,
  so eqNone passes both; failed upper bounds retain below_threshold reason.
- `answers.rules.load_named_rules(path,question_names)` requires the canonical
  rules_by_question envelope with exact keys and duplicate-safe JSON loading.
  Inner policy name does not select question. No alternative block file format.
- `answers.interpret.interpret(raw,named_payloads,named_policies)` iterates requested
  names, returns `{name:{answer,decided,reason}}`, ignores unrequested answers, and
  preserves raw. Invalid predictions and policy rejection are undecided; accepted
  none_or_unclear remains decided. Score: Python round, clamp, zero-based legend.
- `blocks.QuestionBlock(directory).run(text,config=...,registry=...)` loads question
  definitions and named rules, performs one actual adapter call for all questions,
  then real interpretation. Errors propagate to caller. The ticket_triage example
  folder has four files and illustrates two questions, one accepted/one rejected.

## Evidence and development workflow

See docs/phases/phase-01.md through phase-07.md and implementation-plan.md. Preserve
all tests and captured fixtures. Python command: `python -m pytest -q` (pytest9.2.0,
Python3.12.14). At Phase07 candidate:163 passed,0 failed,0 skipped. Build check:
`python -m pip wheel --no-build-isolation --no-deps --wheel-dir /tmp/laya-context-router-wheels .`;
wheel inspected to contain all four example block files. Artifacts/build dirs ignored.
Node24.22.1 is present; no TypeScript dependency/helper/build/tests introduced yet.
Add these only in Phase10. No repository-specific formatter/linter/CI instructions.

Every phase: independent low-cost planner BEFORE implementation; baseline full
suite; tests written and expected missing-behavior red observed; smallest feature;
final accumulated fullsuite; independent final candidate inspection AND rerun;
VERIFIED verdict; focused commit including phase/progress record; publish. Keep
failed/skipped/not-run and fixture/execution provenance explicit. Unexpected bugs
or review blockers go to a heavy reasoning agent (user specified gpt-6-astra/high)
for diagnose+fix, then fullsuite+independent reverify. Expected TDD reds are planned.
Existing Luna reviewer task was phase01_plan; Astra repairs task handled specific
repairs and can be resumed or recreated as needed. Do not claim review not done.

Git CLI lacks remote credentials. Root/publisher use authenticated GitHub API to
create blobs/tree/commit, update remote main, fetch, verify exact tree equality,
then sync local main to the server-assigned commit ID. Send each local verified
commit to root and publisher; WAIT for publication/sync acknowledgement before
starting the next phase. Parent hashes may differ from local candidate hashes
because publication assigns IDs. Never discard working files. Published Phase06
is4fa7c214185d6747cd6a6a37a2576965c1df9173; latest phase appears in git log.

## Source and fixture provenance

Original read-only reusable source is outside this repo at
`/workspace/scratch/aae8a6a84dee/laya-source/LAYA/code/runner/` config/questions/
enrich/rules/evaluator/engine.py. Do not copy the runner/framework or source folder.
The uploaded script was AST-literal-extracted, never executed. Tests fixtures retain
complete supplied raw JSON, full captured request, derived choice-only pair, and
separate enrichment snapshot generated using only original pure enrich.py (source
SHA in fixture README). Requested captured checkpoint `aac6fef/laya-mlx` differs
from source default, deliberately preserved. Raw response model label is
`laya-rl-agent`, not proven checkpoint metadata. SDK/revision unknown. Captured
request covers choice/noul/score and five names. Synthetic variants are clearly
in test code and do not pretend to be captures. No private source archive committed.

## Next work

Continue Phases08–19 sequentially as detailed in implementation-plan.md:
regex detection, bounded deterministic resolution, pinned TypeScript JSON helper/
Python bridge, exact UTF16-safe code retrieval, dynamic method-selection block,
offline explanation flow, bounded disabled fallback/multi-block composition,
officially documented Claude UserPromptSubmit protocol and subprocess scenarios,
broader callable AST coverage, symbol-aware same-file and project-aware cross-file
context. No workflow engine. Keep hook filename hooks/user_prompt_submit.py.

Root's official-doc research: https://code.claude.com/docs/en/hooks fetched2026-10-29
(unversioned). UserPromptSubmit input includes session_id,cwd,hook_event_name,prompt;
exit0 JSON output hookSpecificOutput:{hookEventName:'UserPromptSubmit',
additionalContext:'...'} adds context; exit0 no stdout is no-op. Logs stderr only;
do not exit2/block user prompt on extraction/model error. Confirm docs when reaching15.
No session activation or real harness is required for15–16; delivery remains unverified.
TypeScript official Compiler API wiki and microsoft/TypeScript source document
UTF16 getStart/getEnd positions and checker symbol/alias APIs. Use compiler parser,
not source execution or regex-only dependency resolution. Pin compatible version.

Keep Phase20 explicitly blocked until real supported environment and two distinct
compatible checkpoints/temperatures exist; mock evidence never proves live support
or model accuracy. No real calls are authorized on this host by this handoff.
