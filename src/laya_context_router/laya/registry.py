"""An invocation owns this registry; no global model cache."""
from .predict import real_loader
from ..log_utils import log

class AgentRegistry:
    def __init__(self, *, loader=None, real=False):
        if loader is None and not real:
            raise RuntimeError('mock mode requires an explicit loader')
        self._loader=loader if loader is not None else real_loader
        self._agents={}

    def get_agent(self,config):
        key=(config.model,config.temperature,config.lang)
        if key not in self._agents:
            # Failed loads are never cached.
            log("INFO", "laya", "load_started", requested_config=key)
            try:
                self._agents[key]=self._loader(config.model,**config.load_kwargs())
            except Exception as exc:
                log("ERROR", "laya", "load_failed", error=exc, requested_config=key)
                raise
            log("INFO", "laya", "load_completed", requested_config=key)
        else:
            log("INFO", "laya", "agent_reused", requested_config=key)
        return self._agents[key]

