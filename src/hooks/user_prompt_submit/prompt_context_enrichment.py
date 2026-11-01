"""Shared root/config preparation and a disconnected sandbox-only hook adapter."""
from pathlib import Path
from hooks.contracts import Failure


def _prepare_feature_config(request):
    """Validate explicit root before real opt-in/config loading; never infer cwd."""
    args=request.config
    raw_root=getattr(args,'repository_root',None)
    if not isinstance(raw_root,(str,Path)) or not str(raw_root).strip():
        return Failure('invalid_project_root','configuration','repository_root')
    root=Path(raw_root)
    if not root.is_absolute():
        return Failure('invalid_project_root','configuration','repository_root')
    try:
        root=root.resolve(strict=True)
        if not root.is_dir():
            return Failure('invalid_project_root','configuration','repository_root')
    except TimeoutError:
        raise
    except OSError as exc:
        return Failure('invalid_project_root','configuration','repository_root',str(exc))
    if not getattr(args,'real',False):
        return Failure('model_disabled','configuration','real','explicit --real required')
    from laya.config import RunConfig,load_config
    try:
        model_config=load_config(args.config) if getattr(args,'config',None) else RunConfig()
    except TimeoutError:
        raise
    except (OSError,ValueError,TypeError) as exc:
        return Failure('invalid_configuration','configuration','config',str(exc))
    return {'project_root':root,'project_root_source':'explicit_configuration',
            'cwd':request.envelope.common['cwd'],'model_config':model_config}

_NOOP_REASONS=frozenset({'ineligible_request','unsupported_request','no_file','multiple_files',
    'excluded','missing','ambiguous','no_candidates','candidate_budget_exceeded',
    'ambiguous_candidates','input_budget_exceeded','method_undecided','no_single_match',
    'multiple_undecided','multiple_relevant'})
_FAILURE_REASONS=frozenset({'deadline_exceeded','extractor_error','invalid_dependency_budget',
    'invalid_fallback_budget','invalid_reference','model_error','source_changed','unknown_candidate',
    'inaccessible','outside_repository','not_file','invalid_resolution_mode'})


def _map_flow_result(result, *, project_root, max_dependency_depth=2,
                     max_dependency_chars=12000,formatter=None):
    from hooks.contracts import Context,Noop
    invalid=Failure('invalid_flow_result','feature')
    if not isinstance(result,dict) or not {'status','reason','context'}<=result.keys():
        return invalid
    if result['status']=='noop':
        reason=result['reason']
        if result['context'] is not None or not isinstance(reason,str):return invalid
        if reason in _NOOP_REASONS:return Noop(reason)
        if reason in _FAILURE_REASONS:return Failure(reason,'feature')
        return invalid
    if result['status']!='context' or result['reason'] is not None:
        return invalid
    context=result['context']
    try:
        # Reuse collector schema validation; do not invent a second schema.
        from building_blocks.typescript import _validate_context
        path=Path(context['path'])
        root=Path(project_root).resolve()
        if not path.is_absolute() or path.resolve()!=path or not path.is_relative_to(root):return invalid
        _validate_context(context,path,context['callable']['id'],max_dependency_depth,
                          max_dependency_chars,repository_root=root)
    except (ValueError,TypeError,KeyError,AttributeError) as exc:
        return Failure('invalid_flow_result','feature',message=str(exc))
    except Exception as exc:
        from building_blocks.typescript import TypeScriptError
        if not isinstance(exc,TypeScriptError):raise
        return Failure('invalid_flow_result','feature',message=str(exc))
    if formatter is None:
        from context_format import format_context
        formatter=format_context
    try:
        text=formatter(context,project_root=root)
    except TimeoutError:
        raise
    except Exception as exc:
        return Failure('formatting_error','formatting',message=str(exc))
    if not isinstance(text,str) or not text:return Failure('formatting_error','formatting')
    return Context(text)


def enrich_prompt_context(request,logger,*,flow=None,registry=None,formatter=None):
    """Sandbox-only adapter; the default dispatcher uses first_method_context."""
    prepared=_prepare_feature_config(request)
    if isinstance(prepared,Failure):return prepared
    if flow is None:
        from flows.file_method_context import run
        flow=run
    if registry is None:
        from laya.registry import AgentRegistry
        registry=AgentRegistry(real=True)
    depth=getattr(request.config,'max_dependency_depth',2)
    budget=getattr(request.config,'max_dependency_chars',12000)
    result=flow(request.prompt,cwd=Path(prepared['cwd']),repository_root=prepared['project_root'],
        config=prepared['model_config'],registry=registry,resolve_from_project_root=True,
        max_dependency_depth=depth,max_dependency_chars=budget)
    mapped=_map_flow_result(result,project_root=prepared['project_root'],
        max_dependency_depth=depth,max_dependency_chars=budget,formatter=formatter)
    from hooks.contracts import Context
    if isinstance(mapped,Context):
        limit=getattr(request.config,'max_context_chars',8000)
        if len(mapped.text)>limit:
            logger('WARNING','context_size_warning',context_chars=len(mapped.text),
                   max_context_chars=limit,action='send_unchanged')
    return mapped
