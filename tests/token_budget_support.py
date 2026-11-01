"""Controlled token IDs for unit tests; no tokenizer or SDK qualification evidence."""
import hashlib
import json
import re
import threading
from types import SimpleNamespace

BASE={'type':'choice','instructions':'Choose the relevant function.','criteria':{'yes':'Relevant.','no':'Not relevant.'}}


class MockBackend:
    def __init__(self):
        self.truncation=None; self.padding=None; self.normalizer='mock'; self.vocabulary=[]
    def encode(self, text, **kwargs):
        return SimpleNamespace(ids=[])
    def to_str(self):
        return json.dumps(vars(self),sort_keys=True)
    def add_tokens(self,values):
        self.vocabulary.extend(values)


class MockTokenizer:
    """Scripted IDs take precedence; lexical fallback supplies convenient test lengths."""
    def __init__(self,kind='typed',overrides=None):
        self.backend=MockBackend();self.calls=[];self.overrides=overrides or {}
        self.metadata={'source':'mock','configuration':kind}
        for i,name in enumerate(('cls','sep','pad','mask')):
            setattr(self,name+'_token','<'+name+'>');setattr(self,name+'_token_id',i)
    def encode(self,text):
        self.calls.append(text)
        if text in self.overrides:return list(self.overrides[text])
        return [10+int.from_bytes(hashlib.sha256(piece.encode()).digest()[:4],'big')
                for piece in re.findall(r'\w+|[^\w\s]',text)]


def tokenizer(kind='typed',*,overrides=None):
    return MockTokenizer(kind,overrides)


def mock_runtime():
    lock=threading.RLock()
    def encode_text(tok,text,*,add_special_tokens=False):
        assert add_special_tokens is False
        with lock:return {'input_ids':tok.encode(text)}
    return SimpleNamespace(_TOKENIZE_LOCK=lock,encode_text=encode_text)
