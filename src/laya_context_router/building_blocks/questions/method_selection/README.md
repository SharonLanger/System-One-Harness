# Method selection baseline

These are new provisional signature-only questions, not a recovered original
working method definition. Captured Laya fixtures establish response processing;
controlled method responses establish mechanics, not selection accuracy.

`block.run(text, source_outline, config=..., registry=...)` builds `method` criteria
from opaque source-bound candidate IDs and signatures, with `none_or_unclear`.
`multiple_relevant` is independently bound to its own named policy. Only an accepted
candidate and accepted `multiple_relevant=no` select a method. Sentinel, rejection,
or multiple methods return no selection. Unknown model IDs fail adapter validation.

Result: `selected_id`, `reason`, named `decisions`, and `candidate_map` with the
original range/location/path/hash. This map never goes into the SDK question payload.
One actual shared QuestionBlock call handles both questions and real interpretation.
Dynamic template criteria are copied; policies and expected answers never go to Laya.

No candidates means no call. Defaults:64 candidates;16000 input Unicode characters
(prompt plus compact question JSON, not tokens). Budgets reject explicitly before
inference without truncation. Thresholds are illustrative, not calibrated. Broader
callables and dependency context remain incomplete.
