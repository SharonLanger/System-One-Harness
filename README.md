# Laya Context Router

Reusable Python decisions with a lazy Laya SDK boundary. Implementation is staged
in [the plan](docs/implementation-plan.md) and [progress](docs/progress.md).

```bash
python -m pip install -e '.[test]'
python -m pytest -q
PYTHONPATH=src python examples/basic_question.py
```

The example uses an explicit mock loader. No SDK, weights, GPU, service access,
or inference is required. The real adapter is implemented but has not been verified
against live Laya. Real mode is explicit and never falls back to mock success.

Create `RunConfig(model=..., temperature=..., lang=...)` and an `AgentRegistry`
with an explicit loader to reuse agents within one invocation. Pass both as
`config=` and `registry=` to `predict`. Distinct model/temperature/language keys
load distinct agents; a new registry starts fresh. Defaults preserve the original
SDK argument contract, including omitting `lang` when temperature is omitted.

`questions.load.load_questions(path)` accepts a single complete definition or a
list. Each definition has `name`, `type`, `instructions`, and ordered `criteria`
for choice/score. Build the SDK mapping with
`{name: q.to_predict_dict() for name, q in questions.items()}`. Definitions do not
contain expected answers or policies. Empty lists load to an empty mapping;
submitting an empty question request is rejected by the adapter.

`answers.enrich.enrich_prediction` and `enrich_response` return copies with the
original four-decimal gap/entropy (choice/score) or midpoint distance (noul).
Malformed numbers fail explicitly. Missing distributions or noul values receive
no derived fields; enrichment alone does not establish a usable answer.

`RulesConfig.from_dict` loads an inner policy; `accepts(prediction, rules)` returns
`(decided, reason)` and must be unpacked. Universal conditions precede type-specific
conditions. Operators are `gt/gte/lt/lte/eq`; dotted fields resolve dictionaries.
Legacy semantics: missing and explicit null both resolve to `None`, so `eq None`
passes both. Any failed upper/lower bound retains `below_threshold:<field>`;
missing/null failures use `field_missing:<field>`. The block envelope arrives next.

`answers.interpret.interpret(raw, named_question_payloads, named_policies)` returns
all requested decisions as `{answer, decided, reason}`. Policy rejection and invalid
predictions become `undecided`; accepted `none_or_unclear` stays a distinct answer.
It ignores extra unrequested answers and preserves raw data. Score extraction uses
Python `round(score)`, clamps to legend bounds, then indexes zero-based string keys.
It never uses expected answers or probability argmax for score extraction.

A reusable block is a folder with `questions.json` (a list), `rules.json`
(`{"rules_by_question": {"question_name": inner_policy}}`), `block.py`, and
`README.md`. See the [ticket triage block](src/laya_context_router/building_blocks/questions/ticket_triage/README.md).
`QuestionBlock(directory).run(text, config=config, registry=registry)` sends all
questions in one SDK call and returns independently named decisions. Missing/extra
policies and duplicate configuration keys fail before inference.

`building_blocks.file_reference_utils.detect_file_references(text, pattern)` is a
pure lexical detector. Supply a string or compiled regex with a named `path`
capture containing the complete POSIX path, excluding quotes and `:line:column`.
For example, a pattern containing the named group `(?P<path>[^>]+)` between
angle brackets captures a delimited path including spaces. The expression owns supported syntax; use delimiters for paths with spaces
and never capture only their suffix. Results preserve duplicates and path spelling,
with `filename`, exact capture `start/end`, and a case-sensitive lexical `kind`:
`declaration` (`.d.ts`), `test_code` (`.spec.ts`/`.test.ts`), `production_code`
(`.ts/.tsx/.js/.jsx`), or `non_code`. Backslash paths/control characters reject.
A log mention remains a mention; this API never reads files or decides intent.

`building_blocks.resolve_file.resolve_file(reference, cwd=..., repository_root=...)`
resolves eligible production `.ts` references inside an explicit repository.
Exact paths take precedence; only missing basename-only mentions trigger a sorted
search. It returns `Resolution(status, selected_path, candidates)` with canonical
absolute Paths; ambiguous results never select a file. Statuses distinguish
`resolved`, `missing`, `ambiguous`, `excluded`, `not_file`, `inaccessible`, and
`outside_repository`. Test/declaration/non-TS files are excluded. The search skips
`.git`, `node_modules`, and symlink directories; symlink targets cannot escape the
repository. Any scan error prevents selection. Source contents remain untouched.

Build the source helper before running the accumulated suite:

```bash
npm --prefix typescript-helper ci --ignore-scripts --no-audit --no-fund
npm --prefix typescript-helper run build
npm --prefix typescript-helper test
python -m pytest -q
```

`building_blocks.typescript.outline(path)` calls the real pinned TypeScript5.9.3
parser through a JSON CLI. Initial support is ordinary named top-level function
implementations; other callable forms produce explicit diagnostics. Parse errors
fail. The helper parses source without importing or executing it. Signatures and
UTF16 source ranges retain provenance; dependency collection and exact retrieval
are later stages. The Python bridge uses argv and a bounded process timeout,
validates schema1 output, and raises `TypeScriptError` for helper/protocol errors.
Its default helper path is for this source checkout; installed applications must
supply `helper=` pointing to a built helper with its pinned dependency available.

`building_blocks.typescript.extract_callable(path, callable_id)` returns exact
`code`, its `callable` metadata, path/hash, diagnostics and limitations. Obtain the
ID from the outline; stale/unknown IDs fail. Outline and slice share a single read
snapshot. Slicing happens inside the TypeScript helper using its UTF16 offsets,
so Unicode does not depend on Python indexing. Leading attached comments and
trailing comments are excluded; interior comments remain. Raw code retains source
line endings. Separate `display_code` adds line numbers with LF display newlines.
Dependency context is still incomplete.

The [method selection block](src/laya_context_router/building_blocks/questions/method_selection/README.md)
constructs dynamic ID/signature choices from a real outline and asks `method` plus
`multiple_relevant` in one shared block call. Its source map stays outside the
model payload. Accepted no-match, multiple methods, rejection and explicit input
budget overflow return no selection. The signature questions/policies are a new
provisional baseline; mocks verify processing and source mapping, not accuracy.
`QuestionBlock.run(..., question_payloads=...)` accepts an optional copied/validated
payload override with exactly the block's question names for dynamic definitions.
