from ..json_utils import load_json
from .models import Question


def load_questions(path):
    data=load_json(path)
    if isinstance(data,dict): data=[data]
    if not isinstance(data,list): raise ValueError('questions must be an object or list')
    questions={}
    for item in data:
        question=Question.from_dict(item)
        if question.name in questions: raise ValueError(f'duplicate question name: {question.name}')
        questions[question.name]=question
    return questions
