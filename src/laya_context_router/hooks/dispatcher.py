"""Common ingestion and explicit event dispatch. No source/model work."""
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path

from .contracts import Noop, Failure, ValidationError, validate_result

@dataclass(frozen=True)
class HookEnvelope:
    hook_name: str
    invocation_id: str
    common: dict
    raw_payload: dict
    derived: dict = field(default_factory=dict)

def require_string(payload, field, stage='common', *, allow_empty=False):
    value = payload.get(field)
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise ValidationError('invalid_field', stage, field)
    return value

def ingest_common(payload, invocation_id):
    common = {key:require_string(payload,key) for key in ('hook_event_name','session_id','cwd','transcript_path')}
    if not Path(common['cwd']).is_absolute():
        raise ValidationError('invalid_field','common','cwd')
    for key in ('permission_mode',):
        if key in payload:common[key]=require_string(payload,key)
    return HookEnvelope(common['hook_event_name'],invocation_id,common,deepcopy(payload))

def enrich_envelope(envelope):
    """Reserved identity seam; enrichers and filters are future work."""
    return envelope

def _user_prompt_dispatch(envelope,args,logger):
    from .user_prompt_submit.dispatcher import dispatch_user_prompt_submit
    return dispatch_user_prompt_submit(envelope,args,logger)

def dispatch_hook(payload,args,invocation_id,logger,*,dispatchers=None,enricher=enrich_envelope):
    try:
        if not isinstance(payload,dict):raise ValidationError('invalid_object','input')
        name=require_string(payload,'hook_event_name','input')
        if name!=args.hook:raise ValidationError('event_mismatch','input','hook_event_name',command_hook=args.hook,payload_hook=name)
        registry = {'UserPromptSubmit':_user_prompt_dispatch} if dispatchers is None else dispatchers
        if name not in registry:return Noop('unsupported_event')
        envelope=ingest_common(payload,invocation_id)
        baseline=deepcopy(envelope)
        envelope=enricher(envelope)
        if (not isinstance(envelope,HookEnvelope) or envelope.common!=baseline.common
                or envelope.raw_payload!=baseline.raw_payload or envelope.hook_name!=baseline.hook_name
                or envelope.invocation_id!=baseline.invocation_id or not isinstance(envelope.derived,dict)
                or 'project_root' in envelope.derived):
            raise ValidationError('invalid_enrichment','common')
        logger('INFO','common_input_validated',session_id=envelope.common['session_id'],
               fields=sorted(envelope.common),derived_fields=sorted(envelope.derived))
        return validate_result(registry[name](envelope,args,logger))
    except ValidationError as exc:
        if exc.evidence:logger('ERROR','input_rejected',**exc.evidence)
        return Failure(exc.code,exc.stage,exc.field,str(exc))
