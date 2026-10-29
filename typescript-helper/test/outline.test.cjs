const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {spawnSync} = require('node:child_process');
const {outline} = require('../dist/index.js');
function fixture(text) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'laya-ts-'));
  const file = path.join(dir, 'source file.ts');
  fs.writeFileSync(file, text);
  return {dir, file};
}
test('ordinary functions preserve signature and UTF16 locations, not text lookalikes', () => {
  const text = '// 😀\r\nexport function greet(name: string): string { return name; }\r\nconst s="function fake() {}";';
  const {file,dir} = fixture(text);
  try {
    const result = outline(file);
    assert.equal(result.schema_version, 1);
    assert.equal(result.path, file);
    assert.match(result.source_hash, /^[0-9a-f]{64}$/);
    assert.equal(result.callables.length, 1);
    const f = result.callables[0];
    assert.equal(f.name, 'greet');
    assert.equal(f.signature, 'export function greet(name: string): string');
    assert.equal(f.start, text.indexOf('export'));
    assert.equal(f.end, text.indexOf('}') + 1);
    assert.deepEqual(f.location, {line:2,column:1});
    assert.equal(result.diagnostics.length, 0);
    assert.ok(result.limitations.length > 0);
  } finally { fs.rmSync(dir,{recursive:true}); }
});
test('empty and malformed source', () => {
  const {file,dir} = fixture('');
  try {
    assert.deepEqual(outline(file).callables, []);
    fs.writeFileSync(file, 'function broken( {');
    assert.throws(() => outline(file), /parse/i);
  } finally { fs.rmSync(dir,{recursive:true}); }
});
test('unsupported callable forms remain visible diagnostics', () => {
  const text = 'function outer() { function inner() {} }\nclass C { m() {} }\nconst a=()=>1;\nasync function af() {}\nfunction* gen() {}\nfunction ov(x:string):void; function ov(x:any) {}';
  const {file,dir} = fixture(text);
  try {
    const result = outline(file);
    assert.deepEqual(result.callables.map(f=>f.name), ['outer','m','a']);
    for (const name of ['inner','af','gen','ov']) assert.ok(result.diagnostics.some(d=>d.message.includes(name)), name);
    assert.ok(result.callables.some(c=>c.signature==='a=()=>'));
    assert.equal(result.diagnostics.length, 5);
  } finally { fs.rmSync(dir,{recursive:true}); }
});
test('JSON CLI parses without executing source and validates requests', () => {
  const {file,dir} = fixture('require("node:fs").writeFileSync("marker", "bad"); function safe() {}');
  try {
    const cli = path.resolve(__dirname, '../dist/cli.js');
    const run = input => spawnSync(process.execPath,[cli],{cwd:dir,input,encoding:'utf8'});
    const ok = run(JSON.stringify({action:'outline',path:file}));
    assert.equal(ok.status,0); assert.equal(ok.stderr,'');
    assert.equal(JSON.parse(ok.stdout).callables[0].name,'safe');
    assert.equal(fs.existsSync(path.join(dir,'marker')),false);
    for (const input of ['oops','{}',JSON.stringify({action:'execute',path:file}),JSON.stringify({action:'outline',path:file+'missing'})]) {
      const bad=run(input); assert.notEqual(bad.status,0); assert.equal(bad.stdout,''); assert.ok(bad.stderr.length);
    }
  } finally { fs.rmSync(dir,{recursive:true}); }
});
