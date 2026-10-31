"""Generate offline per-temperature tables and pooled totals from one frozen run."""
import argparse,sys
from pathlib import Path
sys.path[:0]=[str(Path(__file__).resolve().parents[2]),str(Path(__file__).resolve().parents[4]/'src')]
from method_reporting import summarize

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',required=True);p.add_argument('--split',choices=['development','held_out','all'],default='development');p.add_argument('--allow-partial',action='store_true');p.add_argument('--finalists');a=p.parse_args()
    try:
        t=summarize(a.run,a.split,a.allow_partial,a.finalists);print('Reports:',Path(a.run)/'analysis'/a.split);print('Unique evidence:',t['unique_evidence']);return 0
    except (ValueError,OSError) as e:print(str(e),file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
