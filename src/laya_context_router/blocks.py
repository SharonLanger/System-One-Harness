"""One reusable block: question definitions, named policies, one SDK request."""
from pathlib import Path
from .questions.load import load_questions
from .questions.models import Question
from .answers.rules import load_named_rules
from .answers.interpret import interpret
from .laya.predict import predict, predict_strict
from .log_utils import log

class QuestionBlock:
    def __init__(self,directory):
        self.directory=Path(directory)
        log("INFO", "questions", "load_started", block=self.directory)
        self.questions=load_questions(self.directory/'questions.json')
        if not self.questions: raise ValueError('block questions cannot be empty')
        self.policies=load_named_rules(self.directory/'rules.json',self.questions)
        log("DEBUG", "questions", "loaded", block=self.directory,
            questions={name:q.to_predict_dict() for name,q in self.questions.items()},
            rules=self.policies)

    def run(self,text,*,config,registry,question_payloads=None,strict=False):
        if question_payloads is None:
            questions={name:q.to_predict_dict() for name,q in self.questions.items()}
        else:
            if not isinstance(question_payloads,dict) or set(question_payloads)!=set(self.questions):
                raise ValueError('dynamic payload names must match block questions')
            questions={}
            for name,payload in question_payloads.items():
                if not isinstance(payload,dict): raise ValueError('dynamic question must be an object')
                questions[name]=Question.from_dict({**payload,'name':name}).to_predict_dict()
        log("DEBUG", "questions", "prepared", block=self.directory,
            dynamic=question_payloads is not None, questions=questions)
        if type(strict) is not bool: raise ValueError("strict must be boolean")
        raw=(predict_strict if strict else predict)(text,questions,config=config,registry=registry)
        return interpret(raw,questions,self.policies)

