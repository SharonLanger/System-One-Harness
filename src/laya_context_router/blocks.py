"""One reusable block: question definitions, named policies, one SDK request."""
from pathlib import Path
from .questions.load import load_questions
from .answers.rules import load_named_rules
from .answers.interpret import interpret
from .laya.predict import predict

class QuestionBlock:
    def __init__(self,directory):
        self.directory=Path(directory)
        self.questions=load_questions(self.directory/'questions.json')
        if not self.questions: raise ValueError('block questions cannot be empty')
        self.policies=load_named_rules(self.directory/'rules.json',self.questions)

    def run(self,text,*,config,registry):
        questions={name:q.to_predict_dict() for name,q in self.questions.items()}
        raw=predict(text,questions,config=config,registry=registry)
        return interpret(raw,questions,self.policies)
