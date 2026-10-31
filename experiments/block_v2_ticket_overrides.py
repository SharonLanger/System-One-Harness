"""IDE Play: run the real V2 ticket block with obvious input and a replaced question and a clear-winner rule."""
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
import argparse
import json
import os
import sys
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'src'))
from laya_context_router.block_runtime.catalog import Catalog, TypedRule
from laya_context_router.building_blocks.questions.ticket_triage_v2.block import run as run_block
from laya_context_router.laya.config import RunConfig
from laya_context_router.laya.registry import AgentRegistry
from laya_context_router.log_utils import LOG_PATH
from block_method_selection import CapturingRegistry
from support import allocate_result_dir, start_record, write_report
from block_v2_ticket_overrides_summary import render_summary

INPUT_PATH = HERE / 'inputs' / 'block_v2_ticket_overrides.json'
RULE_DIR = HERE / 'fixtures' / 'v2_ticket_rules' / 'rules'
OVERRIDES = {'department': 'demo_choice_clear_winner', 'churn_risk': 'demo_noul_accept_valid'}
DEFAULTS = {'department': 'ticket_department_default', 'churn_risk': 'ticket_churn_default'}


class DemoCatalog(Catalog):
    """Load shared questions/defaults unchanged, adding experiment-only named rules."""
    def rule(self, name):
        if name in OVERRIDES.values():
            return TypedRule.from_dict(json.loads((RULE_DIR / f'{name}.json').read_text()))
        return super().rule(name)


def capture_trace(offset):
    try:
        with LOG_PATH.open('rb') as handle:
            handle.seek(offset)
            records = []
            for line in handle:
                try:
                    record = json.loads(line)
                    if record.get('pid') == os.getpid():
                        records.append(record)
                except (ValueError, TypeError):
                    continue
            return records
    except OSError:
        return []


def run(*, input_path=INPUT_PATH, model=None, temperature=None, loader=None, inspection_provider=None,
        output_root=None, printer=print):
    started, stamp = time.monotonic(), datetime.now().astimezone()
    offset = LOG_PATH.stat().st_size if LOG_PATH.exists() else 0
    details = {'run': start_record('block_v2_ticket_overrides.py', 'ticket_triage_v2.block.run',
                                   'injected' if loader is not None else 'real'),
               'input': '', 'config': {}, 'questions': {}, 'raw_response': None,
               'enriched': {}, 'configured_rules': None, 'result': None, 'error': None}
    printer('V2 TICKET BLOCK — QUESTION OVERRIDE + DIFFERENT NAMED RULE')
    try:
        payload = json.loads(Path(input_path).read_text())
        cfg = dict(payload.get('config', {}))
        if model is not None:
            cfg['model'] = model
        if temperature is not None:
            cfg['temperature'] = temperature
        config = RunConfig.from_dict(cfg)
        details['config'] = {'model': config.model, 'temperature': config.temperature, 'lang': config.lang}
        details['input'] = payload['text']
        catalog = DemoCatalog()
        for name, rule_name in OVERRIDES.items():
            # Resolve through the same catalog instance passed to the actual block.
            rule = catalog.rule(rule_name)
            details['questions'][name] = {'definition': payload.get('question_overrides', {}).get(name, catalog.question(name)),
                'shared_definition': catalog.question(name),
                'default_rule': DEFAULTS[name], 'rule': {'name': rule.name,
                'question_type': rule.question_type, 'conditions': rule.conditions},
                'rule_file': str((RULE_DIR / f'{rule_name}.json').relative_to(HERE.parent))}
        printer(f"Model: {config.model}; temperature: {config.temperature} (None = SDK default)")
        printer("INPUT: " + payload["text"])
        for name, question in details["questions"].items():
            printer("QUESTION AND RULE: " + name + "\n" + json.dumps(question, indent=2))
        printer("Calling ticket_triage_v2 now (one model request)...")
        registry = CapturingRegistry(AgentRegistry(inspection_provider=inspection_provider, loader=loader, real=loader is None), details)
        result = run_block({'text': payload['text']}, config=config, registry=registry,
                           catalog=catalog, rule_overrides=OVERRIDES,
                           question_overrides=payload.get('question_overrides', {}))
        details['result'] = asdict(result)
        details['run']['status'] = 'success'
    except Exception as exc:
        details['error'] = {'type': type(exc).__name__, 'message': str(exc)}
        details['run']['status'] = 'failed'
    trace = capture_trace(offset)
    for record in trace:
        value = record.get('details', {})
        if record.get('component') == 'enrichment' and record.get('event') == 'completed' and value.get('block') == 'ticket_triage':
            details['enriched'][value['question']] = value['enriched']
        if record.get('component') == 'block_runtime' and record.get('event') == 'configured' and value.get('block') == 'ticket_triage':
            details['configured_rules'] = value.get('rules')
    details['run']['duration_seconds'] = round(time.monotonic() - started, 3)
    summary = render_summary(details)
    printer(summary)
    try:
        out = allocate_result_dir(Path(output_root) if output_root else HERE / 'results' / Path(__file__).stem, stamp)
        write_report(out, details, summary)
        (out / 'trace.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in trace))
        printer(f"Saved: {out / 'summary.md'}\nDetails: {out / 'details.json'}\nTrace: {out / 'trace.jsonl'}")
    except Exception as exc:
        printer(f'ERROR saving results: {exc}')
        return 1
    return 0 if details['run']['status'] == 'success' else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', default=str(INPUT_PATH))
    parser.add_argument('--model')
    parser.add_argument('--temperature', type=float)
    args = parser.parse_args(argv)
    return run(input_path=args.input, model=args.model, temperature=args.temperature)


if __name__ == '__main__':
    raise SystemExit(main())
