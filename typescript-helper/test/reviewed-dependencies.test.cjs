const {test}=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const {outline,collectLocalContext,collectProjectContext}=require('../../build/typescript/index.js');

function fixture(source,run){
  const root=fs.mkdtempSync(path.join(os.tmpdir(),'laya-reviewed-')),file=path.join(root,'main.ts');
  fs.writeFileSync(file,source);
  fs.writeFileSync(path.join(root,'dep.ts'),'export const original=42;');
  fs.writeFileSync(path.join(root,'tsconfig.json'),JSON.stringify({compilerOptions:{module:'commonjs',moduleResolution:'node'},include:['*.ts']}));
  try{run(file,root);}finally{fs.rmSync(root,{recursive:true});}
}

for(const project of [false,true]){
  const mode=project?'project':'local';
  const collect=(file,root,name='chosen',options={})=>{
    const id=outline(file).callables.find(c=>c.name===name).id;
    return project?collectProjectContext(file,id,{repositoryRoot:root,...options}):collectLocalContext(file,id,options);
  };
  test(mode+' shorthand respects shadows, deduplicates references and matches explicit properties',()=>{
    fixture('const value=42; const shadow=99; function chosen(shadow:number){return [{value,shadow},{value},{explicit:value}];} function explicit(){return {value:value};}',(file,root)=>{
      const result=collect(file,root),explicit=collect(file,root,'explicit');
      assert.deepEqual(result.dependencies.map(d=>d.code),['const value=42;']);
      assert.deepEqual(result.dependencies,explicit.dependencies);
      assert.equal(result.collection.dependency_chars,'const value=42;'.length);
      assert.ok(!result.gaps.some(g=>g.code==='closure_capture'));
    });
    fixture('const value=42; function chosen(){const value=7; return {value};}',(file,root)=>{
      assert.deepEqual(collect(file,root).dependencies,[]);
    });
  });
  test(mode+' shorthand import aliases retain provenance and obey source budgets',()=>{
    const imported='import {original as value} from "./dep";';
    fixture(imported+' function chosen(){return [{value},{value}];}',(file,root)=>{
      const result=collect(file,root),codes=result.dependencies.map(d=>d.code);
      assert.equal(codes.filter(c=>c===imported).length,1);
      assert.equal(codes.filter(c=>c==='export const original=42;').length,project?1:0);
      for(const d of result.dependencies)assert.ok(d.symbol_ids.length);
      const size=result.dependencies.reduce((n,d)=>n+d.code.length,0);
      assert.equal(result.collection.dependency_chars,size);
      assert.deepEqual(collect(file,root,'chosen',{maxDependencyChars:size}).dependencies,result.dependencies);
      for(const [options,code]of [[{maxDepth:0},'depth_limit'],[{maxDependencyChars:1},'size_limit']]){
        const limited=collect(file,root,'chosen',options);
        assert.deepEqual(limited.dependencies,[]);
        assert.ok(limited.gaps.some(g=>g.code===code));
      }
    });
  });
  test(mode+' bodyless declaration context has an implementation gap and respects budgets',()=>{
    for(const declaration of ['declare function value():number;','function value():number;','declare const value:number;','declare class value {}']){
      fixture(declaration+' function chosen(){return {value};}',(file,root)=>{
        const result=collect(file,root);
        assert.deepEqual(result.dependencies.map(d=>d.code),[declaration]);
        assert.ok(result.gaps.some(g=>g.code==='declaration_only'));
        for(const [options,code]of [[{maxDepth:0},'depth_limit'],[{maxDependencyChars:1},'size_limit']]){
          const limited=collect(file,root,'chosen',options);
          assert.deepEqual(limited.dependencies,[]);
          assert.ok(limited.gaps.some(g=>g.code===code));
          assert.ok(limited.gaps.some(g=>g.code==='declaration_only'));
        }
      });
    }
  });
  test(mode+' implemented functions and overloads do not report declaration-only gaps',()=>{
    for(const prefix of ['', 'function value(x:number):number;']){
      fixture(prefix+' function value(x:number){return x;} function chosen(){return value(1);}',(file,root)=>{
        const result=collect(file,root);
        assert.ok(result.dependencies.some(d=>d.code==='function value(x:number){return x;}'));
        assert.ok(!result.gaps.some(g=>g.code==='declaration_only'));
      });
    }
  });
}
