const {test}=require('node:test'); const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),os=require('node:os');
const {outline,extractCallable}=require('../dist/index.js');
for(const newline of ['\n','\r\n']) test('exact source slice '+JSON.stringify(newline),()=>{
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),'laya-extract-')), file=path.join(dir,'a.ts');
  const code='export function f() {\n  return "😀"; /*inside*/\n}'.replaceAll('\n',newline);
  const source='// 🙃\n/**leading*/\n'.replaceAll('\n',newline)+code+' //trailing';
  fs.writeFileSync(file,source);
  try {
    const candidate=outline(file).callables[0], result=extractCallable(file,candidate.id);
    assert.equal(result.code,code);
    assert.equal(result.code,source.slice(candidate.start,candidate.end));
    assert.equal(result.callable.location.line,3);
    assert.equal(fs.readFileSync(file,'utf8'),source);
    assert.throws(()=>extractCallable(file,'bad'),/stale|unknown/i);
    fs.writeFileSync(file,source+'\n//changed');
    assert.throws(()=>extractCallable(file,candidate.id),/stale|unknown/i);
  } finally { fs.rmSync(dir,{recursive:true}); }
});
