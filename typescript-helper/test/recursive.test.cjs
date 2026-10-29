const {test}=require('node:test'), assert=require('node:assert/strict');
const fs=require('node:fs'), os=require('node:os'), path=require('node:path');
const {outline,extractCallable}=require('../dist/index.js');
function check(file,source,expected,diagnosticCount=0) {
  fs.writeFileSync(file,source);
  const result=outline(file);
  assert.equal(result.callables.length,expected.length);
  assert.equal(result.diagnostics.length,diagnosticCount);
  assert.equal(new Set(result.callables.map(c=>c.id)).size,expected.length);
  let cursor=0;
  for(const [i,c] of result.callables.entries()) {
    const [name,signature,raw]=expected[i];
    const start=source.indexOf(raw,cursor), prefix=source.slice(0,start).split(/\r\n|\r|\n/);
    assert.notEqual(start,-1,raw); cursor=start+1;
    const location={line:prefix.length,column:prefix.at(-1).length+1};
    assert.equal(c.name,name==='<anonymous>'?`<anonymous@${location.line}:${location.column}>`:name);
    assert.equal(c.signature,signature); assert.equal(c.start,start); assert.equal(c.end,start+raw.length);
    assert.deepEqual(c.location,location); assert.equal(c.id,`${result.source_hash}:${start}:${start+raw.length}`);
    const extracted=extractCallable(file,c.id);
    assert.equal(extracted.code,raw); assert.equal(extracted.code,source.slice(c.start,c.end));
    assert.equal(extracted.display_code,raw.split(/\r\n|\r|\n/).map((line,j)=>`${location.line+j}: ${line}`).join('\n'));
  }
  assert.equal(fs.readFileSync(file,'utf8'),source);
  return result;
}
for(const newline of ['\n','\r\n']) test('recursive/special callable matrix '+JSON.stringify(newline),()=>{
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),'laya-recursive-')),file=path.join(dir,'a.ts');
  const outer='function outer() {\n  function same() { return 1; }\n  const local = () => 2;\n  return (() => function nested() { return 3; });\n}';
  const method='method() { class Inner { same() {} field = () => 4; } const obj = { same() {}, fn: function own() {} }; }';
  const units=[
    [outer, [
      ['outer','function outer()',outer], ['same','function same()','function same() { return 1; }'],
      ['local','local = () =>','() => 2'], ['<anonymous>','() =>','() => function nested() { return 3; }'],
      ['nested','function nested()','function nested() { return 3; }']]],
    ['class Outer { '+method+' }',[
      ['method','method()',method], ['same','same()','same() {}'], ['field','field = () =>','() => 4'],
      ['same','same()','same() {}'], ['fn','fn: function own()','function own() {}']]],
    ['async function af() {}', [['af','async function af()','async function af() {}']]],
    ['function* gen() { yield 1; }', [['gen','function* gen()','function* gen() { yield 1; }']]],
    ['async function* agen() { yield 1; }', [['agen','async function* agen()','async function* agen() { yield 1; }']]],
    ['function ov(x: string): string; function ov(x: any) { return x; }', [['ov','function ov(x: any)','function ov(x: any) { return x; }']]],
    [String.raw`function \u0066(x: number): number; function \u0066(x: any) { return x; }`, [['f',String.raw`function \u0066(x: any)`,String.raw`function \u0066(x: any) { return x; }`]]],
    ['export default function () { return "😀"; }', [['<default>','export default function ()','export default function () { return "😀"; }']]],
    ['export default class { constructor() {} get value() { return 1; } field = () => 5; [key]() {} }',[
      ['constructor','constructor()','constructor() {}'], ['value','get value()','get value() { return 1; }'],
      ['field','field = () =>','() => 5'], ['[key]','[key]()','[key]() {}']]],
    ['const literals = { *[Symbol.iterator]() { yield 1; }, ["literal"]: () => 9, [1]() {}, [`template`]() {} };',[
      ['[Symbol.iterator]','*[Symbol.iterator]()','*[Symbol.iterator]() { yield 1; }'],
      ['["literal"]','["literal"]: () =>','() => 9'], ['[1]','[1]()','[1]() {}'],
      ['[`template`]','[`template`]()','[`template`]() {}']]],
    ['const object = { [key]: function () {}, get [other]() { return 1; }, [(() => "computed")()]() {} };',[
      ['[key]','[key]: function ()','function () {}'], ['[other]','get [other]()','get [other]() { return 1; }'],
      ['[(() => "computed")()]','[(() => "computed")()]()','[(() => "computed")()]() {}'],
      ['<anonymous>','() =>','() => "computed"']]],
  ];
  const source=('// 😀 prefix\n'+units.map(x=>x[0]).join('\n')).replaceAll('\n',newline);
  const expected=units.flatMap(x=>x[1]).map(row=>row.map(text=>text.replaceAll('\n',newline)));
  try {
    const result=check(file,source,expected,2);
    assert.ok(result.callables[0].end>result.callables[1].end,'nested ranges may overlap');
    for(const d of result.diagnostics) assert.equal(d.code,'unsupported_callable');
    fs.appendFileSync(file,'// change');
    assert.throws(()=>extractCallable(file,result.callables[0].id), /stale|unknown/);
  } finally {fs.rmSync(dir,{recursive:true});}
});
test('transparent wrappers preserve binding headers and inner callable spans',()=>{
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),'laya-wrapper-')),file=path.join(dir,'a.ts');
  const rows=[
    ['const paren = (() => 1);','paren','paren = (() =>','() => 1'],
    ['const cast = (() => 2) as unknown;','cast','cast = (() =>','() => 2'],
    ['const satisfies = (() => 3) satisfies unknown;','satisfies','satisfies = (() =>','() => 3'],
    ['const nonnull = (() => 4)!;','nonnull','nonnull = (() =>','() => 4'],
    ['const asserted = <unknown>(() => 5);','asserted','asserted = <unknown>(() =>','() => 5'],
    ['const stack = (((() => 6) as unknown) satisfies unknown)!;','stack','stack = (((() =>','() => 6'],
    ['class C { field = (() => 7) as unknown; }','field','field = (() =>','() => 7'],
    ['const object = { [key]: (() => 8) satisfies unknown };','[key]','[key]: (() =>','() => 8'],
  ];
  try {check(file,'// 🙃\r\n'+rows.map(x=>x[0]).join('\r\n'),rows.map(x=>x.slice(1)));}
  finally {fs.rmSync(dir,{recursive:true});}
});
test('inference never crosses calls/conditional/comma/await/new; destructuring stays explicit',()=>{
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),'laya-inference-')),file=path.join(dir,'a.ts');
  const rows=[
    ['const a = choose(() => 1);',[['<anonymous>','() =>','() => 1']]],
    ['const b = true ? () => 2 : function own() {};',[['<anonymous>','() =>','() => 2'],['own','function own()','function own() {}']]],
    ['const c = (0, () => 3);',[['<anonymous>','() =>','() => 3']]],
    ['const d = await (() => 4);',[['<anonymous>','() =>','() => 4']]],
    ['const e = new Builder(() => 5);',[['<anonymous>','() =>','() => 5']]],
    ['export default consume(() => 7);',[['<anonymous>','() =>','() => 7']]],
    ['const {bad} = (() => () => 6);',[['<anonymous>','() =>','() => 6']]],
    ['const [alsoBad] = function () {};',[]],
  ];
  try {
    const result=check(file,rows.map(x=>x[0]).join('\n'),rows.flatMap(x=>x[1]),2);
    assert.ok(result.diagnostics.every(d=>d.message.includes('destructuring')));
  } finally {fs.rmSync(dir,{recursive:true});}
});
test('declaration-only diagnostics/type-only exclusion/computed keys never execute',()=>{
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),'laya-type-')),file=path.join(dir,'a.ts'),marker=path.join(dir,'marker');
  const computed=`[require("fs").writeFileSync(${JSON.stringify(marker)},"bad")]() {}`;
  const source='declare function absent(): void; abstract class C { abstract m(): void; } declare class D { constructor(); get x(): number; } interface I { m(): void; (): number; new(): I; } type F = () => void; type Constructor = new() => I; const object = { '+computed+' };';
  try {
    const result=check(file,source,[[computed.slice(0,-5),computed.slice(0,-3),computed]],4);
    assert.ok(result.limitations.some(x=>x.includes('Type-only')));
    assert.equal(fs.existsSync(marker),false);
    for(const d of result.diagnostics) assert.equal(d.code,'unsupported_callable');
    fs.writeFileSync(file,'class C { [broken( {'); assert.throws(()=>outline(file),/parse/i);
  } finally {fs.rmSync(dir,{recursive:true});}
});
