"""Command-line adapters; hook execution belongs to the existing gateway."""
import argparse
import sys


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    # Dispatch before argparse so gateway flags, validation, streams and exit
    # conventions remain owned entirely by the gateway.
    if argv and argv[0] == 'hook':
        from ..hooks.gateway import main as gateway_main
        return gateway_main(argv[1:])

    parser = argparse.ArgumentParser(prog='laya-context-router')
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('hook', help='pass all following arguments to the hook gateway')
    commands.add_parser('doctor', help='report local CLI setup (no model checks)')
    logs = commands.add_parser('logs', help='print recent lines from the existing JSONL log')
    logs.add_argument('--last', type=int, default=5, metavar='N', help='number of lines (default: 5)')
    args = parser.parse_args(argv)
    if args.command == 'doctor':
        from .doctor import run
        return run()
    if args.last <= 0:
        parser.error('--last must be a positive integer')
    from .logs import run
    return run(args.last)
