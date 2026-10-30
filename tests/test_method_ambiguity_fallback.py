"""F02 decision: indistinguishable candidate descriptions cause a no-op.

For V1, detect this ambiguity before model selection and let Claude handle the
original prompt normally. Do not guess or require owner-enriched descriptions.
Implementation fix pending; these regression tests currently fail.
"""

import pytest

from laya_context_router.flows import file_method_context as flow
from laya_context_router.laya.config import RunConfig
from laya_context_router.laya.registry import AgentRegistry
from test_method_selection import raw_for
from laya_context_router.building_blocks.typescript import outline
from laya_context_router.building_blocks.questions.method_selection.block import run as select_method


@pytest.mark.parametrize("source", [
    "class Alpha {run(){return 1;}} class Bravo {run(){return 2;}}",
    "const Alpha={run(){return 1;}}; const Bravo={run(){return 2;}};",
], ids=["class-methods", "object-methods"])
def test_indistinguishable_method_candidates_skip_enrichment(tmp_path, source):
    (tmp_path / "main.ts").write_text(source, encoding="utf-8")
    calls = []

    class Spy:
        def predict(self, text, questions, **kwargs):
            calls.append(questions)
            selected = next(iter(questions["method"]["criteria"]))
            return raw_for(questions, selected)

    result = flow.run(
        "Explain `main.ts`: explain the run method in Bravo",
        cwd=tmp_path,
        repository_root=tmp_path,
        config=RunConfig(),
        registry=AgentRegistry(loader=lambda *args, **kwargs: Spy()),
    )
    assert result["status"] == "noop", result
    assert result["context"] is None
    assert calls == [], "Detect indistinguishable candidates before asking the model to choose"


def test_ambiguous_block_refuses_before_model_load(tmp_path):
    path = tmp_path / "main.ts"
    path.write_text("class A {run(){}} class B {run(){}}", encoding="utf-8")

    def forbidden(*args, **kwargs):
        raise AssertionError("Ambiguous candidates must not load a model")

    result = select_method("Explain B.run", outline(path), config=RunConfig(),
                           registry=AgentRegistry(loader=forbidden))
    assert result["selected_id"] is None
    assert result["reason"] == "ambiguous_candidates"
    assert result["decisions"] == {}
