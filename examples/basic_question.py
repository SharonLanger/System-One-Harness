"""Explicit offline mock example; this synthetic response is not a live result."""
import json
from laya_context_router.laya.predict import predict

QUESTION = {'fruit': {'type': 'choice', 'instructions': 'Which fruit is mentioned?', 'criteria': {'apple': 'apple', 'pear': 'pear'}}}
RAW = {'answers': {'fruit': {'type': 'choice', 'choice': 'apple', 'probabilities': {'apple': 0.9, 'pear': 0.1}, 'answer_confidence': 0.9}}}

class MockAgent:
    def predict(self, text, questions):
        assert text == 'I ate an apple.' and questions == QUESTION
        return RAW

if __name__ == '__main__':
    print(json.dumps(predict('I ate an apple.', QUESTION, loader=lambda model: MockAgent())))
