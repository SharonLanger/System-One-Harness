"""Compact tuning evidence plus a separate sealed full-run archive and inventories."""
import json
import tarfile
from pathlib import Path
from .protocol import digest,file_hash
from .records import read_run
from .analyze import analyze,write_report


def export_evidence(run_root, roles, stage, destination, sealed_destination, *, source_commit, finalists=None, protocol=None, decision_history=None, frozen_references=None):
    run_root=Path(run_root).resolve(); destination=Path(destination).resolve(); sealed_destination=Path(sealed_destination).resolve()
    if destination.exists() or sealed_destination.exists(): raise ValueError('immutable export destination already exists')
    if destination==sealed_destination or destination in sealed_destination.parents or sealed_destination in destination.parents:
        raise ValueError('sealed raw archive must be stored separately from tuning package')
    if run_root==destination or run_root in destination.parents or run_root==sealed_destination or run_root in sealed_destination.parents:
        raise ValueError('exports cannot be inside source run')
    evidence=read_run(run_root,roles,stage,finalists); report=analyze(evidence,roles)
    destination.mkdir(parents=True);sealed_destination.mkdir(parents=True)
    # Archive raw originals without parsing withheld evidence. Not accessible from tuning report links.
    inventory=[]
    for path in sorted(run_root.rglob('*')):
        if path.is_symlink(): raise ValueError('raw run symlinks are not supported')
        if path.is_file(): inventory.append({'path':str(path.relative_to(run_root)),'sha256':file_hash(path),'bytes':path.stat().st_size})
    archive=sealed_destination/'full-raw-run.tar.gz'
    with tarfile.open(archive,'w:gz') as tar:
        for entry in inventory: tar.add(run_root/entry['path'],arcname=entry['path'],recursive=False)
    sealed={'sealed':stage!='final','run_id':evidence['run_id'],'archive':archive.name,'sha256':file_hash(archive),'inventory':inventory}
    (sealed_destination/'archive-manifest.json').write_text(json.dumps(sealed,indent=2)+'\n')
    recipe={'roles':roles,'suite':evidence['suite'],'protocol':protocol,'decision_history':decision_history or [],'finalists':finalists,
        'frozen_references':frozen_references or {},'replay':'python -m research analyze --run ORIGINAL --roles roles.json --stage '+stage+' --output REPORT',
        'limitations':['Original case/suite byte hashes and original run archive must remain retrievable.']}
    (destination/'recipe.json').write_text(json.dumps(recipe,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    (destination/'roles.json').write_text(json.dumps(roles,indent=2)+'\n')
    (destination/'predictions.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    write_report(report,destination)
    helper_root=Path(__file__).parent
    manifest={'schema_version':1,'run_id':evidence['run_id'],'source_commit':source_commit,'analysis_version':'research-v1',
        'identity':evidence['identity'],'original_inventory':inventory,'stage':stage,'held_out_values_included':stage=='final',
        'sealed_archive':{'reference':str(archive),'sha256':sealed['sha256'],'withheld':stage!='final'},
        'helpers':{p.name:file_hash(p) for p in sorted(helper_root.glob('*.py'))},
        'files':{p.name:file_hash(p) for p in sorted(destination.iterdir()) if p.is_file()},
        'handoff_status':'local_only_pending_publication','publication':None}
    (destination/'evidence-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');return manifest


def mark_published(destination, public_reference, sealed_reference):
    """Operator supplies exact retrievable references after separately publishing both artifacts."""
    if not public_reference or not sealed_reference: raise ValueError('both durable references required')
    path=Path(destination)/'evidence-manifest.json'; m=json.loads(path.read_text())
    for name,sha in m['files'].items():
        if file_hash(Path(destination)/name)!=sha: raise ValueError('export changed before publication')
    if m['publication'] is not None: raise ValueError('publication already recorded')
    m.update(handoff_status='published_references_recorded',publication={'compact_reference':public_reference,'sealed_reference':sealed_reference,
        'verification':'references supplied by operator; recipient must verify availability/checksums'})
    path.write_text(json.dumps(m,indent=2)+'\n');return m
