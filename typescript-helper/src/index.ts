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
export function outline(path: string): Outline {
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
  const visit = (node: ts.Node): void => {
    const callable = ts.isFunctionDeclaration(node) || ts.isFunctionExpression(node) ||
      ts.isArrowFunction(node) || ts.isMethodDeclaration(node) || ts.isConstructorDeclaration(node) ||
      ts.isGetAccessorDeclaration(node) || ts.isSetAccessorDeclaration(node);
    if (callable) {
      const supported = ts.isFunctionDeclaration(node) && node.parent === sf &&
        !!node.name && !!node.body && !node.asteriskToken &&
        !node.modifiers?.some(m => m.kind === ts.SyntaxKind.AsyncKeyword) &&
        !overloaded.has(node.name.text);
      const start = node.getStart(sf), end = node.getEnd();
      if (supported && ts.isFunctionDeclaration(node) && node.name && node.body) {
        const pos = sf.getLineAndCharacterOfPosition(start);
        callables.push({id: `${hash}:${start}:${end}`, name: node.name.text,
          signature: source.slice(start, node.body.getStart(sf)).trimEnd(), start, end,
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
  return {schema_version: 1, path: canonical, source_hash: hash, callables, diagnostics,
    limitations: ['Only ordinary named top-level function implementations are supported.',
      'Locations and ranges use UTF-16 code units; comments before declarations are excluded.',
      'Dependency context is not collected.']};
}
