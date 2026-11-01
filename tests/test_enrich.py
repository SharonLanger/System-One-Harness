import copy
import json
from pathlib import Path
import pytest
from answers.enrich import enrich_prediction, enrich_response

@pytest.mark.parametrize('kind',['choice','score'])
@pytest.mark.parametrize('probs,gap,entropy',[
    ([0.75,0.25],0.5,0.8113),([0.5,0.5],0.0,1.0),([1,0],1.0,0.0),
    ([1/3]*3,0.0,1.0),([0.5,0.5,0],0.0,0.6309),
    ([0.56172,0.43828],0.1234,0.989),
])
def test_gap_entropy_hand_calculated(kind,probs,gap,entropy):
    raw={'type':kind,'probabilities':dict(enumerate(probs)), 'metadata':{'keep':True}}
    original=copy.deepcopy(raw)
    got=enrich_prediction(raw)
    assert got['probability_gap']==gap and got['normalized_entropy']==entropy
    assert raw==original and got['metadata']=={'keep':True}
    assert enrich_prediction(got)==got

@pytest.mark.parametrize('value,distance',[(0,0.5),(0.5,0),(1,0.5),(0.49994,0.0001),(0.50004,0)])
def test_noul_distance(value,distance):
    assert enrich_prediction({'type':'noul','noul':value})['distance_from_boundary']==distance

@pytest.mark.parametrize('data',[{'type':'choice'},{'type':'score','probabilities':{}},{'type':'choice','probabilities':{'only':1}},{'type':'noul'},{'type':'noul','noul':None}])
def test_legacy_missing_singleton_unchanged(data):
    assert enrich_prediction(data)==data

@pytest.mark.parametrize('prediction',[
    {},{'type':'other'}, {'type':'choice','probabilities':[]},
    {'type':'choice','probabilities':{'x':True}},
    {'type':'choice','probabilities':{'x':'1'}},
    {'type':'choice','probabilities':{'x':float('nan')}},
    {'type':'choice','probabilities':{'x':float('inf')}},
    {'type':'choice','probabilities':{'x':-0.1,'y':1.1}},
    {'type':'choice','probabilities':{'x':0.4,'y':0.4}},
    {'type':'noul','noul':True},{'type':'noul','noul':'0.5'},
    {'type':'noul','noul':-0.1},{'type':'noul','noul':1.1},
    {'type':'noul','noul':float('-inf')},
])
def test_invalid_data_is_explicit(prediction):
    with pytest.raises(ValueError): enrich_prediction(prediction)


def test_original_helper_golden_parity_and_raw_unchanged():
    root=Path(__file__).parent/'fixtures/laya'
    raw=json.loads((root/'captured-raw.json').read_text())
    original=copy.deepcopy(raw)
    got=enrich_response(raw)
    assert got==json.loads((root/'enriched-original.json').read_text())
    assert raw==original
    assert got['answers']['department']['probability_gap']==0.9546
    assert got['answers']['churn_risk']['distance_from_boundary']==0.0339
