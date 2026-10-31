"""Exercise adapter baseline capture, independent direct calls and replay copies."""
import sys
sys.dont_write_bytecode=True
import unittest
from pathlib import Path
from copy import deepcopy
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import engine
from schema import load
from laya_context_router.laya.config import RunConfig

class ReplayContracts(unittest.TestCase):
    def test_each_supported_adapter_type(self):
        variants=[('generic-question','choice'),('generic-question','noul'),('requested-action','choice'),('context-scope','choice')]
        for adapter,kind in variants:
            if adapter=='generic-question':
                definition={'name':'topic','type':kind,'instructions':'Classify the input'}
                if kind=='choice': definition['criteria']={'fruit':'Fruit','other':'Other'}
                input_value='An apple'
            else:
                definition=load(engine.ROOT/'src/laya_context_router/defaults/questions'/f"{adapter.replace('-','_')}.json")
                input_value={'prompt':'Explain this method'}
            name=definition['name'];suite={'adapter':adapter,'question_type':kind};q={'id':'q','definition':definition}
            field='distance_from_boundary' if kind=='noul' else 'probability_gap'
            baseline={'definition':{'name':'baseline','conditions':[{'field':field,'op':'gte','value':0}]}}
            strict={'definition':{'name':'strict','conditions':[{'field':field,'op':'gte','value':.3}]}}
            if kind=='choice':
                labels=list(definition['criteria'])
                def answer(p):
                    probs={label:0 for label in labels};probs[labels[0]]=p;probs[labels[1]]=1-p
                    return {'type':kind,'choice':labels[0],'probabilities':probs,'answer_confidence':p}
            else:
                def answer(p):return {'type':'noul','noul':p,'answer_confidence':p}
            for raw in [None, {'answers':{}}, {'answers':{name:{'type':kind}}}, *({'answers':{name:answer(p)}} for p in (.574999,.649999,.9))]:
                with self.subTest(adapter=adapter,kind=kind,raw=raw):
                    original=deepcopy(raw)
                    capture=engine.Boundary(engine.RecordedAgent(raw), inspector=engine.plumbing_provider(None, RunConfig()))
                    try: engine.execute(input_value,q,baseline,suite,RunConfig(),capture)
                    except Exception: pass
                    captured=deepcopy(capture.raw)
                    def outcome(response):
                        try:
                            return ('result',engine.execute(input_value,q,strict,suite,RunConfig(),engine.Boundary(engine.RecordedAgent(response), inspector=engine.plumbing_provider(None, RunConfig()))))
                        except Exception as exc:
                            return ('error',type(exc).__name__,str(exc))
                    self.assertEqual(outcome(capture.raw),outcome(original))
                    self.assertEqual(capture.raw,captured)
                    self.assertEqual(raw,original)

if __name__=='__main__':unittest.main()
