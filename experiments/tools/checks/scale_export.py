"""Opt-in synthetic 35k check. Temporary outputs only; no SDK imports."""
import json
from pathlib import Path
import resource
import tempfile
import time
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_export_v2_results import fixture,e


def main():
    with tempfile.TemporaryDirectory() as tmp:
        base=Path(tmp);source=base/'source';fixture(source,500,10,7)
        # Include an unusually long raw response without increasing every record.
        path=next((source/'inferences').glob('*.json'));raw=e.read(path)
        raw['raw_response']['long_field']='x'*1_000_000;e.write(path,raw)
        started=time.monotonic()
        dest=e.export_run(source,base/'exports',source_stopped=True)
        info=e.read(dest/'export.json')
        assert info['found']==35000 and len(info['partitions'])==70
        assert all(p['found']==500 for p in info['partitions'])
        print(json.dumps({'records':info['found'],'partitions':70,'export_bytes':info['export_bytes'],
            'source_inference_bytes':info['source_inference_bytes'],'seconds':round(time.monotonic()-started,3),
            'peak_rss_kib_linux':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}))

if __name__=='__main__':main()
