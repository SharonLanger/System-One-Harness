/** Additive name-based facade. Legacy IDs never cross this public boundary. */
import {realpathSync, statSync} from 'node:fs';
import {resolve, relative, isAbsolute, sep} from 'node:path';
import {outline, extractCallable, Callable} from './index';
import {getCalledMethodLocations} from './calls';
import {getCallingMethodLocations} from './incoming';

type Options = {projectRoot: string; tsconfigPath?: string};
type Outcome = {status: 'ok'|'uncertain'|'ambiguous'|'error'; data: Record<string, unknown>|null; diagnostics: {code:string; message:string}[]};
class Failure extends Error {constructor(public code:string, public status:'error'|'uncertain'|'ambiguous'='error'){super(code);}}
const messages:Record<string,string> = {
 invalid_input:'Provide an absolute project root, relative file path and valid method name.',
 source_error:'Source could not be read or parsed.', method_not_found:'Method was not found.',
 ambiguous_method:'More than one method has this name; selection was skipped.',
 uncertain_navigation:'Static navigation is incomplete; hints were skipped.',
 unaddressable_method:'A related method cannot be selected uniquely by file and name.',
 navigation_error:'Static navigation failed; hints were skipped.'
};
function failed(code:string,status:Outcome['status']='error'):Outcome{return {status,data:null,diagnostics:[{code,message:messages[code]??'The operation could not be completed.'}]};}
function boundary(work:()=>Record<string,unknown>):Outcome {
 try{return {status:'ok',data:work(),diagnostics:[]};}
 catch(e){return e instanceof Failure?failed(e.code,e.status):failed('source_error');}
}
function project(options:Options) {
 if(!options||typeof options.projectRoot!=='string'||!isAbsolute(options.projectRoot))throw new Failure('invalid_input');
 const root=realpathSync(options.projectRoot);if(!statSync(root).isDirectory())throw new Failure('invalid_input');
 const inside=(p:string)=>{const r=relative(root,p);return !isAbsolute(r)&&r!=='..'&&!r.startsWith('..'+sep);};
 const input=(p:string)=>{
  if(typeof p!=='string'||!p||isAbsolute(p)||p.includes('\\')||!inside(resolve(root,p)))throw new Failure('invalid_input');
  const result=realpathSync(resolve(root,p));if(!inside(result)||!statSync(result).isFile())throw new Failure('invalid_input');return result;
 };
 const display=(p:string)=>{const canonical=realpathSync(p);if(!inside(canonical))throw new Failure('invalid_input');return relative(root,canonical).split(sep).join('/');};
 return {root,input,display};
}
function selected(path:string,name:string) {
 if(typeof name!=='string'||!name.trim())throw new Failure('invalid_input');
 const matches=outline(path).callables.filter(c=>c.name===name);
 if(!matches.length)throw new Failure('method_not_found');
 if(matches.length!==1)throw new Failure('ambiguous_method','ambiguous');
 return matches[0];
}
function metadata(path:string,c:Callable,p:ReturnType<typeof project>) {
 const extracted=extractCallable(path,c.id);
 // Occupied source lines, preserving UTF-16 offsets inside TypeScript.
 const breaks=extracted.code.match(/\r\n|[\r\n\u2028\u2029]/g)?.length??0;
 const end=c.location.line+breaks-(/[\r\n\u2028\u2029]$/.test(extracted.code)?1:0);
 return {file:p.display(path),name:c.name,signature:c.signature,start_line:c.location.line,end_line:Math.max(c.location.line,end)};
}
export function listMethods(file:string,options:Options):Outcome{return boundary(()=>{
 const p=project(options),path=p.input(file);return {methods:outline(path).callables.map(c=>metadata(path,c,p))};
});}
export function getMethodImplementation(file:string,name:string,options:Options):Outcome{return boundary(()=>{
 const p=project(options),path=p.input(file),c=selected(path,name);return {method:metadata(path,c,p),code:extractCallable(path,c.id).code};
});}
function navigate(file:string,name:string,options:Options,incoming:boolean):Outcome{return boundary(()=>{
 const p=project(options),path=p.input(file),c=selected(path,name);
 const result=incoming?getCallingMethodLocations(path,c.id,{projectRoot:p.root,tsconfigPath:p.input(options.tsconfigPath as string)}):getCalledMethodLocations(path,c.id,{projectRoot:p.root});
 if(result.status==='partial')throw new Failure('uncertain_navigation','uncertain');
 if(result.status==='error'||!result.data)throw new Failure('navigation_error');
 // Projection always checks public-outline identity, not display-name parsing.
 const data=result.data as unknown as {methods?:{path:string;callable_id:string|null;call_sites:unknown[]}[];callers?:{path:string;callable_id:string|null;call_sites:unknown[]}[];scope?:unknown};
 const entries=(incoming?data.callers:data.methods)!.map(item=>{
  const target=p.input(item.path),list=outline(target).callables;
  const found=list.find(x=>x.id===item.callable_id);
  if(!found||list.filter(x=>x.name===found.name).length!==1)throw new Failure('unaddressable_method','uncertain');
  const sites=item.call_sites as {path:string;start_line:number;start_column:number;end_line:number;end_column:number}[];
  return {...metadata(target,found,p),call_sites:sites.map(s=>({file:p.display(p.input(s.path)),start_line:s.start_line,start_column:s.start_column,end_line:s.end_line,end_column:s.end_column}))};
 });
 return incoming?{callers:entries,scope:data.scope}:{methods:entries};
});}
export function listCalledMethods(file:string,name:string,options:Options):Outcome{return navigate(file,name,options,false);}
export function listCallingMethods(file:string,name:string,options:Options):Outcome{return navigate(file,name,options,true);}
