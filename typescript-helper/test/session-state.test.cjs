const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const fsp = require('node:fs/promises');
const os = require('node:os');
const path = require('node:path');
const {SessionStateStore} = require('../../build/typescript/session-state.js');

function fixture(t, id='session-01') {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'laya-state-'));
  t.after(() => fs.rmSync(root, {recursive:true, force:true}));
  const logs = path.join(root, 'logs');
  const file = path.join(logs, 'session-state', id + '.jsonl');
  const store = new SessionStateStore(logs, id);
  const write = text => {fs.mkdirSync(path.dirname(file), {recursive:true}); fs.writeFileSync(file, text);};
  return {root, logs, file, store, write};
}
function event(payload={}) {return {source:{kind:'flow',name:'method-enrichment'},type:'context_enriched',payload};}
function stored(payload={}) {return {...event(payload),timestamp:'2026-10-31T18:00:00.000Z'};}

test('load missing/empty history has no side effects; first save creates only session file', async t => {
  const f=fixture(t);
  assert.deepEqual(await f.store.load(), []);
  assert.equal(fs.existsSync(f.logs), false);
  f.write('');
  assert.deepEqual(await f.store.load(), []);
  const saved=await f.store.save(event());
  assert.equal(saved.timestamp,new Date(saved.timestamp).toISOString());
  assert.equal(fs.readFileSync(f.file,'utf8'),JSON.stringify(saved)+'\n');
  assert.deepEqual(fs.readdirSync(path.dirname(f.file)),['session-01.jsonl']);
});
test('appends preserve bytes, intentional duplicates and restart history; sessions isolated', async t => {
  const f=fixture(t);
  const first=await f.store.save(event({a:1}));
  const prefix=fs.readFileSync(f.file);
  await f.store.save(event({a:1}));
  assert.deepEqual(fs.readFileSync(f.file).subarray(0,prefix.length),prefix);
  const records=await new SessionStateStore(f.logs,'session-01').load();
  assert.equal(records.length,2); assert.deepEqual(records[0],first);
  const other=new SessionStateStore(f.logs,'session-02');
  assert.deepEqual(await other.load(),[]);
  await other.save({source:{kind:'hook',name:'UserPromptSubmit'},type:'prompt_submitted',payload:{}});
  assert.equal((await f.store.load()).length,2);
});
test('escaped strings, Unicode, nested JSON, multiple files and method names round trip', async t => {
  const f=fixture(t);
  const payload={files:[{filePath:'C:\\project\\a.ts',methodNames:['a','b']},{filePath:'/project/b.ts',methodNames:[]}],
    text:'"\\\n\r\t\b\f\u0000 שלום 😀 /', nested:[null,true,false,1.25,{value:'x'}]};
  const saved=await f.store.save(event(payload));
  assert.equal(fs.readFileSync(f.file,'utf8').split('\n').length,2);
  assert.deepEqual(await f.store.load(),[saved]); assert.deepEqual(saved.payload,payload);
  const unknown=await f.store.save({...event(),type:'future_event'});
  assert.equal((await f.store.load())[1].type,unknown.type);
});
test('capture is immediate and returned event detached from mutable input', async t => {
  const f=fixture(t); const input=event({files:[{methodNames:['before']}]});
  const saving=f.store.save(input);
  input.source.name='changed';input.payload.files[0].methodNames.push('after');
  const saved=await saving;
  assert.equal(saved.source.name,'method-enrichment');
  assert.deepEqual(saved.payload.files[0].methodNames,['before']);
  assert.deepEqual((await f.store.load())[0],saved);
  saved.payload.files[0].methodNames.push('returned change');
  assert.deepEqual((await f.store.load())[0].payload.files[0].methodNames,['before']);
});
test('same-instance saves and loads queue in invocation order', async t => {
  const f=fixture(t);
  const first=f.store.save(event({i:0})); const early=f.store.load();
  const writes=Array.from({length:30},(_,i)=>f.store.save(event({i:i+1})));
  const final=f.store.load();
  assert.deepEqual((await early).map(x=>x.payload.i),[0]);
  await Promise.all([first,...writes]);
  assert.deepEqual((await final).map(x=>x.payload.i),Array.from({length:31},(_,i)=>i));
});
test('reject unsafe session IDs and relative log roots', t => {
  const f=fixture(t);
  for(const id of ['', '.', '..', '../x', 'a/b', 'a\\b', 'a\nx', 'a.jsonl', null, 2])
    assert.throws(()=>new SessionStateStore(f.logs,id),/sessionId/);
  assert.throws(()=>new SessionStateStore('logs','ok'),/absolute/);
});
test('non-JSON input and invalid event shape reject before writing', async t => {
  const f=fixture(t); await f.store.save(event()); const before=fs.readFileSync(f.file);
  const cycle={};cycle.self=cycle;
  const symbolKey={[Symbol('hidden')]:1};
  const getter=Object.defineProperty({},'x',{enumerable:true,get(){throw Error('getter invoked');}});
  const hidden=Object.defineProperty({},'x',{value:1});
  const decorated=[];decorated.extra=1;
  const bad=[undefined,()=>{},Symbol('x'),1n,NaN,Infinity,-Infinity,cycle,new Date(),new Map(),
    new Set(),/x/,new Uint8Array(2),symbolKey,getter,hidden,new Array(2),decorated,{toJSON(){return {};}}];
  for(const value of bad) await assert.rejects(f.store.save(event({value})), /JSON|Cyclic|Sparse|enumerable|Symbol/);
  for(const input of [null,{},event([]),{...event(),type:''},{...event(),source:{kind:'other',name:'x'}},
    {...event(),source:{kind:'hook',name:' '}},{...event(),payload:null}]) await assert.rejects(f.store.save(input));
  assert.deepEqual(fs.readFileSync(f.file),before);
  await f.store.save(event({still:'usable'}));assert.equal((await f.store.load()).length,2);
});
test('shared references are legal JSON without being mistaken for cycles', async t => {
  const f=fixture(t);const shared={a:1};
  await f.store.save(event({a:shared,b:shared}));
  assert.deepEqual((await f.store.load())[0].payload,{a:{a:1},b:{a:1}});
});
test('loads CRLF, trailing JSON whitespace and unterminated valid records in file order', async t => {
  const f=fixture(t);const a=stored({i:1}),b={...stored({i:2}),timestamp:'2020-01-01T00:00:00.000Z'};
  f.write(JSON.stringify(a)+' \r\n'+JSON.stringify(b)+'\t');
  assert.deepEqual(await f.store.load(),[a,b]);
  const before=fs.readFileSync(f.file,'utf8'); const saved=await f.store.save(event({i:3}));
  assert.equal(fs.readFileSync(f.file,'utf8'),before+'\n'+JSON.stringify(saved)+'\n');
  assert.deepEqual(await f.store.load(),[a,b,saved]);
});
test('equal timestamps preserve physical order', async t => {
  const f=fixture(t);f.write(JSON.stringify(stored({i:2}))+'\n'+JSON.stringify(stored({i:1}))+'\n');
  assert.deepEqual((await f.store.load()).map(x=>x.payload.i),[2,1]);
});
for(const [name,text,line] of [
  ['broken final',JSON.stringify(stored())+'\n{"partial":',2],
  ['broken final with LF',JSON.stringify(stored())+'\nbroken\n',2],
  ['bad earlier record','broken\n'+JSON.stringify(stored())+'\n',1],
  ['invalid shape','{}\n',1],
  ['invalid timestamp',JSON.stringify({...stored(),timestamp:'2026-02-30T00:00:00.000Z'})+'\n',1],
  ['blank record',JSON.stringify(stored())+'\n\n',2],
]) test(`load and save reject ${name}, preserve bytes and report file/line`, async t => {
  const f=fixture(t);f.write(text);
  for(const operation of [()=>f.store.load(),()=>f.store.save(event())]) {
    await assert.rejects(operation(),error=>error.message.includes(f.file)&&error.message.endsWith(`line ${line}`));
    assert.equal(fs.readFileSync(f.file,'utf8'),text);
  }
});
test('read/write failures reject and queue recovers after transient failure', async t => {
  const f=fixture(t); await f.store.save(event());
  const realRead=fsp.readFile,realAppend=fsp.appendFile;
  t.after(()=>{fsp.readFile=realRead;fsp.appendFile=realAppend;});
  fsp.readFile=async()=>{throw Object.assign(Error('denied'),{code:'EACCES'});};
  await assert.rejects(f.store.load(),{code:'EACCES'});
  await assert.rejects(f.store.save(event()),{code:'EACCES'});
  fsp.readFile=realRead;
  const before=fs.readFileSync(f.file);
  fsp.appendFile=async()=>{throw Object.assign(Error('disk full'),{code:'ENOSPC'});};
  await assert.rejects(f.store.save(event()),{code:'ENOSPC'});
  assert.deepEqual(fs.readFileSync(f.file),before);
  fsp.appendFile=realAppend;
  await f.store.save(event());assert.equal((await f.store.load()).length,2);
});
test('partial append failure is surfaced and subsequent saves reject damaged history', async t => {
  const f=fixture(t); await f.store.save(event()); const realAppend=fsp.appendFile;
  t.after(()=>{fsp.appendFile=realAppend;});
  fsp.appendFile=async(file)=>{fs.appendFileSync(file,'{"partial":');throw Error('interrupted');};
  await assert.rejects(f.store.save(event()),/interrupted/);fsp.appendFile=realAppend;
  const damaged=fs.readFileSync(f.file);
  await assert.rejects(f.store.save(event()),/line 2/);
  assert.deepEqual(fs.readFileSync(f.file),damaged);
});
test('sparse array with a numeric non-index property rejects without losing data', async t => {
  const f=fixture(t);const value=new Array(1);value['4294967295']=42;
  await assert.rejects(f.store.save(event({value})),/JSON|array/i);
  assert.equal(fs.existsSync(f.file),false);
});
test('invalid UTF-8 inside a JSON string rejects load/save with file and line; bytes intact', async t => {
  const f=fixture(t);f.write(JSON.stringify(stored())+'\n');
  const damaged=Buffer.concat([fs.readFileSync(f.file),Buffer.from(JSON.stringify(stored({text:'MARKER'})).replace('MARKER','')),]);
  const offset=damaged.indexOf(Buffer.from('"text":"'))+8;
  const bytes=Buffer.concat([damaged.subarray(0,offset),Buffer.from([0xff]),damaged.subarray(offset)]);
  fs.writeFileSync(f.file,bytes);
  for(const op of [()=>f.store.load(),()=>f.store.save(event())]) {
    await assert.rejects(op(),e=>e.message.includes(f.file)&&e.message.includes('line 2'));
    assert.deepEqual(fs.readFileSync(f.file),bytes);
  }
});
