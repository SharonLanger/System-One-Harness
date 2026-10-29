const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs'), os = require('node:os'), path = require('node:path');
const {createHash} = require('node:crypto');
const {outline, extractCallable} = require('../dist/index.js');
// Independently specified synthetic source units: no implementation generates this oracle.
const members = [
  ['constructor', 'constructor(public value: number)', 'constructor(public value: number) { /* 😀 */ }'],
  ['same', 'public same(x: number): number', 'public same(x: number): number { return x; }'],
  ['same', 'static same(): number', 'static same(): number { return 2; }'],
  ['secret', 'private secret(): void', 'private secret(): void {}'],
  ['#hidden', '#hidden(): void', '#hidden(): void {}'],
  ['guarded', 'protected guarded(): void', 'protected guarded(): void {}'],
  ['valueOf', 'get valueOf(): number', 'get valueOf(): number { return this.value; }'],
  ['valueOf', 'set valueOf(x: number)', 'set valueOf(x: number) { this.value = x; }'],
  ['fetch', 'async fetch(): Promise<number>', 'async fetch(): Promise<number> { return 1; }'],
  ['items', '*items()', '*items() { yield 1; }'],
  ['stream', 'async *stream()', 'async *stream() { yield 1; }'],
  ['decorated', '@trace\n  public decorated(): void', '@trace\n  public decorated(): void {\n    // interior 🙃\n  }'],
  ['over', 'over(x: unknown): unknown', 'over(x: unknown): unknown { return x; }'],
];
for (const newline of ['\n', '\r\n']) test('class callable matrix and source fidelity '+JSON.stringify(newline), () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'laya-class-')), file = path.join(dir, 'a.ts');
  const units = members.map(([name, signature, raw]) => [name, signature.replaceAll('\n', newline), raw.replaceAll('\n', newline)]);
  const text = ('// 😀 prefix\nexport class Example {\n  /** attached excluded */\n  '+units.map(x=>x[2]).join(newline+'  ')+
    '\n}\nclass Other { same() { return 3; } }\nabstract class Abstract { abstract absent(): void; }\ndeclare class Ambient { declared(): void; }\n').replace(/(?<!\r)\n/g, newline);
  // Add overload signatures before their implementation without treating them as bodies.
  const source = text.replace('over(x: unknown)', 'over(x: string): string;'+newline+'  over(x: number): number;'+newline+'  over(x: unknown)');
  fs.writeFileSync(file, source);
  try {
    const result = outline(file), expected = [...units, ['same', 'same()', 'same() { return 3; }']];
    assert.deepEqual(result.callables.map(x=>x.name), expected.map(x=>x[0]));
    assert.equal(new Set(result.callables.map(x=>x.id)).size, expected.length);
    assert.equal(result.source_hash, createHash('sha256').update(source).digest('hex'));
    for (const [index, c] of result.callables.entries()) {
      const [name, signature, raw] = expected[index];
      assert.equal(c.signature, signature, name);
      assert.equal(c.start, source.indexOf(raw));
      assert.equal(c.end, c.start + raw.length);
      assert.equal(c.id, `${result.source_hash}:${c.start}:${c.end}`);
      const prefix = source.slice(0, c.start).split(/\r\n|\r|\n/);
      assert.deepEqual(c.location, {line: prefix.length, column: prefix.at(-1).length+1});
      const extracted = extractCallable(file, c.id);
      assert.equal(extracted.code, raw);
      assert.equal(extracted.code, source.slice(c.start,c.end));
      assert.deepEqual(extracted.callable,c);
      assert.equal(extracted.display_code,raw.split(/\r\n|\r|\n/).map((line,i)=>`${c.location.line+i}: ${line}`).join('\n'));
    }
    assert.equal(result.diagnostics.length, 4);
    for (const fragment of ['over(x: string): string;', 'over(x: number): number;', 'abstract absent(): void;', 'declared(): void;']) {
      const d = result.diagnostics.find(d=>source.slice(d.start,d.end)===fragment);
      assert.ok(d, fragment); assert.equal(d.code,'unsupported_callable');
      assert.throws(()=>extractCallable(file,`${result.source_hash}:${d.start}:${d.end}`), /unknown/);
    }
    assert.equal(fs.readFileSync(file,'utf8'),source);
    fs.appendFileSync(file,'// changed');
    assert.throws(()=>extractCallable(file,result.callables[0].id), /stale|unknown/);
  } finally { fs.rmSync(dir,{recursive:true}); }
});
test('class coverage keeps deferred forms diagnostic and parser errors fatal', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'laya-class-')), file = path.join(dir, 'a.ts');
  try {
    fs.writeFileSync(file, 'class C { field=()=>1; [key]() {} } const C2=class { m() {} }; function f() { class Nested { n() {} } }');
    const result=outline(file);
    assert.deepEqual(result.callables.map(x=>x.name),['f']);
    assert.equal(result.diagnostics.length,4);
    fs.writeFileSync(file, 'class C { broken( {');
    assert.throws(()=>outline(file), /parse/i);
  } finally { fs.rmSync(dir,{recursive:true}); }
});
test('ordinary escaped names keep semantic identity while member names keep source spelling', () => {
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),'laya-names-')), file=path.join(dir,'a.ts');
  const source=String.raw`function \u0066() {} class C { \u006d() {} }`;
  fs.writeFileSync(file,source);
  try {
    const result=outline(file);
    assert.deepEqual(result.callables.map(c=>c.name),['f', String.raw`\u006d`]);
    assert.deepEqual(result.callables.map(c=>c.signature),[String.raw`function \u0066()`,String.raw`\u006d()`]);
    assert.equal(extractCallable(file,result.callables[0].id).code,String.raw`function \u0066() {}`);
  } finally { fs.rmSync(dir,{recursive:true}); }
});
