"""Question definitions only: names bind answers, bodies define SDK questions."""
from copy import deepcopy

class Question:
    def __init__(self,name,type,instructions):
        if not isinstance(name,str) or not name:
            raise ValueError('name must be a nonempty string')
        if not isinstance(instructions,str):
            raise ValueError('instructions must be a string')
        self.name,self.type,self.instructions=name,type,instructions

    def to_predict_dict(self):
        return {'type':self.type,'instructions':self.instructions}

    def to_dict(self):
        return {'name':self.name,**self.to_predict_dict()}

    @classmethod
    def from_dict(cls,data):
        if not isinstance(data,dict): raise ValueError('question must be an object')
        try:
            kind=data['type']
            args=(data['name'],data['instructions'])
            if kind=='choice': return ChoiceQuestion(*args,data['criteria'])
            if kind=='noul': return NoulQuestion(*args)
            if kind=='score': return ScoreQuestion(*args,data['criteria'])
        except KeyError as exc:
            raise ValueError(f'missing question field: {exc.args[0]}') from exc
        raise ValueError(f'unknown question type: {kind}')

class ChoiceQuestion(Question):
    def __init__(self,name,instructions,criteria):
        super().__init__(name,'choice',instructions)
        if not isinstance(criteria,dict) or not criteria or not all(isinstance(k,str) and k and isinstance(v,str) for k,v in criteria.items()):
            raise ValueError('choice criteria must be a nonempty string mapping')
        self.criteria=deepcopy(criteria)

    def to_predict_dict(self):
        return {**super().to_predict_dict(),'criteria':deepcopy(self.criteria)}

class NoulQuestion(Question):
    def __init__(self,name,instructions):
        super().__init__(name,'noul',instructions)

class ScoreQuestion(Question):
    def __init__(self,name,instructions,criteria):
        super().__init__(name,'score',instructions)
        if not isinstance(criteria,list) or not criteria or not all(isinstance(v,str) for v in criteria):
            raise ValueError('score criteria must be a nonempty string list')
        self.criteria=deepcopy(criteria)

    def to_predict_dict(self):
        return {**super().to_predict_dict(),'criteria':deepcopy(self.criteria)}
