"""Opaque observation wrappers retain the ordinary prediction contract."""
from copy import deepcopy
from types import SimpleNamespace
from laya.predict import predict
from test_predict import REQUEST, RAW


def test_observation_wrapper_needs_only_prediction_capability():
    calls=[]
    inner=SimpleNamespace(predict=lambda *a, **kw: (calls.append(1), deepcopy(RAW))[1])
    class Wrapper:
        def get_agent(self, config):
            return SimpleNamespace(predict=inner.predict)
    assert predict(REQUEST['text'], REQUEST['questions'], registry=Wrapper()) == RAW
    assert calls == [1]
