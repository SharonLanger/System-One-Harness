const {test}=require('node:test'), assert=require('node:assert/strict');
const fs=require('node:fs'), os=require('node:os'), path=require('node:path');
const {outline,extractCallable}=require('../dist/index.js');
const entries=[
  ['arrow','arrow = (x: number) =>','(x: number) => x+1','export const arrow = (x: number) => x+1;'],
  ['block','block: (x: string) => string = (x) =>','(x) => { return x; }','let block: (x: string) => string = (x) => { return x; };'],
  ['publicName','publicName = function inner(x: number)','function inner(x: number) { return x; }','const publicName = function inner(x: number) { return x; };'],
  ['anonymous','anonymous = function ()','function () {}','const anonymous = function () {};'],
  ['fetch','fetch = async () =>','async () => 1','const ignored=42, fetch = async () => 1;'],
  ['gen','gen = function* ()','function* () { yield 1; }','const gen = function* () { yield 1; };'],
  ['stream','stream = async function* ()','async function* () { yield 1; }','const stream = async function* () { yield 1; };'],
  [String.raw`\u0062ound`,String.raw`\u0062ound = () =>`,'() => 2',String.raw`const \u0062ound = () => 2;`],
  ['method','method(x: number)','method(x: number) { return x; }','const objectA={ method(x: number) { return x; },'],
  ['value','get value()','get value() { return 1; }','get value() { return 1; },'],
  ['value','set value(x: number)','set value(x: number) {}','set value(x: number) {},'],
  ['handler','handler: function innerObject()','function innerObject() {}','handler: function innerObject() {},'],
  ['"quoted"','"quoted": () =>','() => 3','"quoted": () => 3,'],
  ['42','42: function ()','function () { return 42; }','42: function () { return 42; },'],
  ['tick','async *tick()','async *tick() { yield 1; }','async *tick() { yield 1; } };'],
  ['method','method()','method() { return 9; }','const objectB={method() { return 9; }};'],
  ['constructor','constructor()','constructor() {}','const Named=class Inner { constructor() {}'],
  ['method','static method()','static method() {}','static method() {}'],
  ['field','readonly field = () =>','() => 4','readonly field = () => 4;'],
  ['#privateField','#privateField = function ()','function () { return 5; }','#privateField = function () { return 5; }; };'],
  ['method','method()','method() { return 6; }','const Anonymous=class { method() { return 6; }'],
  ['field','field = async () =>','async () => 7','field = async () => 7; };'],
  ['field','public field = function named()','function named() { return 8; }','class Declared { public field = function named() { return 8; }; }'],
];
for(const newline of ['\n','\r\n']) test('bound expression/object/class expression matrix '+JSON.stringify(newline),()=>{
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),'laya-expr-')),file=path.join(dir,'a.ts');
  const source=('// 😀 prefix\n'+entries.map(x=>x[3]).join('\n')).replaceAll('\n',newline);
  fs.writeFileSync(file,source);
  try {
    const result=outline(file);
    assert.deepEqual(result.callables.map(c=>c.name),entries.map(x=>x[0]));
    assert.deepEqual(result.diagnostics,[]);
    assert.equal(new Set(result.callables.map(c=>c.id)).size,entries.length);
    let cursor=0;
    for(const [i,c] of result.callables.entries()) {
      const [name,signature,raw]=entries[i], expectedStart=source.indexOf(raw,cursor);
      assert.equal(c.start,expectedStart,name); assert.equal(c.end,c.start+raw.length);
      cursor=c.end;
      assert.equal(c.signature,signature); assert.ok(!c.signature.includes('ignored'));
      assert.equal(c.id,`${result.source_hash}:${c.start}:${c.end}`);
      assert.deepEqual(c.location,{line:source.slice(0,c.start).split(newline).length,column:source.slice(0,c.start).split(newline).at(-1).length+1});
      const extracted=extractCallable(file,c.id);
      assert.equal(extracted.code,raw); assert.equal(extracted.code,source.slice(c.start,c.end));
      assert.deepEqual(extracted.callable,c);
    }
    assert.equal(fs.readFileSync(file,'utf8'),source);
  } finally {fs.rmSync(dir,{recursive:true});}
});
test('binding header comments/newlines are exact, excluded from raw callable',()=>{
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),'laya-binding-')),file=path.join(dir,'a.ts');
  const source='// 😀\r\nconst multiline /*binding*/\r\n : (x: number) => number = /*between*/\r\n (x: number) => { return x; };';
  fs.writeFileSync(file,source);
  try {
    const c=outline(file).callables[0];
    assert.equal(c.name,'multiline');
    assert.equal(c.signature,'multiline /*binding*/\r\n : (x: number) => number = /*between*/\r\n (x: number) =>');
    assert.equal(extractCallable(file,c.id).code,'(x: number) => { return x; }');
    assert.deepEqual(c.location,{line:4,column:2});
  } finally {fs.rmSync(dir,{recursive:true});}
});
test('deferred wrappers/computed/nested binding forms remain diagnostics',()=>{
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),'laya-deferred-')),file=path.join(dir,'a.ts');
  const source='const wrapped=(()=>1); const asserted=(()=>2) as unknown; const sat=(()=>3) satisfies unknown; const nonnull=(()=>4)!; const {bad}=()=>5; const object={ [key]() {}, nested:{ deep() {} }, value:42 }; function outer() { const local=()=>6; const object={m(){}}; } consume(()=>7); const cls=class { [key](){} };';
  fs.writeFileSync(file,source);
  try {
    const result=outline(file);
    assert.deepEqual(result.callables.map(c=>c.name),['outer']);
    assert.equal(result.diagnostics.length,11);
    for(const d of result.diagnostics) assert.equal(d.code,'unsupported_callable');
    fs.writeFileSync(file,'const invalid = { method( {');
    assert.throws(()=>outline(file), /parse/i);
  } finally {fs.rmSync(dir,{recursive:true});}
});
