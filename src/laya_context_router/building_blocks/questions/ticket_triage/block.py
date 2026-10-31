"""Ticket questions from the supplied capture; policy thresholds are illustrative."""
from pathlib import Path
from ....blocks import QuestionBlock

BLOCK_DIR=Path(__file__).parent


def run_legacy(text,*,config,registry):
    return QuestionBlock(BLOCK_DIR).run(text,config=config,registry=registry)


def run(text, *, config, registry):
    """Compatibility dictionary adapter over the V2 ticket block."""
    from ..ticket_triage_v2.block import run as run_v2
    # Preserve the original public input exception class.
    if not isinstance(text, str):
        return run_legacy(text, config=config, registry=registry)
    return run_v2({'text': text}, config=config, registry=registry).decisions
