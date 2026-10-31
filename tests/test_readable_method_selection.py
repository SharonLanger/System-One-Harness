from examples._plumbing_inspection import plumbing_provider
from laya_context_router.building_blocks.questions.method_selection.block import run
from laya_context_router.building_blocks.typescript import outline
from laya_context_router.laya.config import RunConfig
from laya_context_router.laya.registry import AgentRegistry
from test_method_selection import raw_for


def test_model_sees_readable_labels_and_selection_maps_back_to_source_id(tmp_path):
    path = tmp_path / 'main.ts'
    path.write_text('function calculateInvoiceTotal(invoice: number): number { return invoice; }')
    source = outline(path)
    candidate = source['callables'][0]
    seen = []
    class Agent:
        def predict(self, text, questions, **kwargs):
            labels = list(questions['method']['criteria'])
            label = labels[0]
            assert label == 'calculateInvoiceTotal'
            assert candidate['id'] not in str(questions)
            seen.append(label)
            return raw_for(questions, label)
    result = run('Explain calculateInvoiceTotal', source, config=RunConfig(),
                 registry=AgentRegistry(inspection_provider=plumbing_provider, loader=lambda *args, **kwargs: Agent()))
    assert result['selected_id'] == candidate['id']
    assert result['label_map'][seen[0]] == candidate['id']
    assert result['candidate_map'][candidate['id']]['path'] == str(path)


def test_default_invoice_has_exact_readable_method_identifiers():
    from pathlib import Path
    path = Path(__file__).resolve().parents[1] / 'experiments/fixtures/connected_project/src/billing/invoice-service.ts'
    source = outline(path)
    class Agent:
        def predict(self, text, questions, **kwargs):
            assert list(questions['method']['criteria']) == [
                'calculateInvoiceTotal', 'calculateInvoiceTotalWithAdjustment', 'none_or_unclear']
            assert questions['method']['criteria']['calculateInvoiceTotal'].startswith('export function calculateInvoiceTotal(')
            return raw_for(questions, 'calculateInvoiceTotal')
    result = run('Explain total', source, config=RunConfig(),
                 registry=AgentRegistry(inspection_provider=plumbing_provider, loader=lambda *args, **kwargs: Agent()))
    assert result['selected_id'] == source['callables'][0]['id']
