# Composing V2 blocks

A flow is ordinary Python. A block returns `BlockResult`, with `status`, `reason`,
`decisions`, and block-specific `data`. A completed run may contain undecided
answers; check `decided` before using `answer`. A skipped block has no decisions.
Configuration, input and execution errors remain exceptions for the caller's
existing error boundary.

The caller supplies `RunConfig` and `AgentRegistry`. Reuse one registry to reuse
agents for equal configurations; selecting another configuration selects another
agent. Named `rule_overrides` replace the entire rule for the local question key.
Rules affect acceptance, not the model's submitted questions.

```python
from laya_context_router.building_blocks.questions.ticket_triage_v2.block import run as triage
from laya_context_router.laya.config import RunConfig
from laya_context_router.laya.registry import AgentRegistry

registry = AgentRegistry(real=True)
result = triage({'text': 'My invoice is wrong.'},
                config=RunConfig(), registry=registry)
churn = result.decisions.get('churn_risk', {})
if not churn.get('decided'):
    branch = 'manual_review'
elif churn['answer'] == 'yes':
    branch = 'retention'
else:
    branch = 'ordinary_support'
```

Source utilities are deterministic operations, separate from model inference.
Pass a complete outline from the TypeScript utility; the selection block prepares
readable dynamic choices and retains source IDs internally. Extract only after
both method selection and the independent multiple-method decision permit a
single source result. The reducer exposes that combined gate as `selected_id`.

```python
from laya_context_router.building_blocks.typescript import outline, extract_callable
from laya_context_router.building_blocks.questions.method_selection_v2.block import run as select

source_outline = outline('/absolute/project/example.ts')
selection = select({'text': 'Explain sum', 'source_outline': source_outline},
                   config=RunConfig(), registry=registry,
                   rule_overrides={'method': 'method_selection_default'})
if selection.status == 'completed' and selection.data['selected_id'] is not None:
    context = extract_callable(source_outline['path'], selection.data['selected_id'])
else:
    context = None
```

Use an injected registry loader for offline experiments. Fakes return raw SDK
predictions, allowing the real response validator, enrichment, policy evaluation
and reducer to run. No block or catalog import starts inference or runs a flow.

`tests/test_v2_flow_composition.py` covers G01–G08 and G11–G13 with deterministic
fixtures, exact ordering and model call counts, a real TypeScript source round
trip, preserved flow budgets and error reasons, and the existing offline
experiment's success/error reports. G13's invalid policy uses the experiment's
block boundary because its CLI has no rule-override flag; it does not claim a
new CLI option. See separate block parity and migration coverage for G09/G10/G14;
this file does not claim those cases. Run:

```sh
python -m pytest -q tests/test_v2_flow_composition.py
```
