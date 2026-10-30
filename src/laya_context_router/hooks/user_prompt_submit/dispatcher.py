"""Validate user-prompt evidence and call exactly one feature."""
from dataclasses import dataclass

from ...hook_contracts import Failure, ValidationError, validate_result
from ..dispatcher import HookEnvelope, require_string

@dataclass(frozen=True)
class PromptRequest:
    prompt: str
    envelope: HookEnvelope
    config: object

def _default_handler(request,logger):
    from .prompt_context_enrichment import enrich_prompt_context
    return enrich_prompt_context(request,logger)

def dispatch_user_prompt_submit(envelope,args,logger,*,handler=None):
    try:
        if envelope.hook_name!='UserPromptSubmit':
            raise ValidationError('event_mismatch','user_prompt_submit','hook_event_name')
        prompt=require_string(envelope.raw_payload,'prompt','user_prompt_submit',allow_empty=True)
        request=PromptRequest(prompt,envelope,args)
        logger('INFO','hook_input_ingested',session_id=envelope.common['session_id'],
               fields=sorted(envelope.raw_payload),prompt_chars=len(prompt),cwd=envelope.common['cwd'],
               project_root_source='explicit_configuration' if getattr(args,'repository_root',None) else None)
        logger('INFO','feature_started',session_id=envelope.common['session_id'],
               feature_id='prompt_context_enrichment')
        result=validate_result((handler or _default_handler)(request,logger))
        logger('INFO','feature_finished',session_id=envelope.common['session_id'],
               feature_id='prompt_context_enrichment',outcome=type(result).__name__.lower())
        return result
    except ValidationError as exc:
        return Failure(exc.code,exc.stage,exc.field,str(exc))
