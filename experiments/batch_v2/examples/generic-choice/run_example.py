"""IDE Play: explicitly synthetic RV2 example; no MLX installation required."""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]))
from run import main
if __name__=='__main__':
    raise SystemExit(main(['--cases',str(HERE/'cases.json'),'--suite',str(HERE/'suite.json'),'--mode','fixture','--rule-mode','replay']))
