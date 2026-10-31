"""Offline counts and temperature tables for dynamic method choices."""
import csv,io,json,hashlib
from collections import Counter
from pathlib import Path
from schema import load,hash_value
from reporting import atomic
COUNTS=['planned','evaluated','selectable_evaluated','refusal_evaluated','correct_selection','wrong_selection','missed_selection','correct_refusal','unsafe_selection','error','timeout','skipped','unattempted']
RATES={'selection_precision':('correct_selection','selected'),'correct_selection_yield':('correct_selection','selectable_evaluated'),'refusal_correctness':('correct_refusal','refusal_evaluated'),'selection_coverage':('selected','evaluated'),'end_to_end_correctness':('correct_outcomes','evaluated'),'technical_completion':('evaluated','planned')}

def outcome(expected, output):
    actual=output['data']['selected_id'];target=expected['selected_id']
    if target is None:return 'correct_refusal' if actual is None else 'unsafe_selection'
    return 'missed_selection' if actual is None else ('correct_selection' if actual==target else 'wrong_selection')

def metrics(row):
    row['selected']=sum(row[k] for k in ('correct_selection','wrong_selection','unsafe_selection'))
    row['incorrect_selections']=row['wrong_selection']+row['unsafe_selection']
    row['correct_outcomes']=row['correct_selection']+row['correct_refusal']
    for key,(a,b) in RATES.items():row[key]=row[a]/row[b] if row[b] else None
    row['complete']=row['planned']==row['evaluated']
    return row

def aggregate(rows):
    return metrics({k:sum(r[k] for r in rows) for k in COUNTS})

def collect(root):
    root=Path(root);m=load(root/'manifest.json');rows=[]
    for q in m['suite']['questions']:
      for r in m['suite']['rules']:
       for cfg in m['suite']['configurations']:
        for case in m['cases']['cases']:
            path=root/'batches'/f"{q['id']}__{r['id']}"/cfg['id']/'cases'/f"{case['id']}.json"
            row={'case_id':case['id'],'question_id':q['id'],'rule_id':r['id'],'config_id':cfg['id'],'status':'unattempted'}
            if path.exists():row=load(path)
            rows.append(row)
    # Keep shared lifecycle status checks working; campaign summaries are split-filtered separately.
    return rows

def csv_text(rows):
    if not rows:return ''
    out=io.StringIO();w=csv.DictWriter(out,fieldnames=list(rows[0]),extrasaction='raise');w.writeheader();w.writerows(rows);return out.getvalue()

def rate(row,key):
    a,b=RATES[key];return f"{100*row[key]:.1f}% ({row[a]}/{row[b]})" if row[key] is not None else 'N/A (0/0)'

def table(rows):
    lines=['| Rule | Correct selection | Wrong selection | Missed selection | Correct refusal | Unsafe selection | Evaluated / planned |','| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for r in rows:lines.append('| '+str(r.get('rule_id',r.get('config_id','total')))+' | '+' | '.join(str(r[k]) for k in ['correct_selection','wrong_selection','missed_selection','correct_refusal','unsafe_selection'])+f" | {r['evaluated']}/{r['planned']} |")
    lines+=['','| Rule | Selection precision | Selection yield | Refusal correctness | End to end | Completion |','| --- | ---: | ---: | ---: | ---: | ---: |']
    for r in rows:lines.append('| '+str(r.get('rule_id',r.get('config_id','total')))+' | '+' | '.join(rate(r,k) for k in ['selection_precision','correct_selection_yield','refusal_correctness','end_to_end_correctness','technical_completion'])+' |')
    return '\n'.join(lines)+'\n'

def summarize(root,split='development',allow_partial=False,finalists=None):
    root=Path(root);m=load(root/'manifest.json');suite=m['suite'];cases=m['cases']['cases']
    if m.get('campaign_kind','main')!='main':raise ValueError('smoke runs cannot enter main totals')
    if split not in ('development','held_out','all'):raise ValueError('invalid split')
    if split!='development':
        if finalists is None:raise ValueError('frozen finalists required')
        f=load(finalists)
        for key in ['run_id','cases_hash','suite_hash']:
            if f.get(key)!=m[key]:raise ValueError('finalists identity mismatch')
        dev=root/'analysis/development/vectors.csv'
        if not dev.exists() or hashlib.sha256(dev.read_bytes()).hexdigest()!=f.get('development_report_hash'):raise ValueError('development report hash mismatch')
        valid={(q['id'],r['id'],c['id']) for q in suite['questions'] for r in suite['rules'] for c in suite['configurations']}
        vectors=f.get('finalists',[])
        if len(vectors)>2 or not f.get('frozen_at') or f.get('baseline')!=suite['baseline']:raise ValueError('invalid finalist freeze')
        for v in vectors:
            if tuple(v[k] for k in ('question_id','rule_id','config_id')) not in valid:raise ValueError('unknown finalist')
    cases=[c for c in cases if split=='all' or c['split']==split]
    selected_ids={c['id'] for c in cases}
    ledger=root/'attempt-events.jsonl'
    events=[json.loads(line) for line in ledger.read_text().splitlines()] if ledger.exists() else []
    events=[e for e in events if e['case_id'] in selected_ids]
    vectors=[];raw={};ids=set();reasons=Counter();source_hashes={}
    from method_evidence import read as read_evidence
    for q in suite['questions']:
      for cfg in suite['configurations']:
       for rule in suite['rules']:
        row={k:0 for k in COUNTS}; row.update(schema_version=1,experiment_id=suite['experiment_id'],run_id=m['run_id'],dataset_version=m['cases']['dataset_version'],cases_hash=m['cases_hash'],suite_hash=m['suite_hash'],split=split,question_id=q['id'],rule_id=rule['id'],config_id=cfg['id'],temperature=cfg['temperature'])
        for case in cases:
            row['planned']+=1
            p=root/'batches'/f"{q['id']}__{rule['id']}"/cfg['id']/'cases'/f"{case['id']}.json"
            if not p.exists():
                worker=root/f"worker-{cfg['id']}-status.json"
                failed=worker.exists() and load(worker).get('status')=='configuration_error'
                row['error' if failed else 'unattempted']+=1;continue
            saved=load(p);key=(q['id'],rule['id'],cfg['id'],case['id'])
            if key in ids:raise ValueError('duplicate logical key')
            ids.add(key);source_hashes[str(p.relative_to(root))]=hash_value(saved)
            for name,value in zip(('question_id','rule_id','config_id','case_id'),key):
                if saved.get(name)!=value:raise ValueError('checkpoint identity mismatch')
            if saved.get('input_hash')!=hash_value(case['input']):raise ValueError('checkpoint input hash mismatch')
            for field,value in [('question_hash',q),('rule_hash',rule),('config_hash',cfg)]:
                if saved.get(field)!=hash_value(value):raise ValueError('checkpoint settings hash mismatch')
            status=saved['status']
            if status!='completed':row['error' if status=='configuration_error' else status]+=1;continue
            try:bucket=outcome(case['expected'],saved['block_result'])
            except (KeyError,TypeError):row['error']+=1;continue
            row[bucket]+=1;row['evaluated']+=1;row['selectable_evaluated' if case['expected']['selected_id'] else 'refusal_evaluated']+=1
            reasons[(q['id'],rule['id'],cfg['id'],saved['block_result']['data'].get('reason') or 'selected')]+=1
            iid=saved['inference_id']
            if iid not in raw:
                evidence=read_evidence(root,iid)
                if evidence is None:raise ValueError('missing canonical inference')
                answers=evidence['raw_response']['answers'];ma=answers['method']['choice'];mult=saved['block_result']['decisions']['multiple_relevant']['answer']
                raw[iid]={'question_id':q['id'],'config_id':cfg['id'],'case_id':case['id'],'method_correct':ma==case['expected']['method_label'],'multiple_correct':mult==case['expected']['multiple_relevant']}
        vectors.append(metrics(row))
    complete=all(r['complete'] for r in vectors)
    if not complete and not allow_partial:raise ValueError('incomplete run; use --allow-partial')
    out=root/'analysis'/split;out.mkdir(parents=True,exist_ok=True)
    files={}
    def emit(name,text):files[name]=text;atomic(out/name,text)
    header=f"Run {m['run_id']}; split {split}; {'COMPLETE' if complete else 'PARTIAL'}.\n\nDataset {m['cases_hash']}; suite {m['suite_hash']}.\n\n"
    def pair(stem,rs,md):emit(stem+'.csv',csv_text(rs));emit(stem+'.md',header+md)
    summary=[];temperature_totals=[];raw_rows=[]
    for cfg in suite['configurations']:
        rs=[r for r in vectors if r['config_id']==cfg['id']];tot=aggregate(rs)
        ev=[r for r in raw.values() if r['config_id']==cfg['id']]
        tot.update(config_id=cfg['id'],temperature=cfg['temperature'],vector_count=len(rs),distinct_inputs=len(cases),distinct_evidence_count=len(ev),prediction_attempts=sum(e['config_id']==cfg['id'] for e in events))
        temperature_totals.append(tot)
        md=f"# Temperature {cfg['temperature']}\n\n{tot['evaluated']}/{tot['planned']} outcomes evaluated.\n\n"
        for q in suite['questions']:
            qr=[r for r in rs if r['question_id']==q['id']];md+='## '+q['id']+'\n\n'+table(qr)+'\n'
            evidence=[r for r in ev if r['question_id']==q['id']]
            raw_rows.append(dict(question_id=q['id'],config_id=cfg['id'],temperature=cfg['temperature'],evaluated=len(evidence),planned=len(cases),method_correct=sum(r['method_correct'] for r in evidence),multiple_correct=sum(r['multiple_correct'] for r in evidence)))
        baseline=next(r for r in rs if r['question_id']==suite['baseline']['question_id'] and r['rule_id']==suite['baseline']['rule_id'])
        md+=f"Baseline: {baseline['incorrect_selections']} incorrect selections; {baseline['correct_selection']} correct selections.\n\n"
        for r in rs:md+=f"- {r['question_id']} / {r['rule_id']}: incorrect selections {r['incorrect_selections']-baseline['incorrect_selections']:+d}; correct selections {r['correct_selection']-baseline['correct_selection']:+d} versus baseline.\n"
        pair('by-temperature/'+cfg['id'],rs,md);summary.append(md)
    pair('vectors',vectors,'\n'.join(summary))
    emit('summary.md',header+'\n'.join(summary))
    for q in suite['questions']:
        rs=[r for r in vectors if r['question_id']==q['id']]
        pair('by-question/'+q['id'],rs,'\n'.join(f"## Temperature {cfg['temperature']}\n\n"+table([r for r in rs if r['config_id']==cfg['id']]) for cfg in suite['configurations']))
    pooled=[]
    for q in suite['questions']:
      for rule in suite['rules']:
        row=aggregate([r for r in vectors if r['question_id']==q['id'] and r['rule_id']==rule['id']]);row.update(question_id=q['id'],rule_id=rule['id']);pooled.append(row)
    pair('temperature-totals',temperature_totals,'\n'.join(f"## Temperature {r['temperature']}\n\n"+table([r]) for r in temperature_totals))
    pair('question-rule-totals',pooled,'\n'.join(summary)+'\n## Pooled across temperatures\n\n'+table(pooled))
    pair('raw-answers',raw_rows,'\n'.join('## Temperature '+str(c['temperature'])+'\n\n'+ '\n'.join(f"- {r['question_id']}: method {r['method_correct']}/{r['evaluated']}; multiple {r['multiple_correct']}/{r['evaluated']}" for r in raw_rows if r['config_id']==c['id']) for c in suite['configurations']))
    totals={'logical_outcomes':aggregate(vectors),'unique_evidence':len(raw),'prediction_attempts':len(events),'temperature_totals':temperature_totals,'question_rule_totals':pooled,'complete':complete,'cases_hash':m['cases_hash'],'suite_hash':m['suite_hash'],'split':split}
    emit('totals.json',json.dumps(totals,indent=2)+'\n')
    emit('reasons.json',json.dumps([{'question_id':k[0],'rule_id':k[1],'config_id':k[2],'reason':k[3],'count':v} for k,v in sorted(reasons.items())],indent=2)+'\n')
    atomic(out/'report-manifest.json',json.dumps({'schema_version':1,'complete':complete,'source_hashes':source_hashes,'script_hash':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'outputs':{k:hashlib.sha256(v.encode()).hexdigest() for k,v in files.items()}},indent=2)+'\n')
    return totals
