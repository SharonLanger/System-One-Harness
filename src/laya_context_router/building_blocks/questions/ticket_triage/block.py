"""Ticket questions from the supplied capture; policy thresholds are illustrative."""
from pathlib import Path
from ....blocks import QuestionBlock

BLOCK_DIR=Path(__file__).parent


def run(text,*,config,registry):
    return QuestionBlock(BLOCK_DIR).run(text,config=config,registry=registry)
