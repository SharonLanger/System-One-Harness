"""Mechanical evidence demonstration: existing RV2 fruit fixtures, no new cases."""
import sys
sys.dont_write_bytecode=True
import argparse,json
from pathlib import Path
HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE))
import engine
from schema import load
from research.protocol import file_hash
from research.export import export_evidence

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);p.add_argument('--source-commit',required=True);a=p.parse_args()
    output=Path(a.output).resolve()
    if output.exists():raise ValueError('immutable demonstration destination already exists')
    cases=load(HERE/'examples/generic-choice/cases.json');suite=load(HERE/'examples/generic-choice/suite.json')
    roles={c['source_family_id']:'development' for c in cases['cases']}
    root=engine.create(cases,suite,'fixture','replay',{})
    if engine.run(root):raise RuntimeError('fixture did not complete')
    manifest=export_evidence(root,roles,'development',output/'compact',output/'sealed',source_commit=a.source_commit,
        frozen_references={'cases':'experiments/batch_v2/examples/generic-choice/cases.json','suite':'experiments/batch_v2/examples/generic-choice/suite.json',
            'case_file_sha256':file_hash(HERE/'examples/generic-choice/cases.json'),'suite_file_sha256':file_hash(HERE/'examples/generic-choice/suite.json')})
    (output/'roles.json').write_text(json.dumps(roles,indent=2)+'\n')
    result={'kind':'synthetic mechanical only','run_folder':str(root),'inference_calls':load(root/'attempts.json')['count'],
        'logical_outcomes':load(root/'manifest.json')['planned_counts']['logical_outcomes'],'campaign_ready':False,
        'compact_manifest':'compact/evidence-manifest.json','raw_archive_sha256':manifest['sealed_archive']['sha256']}
    (output/'demonstration.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
