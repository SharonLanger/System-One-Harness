# Ticket triage V2

`run({"text": text}, config=config, registry=registry)` returns a `BlockResult`
with independent `department` and `churn_risk` decisions and empty domain `data`.
Text must be a string; blank text and whitespace are preserved. Both questions
share the caller's explicit model configuration and one prediction request.

```python
from building_blocks.questions.ticket_triage_v2.block import run
result = run({"text": "Please refund the invoice"}, config=config, registry=registry)
if result.status == "completed" and result.decisions["department"]["decided"]:
    department = result.decisions["department"]["answer"]
```

Use `rule_overrides={"department": "a_named_choice_rule"}` with a rule in an
injected catalog to replace that rule entirely. `question_overrides` replaces
complete question bodies or references. A custom `prepare_input` replaces the
preparer, receives validated input and copied effective definitions, and returns
`PreparedInput`; it cannot change question names/types or bypass validation.
The original `ticket_triage.block.run(text, ...)` remains the compatibility API
returning the decisions dictionary.
