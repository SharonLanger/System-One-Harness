"""Readable report for the V2 ticket experiment; imported helper, not an entry point."""
import json


def show(value, **kwargs):
    return "```json\n" + json.dumps(value, **kwargs) + "\n```"


def render_summary(details):
    cfg = details.get('config', {})
    lines = ['# V2 ticket block — permissive rule override',
             f"Status: {details['run']['status']}",
             f"Model requested: {cfg.get('model')}; temperature: {cfg.get('temperature')} (null = SDK default).",
             'This experiment calls the real V2 ticket block once. Both questions use explicit demo rule overrides.',
             'These permissive rules accept any structurally valid prediction. Acceptance does not prove the answer is correct.',
             '## Input', details.get('input', '')]
    for name, entry in details.get('questions', {}).items():
        lines += [f'## QUESTION: {name}',
                  show(entry['definition'], indent=2, ensure_ascii=False),
                  f"DEFAULT RULE: {entry['default_rule']}",
                  f"OVERRIDE RULE LOADED: {entry['rule']['name']}",
                  f"Rule file: {entry['rule_file']}",
                  show(entry['rule'], indent=2),
                  '## What happened to this question',
                  'Raw answer:\n' + show((details.get('raw_response') or {}).get('answers', {}).get(name), indent=2),
                  'Actual runtime enrichment:\n' + show(details.get('enriched', {}).get(name), indent=2),
                  'Rule decision:\n' + show((details.get('result') or {}).get('decisions', {}).get(name), indent=2)]
    lines += ['## Actual SDK questions', show(details.get('submitted_questions'), indent=2),
              '## Runtime rule configuration observed in this run', show(details.get('configured_rules'), indent=2),
              '## Final V2 result', show(details.get('result'), indent=2)]
    if details.get('error'):
        lines += ['## ERROR', show(details['error'], indent=2)]
    if not details.get('enriched'):
        lines += ['Runtime enrichment was not captured. Inspect trace.jsonl; missing evidence is not presented as a successful enrichment.']
    return '\n\n'.join(lines) + '\n'
