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
        const name = binding ? binding.name.getText(sf) : ts.isConstructorDeclaration(node) ? 'constructor'
          : ts.isFunctionDeclaration(node) ? (node.name?.text ??
            (node.modifiers?.some(m => m.kind === ts.SyntaxKind.DefaultKeyword) ? '<default>' : anonymous))
          : ('name' in node && node.name ? node.name.getText(sf) : anonymous);
        callables.push({id: `${hash}:${start}:${end}`, name,
          signature: source.slice(binding ? binding.getStart(sf) : start, node.body.getStart(sf)).trimEnd(), start, end,
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
  return {source, outline: {schema_version: 1, path: canonical, source_hash: hash, callables, diagnostics,
    limitations: ['Runtime callable bodies are discovered recursively; destructuring-bound callable expressions remain unsupported.',
      'Locations and ranges use UTF-16 code units; comments before declarations are excluded.',
      'Bound expression signatures include their immediate binding header and transparent wrappers; raw code is only the callable expression.',
      'Type-only signatures are not runtime implementation candidates; computed names are source text, never evaluated.',
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
