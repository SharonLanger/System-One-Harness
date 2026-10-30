import ts from 'typescript';
import {readFileSync, realpathSync, statSync, readdirSync} from 'node:fs';
import {dirname, join, resolve, relative, isAbsolute, sep} from 'node:path';
import {createHash} from 'node:crypto';
import {readOutline, collectLocalContext, LocalContext, LocalDependency, Diagnostic} from './index';

type Snapshot = ReturnType<typeof readOutline>;
interface ProjectGap extends Diagnostic {path: string; source_hash: string}
interface ConfigSource {path: string; source_hash: string}
const compareText = (a: string, b: string) => a < b ? -1 : a > b ? 1 : 0;
export interface ProjectContext extends Omit<LocalContext, 'gaps'> {
  gaps: ProjectGap[];
  project: {repository_root: string; config_path: string | null; config_hash: string | null; config_sources: ConfigSource[]};
}
export function collectProjectContext(path: string, id: string,
  options: {repositoryRoot: string; maxDepth?: number; maxDependencyChars?: number}): ProjectContext {
  const maxDepth = options.maxDepth ?? 2, maxChars = options.maxDependencyChars ?? 12000;
  if (!Number.isInteger(maxDepth) || maxDepth < 0 || maxDepth > 20 ||
      !Number.isInteger(maxChars) || maxChars < 1 || maxChars > 1000000) throw new Error('Invalid collection limit/budget');
  const root = realpathSync(options.repositoryRoot);
  if (!statSync(root).isDirectory()) throw new Error('Repository root must be a directory');
  let boundaryAttempts = 0;
  const packageRoots = new Set<string>();
  const inside = (name: string) => {const rel = relative(root, name); return !isAbsolute(rel) && rel !== '..' && !rel.startsWith('..' + sep);};
  const canonical = (name: string): string | undefined => {
    const absolute = resolve(name);
    if (!inside(absolute)) {boundaryAttempts++; return undefined;}
    const parts = absolute.split(sep), packageIndex = parts.lastIndexOf('node_modules');
    if (packageIndex >= 0 && parts.length > packageIndex + 1) {
      const count = parts[packageIndex + 1].startsWith('@') ? 3 : 2;
      try {const packageRoot = realpathSync(parts.slice(0, packageIndex + count).join(sep)); if (inside(packageRoot)) packageRoots.add(packageRoot);} catch {}
    }
    try {const real = realpathSync(absolute); if (!inside(real)) {boundaryAttempts++; return undefined;} return real;}
    catch {return undefined;}
  };
  const file = canonical(path);
  if (!file) throw new Error('Selected source outside repository or missing');
  const exists = (name: string) => {const p = canonical(name); return !!p && statSync(p).isFile();};
  const directoryExists = (name: string) => {const p = canonical(name); return !!p && statSync(p).isDirectory();};
  const configTexts = new Map<string, string>();
  const readConfig = (name: string): string | undefined => {
    const p = canonical(name);
    if (!p || !p.endsWith('.json') || !statSync(p).isFile()) return undefined;
    if (!configTexts.has(p)) configTexts.set(p, readFileSync(p, 'utf8'));
    return configTexts.get(p);
  };
  // Pinned TypeScript exports this matcher, though its declaration surface omits it.
  // Its filesystem callback rejects escaped/symlinked directories before listing.
  type Matcher = (path: string, extensions: readonly string[] | undefined, excludes: readonly string[] | undefined,
    includes: readonly string[] | undefined, sensitive: boolean, cwd: string, depth: number | undefined,
    entries: (path: string) => {files: string[]; directories: string[]}, realpath: (path: string) => string) => string[];
  const matchFiles = (ts as unknown as {matchFiles: Matcher}).matchFiles;
  const readDirectory: ts.ParseConfigHost['readDirectory'] = (name, extensions, excludes, includes, depth) => {
    if (!canonical(name)) return [];
    return matchFiles(name, extensions, excludes, includes, true, root, depth, dir => {
      const p = canonical(dir), files: string[] = [], directories: string[] = [];
      if (!p || !statSync(p).isDirectory()) return {files, directories};
      for (const entry of readdirSync(p, {withFileTypes: true})) {
        if (entry.name === '.git' || entry.name === 'node_modules') continue;
        const child = canonical(join(p, entry.name));
        if (child) (statSync(child).isDirectory() ? directories : files).push(entry.name);
      }
      return {files, directories};
    }, name => canonical(name) ?? name);
  };
  let configPath: string | undefined;
  for (let dir = dirname(file); inside(dir); dir = dirname(dir)) {
    const candidate = join(dir, 'tsconfig.json');
    if (exists(candidate)) {configPath = canonical(candidate); break;}
    if (dir === root) break;
  }
  const configSources = (): ConfigSource[] => [...configTexts].map(([path, source]) => ({path,
    source_hash: createHash('sha256').update(source, 'utf8').digest('hex')})).sort((a,b) => compareText(a.path,b.path));
  const projectMetadata = () => ({repository_root: root, config_path: configPath ?? null,
    config_hash: configPath && configTexts.has(configPath) ? createHash('sha256').update(configTexts.get(configPath)!, 'utf8').digest('hex') : null,
    config_sources: configSources()});
  // Configuration is inspected before any selected snapshot is read, so fallback
  // invokes the local collector once and never mixes two source snapshots.
  const fallback = (code: string, message: string): ProjectContext => {
    const local = collectLocalContext(file, id, {maxDepth, maxDependencyChars: maxChars});
    const gap = (code: string, message: string): ProjectGap => ({code, message,
      start: local.callable.start, end: local.callable.end, path: local.path, source_hash: local.source_hash});
    return {...local, project: projectMetadata(), gaps: [...local.gaps.map(g => ({...g, path: local.path, source_hash: local.source_hash})),
      gap(code, message), gap('caller_coverage', 'Callers and ambient project/library context are not exhaustively analysed.'),
      ...(boundaryAttempts ? [gap('outside_repository', 'A configuration or resolution path crossed the repository boundary.')] : [])],
      limitations: [...local.limitations, 'Project resolution unavailable; local context only.']};
  };
  if (!configPath) return fallback('missing_config', 'No tsconfig.json was found within the repository.');
  const configErrors: ts.Diagnostic[] = [];
  const parsed = ts.getParsedCommandLineOfConfigFile(configPath, {}, {
    useCaseSensitiveFileNames: true, readDirectory, fileExists: exists, readFile: readConfig,
    getCurrentDirectory: () => root, onUnRecoverableConfigFileDiagnostic: d => configErrors.push(d)
  });
  if (!parsed || configErrors.length || parsed.errors.some(e => ![18002,18003].includes(e.code)))
    return fallback('config_error', 'TypeScript configuration could not be parsed under repository confinement.');
  if (!parsed.fileNames.some(name => canonical(name) === file))
    return fallback('project_membership', 'Selected source is not included in the parsed TypeScript project.');
  if (parsed.options.moduleResolution === undefined && parsed.options.module !== undefined &&
      [ts.ModuleKind.Node16, ts.ModuleKind.Node18, ts.ModuleKind.Node20, ts.ModuleKind.NodeNext, ts.ModuleKind.Preserve].includes(parsed.options.module))
    return fallback('unsupported_resolution_mode', 'Implicit modern module resolution is not approximated.');
  const resolutionMode = parsed.options.moduleResolution ??
    (parsed.options.module === ts.ModuleKind.CommonJS ? ts.ModuleResolutionKind.Node10 : ts.ModuleResolutionKind.Classic);
  if (![ts.ModuleResolutionKind.Node10, ts.ModuleResolutionKind.Classic].includes(resolutionMode))
    return fallback('unsupported_resolution_mode', 'This collector supports Classic/Node10 resolution; modern condition-dependent modes remain explicit gaps.');
  const compilerOptions = {...parsed.options, noLib: true, types: [], noResolve: false};
  const snapshots = new Map<string, Snapshot>(), loadFailures = new Map<string, string>();
  const main = readOutline(file); snapshots.set(file, main);
  const bySource = new Map<ts.SourceFile, Snapshot>([[main.sf, main]]);
  const packageImplementation = (name: string) => !name.endsWith('.d.ts') && (name.includes(sep+'node_modules'+sep) ||
    [...packageRoots].some(root => name === root || name.startsWith(root + sep)));
  let loadedChars = 0, sourceAttempts = 1, foreignBytes = 0;
  const snapshot = (name: string): Snapshot | undefined => {
    const p = canonical(name);
    if (!p || !p.endsWith('.ts')) return undefined;
    if (packageImplementation(name) || packageImplementation(p)) {loadFailures.set(p, 'external_dependency'); return undefined;}
    if (snapshots.has(p)) return snapshots.get(p);
    if (loadFailures.has(p)) return undefined;
    if (sourceAttempts >= 64) {loadFailures.set(p, 'source_load_limit'); return undefined;}
    sourceAttempts++;
    const bytes = statSync(p).size;
    if (foreignBytes + bytes > 4000000) {loadFailures.set(p, 'source_load_limit'); return undefined;}
    foreignBytes += bytes;
    try {
      const data = readOutline(p);
      if (loadedChars + data.source.length > 1000000) {loadFailures.set(p, 'source_load_limit'); return undefined;}
      loadedChars += data.source.length; snapshots.set(p, data); bySource.set(data.sf, data); return data;
    } catch {loadFailures.set(p, 'dependency_parse_error'); return undefined;}
  };
  const host: ts.CompilerHost = {
    resolveModuleNames: (names, containing) => names.map(name => {
      const result = ts.resolveModuleName(name, containing, compilerOptions, host).resolvedModule;
      // Classify origin before the compiler canonicalizes package symlinks.
      return result?.isExternalLibraryImport && !result.resolvedFileName.endsWith('.d.ts') ? undefined : result;
    }),
    getSourceFile: name => snapshot(name)?.sf, getDefaultLibFileName: () => '', writeFile: () => {},
    getCurrentDirectory: () => root, getDirectories: name => {
      const p = canonical(name); return p && directoryExists(p) ? readdirSync(p, {withFileTypes: true})
        .filter(e => e.isDirectory() && !!canonical(join(p,e.name))).map(e => e.name) : [];
    }, fileExists: exists, directoryExists, realpath: name => canonical(name) ?? name,
    readFile: name => name.endsWith('.json') ? readConfig(name) : snapshot(name)?.source,
    getCanonicalFileName: name => canonical(name) ?? name, useCaseSensitiveFileNames: () => true, getNewLine: () => '\n'
  };
  // Root-only program follows the resolved graph; unrelated project files and
  // automatic libraries/types are not loaded. No compiler plugin is instantiated.
  const program = ts.createProgram([file], compilerOptions, host), checker = program.getTypeChecker();
  const selected = main.outline.callables.find(c => c.id === id);
  if (!selected) throw new Error('Stale or unknown callable ID');
  let selectedNode: ts.Node = main.sf;
  const find = (n: ts.Node): void => {if (n.getStart(main.sf) === selected.start && n.end === selected.end) selectedNode=n; ts.forEachChild(n,find);}; find(main.sf);
  const sourceOf = (node: ts.Node) => bySource.get(node.getSourceFile())!;
  const within = (node: ts.Node, container: ts.Node) => node.getSourceFile() === container.getSourceFile() && node.pos >= container.pos && node.end <= container.end;
  const gaps: ProjectGap[] = [], gapKeys = new Set<string>();
  const gap = (code: string, node: ts.Node, message: string) => {
    const s=sourceOf(node),start=node.getStart(s.sf),end=node.end,key=`${s.outline.path}:${code}:${start}:${end}`;
    if (!gapKeys.has(key)) {gapKeys.add(key);gaps.push({code,message,start,end,path:s.outline.path,source_hash:s.outline.source_hash});}
  };
  gap('caller_coverage',selectedNode,'Callers and ambient project/library context are not exhaustively analysed.');
  if (parsed.projectReferences?.length) {
    gap('project_references',selectedNode,'Referenced projects are not traversed as separate programs.');
    for(const reference of parsed.projectReferences){const before=boundaryAttempts;canonical(reference.path);if(boundaryAttempts>before)gap('outside_repository',selectedNode,'Referenced project crossed the repository boundary and was not read.');}
  }
  const enclosingClass=(n:ts.Node):ts.ClassLikeDeclaration|undefined=>{for(let p=n.parent;p;p=p.parent)if(ts.isClassLike(p))return p;};
  const selectedClass=enclosingClass(selectedNode);
  const unitFor=(declaration:ts.Declaration):ts.Node|undefined=>{
    let n:ts.Node=declaration;
    if(ts.isImportSpecifier(n)||ts.isImportClause(n)||ts.isNamespaceImport(n)){while(n.parent&&!ts.isImportDeclaration(n))n=n.parent;return n;}
    if(ts.isVariableDeclaration(n)){while(n.parent&&!ts.isVariableStatement(n))n=n.parent;return ts.isVariableStatement(n)&&ts.isSourceFile(n.parent)?n:undefined;}
    if((ts.isFunctionDeclaration(n)||ts.isTypeAliasDeclaration(n)||ts.isInterfaceDeclaration(n)||ts.isEnumDeclaration(n)||ts.isClassDeclaration(n))&&ts.isSourceFile(n.parent))return n;
    if((ts.isPropertyDeclaration(n)||ts.isMethodDeclaration(n)||ts.isGetAccessorDeclaration(n)||ts.isSetAccessorDeclaration(n)||ts.isConstructorDeclaration(n))&&n.parent===selectedClass)return n;
  };
  const dependencies=new Map<string,LocalDependency>(),queued=new Set<ts.Node>([selectedNode]);
  const queue:{node:ts.Node;depth:number}[]=[{node:selectedNode,depth:0}];let chars=0;
  const add=(unit:ts.Node,depth:number,ref:ts.Node,symbol?:ts.Symbol):boolean=>{
    if(within(unit,selectedNode))return true;
    const s=sourceOf(unit),start=unit.getStart(s.sf),end=unit.end,unitId=`${s.outline.source_hash}:${start}:${end}`,key=`${s.outline.path}:${unitId}`;
    const symbols=symbol?(symbol.declarations??[]).filter(d=>d.getSourceFile()===s.sf).map(d=>`${s.outline.source_hash}:${d.getStart(s.sf)}:${d.end}`).sort():[unitId];
    const existing=dependencies.get(key);if(existing){existing.symbol_ids=[...new Set([...existing.symbol_ids,...symbols])].sort();return true;}
    if(depth>maxDepth){gap('depth_limit',ref,'Complete dependency route/unit omitted at depth limit.');return false;}
    if(chars+end-start>maxChars){gap('size_limit',ref,'Complete dependency route/unit omitted at source budget limit.');return false;}
    const pos=s.sf.getLineAndCharacterOfPosition(start);dependencies.set(key,{id:unitId,path:s.outline.path,source_hash:s.outline.source_hash,start,end,
      location:{line:pos.line+1,column:pos.character+1},kind:ts.SyntaxKind[unit.kind],code:s.source.slice(start,end),symbol_ids:symbols.length?symbols:[unitId]});chars+=end-start;
    if(!queued.has(unit)){queued.add(unit);queue.push({node:unit,depth});}return true;
  };
  const ultimate=(symbol:ts.Symbol):ts.Symbol=>symbol.flags&ts.SymbolFlags.Alias?checker.getAliasedSymbol(symbol):symbol;
  const resolveModule=(specifier:string,from:ts.Node):Snapshot|undefined=>{
    const before=boundaryAttempts;
    const result=ts.resolveModuleName(specifier,sourceOf(from).outline.path,compilerOptions,host).resolvedModule;
    if(!result){gap(boundaryAttempts>before?'outside_repository':specifier.startsWith('.')?'missing_module':'external_dependency',from,'Module implementation was not resolved within the supported project boundary.');return;}
    const p=canonical(result.resolvedFileName);
    if(!p){gap('outside_repository',from,'Resolved module crossed the repository boundary.');return;}
    if(p.endsWith('.d.ts')){gap('declaration_only',from,'Declaration-only module has no collected implementation.');return;}
    if(result.isExternalLibraryImport||p.includes(sep+'node_modules'+sep)){gap('external_dependency',from,'Package implementations are not loaded or collected.');return;}
    const s=snapshot(p);if(!s)gap(loadFailures.get(p)??'unsupported_dependency',from,'Module source could not be collected under the source-loading policy.');return s;
  };
  const ambiguousModules = new Map<ts.SourceFile, boolean>();
  const importName=(declaration:ts.Declaration):string=>ts.isImportSpecifier(declaration)
    ? (declaration.propertyName?.text??declaration.name.text) : ts.isNamespaceImport(declaration)?'*':'default';
  const route=(module:Snapshot,target:ts.Symbol,name:string,depth:number,ref:ts.Node,seen:Set<string>):boolean=>{
    if(name==='*'&&target.declarations?.some(d=>d===module.sf))return true;
    if(!ambiguousModules.has(module.sf))ambiguousModules.set(module.sf,program.getSemanticDiagnostics(module.sf).some(d=>d.code===2308));
    if(ambiguousModules.get(module.sf)){gap('unsupported_reexport_route',ref,'Module exports are ambiguous; implementation route is omitted.');return false;}
    const key=module.outline.path+':'+name;if(seen.has(key))return false;seen.add(key);
    const moduleSymbol=checker.getSymbolAtLocation(module.sf);
    const exported=moduleSymbol&&checker.getExportsOfModule(moduleSymbol).find(s=>s.name===name);
    if(!exported||ultimate(exported)!==target){gap('unsupported_reexport_route',ref,'Requested export binding was not proved by the compiler.');return false;}
    const followLocal=(local:ts.Symbol|undefined):boolean=>{
      if(!local||ultimate(local)!==target)return false;
      for(const declaration of local.declarations??[]){const binding=unitFor(declaration);
        if(binding&&ts.isImportDeclaration(binding)&&ts.isStringLiteralLike(binding.moduleSpecifier)){
          if(!add(binding,depth,ref,local))return false;const next=resolveModule(binding.moduleSpecifier.text,binding);
          if(next&&route(next,target,importName(declaration),depth,ref,new Set(seen)))return true;
        }else if(declaration.getSourceFile()===module.sf)return true;
      }
      return false;
    };
    for(const statement of module.sf.statements){
      if(ts.isExportAssignment(statement)&&!statement.isExportEquals&&name==='default'){
        const local=checker.getSymbolAtLocation(statement.expression);
        if(local&&ultimate(local)===target){if(!add(statement,depth,ref))return false;if(followLocal(local))return true;}
      }
      if(!ts.isExportDeclaration(statement))continue;
      if(statement.exportClause&&ts.isNamedExports(statement.exportClause)){
        const element=statement.exportClause.elements.find(e=>e.name.text===name&&(()=>{const s=checker.getSymbolAtLocation(e.name);return !!s&&ultimate(s)===target;})());
        if(!element)continue;if(!add(statement,depth,ref))return false;
        if(statement.moduleSpecifier&&ts.isStringLiteralLike(statement.moduleSpecifier)){
          const next=resolveModule(statement.moduleSpecifier.text,statement);
          if(next&&route(next,target,element.propertyName?.text??element.name.text,depth,ref,new Set(seen)))return true;
        }else if(followLocal(checker.getExportSpecifierLocalTargetSymbol(element)))return true;
      }else if(!statement.exportClause&&statement.moduleSpecifier&&ts.isStringLiteralLike(statement.moduleSpecifier)&&name!=='default'){
        const next=resolveModule(statement.moduleSpecifier.text,statement),symbol=next&&checker.getSymbolAtLocation(next.sf);
        if(!next||!symbol||!checker.getExportsOfModule(symbol).some(s=>s.name===name&&ultimate(s)===target))continue;
        if(!add(statement,depth,ref))return false;if(route(next,target,name,depth,ref,new Set(seen)))return true;
      }
    }
    for(const declaration of target.declarations??[]){
      if(declaration.getSourceFile()!==module.sf)continue;
      let top:ts.Node=declaration;while(top.parent&&!ts.isSourceFile(top.parent))top=top.parent;
      const modifiers=ts.canHaveModifiers(top)?ts.getModifiers(top):undefined;
      if(modifiers?.some(m=>m.kind===ts.SyntaxKind.ExportKeyword)&&
          (name==='default')===!!modifiers.some(m=>m.kind===ts.SyntaxKind.DefaultKeyword))return true;
    }
    gap('unsupported_reexport_route',ref,'A complete route for the requested export name could not be preserved.');return false;
  };
  const analysedFiles=new Set<ts.SourceFile>();
  const analyseFile=(sf:ts.SourceFile)=>{if(analysedFiles.has(sf))return;analysedFiles.add(sf);gap('module_side_effects',sf,'Module initialization and side effects are not reconstructed or executed.');
    for(const reference of sf.referencedFiles){const target=resolve(dirname(sourceOf(sf).outline.path),reference.fileName),p=canonical(target);if(!p)gap('outside_repository',sf,'Triple-slash reference crossed repository boundary.');else if(packageImplementation(target)||packageImplementation(p))gap('external_dependency',sf,'Package implementation reference is not read or collected.');}
    for(const statement of sf.statements)if(ts.isImportDeclaration(statement)&&!statement.importClause&&ts.isStringLiteralLike(statement.moduleSpecifier))resolveModule(statement.moduleSpecifier.text,statement);
  };
  if(selectedClass){gap('class_state',selectedClass,'Initialization, writes, inheritance and dispatch remain partial.');for(const member of selectedClass.members)if(ts.isConstructorDeclaration(member))add(member,1,selectedNode);}
  let binding=selectedNode;while(binding.parent&&(ts.isParenthesizedExpression(binding.parent)||ts.isAsExpression(binding.parent)||ts.isSatisfiesExpression(binding.parent)||ts.isNonNullExpression(binding.parent)||ts.isTypeAssertionExpression(binding.parent)))binding=binding.parent;
  if(binding.parent&&(ts.isVariableDeclaration(binding.parent)||ts.isPropertyDeclaration(binding.parent)||ts.isPropertyAssignment(binding.parent)))queue[0].node=binding.parent;
  const seenSymbols=new Set<ts.Symbol>();
  for(let index=0;index<queue.length;index++){
    const {node:unit,depth}=queue[index];analyseFile(unit.getSourceFile());
    const visit=(node:ts.Node):void=>{
      if(ts.isElementAccessExpression(node))gap('dynamic_reference',node,'Computed dispatch target is not statically reconstructed.');
      if((ts.isCallExpression(node)||ts.isNewExpression(node))&&!(ts.isIdentifier(node.expression)||ts.isPropertyAccessExpression(node.expression)))gap('dynamic_reference',node,'Indirect invocation target is not resolved.');
      if(ts.isIdentifier(node)||ts.isPrivateIdentifier(node)){
        const parent=node.parent,declarationName='name'in parent&&parent.name===node&&!ts.isShorthandPropertyAssignment(parent)&&!ts.isPropertyAccessExpression(parent);
        if(!declarationName&&!ts.isImportSpecifier(parent)&&!ts.isImportClause(parent)&&!ts.isNamespaceImport(parent)&&!ts.isExportSpecifier(parent)){
          // Resolve the value binding of shorthand properties before following
          // the existing import/alias route and dependency budgets.
          const symbol=ts.isShorthandPropertyAssignment(parent)&&parent.name===node
            ? checker.getShorthandAssignmentValueSymbol(parent):checker.getSymbolAtLocation(node);
          if(!symbol?.declarations?.length)gap('unresolved_reference',node,'No supported semantic declaration was found.');
          else if(ts.isPropertyAccessExpression(parent)&&parent.name===node&&ultimate(symbol).declarations?.some(d=>d.getSourceFile()!==node.getSourceFile())) {
            gap('unsupported_reexport_route',node,'Foreign property targets require a proven import route; namespace/object dispatch is not collected.');
          } else if(!seenSymbols.has(symbol)){
            seenSymbols.add(symbol);let routeAllowed=true;
            for(const declaration of symbol.declarations){const unit=unitFor(declaration);if(unit&&ts.isImportDeclaration(unit)&&ts.isStringLiteralLike(unit.moduleSpecifier)){
              if(!add(unit,depth+1,node,symbol)){routeAllowed=false;continue;}const module=resolveModule(unit.moduleSpecifier.text,node);const target=ultimate(symbol);
              if(!module)routeAllowed=false;
              else if(target===symbol||!target.declarations?.length){gap('unresolved_reference',node,'Imported binding has no resolved implementation declaration.');routeAllowed=false;}
              else if(!route(module,target,importName(declaration),depth+1,node,new Set()))routeAllowed=false;
            }}
            const target=ultimate(symbol);
            if(target.declarations?.some(d=>ts.isSourceFile(d)))gap('namespace_context',node,'Namespace operations remain partial; foreign property endpoints are not inferred.');
            if(routeAllowed)for(const declaration of target.declarations??[]){
              if(ts.isSourceFile(declaration))continue;
              if(within(declaration,selectedNode)||within(declaration,unit))continue;
              if(declaration.getSourceFile().isDeclarationFile ||
                 (!ts.isTypeAliasDeclaration(declaration)&&!ts.isInterfaceDeclaration(declaration)&&
                  !!(ts.getCombinedModifierFlags(declaration)&ts.ModifierFlags.Ambient))){gap('declaration_only',node,'Declaration target has no implementation.');continue;}
              if(ts.isFunctionDeclaration(declaration)&&!declaration.body){
                if(!target.declarations?.some(d=>ts.isFunctionDeclaration(d)&&!!d.body))gap('declaration_only',node,'Function declaration has no implementation.');
                continue;
              }
              const destination=unitFor(declaration);
              if(!destination){gap(enclosingClass(declaration)&&enclosingClass(declaration)!==selectedClass?'inherited_dispatch':'closure_capture',node,'Inherited, outer-local or unsupported dispatch remains partial.');continue;}
              if(ts.isVariableStatement(destination))gap('mutable_state',node,'Declaration text does not establish runtime state or immutability.');
              if(ts.isClassDeclaration(destination))gap('class_state',node,'Whole class text does not establish initialization or dispatch.');
              add(destination,depth+1,node,target);
            }
          }
        }
      }
      ts.forEachChild(node,visit);
    };visit(unit);
  }
  const code=main.source.slice(selected.start,selected.end),{callables:_unused,...base}=main.outline;
  return {...base,callable:selected,code,display_code:code.split(/\r\n|\r|\n/).map((line,i)=>`${selected.location.line+i}: ${line}`).join('\n'),coverage:'partial',
    dependencies:[...dependencies.values()].sort((a,b)=>compareText(a.path,b.path)||a.start-b.start||a.end-b.end),
    gaps:gaps.sort((a,b)=>compareText(a.path,b.path)||a.start-b.start||a.end-b.end||compareText(a.code,b.code)),
    collection:{max_depth:maxDepth,max_dependency_chars:maxChars,dependency_chars:chars},project:projectMetadata(),
    limitations:base.limitations.filter(x=>x!=='Dependency context is not collected.').concat(['Project graph uses parsed Classic/Node10 resolution only; automatic libraries/types, ambient globals, separate referenced projects and callers remain partial.',
      'Only repository .ts implementations are collected. Package/declaration-only implementations are omitted; project modules are never executed.',
      'Dependency graph loading is capped at64 unique source attempts,4,000,000 cumulative foreign pre-read bytes and1,000,000 admitted foreign UTF16 source units; selected source is governed by the subprocess deadline.'])};
}
