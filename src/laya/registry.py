"""An invocation owns this registry; no global model cache."""
from laya.predict import real_loader
from log_utils import log

class AgentRegistry:
    def __init__(self, *, loader=None, real=False, inspection_provider=None):
        if loader is None and not real:
            raise RuntimeError('mock mode requires an explicit loader')
        self._loader=loader if loader is not None else real_loader
        self._agents={}
        self._inspectors={}
        self._inspection_provider=inspection_provider

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


    def get_inspector(self, config):
        """Resolve once per loaded configuration; failed initialization is not verified."""
        from laya.budget_profiles import verified_provider
        from laya.budget import InspectionUnavailable, make_report
        key=(config.model,config.temperature,config.lang)
        if key not in self._inspectors:
            agent=self.get_agent(config)
            provider=self._inspection_provider or verified_provider
            inspector=provider(agent,config)
            if not callable(getattr(inspector,'inspect',None)):
                raise InspectionUnavailable(make_report(config.model), 'Provider did not return an inspection capability')
            self._inspectors[key]=inspector
        return self._inspectors[key]
