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
function readOutline(path: string): {outline: Outline; source: string} {
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
  const overloaded = new Set(sf.statements.filter(ts.isFunctionDeclaration)
    .filter(n => !n.body && n.name).map(n => n.name!.text));
  const topVariable = (node: ts.Node): node is ts.VariableDeclaration =>
    ts.isVariableDeclaration(node) && ts.isIdentifier(node.name) &&
    ts.isVariableDeclarationList(node.parent) && ts.isVariableStatement(node.parent.parent) &&
    node.parent.parent.parent === sf;
  const boundContainer = (node: ts.Node): boolean =>
    topVariable(node.parent) && node.parent.initializer === node;
  const classContainer = (node: ts.Node): boolean =>
    (ts.isClassDeclaration(node) && !!node.name && node.parent === sf) ||
    (ts.isClassExpression(node) && boundContainer(node));
  const objectContainer = (node: ts.Node): boolean =>
    ts.isObjectLiteralExpression(node) && boundContainer(node);
  const bindingFor = (node: ts.Node): ts.VariableDeclaration | ts.PropertyDeclaration | ts.PropertyAssignment | undefined => {
    const parent = node.parent;
    if (topVariable(parent) && parent.initializer === node) return parent;
    if ((ts.isPropertyDeclaration(parent) && classContainer(parent.parent) ||
         ts.isPropertyAssignment(parent) && objectContainer(parent.parent)) &&
        parent.initializer === node && !ts.isComputedPropertyName(parent.name)) return parent;
    return undefined;
  };
  const visit = (node: ts.Node): void => {
    const callable = ts.isFunctionDeclaration(node) || ts.isFunctionExpression(node) ||
      ts.isArrowFunction(node) || ts.isMethodDeclaration(node) || ts.isConstructorDeclaration(node) ||
      ts.isGetAccessorDeclaration(node) || ts.isSetAccessorDeclaration(node);
    if (callable) {
      const ordinaryFunction = ts.isFunctionDeclaration(node) && node.parent === sf &&
        !!node.name && !!node.body && !node.asteriskToken &&
        !node.modifiers?.some(m => m.kind === ts.SyntaxKind.AsyncKeyword) &&
        !overloaded.has(node.name.text);
      const classMember = (ts.isMethodDeclaration(node) || ts.isConstructorDeclaration(node) ||
        ts.isGetAccessorDeclaration(node) || ts.isSetAccessorDeclaration(node)) &&
        classContainer(node.parent) && (!node.name || !ts.isComputedPropertyName(node.name));
      const objectMember = (ts.isMethodDeclaration(node) || ts.isGetAccessorDeclaration(node) ||
        ts.isSetAccessorDeclaration(node)) && objectContainer(node.parent) &&
        !ts.isComputedPropertyName(node.name);
      const binding = ts.isFunctionExpression(node) || ts.isArrowFunction(node) ? bindingFor(node) : undefined;
      const supported = (ordinaryFunction || classMember || objectMember || !!binding) && !!node.body;
      const start = node.getStart(sf), end = node.getEnd();
      if (supported && node.body) {
        const pos = sf.getLineAndCharacterOfPosition(start);
        callables.push({id: `${hash}:${start}:${end}`,
          name: binding ? binding.name.getText(sf) : ts.isConstructorDeclaration(node) ? 'constructor'
            : ts.isFunctionDeclaration(node) ? node.name!.text
            : ('name' in node && node.name ? node.name.getText(sf) : ''),
          signature: source.slice(binding ? binding.getStart(sf) : start, node.body.getStart(sf)).trimEnd(), start, end,
          location: {line: pos.line + 1, column: pos.character + 1}});
      } else {
        const name = 'name' in node && node.name ? (node.name as ts.Node).getText(sf) : '';
        diagnostics.push({code: 'unsupported_callable',
          message: `Unsupported ${ts.SyntaxKind[node.kind]}${name ? ' ' + name : ''}`,
          start, end});
      }
    }
    ts.forEachChild(node, visit);
  };
  visit(sf);
  return {source, outline: {schema_version: 1, path: canonical, source_hash: hash, callables, diagnostics,
    limitations: ['Supported: ordinary named top-level functions, class declaration members, and directly top-level-bound expressions, objects and class expressions. Computed, wrapped and nested callable forms remain unsupported.',
      'Locations and ranges use UTF-16 code units; comments before declarations are excluded.',
      'Bound expression signatures include their immediate binding header; raw code is only the callable expression.',
      'Dependency context is not collected.']}};
}


export function outline(path: string): Outline {
  return readOutline(path).outline;
}
export interface CallableSource extends Omit<Outline, 'callables'> {
  callable: Callable; code: string; display_code: string;
}
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
