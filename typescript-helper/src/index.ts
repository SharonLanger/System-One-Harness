import ts from 'typescript';
import {readFileSync, realpathSync} from 'node:fs';
import {createHash} from 'node:crypto';

export interface Callable {
  id: string; name: string; signature: string; start: number; end: number;
  location: {line: number; column: number};
}
export interface Diagnostic {code: string; message: string; start: number; end: number}
export interface Outline {
  schema_version: number; path: string; source_hash: string; callables: Callable[];
  diagnostics: Diagnostic[]; limitations: string[];
}
/** @internal Exhaustive snapshot discovery for extraction/collectors; public callers use outline (README "File outline"). */
export function readOutline(path: string): {outline: Outline; source: string; sf: ts.SourceFile} {
  const canonical = realpathSync(path);
  const source = readFileSync(canonical, 'utf8');
  const sf = ts.createSourceFile(canonical, source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);
  // parseDiagnostics is attached by the public parser, but omitted from SourceFile's declared surface.
  const parseDiagnostics = (sf as ts.SourceFile & {parseDiagnostics: readonly ts.Diagnostic[]}).parseDiagnostics;
  if (parseDiagnostics.length) {
    throw new Error('TypeScript parse error: ' + parseDiagnostics.map(d =>
      ts.flattenDiagnosticMessageText(d.messageText, '\n')).join('; '));
  }
  const hash = createHash('sha256').update(source, 'utf8').digest('hex');
  const callables: Callable[] = [];
  const diagnostics: Diagnostic[] = [];
  // A binding can own a callable through syntax-only wrappers, never through a
  // call, conditional, binary expression or arbitrary ancestor.
  const bindingFor = (node: ts.Expression): ts.VariableDeclaration | ts.PropertyDeclaration | ts.PropertyAssignment | undefined => {
    let expression: ts.Expression = node;
    while (expression.parent &&
      (ts.isParenthesizedExpression(expression.parent) || ts.isAsExpression(expression.parent) ||
       ts.isSatisfiesExpression(expression.parent) || ts.isNonNullExpression(expression.parent) ||
       ts.isTypeAssertionExpression(expression.parent)) && expression.parent.expression === expression) {
      expression = expression.parent;
    }
    const parent = expression.parent;
    if ((ts.isVariableDeclaration(parent) || ts.isPropertyDeclaration(parent) ||
         ts.isPropertyAssignment(parent)) && parent.initializer === expression) return parent;
    return undefined;
  };
  const visit = (node: ts.Node): void => {
    const callable = ts.isFunctionDeclaration(node) || ts.isFunctionExpression(node) ||
      ts.isArrowFunction(node) || ts.isMethodDeclaration(node) || ts.isConstructorDeclaration(node) ||
      ts.isGetAccessorDeclaration(node) || ts.isSetAccessorDeclaration(node);
    if (callable) {
      const binding = ts.isFunctionExpression(node) || ts.isArrowFunction(node) ? bindingFor(node) : undefined;
      const destructuring = !!binding && ts.isVariableDeclaration(binding) && !ts.isIdentifier(binding.name);
      const supported = !!node.body && !destructuring;
      const start = node.getStart(sf), end = node.getEnd();
      if (supported && node.body) {
        const pos = sf.getLineAndCharacterOfPosition(start);
        const anonymous = `<anonymous@${pos.line + 1}:${pos.character + 1}>`;
        let name = binding ? binding.name.getText(sf) : ts.isConstructorDeclaration(node) ? 'constructor'
          : ts.isFunctionDeclaration(node) ? (node.name?.text ??
            (node.modifiers?.some(m => m.kind === ts.SyntaxKind.DefaultKeyword) ? '<default>' : anonymous))
          : ('name' in node && node.name ? node.name.getText(sf) : anonymous);
        // Source headers are AST bounded. Hide nested callable bodies in
        // defaults/decorators/computed names without hand-parsing signatures.
        const headerStart = binding ? binding.getStart(sf) : start, headerEnd = node.body.getStart(sf);
        const hidden: {start: number; end: number}[] = [];
        const hideBodies = (child: ts.Node): void => {
          if (child !== node && ts.isFunctionLike(child) && 'body' in child && child.body) {
            const body = child.body as ts.Node;
            if (body.getStart(sf) >= headerStart && body.end <= headerEnd) {
              hidden.push({start: body.getStart(sf), end: body.end}); return;
            }
          }
          if (child.getStart(sf) < headerEnd) ts.forEachChild(child, hideBodies);
        };
        ts.forEachChild(node, hideBodies);
        const nameNode = binding?.name ?? ('name' in node ? node.name : undefined);
        if (nameNode && ts.isComputedPropertyName(nameNode)) {
          const nameStart = nameNode.getStart(sf);
          for (const range of hidden.filter(r => r.start >= nameStart && r.end <= nameNode.end).sort((a,b) => b.start - a.start)) {
            name = name.slice(0, range.start - nameStart) + '…' + name.slice(range.end - nameStart);
          }
        }
        let signature = source.slice(headerStart, headerEnd);
        for (const range of hidden.sort((a,b) => b.start - a.start)) {
          signature = signature.slice(0, range.start - headerStart) + '…' + signature.slice(range.end - headerStart);
        }
        callables.push({id: `${hash}:${start}:${end}`, name,
          signature: signature.trimEnd(), start, end,
          location: {line: pos.line + 1, column: pos.character + 1}});
      } else {
        const name = 'name' in node && node.name ? (node.name as ts.Node).getText(sf) : '';
        diagnostics.push({code: 'unsupported_callable',
          message: `Unsupported ${ts.SyntaxKind[node.kind]}${name ? ' ' + name : ''}${destructuring ? ' (destructuring binding)' : ''}`,
          start, end});
      }
    }
    ts.forEachChild(node, visit);
  };
  visit(sf);
  return {source, sf, outline: {schema_version: 1, path: canonical, source_hash: hash, callables, diagnostics,
    limitations: ['Runtime callable bodies are discovered recursively; destructuring-bound callable expressions remain unsupported.',
      'Locations and ranges use UTF-16 code units; comments before declarations are excluded.',
      'Bound expression signatures include their immediate binding header and transparent wrappers; raw code is only the callable expression.',
      'Type-only signatures are not runtime implementation candidates; computed names are source text, never evaluated.',
      'Dependency context is not collected.']}};
}


/** Public declaration-only outline; see README "File outline". Stops at every function subtree. */
export function outline(path: string): Outline {
  const snapshot = readOutline(path);
  const allowed = new Set<number>();
  const visit = (node: ts.Node): void => {
    if (ts.isFunctionLike(node)) {
      // Only direct named bindings, declarations and members are public peers.
      const candidate = snapshot.outline.callables.find(c => c.start === node.getStart(snapshot.sf) && c.end === node.end);
      if (candidate && !candidate.name.startsWith('<anonymous@')) allowed.add(candidate.start);
      return;
    }
    ts.forEachChild(node, visit);
  };
  visit(snapshot.sf);
  const result = snapshot.outline;
  return {...result, callables: result.callables.filter(c => allowed.has(c.start)),
    diagnostics: result.diagnostics.filter(d => {
      let nested = false;
      const check = (n: ts.Node): void => {
        if (ts.isFunctionLike(n) && n.getStart(snapshot.sf) < d.start && n.end >= d.end) { nested = true; return; }
        if (!nested) ts.forEachChild(n, check);
      };
      check(snapshot.sf); return !nested;
    }),
    limitations: result.limitations.map(x => x.startsWith('Runtime callable')
      ? 'Public outline stops at every function subtree; nested definitions and unbound anonymous expressions are excluded.' : x)};
}
export interface CallableSource extends Omit<Outline, 'callables'> {
  callable: Callable; code: string; display_code: string;
}
/** Exact snapshot source slice; see README "Extract callable". */
export function extractCallable(path: string, id: string): CallableSource {
  // Outline and code share one read snapshot; JS slice uses compiler UTF-16 offsets.
  const snapshot = readOutline(path);
  const callable = snapshot.outline.callables.find(c => c.id === id);
  if (!callable) throw new Error('Stale or unknown callable ID');
  const code = snapshot.source.slice(callable.start, callable.end);
  const display_code = code.split(/\r\n|\r|\n/).map((line, index) =>
    `${callable.location.line + index}: ${line}`).join('\n');
  const {callables: _unused, ...metadata} = snapshot.outline;
  return {...metadata, callable, code, display_code};
}

export interface LocalDependency {
  id: string; path: string; source_hash: string; start: number; end: number;
  location: {line: number; column: number}; kind: string; code: string; symbol_ids: string[];
}
export interface LocalContext extends CallableSource {
  coverage: 'partial'; dependencies: LocalDependency[]; gaps: Diagnostic[];
  collection: {max_depth: number; max_dependency_chars: number; dependency_chars: number};
}
/** Bounded partial same-file declarations; see README "Local context". */
export function collectLocalContext(path: string, id: string,
  options: {maxDepth?: number; maxDependencyChars?: number} = {}): LocalContext {
  const maxDepth = options.maxDepth ?? 2, maxChars = options.maxDependencyChars ?? 12000;
  if (!Number.isInteger(maxDepth) || maxDepth < 0 || maxDepth > 20 ||
      !Number.isInteger(maxChars) || maxChars < 1 || maxChars > 1000000) throw new Error('Invalid collection limit/budget');
  const {outline: metadata, source, sf} = readOutline(path);
  const selected = metadata.callables.find(c => c.id === id);
  if (!selected) throw new Error('Stale or unknown callable ID');
  // Isolated semantic program: only the already-read snapshot can be supplied.
  // No filesystem module resolution, standard library loading, or source execution.
  const compilerOptions: ts.CompilerOptions = {noLib: true, noResolve: true, target: ts.ScriptTarget.Latest};
  const host: ts.CompilerHost = {
    getSourceFile: name => name === metadata.path ? sf : undefined,
    getDefaultLibFileName: () => '', writeFile: () => {}, getCurrentDirectory: () => '',
    getDirectories: () => [], fileExists: name => name === metadata.path,
    readFile: name => name === metadata.path ? source : undefined,
    getCanonicalFileName: name => name, useCaseSensitiveFileNames: () => true, getNewLine: () => '\n'
  };
  const checker = ts.createProgram([metadata.path], compilerOptions, host).getTypeChecker();
  let root: ts.Node = sf;
  const find = (node: ts.Node): void => {
    if (node.getStart(sf) === selected.start && node.end === selected.end) root = node;
    ts.forEachChild(node, find);
  };
  find(sf);
  const within = (node: ts.Node, container: ts.Node) => node.pos >= container.pos && node.end <= container.end;
  const gaps: Diagnostic[] = [], gapKeys = new Set<string>();
  const gap = (code: string, node: ts.Node, message: string) => {
    const start = node.getStart(sf), end = node.end, key = `${code}:${start}:${end}`;
    if (!gapKeys.has(key)) { gapKeys.add(key); gaps.push({code, message, start, end}); }
  };
  const enclosingClass = (node: ts.Node): ts.ClassLikeDeclaration | undefined => {
    for (let parent = node.parent; parent; parent = parent.parent) if (ts.isClassLike(parent)) return parent;
  };
  const selectedClass = enclosingClass(root);
  const unitFor = (declaration: ts.Declaration): ts.Node | undefined => {
    let node: ts.Node = declaration;
    if (ts.isImportSpecifier(node) || ts.isImportClause(node) || ts.isNamespaceImport(node)) {
      while (node.parent && !ts.isImportDeclaration(node)) node = node.parent;
      return node;
    }
    if (ts.isVariableDeclaration(node)) {
      while (node.parent && !ts.isVariableStatement(node)) node = node.parent;
      return ts.isVariableStatement(node) && ts.isSourceFile(node.parent) ? node : undefined;
    }
    if ((ts.isFunctionDeclaration(node) || ts.isTypeAliasDeclaration(node) ||
         ts.isInterfaceDeclaration(node) || ts.isEnumDeclaration(node) || ts.isClassDeclaration(node)) &&
        ts.isSourceFile(node.parent)) return node;
    if ((ts.isPropertyDeclaration(node) || ts.isMethodDeclaration(node) ||
         ts.isGetAccessorDeclaration(node) || ts.isSetAccessorDeclaration(node) ||
         ts.isConstructorDeclaration(node)) && node.parent === selectedClass) return node;
    return undefined;
  };
  const dependencies = new Map<string, LocalDependency>();
  const queued = new Set<ts.Node>([root]), queue: {node: ts.Node; depth: number}[] = [{node: root, depth: 0}];
  const seenSymbols = new Set<ts.Symbol>();
  let chars = 0;
  const add = (unit: ts.Node, depth: number, reference: ts.Node, symbol?: ts.Symbol) => {
    const start = unit.getStart(sf), end = unit.end, unitId = `${metadata.source_hash}:${start}:${end}`;
    if (within(unit, root)) return;
    const symbolIds = symbol ? (symbol.declarations ?? []).filter(d => d.getSourceFile() === sf)
      .map(d => `${metadata.source_hash}:${d.getStart(sf)}:${d.end}`).sort() : [unitId];
    const existing = dependencies.get(unitId);
    if (existing) { existing.symbol_ids = [...new Set([...existing.symbol_ids, ...symbolIds])].sort(); return; }
    if (depth > maxDepth) { gap('depth_limit', reference, 'Dependency omitted at collection depth limit.'); return; }
    if (chars + end - start > maxChars) { gap('size_limit', reference, 'Complete dependency omitted at source budget limit.'); return; }
    const pos = sf.getLineAndCharacterOfPosition(start);
    dependencies.set(unitId, {id: unitId, path: metadata.path, source_hash: metadata.source_hash,
      start, end, location: {line: pos.line + 1, column: pos.character + 1},
      kind: ts.SyntaxKind[unit.kind], code: source.slice(start, end), symbol_ids: symbolIds});
    chars += end - start;
    if (!queued.has(unit)) { queued.add(unit); queue.push({node: unit, depth}); }
  };
  for (const statement of sf.statements) {
    if (ts.isImportDeclaration(statement) && !statement.importClause)
      gap('module_side_effects', statement, 'Side-effect import behavior is outside local dependency collection.');
    else if (ts.isExpressionStatement(statement) || ts.isExportDeclaration(statement))
      gap('module_side_effects', statement, 'Module initialization or re-export effects are not reconstructed.');
  }
  if (selectedClass) {
    gap('class_state', selectedClass, 'Class initialization, writes, inheritance and dispatch remain partial.');
    for (const member of selectedClass.members) if (ts.isConstructorDeclaration(member)) add(member, 1, root);
  }
  // Bound signatures can precede the raw callable. Visit the immediate binding
  // type/header separately without treating surrounding sibling declarations as references.
  let binding: ts.Node = root;
  while (binding.parent && (ts.isParenthesizedExpression(binding.parent) || ts.isAsExpression(binding.parent) ||
    ts.isSatisfiesExpression(binding.parent) || ts.isNonNullExpression(binding.parent) || ts.isTypeAssertionExpression(binding.parent))) binding = binding.parent;
  if (binding.parent && (ts.isVariableDeclaration(binding.parent) || ts.isPropertyDeclaration(binding.parent) ||
    ts.isPropertyAssignment(binding.parent))) queue[0].node = binding.parent;
  for (let index = 0; index < queue.length; index++) {
    const {node: unit, depth} = queue[index];
    const visit = (node: ts.Node): void => {
      if (ts.isElementAccessExpression(node)) gap('dynamic_reference', node, 'Computed property target is not resolved.');
      if (ts.isCallExpression(node) || ts.isNewExpression(node)) {
        const target = node.expression;
        if (!(ts.isIdentifier(target) || ts.isPropertyAccessExpression(target)))
          gap('dynamic_reference', node, 'Indirect invocation target is not resolved.');
      }
      if (ts.isIdentifier(node) || ts.isPrivateIdentifier(node)) {
        const parent = node.parent;
        const declarationName = ('name' in parent && parent.name === node && !ts.isShorthandPropertyAssignment(parent) &&
          !ts.isPropertyAccessExpression(parent));
        const importPart = ts.isImportSpecifier(parent) || ts.isImportClause(parent) || ts.isNamespaceImport(parent);
        if (!declarationName && !importPart) {
          // A shorthand name owns a property symbol; its value symbol carries
          // the lexical binding (including shadowed locals and import aliases).
          const symbol = ts.isShorthandPropertyAssignment(parent) && parent.name === node
            ? checker.getShorthandAssignmentValueSymbol(parent) : checker.getSymbolAtLocation(node);
          if (!symbol || !symbol.declarations?.length) {
            gap('unresolved_reference', node, 'Reference has no same-file declaration in the isolated semantic program.');
          } else if (!seenSymbols.has(symbol)) {
            seenSymbols.add(symbol);
            for (const declaration of symbol.declarations) {
              if (declaration.getSourceFile() !== sf || within(declaration, root) || within(declaration, unit)) continue;
              const target = unitFor(declaration);
              if (!target) { gap('closure_capture', node, 'Outer local or unsupported declaration is not independently collected.'); continue; }
              const bodylessFunction = ts.isFunctionDeclaration(declaration) && !declaration.body;
              const implementedFunction = bodylessFunction && symbol.declarations.some(d => ts.isFunctionDeclaration(d) && !!d.body);
              if (!implementedFunction && (bodylessFunction ||
                  (!ts.isTypeAliasDeclaration(declaration) && !ts.isInterfaceDeclaration(declaration) &&
                   !!(ts.getCombinedModifierFlags(declaration) & ts.ModifierFlags.Ambient))))
                gap('declaration_only', node, 'Declaration target has no implementation.');
              if (ts.isImportDeclaration(target)) gap('external_dependency', node, 'Imported implementation and module effects are not collected.');
              if (ts.isVariableStatement(target)) gap('mutable_state', node, 'Declaration text does not establish runtime value, writes or object immutability.');
              if (ts.isClassDeclaration(target)) gap('class_state', node, 'Whole class text does not establish initialization, inheritance or dispatch.');
              add(target, depth + 1, node, symbol);
            }
          }
        }
      }
      ts.forEachChild(node, visit);
    };
    visit(unit);
  }
  const code = source.slice(selected.start, selected.end);
  const {callables: _unused, ...base} = metadata;
  return {...base, callable: selected, code,
    display_code: code.split(/\r\n|\r|\n/).map((line, i) => `${selected.location.line + i}: ${line}`).join('\n'),
    limitations: metadata.limitations.filter(x => x !== 'Dependency context is not collected.').concat([
      'Same-file semantic dependencies only; runtime state, external implementations, callers and module effects remain partial.']),
    coverage: 'partial', dependencies: [...dependencies.values()].sort((a, b) => a.start - b.start || a.end - b.end),
    gaps: gaps.sort((a, b) => a.start - b.start || a.end - b.end || a.code.localeCompare(b.code)),
    collection: {max_depth: maxDepth, max_dependency_chars: maxChars, dependency_chars: chars}};
}

export {collectProjectContext} from './project';

export {listCalledCallables} from './calls';

export {detectReferences, resolveReference} from './files';
