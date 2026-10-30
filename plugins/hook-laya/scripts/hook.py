#!/usr/bin/env python3
"""Forward a named Claude hook to the shared application gateway."""
import sys


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    try:
        from laya_context_router.hooks.gateway import main as gateway_main
    except ImportError as exc:
        print(f"laya hook error: gateway_unavailable: {exc}", file=sys.stderr)
        return 0
    return gateway_main(["--hook", *args])


if __name__ == "__main__":
    raise SystemExit(main())
