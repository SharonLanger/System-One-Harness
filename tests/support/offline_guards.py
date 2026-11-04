"""Fail fast if an offline suite crosses the real SDK or Python network boundary."""
import socket

import pytest


@pytest.fixture(autouse=True)
def offline_boundaries(monkeypatch):
    import laya.predict as predict
    import laya.registry as registry

    def forbidden(*args, **kwargs):
        raise AssertionError('offline suite crossed a real model or network boundary')

    monkeypatch.setattr(predict, 'real_loader', forbidden)
    monkeypatch.setattr(registry, 'real_loader', forbidden)
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    monkeypatch.setattr(socket.socket, 'connect_ex', forbidden)
