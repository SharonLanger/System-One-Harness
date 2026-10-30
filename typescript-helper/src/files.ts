import * as fs from 'node:fs';
import * as path from 'node:path';

export interface UtilityDiagnostic {code: string; message: string}
export interface UtilityOutcome<T> {
  status: 'ok' | 'partial' | 'error'; data: T | null; diagnostics: UtilityDiagnostic[];
}
export interface DetectionConfig {
  preset?: 'production' | 'test'; include_patterns?: string[]; exclude_patterns?: string[];
}
export interface FileReference {
  path: string; filename: string; start: number; end: number;
  category: 'production_code' | 'test_code' | 'declaration' | 'non_code';
}
export interface ReferenceResolution {
  resolution: 'resolved' | 'missing' | 'ambiguous' | 'outside_repository' | 'not_file';
  selected_path: string | null; candidates: string[];
}
const error = <T>(code: string, message: string): UtilityOutcome<T> =>
  ({status: 'error', data: null, diagnostics: [{code, message}]});
const ok = <T>(data: T): UtilityOutcome<T> => ({status: 'ok', data, diagnostics: []});
const validPath = (value: unknown): value is string => typeof value === 'string' &&
  !!value.trim() && !/[\\\x00-\x1f\x7f]/.test(value);

/** README: Detection. Pure lexical POSIX references; configured exclusions win. */
export function detectReferences(text: string, config: DetectionConfig = {}): UtilityOutcome<{references: FileReference[]}> {
  if (typeof text !== 'string' || !config || typeof config !== 'object' || Array.isArray(config) ||
      Object.keys(config).some(k => !['preset', 'include_patterns', 'exclude_patterns'].includes(k)) ||
      (config.preset !== undefined && config.preset !== 'production' && config.preset !== 'test'))
    return error('invalid_input', 'Expected text and a production/test detector configuration.');
  let include: RegExp[], exclude: RegExp[];
  try {
    const compile = (value: unknown, fallback: string[]): RegExp[] => {
      const patterns = value === undefined ? fallback : value;
      if (!Array.isArray(patterns) || !patterns.every(p => typeof p === 'string')) throw new Error('Patterns must be arrays of strings.');
      return patterns.map(p => new RegExp(p));
    };
    include = compile(config.include_patterns, config.preset === 'test' ? ['(?:\\.spec\\.ts|\\.test\\.ts)$'] : ['\\.ts$']);
    exclude = compile(config.exclude_patterns, config.preset === 'test' ? ['\\.d\\.ts$'] : ['(?:\\.spec\\.ts|\\.test\\.ts|\\.d\\.ts)$']);
  } catch (e) { return error('invalid_input', `Invalid detector patterns: ${String(e)}`); }
  const references: FileReference[] = [];
  // Recognize the entire filename before filtering; never restart inside a rejected name.
  const mentions = /(["'`])([^"'`\r\n]+)\1|(?<![\p{L}\p{N}_./@+\\-])([\p{L}\p{N}_./@+-]+\.[\p{L}\p{N}_-]+)(?::\d+(?::\d+)?)?/gu;
  for (const match of text.matchAll(mentions)) {
    const raw = match[2] ?? match[3];
    if (!validPath(raw) || !/[^/]+\.[\p{L}\p{N}_-]+$/u.test(raw)) continue;
    if (!include.some(pattern => pattern.test(raw)) || exclude.some(pattern => pattern.test(raw))) continue;
    const filename = raw.slice(raw.lastIndexOf('/') + 1);
    const category = filename.endsWith('.d.ts') ? 'declaration' : /\.(?:spec|test)\.ts$/.test(filename) ? 'test_code'
      : /\.(?:ts|tsx|js|jsx)$/.test(filename) ? 'production_code' : 'non_code';
    const start = match.index! + (match[2] === undefined ? 0 : 1);
    references.push({path: raw, filename, start, end: start + raw.length, category});
  }
  return ok({references});
}

const inside = (candidate: string, root: string): boolean => {
  const relative = path.relative(root, candidate);
  return relative === '' || (relative !== '..' && !relative.startsWith('..' + path.sep) && !path.isAbsolute(relative));
};
const missing = (e: unknown) => ['ENOENT', 'ENOTDIR'].includes((e as NodeJS.ErrnoException).code ?? '');
// Canonicalize existing parents too, so a nonexistent child of an escaping symlink cannot look confined.
function canonicalCandidate(candidate: string): string {
  try { return fs.realpathSync(candidate); }
  catch (e) {
    if (!missing(e)) throw e;
    const parent = path.dirname(candidate);
    if (parent === candidate) return candidate;
    return path.join(canonicalCandidate(parent), path.basename(candidate));
  }
}

/** README: Resolution. Generic exact lookup then whole-component suffix search within the repository. */
export function resolveReference(reference: string, cwd: string, repositoryRoot: string): UtilityOutcome<ReferenceResolution> {
  if (!validPath(reference) || !validPath(cwd) || !validPath(repositoryRoot))
    return error('invalid_input', 'Expected a nonempty POSIX reference, cwd and repository_root without control characters.');
  let root: string, current: string;
  try {
    root = fs.realpathSync(repositoryRoot); current = fs.realpathSync(cwd);
    if (!fs.statSync(root).isDirectory() || !fs.statSync(current).isDirectory() || !inside(current, root))
      return error('invalid_input', 'cwd must be a directory inside repository_root.');
  } catch (e) { return error('io_error', `Cannot access repository_root/cwd: ${String(e)}`); }
  const result = (resolution: ReferenceResolution['resolution'], candidates: string[] = []) =>
    ok({resolution, selected_path: resolution === 'resolved' ? candidates[0] : null, candidates});
  const navigation = reference.split('/').some(segment => segment === '.' || segment === '..');
  try {
    const exact = new Set<string>(); let outside = false, notFile = false;
    const bases = path.isAbsolute(reference) ? [reference] : [path.resolve(current, reference), path.resolve(root, reference)];
    for (const candidate of new Set(bases)) {
      const canonical = canonicalCandidate(candidate);
      if (!inside(canonical, root)) { outside = true; continue; }
      let stat: fs.Stats;
      try { stat = fs.statSync(canonical); }
      catch (e) { if (missing(e)) continue; throw e; }
      if (!stat.isFile()) { notFile = true; continue; }
      fs.accessSync(canonical, fs.constants.R_OK); exact.add(canonical);
    }
    const exactPaths = [...exact].sort();
    if (exactPaths.length) return result(exactPaths.length === 1 ? 'resolved' : 'ambiguous', exactPaths);
    if (path.isAbsolute(reference) || navigation) return result(outside ? 'outside_repository' : notFile ? 'not_file' : 'missing');
    if (notFile) return result('not_file');
    const wanted = reference.split('/').filter(Boolean), basename = wanted[wanted.length - 1];
    const matches = new Set<string>();
    const scan = (directory: string): void => {
      for (const entry of fs.readdirSync(directory, {withFileTypes: true})) {
        if (entry.name === '.git' || entry.name === 'node_modules') continue;
        const candidate = path.join(directory, entry.name);
        if (entry.isDirectory()) { scan(candidate); continue; }
        if (entry.name !== basename || !(entry.isFile() || entry.isSymbolicLink())) continue;
        const components = path.relative(root, candidate).split(path.sep);
        if (components.length < wanted.length || !wanted.every((segment, i) => segment === components[components.length - wanted.length + i])) continue;
        const canonical = canonicalCandidate(candidate);
        if (!inside(canonical, root)) { outside = true; continue; }
        let stat: fs.Stats;
        try { stat = fs.statSync(canonical); } catch (e) { if (missing(e)) continue; throw e; }
        if (!stat.isFile()) continue; // Includes symlink directories: never traversed.
        fs.accessSync(canonical, fs.constants.R_OK); matches.add(canonical);
      }
    };
    scan(root);
    const candidates = [...matches].sort();
    return result(candidates.length === 1 ? 'resolved' : candidates.length > 1 ? 'ambiguous' : outside ? 'outside_repository' : 'missing', candidates);
  } catch (e) { return error('io_error', `Path lookup/scan failed; no candidate selected: ${String(e)}`); }
}
