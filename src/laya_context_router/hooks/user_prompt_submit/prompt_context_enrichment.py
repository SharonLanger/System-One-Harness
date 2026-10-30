"""Private adapter preparation; real-flow integration awaits reviewed root API."""
from pathlib import Path
from ...hook_contracts import Failure


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
        return Failure('model_disabled','configuration','real')
    from ...laya.config import RunConfig,load_config
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
    'inaccessible','outside_repository','not_file'})


def _map_flow_result(result, *, project_root, max_dependency_depth=2,
                     max_dependency_chars=12000,formatter=None):
    from ...hook_contracts import Context,Noop
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
        from ...building_blocks.typescript import _validate_context
        path=Path(context['path'])
        root=Path(project_root).resolve()
        if not path.is_absolute() or path.resolve()!=path or not path.is_relative_to(root):return invalid
        _validate_context(context,path,context['callable']['id'],max_dependency_depth,
                          max_dependency_chars,repository_root=root)
    except (ValueError,TypeError,KeyError,AttributeError) as exc:
        return Failure('invalid_flow_result','feature',message=str(exc))
    except Exception as exc:
        from ...building_blocks.typescript import TypeScriptError
        if not isinstance(exc,TypeScriptError):raise
        return Failure('invalid_flow_result','feature',message=str(exc))
    if formatter is None:
        from ...context_format import format_context
        formatter=format_context
    try:
        text=formatter(context,project_root=root)
    except TimeoutError:
        raise
    except Exception as exc:
        return Failure('formatting_error','formatting',message=str(exc))
    if not isinstance(text,str) or not text:return Failure('formatting_error','formatting')
    return Context(text)


def enrich_prompt_context(request,logger):
    """Unfinished boundary: no real flow runs until the reviewed root API lands."""
    prepared=_prepare_feature_config(request)
    if isinstance(prepared,Failure):return prepared
    return Failure('root_api_unavailable','feature',
        message='Real-flow integration awaits the reviewed project-root resolution API')
