"""Named runtime decisions, without ground truth or report machinery."""
from .enrich import enrich_prediction
from .rules import accepts
from ..laya.predict import validate_questions, validate_response


def extract_answer(prediction):
    kind=prediction['type']
    if kind=='choice': return prediction['choice']
    if kind=='noul': return 'yes' if prediction['noul']>=0.5 else 'no'
    if kind=='score':
        legend=prediction['legend']
        index=max(0,min(round(prediction['score']),len(legend)-1))
        return legend[str(index)]
    raise ValueError(f'unknown prediction type: {kind}')


def interpret(raw,questions,policies):
    validate_questions(questions)
    if set(policies)!=set(questions): raise ValueError('policies must match requested questions')
    decisions={}
    answers=raw.get('answers') if isinstance(raw,dict) else None
    for name,question in questions.items():
        try:
            prediction=answers.get(name) if isinstance(answers,dict) else None
            validate_response({'answers':{name:prediction}},{name:question})
            enriched=enrich_prediction(prediction)
            decided,reason=accepts(enriched,policies[name])
            answer=extract_answer(enriched) if decided else 'undecided'
        except (ValueError,TypeError,KeyError) as exc:
            answer,decided,reason='undecided',False,f'invalid_prediction:{exc}'
        decisions[name]={'answer':answer,'decided':decided,'reason':reason}
    return decisions
