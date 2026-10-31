"""Reusable method-selection block refuses indistinguishable candidates."""
from laya_context_router.laya.config import RunConfig
from laya_context_router.laya.registry import AgentRegistry
from laya_context_router.building_blocks.typescript import outline
from laya_context_router.building_blocks.questions.method_selection.block import run as select_method




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
