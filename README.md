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
