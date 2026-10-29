"""Source-compatible operators, dotted lookup and first-failure reasons."""
OPS = {
    'gt': lambda a,b: a is not None and a>b,
    'gte': lambda a,b: a is not None and a>=b,
    'lt': lambda a,b: a is not None and a<b,
    'lte': lambda a,b: a is not None and a<=b,
    'eq': lambda a,b: a==b,
}


def resolve_field(data,path):
    for key in path.split('.'):
        if isinstance(data,dict): data=data.get(key)
        else: return None
    return data


def evaluate_conditions(prediction,conditions):
    for condition in conditions:
        value=resolve_field(prediction,condition['field'])
        if not OPS[condition['op']](value,condition['value']):
            reason='field_missing' if value is None else 'below_threshold'
            return False,f"{reason}:{condition['field']}"
    return True,None
