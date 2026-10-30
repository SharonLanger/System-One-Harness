"""F08: duplicate-key rejection deferred for V1; see configuration-conventions.md."""

import pytest

from laya_context_router.answers.rules import RulesConfig
from laya_context_router.laya.config import load_config


# V1 relies on documented unique-key authoring for these two legacy loaders.
@pytest.mark.skip(reason="Deferred for V1: follow documented unique-key configuration conventions")
@pytest.mark.parametrize("loader,payload", [
    (load_config, '{"model":"first","model":"second"}'),
    (RulesConfig.from_file, '{"name":"policy","conditions":[{"field":"answer_confidence","op":"gte","value":0.9}],"conditions":[]}'),
], ids=["run-config", "standalone-policy"])
def test_duplicate_configuration_keys_rejected(tmp_path, loader, payload):
    path = tmp_path / "duplicate.json"
    path.write_text(payload, encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        loader(path)
