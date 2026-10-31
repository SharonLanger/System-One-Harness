"""Allow python -m laya_context_router.cli using the same adapter."""
from . import main

raise SystemExit(main())
