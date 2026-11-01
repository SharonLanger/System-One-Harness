"""Source-compatible load/predict settings, immutable within an invocation."""
from dataclasses import dataclass
import json
import math
from laya.predict import DEFAULT_MODEL

@dataclass(frozen=True)
class RunConfig:
    model: str = DEFAULT_MODEL
    temperature: float | None = None
    lang: str = 'en'

    def __post_init__(self):
        if not isinstance(self.model,str) or not self.model or not isinstance(self.lang,str) or not self.lang:
            raise ValueError('model and lang must be nonempty strings')
        t=self.temperature
        if t is not None and (isinstance(t,bool) or not isinstance(t,(int,float)) or not math.isfinite(t)):
            raise ValueError('temperature must be finite numeric or None')

    def load_kwargs(self):
        if self.temperature is None:
            return {}
        return {'lang_temperatures':{self.lang:{'temperature':[self.temperature]*3}}}

    def predict_kwargs(self):
        return {} if self.temperature is None else {'lang':self.lang}

    def to_dict(self):
        data={'model':self.model}
        if self.temperature is not None: data['temperature']=self.temperature
        if self.lang != 'en': data['lang']=self.lang
        return data

    @classmethod
    def from_dict(cls,data):
        if not isinstance(data,dict): raise ValueError('config must be an object')
        return cls(model=data.get('model',DEFAULT_MODEL),temperature=data.get('temperature'),lang=data.get('lang','en'))


def load_config(path):
    with open(path) as handle:
        return RunConfig.from_dict(json.load(handle))
