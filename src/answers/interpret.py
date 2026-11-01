"""Named runtime decisions, without ground truth or report machinery."""
from answers.enrich import enrich_prediction
from answers.rules import accepts
from log_utils import log
from laya.predict import validate_questions, validate_response


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
            log("DEBUG", "enrichment", "started", question=name, prediction=prediction)
            enriched=enrich_prediction(prediction)
            log("DEBUG", "enrichment", "completed", question=name, enriched=enriched,
                added_properties={k:v for k,v in enriched.items() if k not in prediction})
            log("DEBUG", "rules", "evaluation_started", question=name, policy=policies[name].name,
                conditions=policies[name].conditions_for(enriched['type']))
            decided,reason=accepts(enriched,policies[name])
            answer=extract_answer(enriched) if decided else 'undecided'
        except (ValueError,TypeError,KeyError) as exc:
            log("ERROR", "answers", "interpretation_failed", question=name, error=exc)
            answer,decided,reason='undecided',False,f'invalid_prediction:{exc}'
        decisions[name]={'answer':answer,'decided':decided,'reason':reason}
        log("INFO", "rules", "decision", question=name, decision=decisions[name])
    return decisions

