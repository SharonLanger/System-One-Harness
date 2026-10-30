const {test}=require('node:test'), assert=require('node:assert/strict');
const fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const {outline}=require('../dist/index.js');
const {getCalledMethodLocations,listCalledCallables}=require('../dist/calls.js');
function fixture(source,run,files={}) {
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'laya-navigation-'));
 fs.writeFileSync(path.join(root,'tsconfig.json'),JSON.stringify({compilerOptions:{module:'commonjs',moduleResolution:'node',baseUrl:'.',paths:{'@dep':['dep']}},include:['*.ts']}));
 for(const [name,text] of Object.entries({'main.ts':source,...files})) fs.writeFileSync(path.join(root,name),text);
 const file=path.join(root,'main.ts'), id=outline(file).callables.find(c=>c.name==='chosen').id;
 try {run(getCalledMethodLocations?.('main.ts',id,{projectRoot:root}),root,file,id);}finally{fs.rmSync(root,{recursive:true,force:true});}
}
test('O01 O07 S01 S02 same-file definitions and distinct UTF-16 call spans',()=>{
 fixture('function work() {\n return 1;\n}\nfunction chosen(){ "😀"; work(); work(\n); }',(r,root,file,id)=>{
 assert.equal(r.status,'ok');assert.equal(r.data.methods.length,1);
 const m=r.data.methods[0]; assert.equal(m.path,'main.ts');assert.equal(m.name,'work');assert.equal(m.start_line,1);assert.equal(m.end_line,3);
 assert.deepEqual(m.call_sites,[{path:'main.ts',start_line:4,start_column:26,end_line:4,end_column:32},{path:'main.ts',start_line:4,start_column:34,end_line:5,end_column:2}]);
 assert.equal(m.callable_id,outline(file).callables.find(c=>c.name==='work').id);
 assert.deepEqual(Object.keys(listCalledCallables(file,id,{repositoryRoot:root}).data.calls[0]).sort(),['id','name','path','signature']);
 });
});
for(const [name,imp,call] of [['named','import {work} from "./dep";','work()'],['default','import work from "./dep";','work()'],['namespace','import * as dep from "./dep";','dep.work()'],['alias','import {work as renamed} from "@dep";','renamed()'],['barrel','import {work} from "./barrel";','work()']]) test('O02 O03 '+name,()=>fixture(`${imp}\nfunction chosen(){${call};}`,(r)=>{assert.equal(r.status,'ok');assert.deepEqual(r.data.methods.map(m=>m.path),['dep.ts']);},{'dep.ts':'export function work(){}; export default work;','barrel.ts':'export {work} from "./dep";'}));
test('O08 O09 O10 O11 nested scopes and one hop',()=>fixture('function third(){} function work(){third()} function chosen(){ function local(){work()} local(); (()=>work())(); chosen(); }',r=>{assert.equal(r.status,'partial'); assert.deepEqual(r.data.methods.map(m=>m.name),['work']);assert.equal(r.data.methods[0].call_sites.length,2);}));
test('O12 O13 overload implementation and optional invocation',()=>fixture('function work(x:number):number; function work(x:number){return x} function chosen(){work?.(1)}',r=>{assert.equal(r.status,'ok');assert.equal(r.data.methods[0].name,'work');}));
test('O14 O16 values comments and no calls',()=>fixture('function work(){} function chosen(){const x=work; /* work() */ return "work()"}',r=>{assert.equal(r.status,'ok');assert.deepEqual(r.data.methods,[]);}));
for(const [name,source] of [['computed','const obj={work(){}}; function chosen(){obj["work"]()}'],['mutable','let work=()=>{}; work=()=>{}; function chosen(){work()}'],['interface','interface I {work():void} function chosen(i:I){i.work()}'],['constructor','class A{} function chosen(){new A()}'],['tagged','function tag(x:any){} function chosen(){tag`x`}'],['call','function work(){} function chosen(){work.call(null)}'],['apply','function work(){} function chosen(){work.apply(null,[])}'],['bound','function work(){} const bound=work.bind(null); function chosen(){bound()}']]) test('O17 O19 explicit limitation '+name,()=>fixture(source,r=>{assert.equal(r.status,'partial');assert.ok(r.diagnostics.length);assert.deepEqual(r.data.methods,[]);}));
test('S04 stale IDs and relative roots are errors',()=>fixture('function chosen(){}',(r,root)=>{assert.equal(getCalledMethodLocations('main.ts','stale',{projectRoot:root}).status,'error');assert.equal(getCalledMethodLocations('main.ts','stale',{projectRoot:'.'}).status,'error');}));
test('O04 O05 static and concrete instance methods retain qualified names',()=>fixture('class A {static same(){}; work(){}} class B {static same(){}} const a=new A(); function chosen(){A.same();a.work()}',r=>{assert.equal(r.status,'ok'); assert.deepEqual(r.data.methods.map(m=>m.name),['A.same','A.work']);}));
test('O06 arrow and function initializers and object methods',()=>fixture('const arrow=()=>{}; const expr=function(){}; const obj={work(){}}; function chosen(){arrow();expr();obj.work()}',r=>{assert.equal(r.status,'ok');assert.equal(r.data.methods.length,3);}));
test('O15 proven library target has explicit external classification',()=>fixture('function chosen(){Math.max(1,2)}',r=>{assert.equal(r.status,'partial');assert.ok(r.diagnostics.some(d=>d.code==='external_library'));assert.deepEqual(r.data.methods,[]);}));
test('O15 project function named Map remains a project implementation',()=>fixture('function Map(){} function chosen(){Map()}',r=>{assert.equal(r.status,'ok');assert.equal(r.data.methods[0].name,'Map');}));
test('O18 overrides do not imply runtime dispatch certainty',()=>fixture('class A { work(){} } class B extends A {work(){}} const b=new B(); function chosen(){b.work()}',r=>{assert.equal(r.status,'partial');assert.ok(r.diagnostics.some(d=>d.code==='uncertain_dispatch'));}));
test('O20 deterministic path and source ordering',()=>fixture('import {z} from "./z"; import {a} from "./a"; function chosen(){z();a();z()}',r=>{assert.deepEqual(r.data.methods.map(m=>m.path),['a.ts','z.ts']);assert.equal(r.data.methods[1].call_sites.length,2);},{'z.ts':'export function z(){}','a.ts':'export function a(){}'}));
