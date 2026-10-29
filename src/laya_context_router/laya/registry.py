"""An invocation owns this registry; no global model cache."""
from .predict import real_loader

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
            self._agents[key]=self._loader(config.model,**config.load_kwargs())
        return self._agents[key]
