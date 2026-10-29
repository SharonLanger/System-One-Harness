"""Configuration JSON must not silently overwrite duplicate object keys."""
import json


def _unique_pairs(pairs):
    result={}
    for key,value in pairs:
        if key in result: raise ValueError(f'duplicate JSON key: {key}')
        result[key]=value
    return result


def load_json(path):
    with open(path) as handle:
        return json.load(handle,object_pairs_hook=_unique_pairs)
