"""Allow python -m cli using the same adapter."""
from cli import main

raise SystemExit(main())
