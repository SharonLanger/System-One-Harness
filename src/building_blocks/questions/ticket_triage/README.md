# Ticket triage block

The four files define two questions, their independently named policies, a small
Python entry point, and this explanation. Question text/criteria come unchanged
from the supplied capture. Thresholds are illustrative, not calibrated.

```python
from building_blocks.questions.ticket_triage.block import run
from laya.config import RunConfig
from laya.registry import AgentRegistry

# loader is your explicit fake SDK loader; it returns raw predictions, not decisions.
result = run(ticket_text, config=RunConfig(), registry=AgentRegistry(loader=loader))
```

Input is the original ticket text from the captured request fixture. Both named
question bodies go in one call. Rules and expected answers never enter that call.
For the supplied raw department/churn_risk answers, the exact result is:

```json
{
  "department": {"answer": "billing", "decided": true, "reason": null},
  "churn_risk": {"answer": "undecided", "decided": false, "reason": "below_threshold:distance_from_boundary"}
}
```

Department passes 0.9719 confidence and 0.9546 gap. Churn's derived distance
0.0339 fails the 0.1 rule; it does not override the department decision.
Reuse the same invocation registry for repeated calls. One question uses the same
list of definitions and `rules_by_question` envelope with one entry. Outer keys bind
policies; inner policy names need not match. Missing/extra policies or duplicate
JSON object keys fail explicitly. SDK failures/invalid raw responses raise; callers
choose their error handling. No real Laya compatibility is claimed yet.

`run(text, *, config, registry)` now adapts sibling `ticket_triage_v2` execution
back to the original decisions dictionary. `run_legacy` preserves the original
implementation for comparison and rollback. New callers can use V2 with
`{"text": text}` to receive a `BlockResult` and explicit override/preparation options.
