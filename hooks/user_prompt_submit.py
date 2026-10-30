#!/usr/bin/env python3
"""Compatibility launcher; protocol and feature logic live in the gateway."""
import sys


def main(argv=None):
    try:
        from laya_context_router.hook_gateway import main as gateway_main
    except ImportError as exc:
        print(f'laya hook error: gateway_unavailable: {exc}', file=sys.stderr)
        return 0
    return gateway_main(['--hook','UserPromptSubmit',*(sys.argv[1:] if argv is None else argv)])


if __name__ == '__main__':
    raise SystemExit(main())
