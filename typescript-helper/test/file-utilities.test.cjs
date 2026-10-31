const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const api = require('../../build/typescript/index.js');

function fixture(t) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'laya-files-'));
  t.after(() => fs.rmSync(root, {recursive:true, force:true}));
  const make = name => { const p=path.join(root,name); fs.mkdirSync(path.dirname(p),{recursive:true}); fs.writeFileSync(p,''); return fs.realpathSync(p); };
  return {root,make};
}
function resolved(reference, root, cwd=root) { return api.resolveReference(reference,cwd,root); }

test('production detector captures full names, duplicates, quotes, spaces and suffix locations', () => {
  const text = 'a.ts a.spec.ts a.test.ts a.d.ts a.tsx a.js a.TS `src/my file.ts`:12:3 a.ts';
  const out=api.detectReferences(text);
  assert.equal(out.status,'ok');
  assert.deepEqual(out.data.references.map(r=>r.path),['a.ts','src/my file.ts','a.ts']);
  for(const ref of out.data.references) assert.equal(text.slice(ref.start,ref.end),ref.path);
  assert.equal(out.data.references[1].filename,'my file.ts');
});
test('detector presets and explicit configuration are case-sensitive and exclusions win', () => {
  const text='a.ts a.spec.ts a.test.ts a.d.ts';
  assert.deepEqual(api.detectReferences(text,{preset:'test'}).data.references.map(r=>r.path),['a.spec.ts','a.test.ts']);
  assert.deepEqual(api.detectReferences('a.ts a.tsx a.js',{include_patterns:['\\.tsx?$'],exclude_patterns:['a\\.ts$']}).data.references.map(r=>r.path),['a.tsx']);
  for(const config of [{include_patterns:['[']},{preset:'unknown'},{include_patterns:'x'},{exclude_patterns:[null]}]) {
    const out=api.detectReferences(text,config); assert.equal(out.status,'error'); assert.equal(out.data,null); assert.equal(out.diagnostics[0].code,'invalid_input');
  }
  assert.deepEqual(api.detectReferences('nothing here').data.references,[]);
});
test('recognition never accepts only the suffix of an excluded filename', () => {
  assert.deepEqual(api.detectReferences('invoice.spec.ts invoice.test.ts invoice.d.ts').data.references,[]);
  assert.deepEqual(api.detectReferences('"src/a.test.ts" `a.d.ts`:9').data.references,[]);
});
test('resolver suffix matches whole components, and generic test files resolve', t => {
  const {root,make}=fixture(t); const first=make('src/service1/invoice-service.ts'); make('src/service2/invoice-service.ts'); make('src/oldservice1/invoice-service.ts');
  assert.equal(resolved('service1/invoice-service.ts',root).data.selected_path,first);
  assert.equal(resolved('src/service1/invoice-service.ts',root).data.selected_path,first);
  assert.equal(resolved('invoice-service.ts',root).data.resolution,'ambiguous');
  const spec=make('src/a.spec.ts'); assert.equal(resolved('a.spec.ts',root).data.selected_path,spec);
  make('legacy/service1/invoice-service.ts'); assert.equal(resolved('service1/invoice-service.ts',root).data.resolution,'ambiguous');
});
test('resolver considers both exact bases, normalizes duplicates and keeps navigation exact-only', t => {
  const {root,make}=fixture(t); const first=make('x.ts'); const other=make('src/x.ts');
  assert.equal(resolved('x.ts',root,path.join(root,'src')).data.resolution,'ambiguous');
  assert.equal(resolved('./x.ts',root,path.join(root,'src')).data.resolution,'ambiguous');
  assert.equal(resolved('x.ts',root).data.selected_path,first);
  assert.equal(resolved('./missing/x.ts',root).data.resolution,'missing');
  assert.equal(resolved('../x.ts',root,path.join(root,'src')).data.selected_path,first);
  assert.equal(resolved(path.join(root,'missing/x.ts'),root).data.resolution,'missing');
  assert.equal(resolved(other,root).data.selected_path,other);
});
test('resolver confines symlinks, skips symlink directories and dependency directories', t => {
  const {root,make}=fixture(t); const outside=fs.mkdtempSync(path.join(os.tmpdir(),'laya-outside-')); t.after(()=>fs.rmSync(outside,{recursive:true,force:true}));
  const secret=path.join(outside,'secret.ts'); fs.writeFileSync(secret,'');
  fs.symlinkSync(secret,path.join(root,'escape.ts')); fs.symlinkSync(outside,path.join(root,'linked'));
  assert.equal(resolved('escape.ts',root).data.resolution,'outside_repository');
  assert.equal(resolved(secret,root).data.resolution,'outside_repository');
  assert.equal(resolved('secret.ts',root).data.resolution,'missing');
  make('node_modules/a/hidden.ts'); make('.git/hidden.ts');
  assert.equal(resolved('hidden.ts',root).data.resolution,'missing');
  const target=make('src/a.test.ts'); fs.symlinkSync(target,path.join(root,'alias.ts'));
  assert.equal(resolved('alias.ts',root).data.selected_path,target);
});
test('resolver rejects invalid inputs and reports scan IO failures without selecting', t => {
  const {root,make}=fixture(t); make('nested/a.ts');
  for(const reference of ['', '  ', 'a\u0000.ts', 'C:\\a.ts']) assert.equal(resolved(reference,root).status,'error');
  assert.equal(api.resolveReference('a.ts',path.dirname(root),root).status,'error');
  const original=fs.readdirSync; fs.readdirSync=()=>{throw Object.assign(new Error('controlled scan failure'),{code:'EACCES'});};
  try { const out=resolved('a.ts',root); assert.equal(out.status,'error'); assert.equal(out.data,null); assert.equal(out.diagnostics[0].code,'io_error'); }
  finally {fs.readdirSync=original;}
});
test('resolver exact access failures and incomplete scans cannot select a plausible candidate', t => {
  const {root,make}=fixture(t); const exact=make('exact.ts'); make('a/found.ts'); make('z/other.ts');
  const stat=fs.statSync;
  fs.statSync=(candidate,...args)=>{if(candidate===exact) throw Object.assign(new Error('denied'),{code:'EACCES'}); return stat(candidate,...args);};
  try { const out=resolved('exact.ts',root); assert.equal(out.status,'error'); assert.equal(out.diagnostics[0].code,'io_error'); }
  finally {fs.statSync=stat;}
  const read=fs.readdirSync;
  fs.readdirSync=(directory,...args)=>{if(directory===path.join(root,'z')) throw Object.assign(new Error('denied subtree'),{code:'EACCES'}); return read(directory,...args);};
  try { const out=resolved('found.ts',root); assert.equal(out.status,'error'); assert.equal(out.data,null); }
  finally {fs.readdirSync=read;}
});
