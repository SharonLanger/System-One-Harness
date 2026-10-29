import {readFileSync} from 'node:fs';
import {outline, extractCallable, collectLocalContext} from './index';
try {
  const request: unknown = JSON.parse(readFileSync(0, 'utf8'));
  if (!request || typeof request !== 'object' || Array.isArray(request) ||
      !('action' in request) || (request.action !== 'outline' && request.action !== 'extract' && request.action !== 'collect_local_context') ||
      !('path' in request) || typeof request.path !== 'string' || !request.path) {
    throw new Error('Expected {action:"outline", path:<nonempty string>}');
  }
  let result;
  if (request.action === 'outline') {
    result = outline(request.path);
  } else {
    if (!('id' in request) || typeof request.id !== 'string' || !request.id) {
      throw new Error('Extract request requires a nonempty id');
    }
    result = request.action === 'extract' ? extractCallable(request.path, request.id) : collectLocalContext(request.path, request.id, {
      maxDepth: 'max_depth' in request ? request.max_depth as number : undefined,
      maxDependencyChars: 'max_dependency_chars' in request ? request.max_dependency_chars as number : undefined
    });
  }
  process.stdout.write(JSON.stringify(result) + '\n');
} catch (error) {
  process.stderr.write((error instanceof Error ? error.message : String(error)) + '\n');
  process.exitCode = 1;
}
