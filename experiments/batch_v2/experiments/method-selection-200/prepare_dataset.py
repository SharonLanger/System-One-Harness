"""Deterministic authoring helper: real TypeScript outlines, never model predictions."""
import json,re,sys,random,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT/'src'))
from laya_context_router.building_blocks.typescript import outline

def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2)+'\n')

def main():
    plan=(ROOT/'experiments/batch_v2/docs/campaigns/method-selection-200/plan.md').read_text()
    suite=json.loads(re.search(r'### 9\.1.*?```json\n(.*?)\n```',plan,re.S).group(1))
    write(HERE/'rounds/001-small/suite.json',suite)
    domains=['Invoice','Order','CacheEntry','Session','AccessToken','Password','UserProfile','Permission','AuditEvent','Payment','Refund','Shipment','InventoryItem','Subscription','Notification','Attachment','CsvRecord','JsonDocument','SearchQuery','Report','Backup','Connection','Transaction','Schedule','FeatureFlag']
    operations=[('validate','checks whether the supplied value satisfies its validation constraints'),('serialize','converts the supplied value into a serialized string'),('persist','stores the supplied value under its identifier'),('remove','deletes the value associated with the supplied identifier')]
    cats=[('explicit',25),('semantic',20),('distractor',15),('same-name',10),('absent',10),('ambiguous',10),('multiple',10)]
    assignments=[]
    rng=random.Random(20261031)
    for cat,n in cats:
        splits=['development']*int(n*.6)+['held_out']*(n-int(n*.6));rng.shuffle(splits)
        assignments.extend((cat,sp) for sp in splits)
    cases=[]; reviews=[]
    for i,(cat,split) in enumerate(assignments):
        domain=domains[i//4]; verb,meaning=operations[i%4]; name=verb+domain
        n=[2,4,8,16][i%4]
        signatures=[]
        # Each target has a distinct semantic operation and domain, not merely a renamed copy.
        for j in range(n):
            if j==0: nm=name
            elif cat=='same-name' and j==1: nm=name
            else: nm=operations[(i+j)%4][0]+domains[(i//4+j)%len(domains)]
            typ='string' if j==0 else ('number' if cat=='same-name' and j==1 else 'boolean')
            ret='boolean' if nm.startswith('validate') else ('string' if nm.startswith('serialize') else 'void')
            body='return true;' if ret=='boolean' else ('return "";' if ret=='string' else '')
            kind=i%4
            if cat=='same-name' or kind==0: code=f'export class Candidate{j} {{ static {nm}(value: {typ}): {ret} {{ {body} }} }}'
            elif kind==1: code=f'export function {nm}(value: {typ}): {ret} {{ {body} }}'
            elif kind==2: code=f'export const {nm} = (value: {typ}): {ret} => {{ {body} }};'
            else: code=f'export class Candidate{j} {{ async {nm}(value: {typ}): Promise<{ret}> {{ {body} }} }}'
            signatures.append(code)
        # Rotate the source order so expected targets do not always occur first.
        shift=i%n; signatures=signatures[shift:]+signatures[:shift]
        source='\n'.join(signatures)+'\n'; path=HERE/'fixtures'/f'family-{i:03}.ts';path.parent.mkdir(exist_ok=True);path.write_text(source)
        data=outline(path);data['path']=str(path.relative_to(ROOT))
        target=next(c for c in data['callables'] if c['name']==name and 'value: string' in c['signature'])
        other=next(c for c in data['callables'] if c['id']!=target['id'])
        label=name+(f"@{target['location']['line']}:{target['location']['column']}" if cat=='same-name' else '')
        if cat=='explicit': prompts=[f'Explain {name}.',f'Walk me through the callable named {name}.']
        elif cat=='semantic':prompts=[f'Explain the {domain} operation that {meaning}.',f'For {domain}, describe the operation that {meaning}; I want an explanation.']
        elif cat=='distractor':prompts=[f'Explain {name}, not {other["name"]}.',f'I previously looked at {other["name"]}. Now explain only {name}.']
        elif cat=='same-name':prompts=[f'Explain {name} with the string parameter, not the numeric version.',f'Explain the {name} callable at line {target["location"]["line"]}, which accepts a string.']
        elif cat=='absent':prompts=[f'Explain archive{domain}; I do not mean the listed operations.',f'I need an explanation of archive{domain}, which is not one of these candidates.']
        elif cat=='ambiguous':prompts=['Explain the operation that is relevant here; I have not specified which one.','Describe the right callable for my task. I have not described the task yet.']
        else:prompts=[f'Explain both {name} and {other["name"]}.',f'Compare how {name} and {other["name"]} work; explain each.']
        for v,text in enumerate(prompts):
            noise='regular'
            if v==1 and i>=60:
                noise='noisy' if i<90 else 'heavy';text=text.replace('Explain','Pls explian').replace('explain','explian')
                if noise=='heavy':text='[unrelated status: connection retry 3; ignore] '+text+'\n  -- Please keep the target request above. --'
            expected={'method_label':label if i<70 else 'none_or_unclear','multiple_relevant':'yes' if cat=='multiple' else 'no','selected_id':target['id'] if i<70 else None}
            cid=f'case-{i:03}-{v}'
            cases.append(dict(id=cid,input={'text':text,'source_outline':data},expected=expected,label_status='settled',noise_level=noise,tags=[cat],source_family_id=f'family-{i:03}',split=split,notes=f'{cat}: target follows request and visible signatures; explanation only.'))
            reviews.append({'case_id':cid,'rationale':cases[-1]['notes'],'review':'author self-review; independent review not performed'})
    write(HERE/'cases.json',{'schema_version':2,'dataset_id':'method-selection-200','dataset_version':'1','cases':cases})
    write(HERE/'annotation-review.json',reviews)
    write(HERE/'protocol.json',{'seed':20261031,'main_call_cap':1600,'smoke_call_cap':8,'rule_ids':[r['id'] for r in suite['rules']],'temperatures':[.5,.8,1.,1.1],'review_status':'self-reviewed; independent review outstanding','cases_sha256':hashlib.sha256((HERE/'cases.json').read_bytes()).hexdigest()})
if __name__=='__main__':main()
