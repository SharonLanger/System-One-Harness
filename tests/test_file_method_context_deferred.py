"""Deferred scenarios outside the first-version acceptance scope."""

import pytest

from laya_context_router.flows import file_method_context as flow
from laya_context_router.laya.config import RunConfig
from laya_context_router.laya.registry import AgentRegistry
from test_method_selection import raw_for


# This concurrent filesystem scenario is not relevant for the first version.
# Retain it as a future hardening check; ordinary source edits are a different case.
@pytest.mark.skip(reason="Outside V1 scope: concurrent replacement with an outside-project symlink")
def test_source_replaced_by_outside_symlink_before_outline_does_not_reach_model(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    source = root / "main.ts"
    source.write_text("function chosen(){return 1;}", encoding="utf-8")
    outside = tmp_path / "outside.ts"
    outside.write_text("function OUTSIDE_SENTINEL(secret: string){return secret;}", encoding="utf-8")
    original_outline = flow.outline
    calls = []

    def swap_before_read(path, **kwargs):
        source.unlink()
        source.symlink_to(outside)
        return original_outline(path, **kwargs)

    monkeypatch.setattr(flow, "outline", swap_before_read)

    class Spy:
        def predict(self, text, questions, **kwargs):
            calls.append(questions)
            selected = next(iter(questions["method"]["criteria"]))
            return raw_for(questions, selected)

    result = flow.run(
        "Explain `main.ts`: how does chosen work?",
        cwd=root,
        repository_root=root,
        config=RunConfig(),
        registry=AgentRegistry(loader=lambda *args, **kwargs: Spy()),
    )
    assert result["status"] == "noop"
    assert calls == [], calls
