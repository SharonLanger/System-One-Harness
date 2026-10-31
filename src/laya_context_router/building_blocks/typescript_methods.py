"""Name-based TypeScript utilities. Paths are relative to explicit project_root.

These additive APIs return outcomes; legacy ID-based APIs retain their contracts.
"""
from pathlib import Path, PurePosixPath
from .typescript import DEFAULT_HELPER, TypeScriptError, _request
from ..log_utils import log

_MESSAGES = {
    'invalid_input': 'Provide an absolute project root, relative file path and valid method name.',
    'source_error': 'Source could not be read or parsed.',
    'method_not_found': 'Method was not found.',
    'ambiguous_method': 'More than one method has this name; selection was skipped.',
    'uncertain_navigation': 'Static navigation is incomplete; hints were skipped.',
    'unaddressable_method': 'A related method cannot be selected uniquely by file and name.',
    'navigation_error': 'Static navigation failed; hints were skipped.',
    'helper_error': 'TypeScript helper could not complete a valid response.',
}

def _error(code):
    return {'status':'error','data':None,'diagnostics':[{'code':code,'message':_MESSAGES[code]}]}

def _relative(value):
    return (isinstance(value,str) and bool(value) and '\\' not in value
            and not PurePosixPath(value).is_absolute()
            and all(p not in ('','.','..') for p in value.split('/')))

def _positive(value):
    return type(value) is int and value > 0

def _method(item, sites=False):
    keys={'file','name','signature','start_line','end_line'} | ({'call_sites'} if sites else set())
    if (not isinstance(item,dict) or set(item)!=keys or not _relative(item['file'])
            or not all(isinstance(item[k],str) and item[k] for k in ('name','signature'))
            or not _positive(item['start_line']) or not _positive(item['end_line'])
            or item['end_line']<item['start_line']):
        raise TypeScriptError('invalid named method metadata')
    if sites:
        if not isinstance(item['call_sites'],list) or not item['call_sites']:
            raise TypeScriptError('invalid named call sites')
        seen=set()
        for s in item['call_sites']:
            if (not isinstance(s,dict) or set(s)!={'file','start_line','start_column','end_line','end_column'}
                    or not _relative(s['file'])
                    or not all(_positive(s[k]) for k in ('start_line','start_column','end_line','end_column'))
                    or (s['end_line'],s['end_column']) <= (s['start_line'],s['start_column'])):
                raise TypeScriptError('invalid named call site')
            key=tuple(s[k] for k in ('file','start_line','start_column','end_line','end_column'))
            if key in seen: raise TypeScriptError('duplicate named call site')
            seen.add(key)

def _validate(result,action):
    if (not isinstance(result,dict) or set(result)!={'status','data','diagnostics'}
            or result['status'] not in ('ok','uncertain','ambiguous','error')
            or not isinstance(result['diagnostics'],list)):
        raise TypeScriptError('invalid named envelope')
    if result['status']!='ok':
        if result['data'] is not None or not result['diagnostics']:
            raise TypeScriptError('invalid named failure')
        codes=[]
        for d in result['diagnostics']:
            if not isinstance(d,dict) or set(d)!={'code','message'} or d['code'] not in _MESSAGES:
                raise TypeScriptError('invalid named diagnostic')
            codes.append(d['code'])
        return {**result,'diagnostics':[{'code':c,'message':_MESSAGES[c]} for c in codes]}
    if result['diagnostics'] or not isinstance(result['data'],dict):
        raise TypeScriptError('invalid named success')
    data=result['data']
    if action=='get_method_implementation':
        if set(data)!={'method','code'} or not isinstance(data['code'],str) or not data['code']:
            raise TypeScriptError('invalid named extraction')
        _method(data['method'])
    else:
        key='callers' if action=='list_calling_methods' else 'methods'
        expected={key,'scope'} if key=='callers' else {key}
        if set(data)!=expected or not isinstance(data[key],list):
            raise TypeScriptError('invalid named list')
        for item in data[key]: _method(item,action!='list_methods')
        if key=='callers':
            scope=data['scope']
            if (not isinstance(scope,dict) or set(scope)!={'tsconfig_path','searched_files','limits','omissions'}
                    or not _relative(scope['tsconfig_path'])
                    or not isinstance(scope['searched_files'],list)
                    or not all(_relative(p) for p in scope['searched_files'])
                    or scope['searched_files']!=sorted(set(scope['searched_files']))
                    or not all(isinstance(scope[k],list) and all(isinstance(v,str) for v in scope[k]) for k in ('limits','omissions'))):
                raise TypeScriptError('invalid named scope')
    return result

def _run(action,file,method_name=None,*,project_root,tsconfig_path=None,node='node',helper=DEFAULT_HELPER,timeout=5.0):
    try:
        if not isinstance(project_root,(str,Path)) or not Path(project_root).is_absolute():
            return _error('invalid_input')
        try:
            root=Path(project_root).resolve(strict=True)
        except RuntimeError:  # Python 3.11 reports symlink loops this way.
            return _error('invalid_input')
        if (not root.is_dir() or not _relative(file)
                or (action!='list_methods' and (not isinstance(method_name,str) or not method_name.strip()))
                or (action=='list_calling_methods' and not _relative(tsconfig_path))):
            return _error('invalid_input')
        request={'action':action,'file':file,'project_root':str(root)}
        if action!='list_methods': request['method_name']=method_name
        if action=='list_calling_methods': request['tsconfig_path']=tsconfig_path
        return _validate(_request(None,request,node=node,helper=helper,timeout=timeout),action)
    except (OSError,ValueError,TypeError,KeyError,TypeScriptError) as exc:
        log('ERROR','extractor','named_utility_failed',action=action,error=exc)
        return _error('helper_error')

def list_methods(file,*,project_root,node='node',helper=DEFAULT_HELPER,timeout=5.0):
    """List public-outline names/signatures; duplicate names remain listed."""
    return _run('list_methods',file,project_root=project_root,node=node,helper=helper,timeout=timeout)

def get_method_implementation(file,method_name,*,project_root,node='node',helper=DEFAULT_HELPER,timeout=5.0):
    """Return exact selected code, or ambiguous/error without a selection."""
    return _run('get_method_implementation',file,method_name,project_root=project_root,node=node,helper=helper,timeout=timeout)

def list_called_methods(file,method_name,*,project_root,node='node',helper=DEFAULT_HELPER,timeout=5.0):
    """Return one-hop static targets. Any reported gap withholds all hints."""
    return _run('list_called_methods',file,method_name,project_root=project_root,node=node,helper=helper,timeout=timeout)

def list_calling_methods(file,method_name,*,project_root,tsconfig_path,node='node',helper=DEFAULT_HELPER,timeout=5.0):
    """Return configured-project callers/signatures, or withhold uncertain hints."""
    return _run('list_calling_methods',file,method_name,project_root=project_root,tsconfig_path=tsconfig_path,node=node,helper=helper,timeout=timeout)
