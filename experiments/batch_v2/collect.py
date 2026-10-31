"""Rebuild RV2 reports from frozen records without model inference."""
import sys
sys.dont_write_bytecode=True
import argparse
from reporting import collect
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--run',required=True)
    args=parser.parse_args(); collect(args.run)
