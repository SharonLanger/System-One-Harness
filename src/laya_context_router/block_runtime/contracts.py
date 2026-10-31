"""Small, explicit contracts for block execution."""
from dataclasses import dataclass, field
from typing import Any

class BlockConfigurationError(ValueError):
    """An invalid declaration, catalog or override."""

class BlockInputError(ValueError):
    """An invalid input or prepared payload."""

class BlockExecutionError(RuntimeError):
    """Unexpected preparation/reduction failure; original exception is its cause."""

@dataclass
class PreparedInput:
    text: str
    questions: dict
    state: dict = field(default_factory=dict)

@dataclass
class BlockResult:
    status: str
    reason: str | None
    decisions: dict
    data: Any

class SkipBlock(Exception):
    def __init__(self, reason, state=None):
        if not isinstance(reason, str) or not reason:
            raise BlockInputError('skip reason must be a nonempty string')
        super().__init__(reason)
        self.reason = reason
        self.state = {} if state is None else state
