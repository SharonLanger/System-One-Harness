import ts from 'typescript';
import {readFileSync, realpathSync, statSync, readdirSync} from 'node:fs';
import {dirname, join, relative, resolve, isAbsolute, sep} from 'node:path';
import {readOutline, Diagnostic} from './index';

interface CallTarget {path: string; id: string; name: string; signature: string}
export interface CallList {
  status: 'ok' | 'partial' | 'error'; data: {calls: CallTarget[]} | null;
  diagnostics: Diagnostic[];
}
const compare = (a: string,b: string) => a < b ? -1 : a > b ? 1 : 0;

/** Static external implementation needs across the entire selected block; see README "List called callables". */
export interface CallSite {path:string; start_line:number; start_column:number; end_line:number; end_column:number}
export interface MethodLocation {path:string; callable_id:string; name:string; signature:string; start_line:number; end_line:number; call_sites:CallSite[]}
export interface MethodLocations {status:'ok'|'partial'|'error'; data:{methods:MethodLocation[]}|null; diagnostics:Diagnostic[]}
export function getCalledMethodLocations(path:string,id:string,options:{projectRoot:string}):MethodLocations {
  const methods:MethodLocation[]=[];
  if(!options || typeof options.projectRoot!=='string' || !isAbsolute(options.projectRoot) || typeof path!=='string' || !path || typeof id!=='string' || !id)
    return {status:'error',data:null,diagnostics:[{code:'invalid_input',message:'An absolute project_root, source path and callable ID are required',start:0,end:0}]};
  const result=analyzeCalls(resolve(options.projectRoot,path),id,{repositoryRoot:options.projectRoot},methods);
  return {status:result.status,data:result.data?{methods:methods.sort((a,b)=>compare(a.path,b.path)||a.start_line-b.start_line)}:null,diagnostics:result.diagnostics};
}
export function listCalledCallables(path:string,id:string,options:{repositoryRoot:string}):CallList {
  return analyzeCalls(path,id,options);
}
function analyzeCalls(path: string, id: string, options: {repositoryRoot: string}, locations?:MethodLocation[]): CallList {
  const diagnostics: Diagnostic[] = [];
  try {
    const root = realpathSync(options.repositoryRoot);
    if (!statSync(root).isDirectory()) throw new Error('Repository root must be a directory');
    const inside = (name: string) => {const r=relative(root,name);return !isAbsolute(r)&&r!=='..'&&!r.startsWith('..'+sep);};
    const canonical = (name: string): string | undefined => {
      if (!inside(resolve(name))) return;
      try {const p=realpathSync(name);return inside(p)?p:undefined;} catch {return;}
    };
    const file=canonical(path);
    if(locations&&file&&!file.endsWith('.ts'))throw new Error('Unsupported source kind: only TypeScript .ts files are supported');
    if (!file) throw new Error('Selected source outside repository or missing');
    const main=readOutline(file), selected=main.outline.callables.find(c=>c.id===id);
    if (!selected) throw new Error('Stale or unknown callable ID');
    type Snapshot=ReturnType<typeof readOutline>;
    const snapshots=new Map<string,Snapshot>([[file,main]]);
    const exists=(name:string)=>{const p=canonical(name);return !!p&&statSync(p).isFile();};
    const directoryExists=(name:string)=>{const p=canonical(name);return !!p&&statSync(p).isDirectory();};
    let configPath:string|undefined;
    for(let dir=dirname(file);inside(dir);dir=dirname(dir)) {
      if(exists(join(dir,'tsconfig.json'))){configPath=join(dir,'tsconfig.json');break;}
      if(dir===root)break;
    }
    const gap=(code:string,node:ts.Node|undefined,message:string)=>diagnostics.push({code,message,
      start:node?.getStart(main.sf)??selected.start,end:node?.end??selected.end});
    const configHost:ts.ParseConfigFileHost={
      useCaseSensitiveFileNames:true,getCurrentDirectory:()=>root,
      fileExists:exists,readFile:name=>{const p=canonical(name);return p?readFileSync(p,'utf8'):undefined;},
      // Module resolution is root-only: config's include/exclude discovery is unnecessary.
      readDirectory:()=>[],onUnRecoverableConfigFileDiagnostic:()=>{}
    };
    let invalidConfig=false;
    let compilerOptions:ts.CompilerOptions={module:ts.ModuleKind.CommonJS,moduleResolution:ts.ModuleResolutionKind.Node10};
    if(configPath){
      const parsed=ts.getParsedCommandLineOfConfigFile(configPath,{},configHost);
      if(!parsed||parsed.errors.some(d=>![18002,18003].includes(d.code))) {invalidConfig=true;gap('config_error',undefined,'Invalid project configuration; only same-file calls are resolved.');}
      else {compilerOptions=parsed.options; if(locations&&parsed.projectReferences?.length)gap('project_references',undefined,'Referenced projects are outside this single-project outgoing scope.');}
    } else gap('missing_config',undefined,'No tsconfig.json; compiler default Node10 resolution is used.');
    compilerOptions={...compilerOptions,noLib:!locations,types:[],noResolve:invalidConfig};
    const libDir=dirname(ts.getDefaultLibFilePath(compilerOptions));
    const library=(name:string)=>!!locations&&dirname(name)===libDir&&/^lib(?:\..*)?\.d\.ts$/.test(name.slice(libDir.length+1));
    const load=(name:string):Snapshot|undefined=>{
      const p=canonical(name);
      if(!p||!p.endsWith('.ts')||p.split(sep).includes('node_modules'))return;
      if(snapshots.has(p))return snapshots.get(p);
      if(snapshots.size>=64||statSync(p).size>4000000){if(locations)gap('budget_exhausted',undefined,'Source loading limit reached; coverage is incomplete.');return;}
      try{const s=readOutline(p);snapshots.set(p,s);return s;}catch{if(locations)gap('parse_error',undefined,'Imported source could not be parsed: '+relative(root,p));return;}
    };
    const host:ts.CompilerHost={getSourceFile:name=>library(name)?ts.createSourceFile(name,readFileSync(name,'utf8'),ts.ScriptTarget.Latest,true):load(name)?.sf,getDefaultLibFileName:()=>locations?ts.getDefaultLibFilePath(compilerOptions):'',writeFile:()=>{},
      getCurrentDirectory:()=>root,getCanonicalFileName:name=>canonical(name)??name,useCaseSensitiveFileNames:()=>true,getNewLine:()=> '\n',
      fileExists:name=>library(name)||exists(name),directoryExists:name=>(!!locations&&name===libDir)||directoryExists(name),realpath:name=>canonical(name)??name,
      readFile:name=>{if(library(name))return readFileSync(name,'utf8');const p=canonical(name);return p?(p.endsWith('.json')?readFileSync(p,'utf8'):load(p)?.source):undefined;},
      getDirectories:name=>{const p=canonical(name);return p&&directoryExists(p)?readdirSync(p,{withFileTypes:true}).filter(e=>e.isDirectory()&&!!canonical(join(p,e.name))).map(e=>e.name):[];}
    };
    const checker=ts.createProgram([file],compilerOptions,host).getTypeChecker();
    let selectedNode:ts.Node|undefined;
    const find=(n:ts.Node):void=>{if(n.getStart(main.sf)===selected.start&&n.end===selected.end)selectedNode=n;ts.forEachChild(n,find);};find(main.sf);
    if(!selectedNode)throw new Error('Unsupported selected callable');
    const calls=new Map<string,CallTarget>();
    const located=new Map<string,MethodLocation>();
    const expressionBody=(expression:ts.Expression|undefined):ts.FunctionExpression|ts.ArrowFunction|undefined=>{
      if(!expression)return;
      while(ts.isParenthesizedExpression(expression)||ts.isAsExpression(expression)||ts.isSatisfiesExpression(expression)||ts.isNonNullExpression(expression)||ts.isTypeAssertionExpression(expression))expression=expression.expression;
      return ts.isArrowFunction(expression)||ts.isFunctionExpression(expression)?expression:undefined;
    };
    const implementation=(declaration:ts.Declaration):ts.Node|undefined=>{
      if((ts.isFunctionDeclaration(declaration)||ts.isFunctionExpression(declaration)||ts.isArrowFunction(declaration)||ts.isMethodDeclaration(declaration)||ts.isGetAccessorDeclaration(declaration)||ts.isSetAccessorDeclaration(declaration))&&declaration.body)return declaration;
      if(ts.isVariableDeclaration(declaration)||ts.isPropertyDeclaration(declaration)||ts.isPropertyAssignment(declaration))return expressionBody(declaration.initializer);
    };
    const uncertainReceiver=(expression:ts.Expression, seen=new Set<ts.Node>()):boolean=>{
      if(seen.has(expression))return true;
      seen.add(expression);
      if(expression.kind===ts.SyntaxKind.ThisKeyword)return false;
      if(ts.isParenthesizedExpression(expression)||ts.isAsExpression(expression)||ts.isNonNullExpression(expression))return uncertainReceiver(expression.expression,seen);
      if(ts.isPropertyAccessExpression(expression)&&uncertainReceiver(expression.expression,seen))return true;
      if(!(ts.isIdentifier(expression)||ts.isPropertyAccessExpression(expression)))return true;
      const symbol=checker.getSymbolAtLocation(ts.isPropertyAccessExpression(expression)?expression.name:expression);
      if(locations&&symbol?.declarations?.length&&symbol.declarations.every(d=>library(d.getSourceFile().fileName)))return false;
      return symbol?.declarations?.some(d=>ts.isParameter(d)||
        ((ts.isVariableDeclaration(d)||ts.isPropertyDeclaration(d))&&
          (!d.initializer||(!ts.isObjectLiteralExpression(d.initializer)&&!ts.isClassExpression(d.initializer)&&
            !ts.isNewExpression(d.initializer)&&uncertainReceiver(d.initializer,seen)))))??true;
    };
    const visit=(node:ts.Node):void=>{
      if(ts.isNewExpression(node)) gap('unsupported_constructor',node,'Constructor invocation is not a proven callable implementation target.');
      if(ts.isTaggedTemplateExpression(node))gap('unsupported_call_form',node,'Tagged template invocation is not supported.');
      if(ts.isCallExpression(node)){
        const expression=node.expression;
        if(!(ts.isIdentifier(expression)||ts.isPropertyAccessExpression(expression))){gap('dynamic_target',node,'Indirect/computed invocation cannot be safely resolved.');}
        else if(ts.isPropertyAccessExpression(expression) && uncertainReceiver(expression.expression)) gap('dynamic_receiver',node,'Injected or indirect receiver does not establish a concrete runtime implementation.');
        else {
          let symbol=checker.getSymbolAtLocation(ts.isPropertyAccessExpression(expression)?expression.name:expression);
          if(symbol&&(symbol.flags&ts.SymbolFlags.Alias))symbol=checker.getAliasedSymbol(symbol);
          const declarations=symbol?.declarations??[];
          if(locations&&declarations.length&&declarations.every(d=>library(d.getSourceFile().fileName))){gap('external_library',node,'Invocation targets the TypeScript standard library, outside project implementations.');ts.forEachChild(node,visit);return;}
          if(locations&&declarations.some(d=>ts.isMethodDeclaration(d)&&(ts.isClassDeclaration(d.parent)||ts.isClassExpression(d.parent))&&!!d.parent.heritageClauses?.length)){gap('uncertain_dispatch',node,'Inherited/overridden runtime dispatch is not proven.');ts.forEachChild(node,visit);return;}
          const mutable=locations&&declarations.some(d=>ts.isVariableDeclaration(d)&&!(d.parent.flags&ts.NodeFlags.Const));
          if(mutable){gap('mutable_target',node,'Mutable function binding cannot establish runtime implementation.');ts.forEachChild(node,visit);return;}

          const implementations=[...new Set(declarations.map(implementation).filter((n):n is ts.Node=>!!n))];
          if(implementations.length!==1){gap(implementations.length>1?'ambiguous_target':declarations.length?'declaration_only':'unresolved_target',node,
            'Call does not resolve to exactly one project implementation; runtime dispatch is not inferred.');}
          else {
            const target=implementations[0], targetPath=canonical(target.getSourceFile().fileName), snapshot=targetPath&&snapshots.get(targetPath);
            if(!snapshot||target.getSourceFile().isDeclarationFile){gap('declaration_only',node,'Only declaration/library source is available.');}
            else if(targetPath===file&&target.getStart(snapshot.sf)>=selected.start&&target.end<=selected.end){/* already contained, including self calls */}
            else {
              const candidate=snapshot.outline.callables.find(c=>c.start===target.getStart(snapshot.sf)&&c.end===target.end);
              if(!candidate)gap('unsupported_target',node,'Resolved declaration is not extractable as a supported callable.');
              else {
                const key=`${targetPath}:${candidate.id}`;
                calls.set(key,{path:targetPath!,id:candidate.id,name:candidate.name,signature:candidate.signature});
                if(locations){
                  let entry=located.get(key);
                  if(!entry){entry={path:relative(root,targetPath!).split(sep).join('/'),callable_id:candidate.id,name:ts.isMethodDeclaration(target)&&(ts.isClassDeclaration(target.parent)||ts.isClassExpression(target.parent))&&target.parent.name?target.parent.name.text+'.'+candidate.name:candidate.name,signature:candidate.signature,
                    start_line:snapshot.sf.getLineAndCharacterOfPosition(candidate.start).line+1,
                    end_line:snapshot.sf.getLineAndCharacterOfPosition(Math.max(candidate.start,candidate.end-1)).line+1,call_sites:[]};located.set(key,entry);}
                  const start=main.sf.getLineAndCharacterOfPosition(node.getStart(main.sf)), end=main.sf.getLineAndCharacterOfPosition(node.end);
                  entry.call_sites.push({path:relative(root,file).split(sep).join('/'),start_line:start.line+1,start_column:start.character+1,end_line:end.line+1,end_column:end.character+1});
                }
              }
            }
          }
        }
      }
      // Deliberately scan nested bodies; never visit returned external implementations.
      ts.forEachChild(node,visit);
    };
    visit(selectedNode);
    if(locations){
      for(const [name,snapshot]of snapshots)if(readFileSync(name,'utf8')!==snapshot.source)throw new Error('Source snapshot changed during analysis');
      locations.push(...located.values());
      if(compilerOptions.allowJs||compilerOptions.jsx)gap('unsupported_source_kind',undefined,'JavaScript and TSX navigation are unsupported.');
    }
    diagnostics.sort((a,b)=>a.start-b.start||a.end-b.end||compare(a.code,b.code));
    return {status:diagnostics.length?'partial':'ok',data:{calls:[...calls.values()].sort((a,b)=>compare(a.path,b.path)||compare(a.id,b.id))},diagnostics};
  } catch(error) {
    const message=error instanceof Error?error.message:String(error);
    const code=/Stale or unknown/.test(message)?'stale_id':/parse error/.test(message)?'parse_error':'source_error';
    return {status:'error',data:null,diagnostics:[{code,message,start:0,end:0}]};
  }
}
