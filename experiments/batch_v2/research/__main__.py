"""Offline research entry points. No inference command except the separate opt-in probe."""
import argparse
from pathlib import Path
from .records import load, read_run
from .analyze import analyze,write_report
from .export import export_evidence,mark_published


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    for command in ('analyze','export'):
        parser=sub.add_parser(command);parser.add_argument('--run',required=True);parser.add_argument('--roles',required=True);parser.add_argument('--stage',choices=['development','temperature','policy','final'],required=True);parser.add_argument('--finalists');parser.add_argument('--output',required=True)
        if command=='export': parser.add_argument('--sealed-output',required=True);parser.add_argument('--source-commit',required=True)
    pub=sub.add_parser('mark-published');pub.add_argument('--output',required=True);pub.add_argument('--compact-reference',required=True);pub.add_argument('--sealed-reference',required=True)
    args=p.parse_args()
    if args.command=='mark-published': mark_published(args.output,args.compact_reference,args.sealed_reference);return
    roles=load(args.roles);finalists=load(args.finalists) if args.finalists else None
    if args.command=='analyze':
        report=analyze(read_run(args.run,roles,args.stage,finalists),roles);write_report(report,args.output)
    else: export_evidence(args.run,roles,args.stage,args.output,args.sealed_output,source_commit=args.source_commit,finalists=finalists)
if __name__=='__main__':main()
