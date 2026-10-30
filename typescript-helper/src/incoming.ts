import ts from 'typescript';
import {readFileSync,realpathSync,statSync} from 'node:fs';
import {resolve,relative,isAbsolute,sep,dirname} from 'node:path';
import {readOutline,Diagnostic} from './index';
export interface IncomingSite {path:string;start_line:number;start_column:number;end_line:number;end_column:number}
export interface IncomingCaller {kind:'method'|'module';path:string;callable_id:string|null;name:string|null;start_line:number;end_line:number;call_sites:IncomingSite[]}
export interface IncomingLocations {status:'ok'|'partial'|'error';data:{callers:IncomingCaller[];scope:{tsconfig_path:string;searched_files:string[];limits:string[];omissions:string[]}}|null;diagnostics:Diagnostic[]}
export function getCallingMethodLocations(path:string,id:string,options:{projectRoot:string;tsconfigPath:string}):IncomingLocations {
 let service:ts.LanguageService|undefined;
 const diagnostics:Diagnostic[]=[];const gap=(code:string,message:string)=>diagnostics.push({code,message,start:0,end:0});
 try{
 if(!options||typeof options.projectRoot!=='string'||!isAbsolute(options.projectRoot))throw Error('Project root must be explicit and absolute');
 const root=realpathSync(options.projectRoot);if(!statSync(root).isDirectory())throw Error('Project root must be a directory');
 const inside=(p:string)=>{const r=relative(root,p);return !isAbsolute(r)&&r!=='..'&&!r.startsWith('..'+sep);};
 const canonical=(p:string)=>{const a=resolve(root,p);if(!inside(a))throw Error('Path escapes project root');const r=realpathSync(a);if(!inside(r))throw Error('Symlink escapes project root');return r;};
 const display=(p:string)=>relative(root,p).split(sep).join('/');
 if(typeof path!=='string'||!path||typeof id!=='string'||!id)throw Error('Source path and callable ID required');
 if(typeof options.tsconfigPath!=='string'||!options.tsconfigPath)throw Error('Explicit tsconfig path required');
 const file=canonical(path),config=canonical(options.tsconfigPath),main=readOutline(file),selected=main.outline.callables.find(c=>c.id===id);if(!selected)throw Error('Stale or unknown callable ID');
 const compilerLib=dirname(ts.getDefaultLibFilePath({}));
 const trustedLib=(p:string)=>dirname(resolve(p))===compilerLib&&/^lib\..*\.d\.ts$/.test(p.split(sep).pop()??'');
 const readable=(p:string)=>trustedLib(p)?resolve(p):canonical(p);
 const safeRead=(p:string)=>{try{return readFileSync(readable(p),'utf8');}catch{return undefined;}};
 const exists=(p:string)=>{try{return statSync(readable(p)).isFile();}catch{return false;}};
 const configHost:ts.ParseConfigFileHost={...ts.sys,readFile:safeRead,fileExists:exists,getCurrentDirectory:()=>root,onUnRecoverableConfigFileDiagnostic:d=>{throw Error(ts.flattenDiagnosticMessageText(d.messageText,' '));},readDirectory:(...args)=>ts.sys.readDirectory(...args).filter(p=>{try{return inside(realpathSync(p));}catch{return false;}})};
 const parsed=ts.getParsedCommandLineOfConfigFile(config,{},configHost);if(!parsed||parsed.errors.length)throw Error('Invalid project configuration');
 const omissions:string[]=[];
 if(parsed.projectReferences?.length){gap('project_references','Referenced projects are not traversed.');omissions.push('Referenced project configurations');}
 const sources=new Map<string,string>();
 const load=(p:string)=>{try{const r=readable(p);if(r.split(sep).includes('node_modules')&&!trustedLib(r)){gap('omitted_dependency','Package type sources are outside supported incoming coverage.');omissions.push(display(r));return undefined;}if(sources.has(r))return sources.get(r);if(!r.endsWith('.ts')){if(/\.[cm]?[jt]sx?$/.test(r)){gap('unsupported_source','Only .ts sources are supported.');omissions.push(display(r));}return undefined;}if(sources.size>=512||statSync(r).size>4000000){gap('budget_exhausted','File or byte budget exhausted');omissions.push(display(r));return undefined;}const s=readFileSync(r,'utf8');sources.set(r,s);return s;}catch{return undefined;}};
 const host:ts.LanguageServiceHost={getCompilationSettings:()=>parsed.options,getScriptFileNames:()=>parsed.fileNames,getScriptVersion:()=> '0',getScriptSnapshot:p=>{const s=load(p);return s===undefined?undefined:ts.ScriptSnapshot.fromString(s);},getCurrentDirectory:()=>root,getDefaultLibFileName:()=>ts.getDefaultLibFilePath(parsed.options),fileExists:exists,readFile:safeRead,readDirectory:(p,e,x,i,d)=>[...configHost.readDirectory(p,e??[],x,i??[],d)],directoryExists:p=>{try{return statSync(canonical(p)).isDirectory();}catch{return false;}},realpath:p=>{try{return canonical(p);}catch{return p;}}};
 service=ts.createLanguageService(host);const program=service.getProgram();if(!program)throw Error('Compiler project unavailable');const sf=program.getSourceFile(file);if(!sf)throw Error('Selected source outside configured project');
 if(sources.get(file)!==main.source)throw Error('Source changed during analysis');
 const checker=program.getTypeChecker();let target:ts.Node|undefined;
 const find=(n:ts.Node)=>{if(n.getStart(sf)===selected.start&&n.end===selected.end)target=n;ts.forEachChild(n,find);};find(sf);if(!target)throw Error('Unsupported selected callable');
 const symbolAt=(n:ts.Node)=>{let s=checker.getSymbolAtLocation(n);if(s&&(s.flags&ts.SymbolFlags.Alias))s=checker.getAliasedSymbol(s);return s;};
 const declaration=target as ts.FunctionLikeDeclaration;
 const targetSymbol=symbolAt(declaration.name??(ts.isVariableDeclaration(target.parent)||ts.isPropertyDeclaration(target.parent)||ts.isPropertyAssignment(target.parent)?target.parent.name:target));
 if(!targetSymbol)gap('unsupported_target','No statically addressable target symbol');
 // Compiler call hierarchy owns relationship discovery. AST traversal only expands
 // its name spans to complete invocation spans and normalizes callback ownership.
 const hierarchyName=declaration.name??(ts.isVariableDeclaration(target.parent)||ts.isPropertyDeclaration(target.parent)||ts.isPropertyAssignment(target.parent)?target.parent.name:undefined);
 const prepared=service.prepareCallHierarchy(file,hierarchyName?.getStart(sf)??target.getStart(sf));
 const incoming=new Map<string,ts.TextSpan[]>();
 for(const item of prepared?(Array.isArray(prepared)?prepared:[prepared]):[]){
  for(const relation of service.provideCallHierarchyIncomingCalls(item.file,item.selectionSpan.start)){
   let callerFile:string;try{callerFile=canonical(relation.from.file);}catch{gap('external_caller','Call hierarchy caller lies outside project confinement');continue;}
   incoming.set(callerFile,[...(incoming.get(callerFile)??[]),...relation.fromSpans]);
  }
 }
 if(!prepared)gap('unsupported_hierarchy_target','Compiler call hierarchy cannot prepare this callable target.');
 const callers=new Map<string,IncomingCaller>(),searched:string[]=[];
 for(const source of program.getSourceFiles()){
 if(!inside(source.fileName)||source.isDeclarationFile||!sources.has(source.fileName))continue;
 let snapshot:ReturnType<typeof readOutline>;try{snapshot=readOutline(source.fileName);}catch{gap('parse_error','Unparseable source omitted: '+display(source.fileName));omissions.push(display(source.fileName));searched.push(display(source.fileName));continue;}if(snapshot.source!==sources.get(source.fileName))throw Error('Source changed during analysis');searched.push(display(source.fileName));
 if(program.getSyntacticDiagnostics(source).length)gap('parse_error','Syntax errors in '+display(source.fileName));
 for(const d of program.getSemanticDiagnostics(source))if([2307,2792,7016].includes(d.code))gap('unresolved_import','Unresolved import in '+display(source.fileName));
 const visit=(node:ts.Node)=>{
 if(ts.isNewExpression(node)||ts.isTaggedTemplateExpression(node))gap('unsupported_call_form','Constructor and tagged-template invocations are outside supported incoming coverage.');
 if(ts.isCallExpression(node)&&ts.isElementAccessExpression(node.expression))gap('dynamic_target','Computed invocations may hide indirect callers.');
 if(ts.isCallExpression(node)){const e=node.expression;const spans=incoming.get(source.fileName)??[];const related=spans.some(span=>span.start>=e.getStart(source)&&span.start+span.length<=e.end);if(related){
 if(ts.isPropertyAccessExpression(e)&&ts.isMethodDeclaration(target!)){const receiver=checker.getSymbolAtLocation(e.expression);if(receiver?.declarations?.some(d=>ts.isParameter(d)))gap('dynamic_dispatch','Parameter receiver establishes a static declaration, not runtime dispatch.');}
 if(ts.isElementAccessExpression(e))gap('dynamic_target','Computed invocation not proven');else{
 const containers=snapshot.outline.callables.filter(c=>c.start<=node.getStart(source)&&c.end>=node.end);
 const caller=containers.filter(c=>!c.name.startsWith('<anonymous')).sort((a,b)=>(a.end-a.start)-(b.end-b.start))[0];
 let statement:ts.Node=node;while(statement.parent&&!ts.isSourceFile(statement.parent))statement=statement.parent;
 const start=caller?.start??statement.getStart(source),end=caller?.end??statement.end,p=display(source.fileName),key=p+':'+start+':'+end;
 let record=callers.get(key);if(!record){record={kind:caller?'method':'module',path:p,callable_id:caller?.id??null,name:caller?.name??null,start_line:source.getLineAndCharacterOfPosition(start).line+1,end_line:source.getLineAndCharacterOfPosition(Math.max(start,end-1)).line+1,call_sites:[]};callers.set(key,record);}
 const a=source.getLineAndCharacterOfPosition(node.getStart(source)),b=source.getLineAndCharacterOfPosition(node.end);record.call_sites.push({path:p,start_line:a.line+1,start_column:a.character+1,end_line:b.line+1,end_column:b.character+1});
 if(!caller&&containers.length)gap('unsupported_caller','Anonymous scope has no extractable named caller');
 }}}
 if(targetSymbol&&ts.isIdentifier(node)&&symbolAt(node)===targetSymbol){const p=node.parent;if(ts.isPropertyAccessExpression(p)&&p.expression===node&&['call','apply','bind'].includes(p.name.text))gap('indirect_call_form','Function call/apply/bind references may hide runtime invocation relationships.');if((ts.isVariableDeclaration(p)&&p.initializer===node)||ts.isReturnStatement(p)||ts.isBinaryExpression(p)||(ts.isCallExpression(p)&&p.expression!==node))gap('function_value_escape','Target used as a value; indirect runtime callers are outside static coverage.');}
 ts.forEachChild(node,visit);};visit(source);
 }
 for(const [p,s]of sources)if(readFileSync(p,'utf8')!==s)throw Error('Source changed during analysis');
 const unique=[...new Map(diagnostics.map(d=>[d.code+':'+d.message,d])).values()];
 return {status:unique.length?'partial':'ok',data:{callers:[...callers.values()].sort((a,b)=>a.path.localeCompare(b.path)||a.start_line-b.start_line||a.call_sites[0].start_column-b.call_sites[0].start_column),scope:{tsconfig_path:display(config),searched_files:searched.sort(),limits:['Single configured .ts project; static declaration targets only.','512 files; 4000000 bytes per file.'],omissions:[...new Set(omissions)].sort()}},diagnostics:unique};
 }catch(error){const message=error instanceof Error?error.message:String(error);return {status:'error',data:null,diagnostics:[{code:/Stale/.test(message)?'stale_id':/changed/.test(message)?'snapshot_changed':'project_error',message,start:0,end:0}]};}finally{service?.dispose();}
}
