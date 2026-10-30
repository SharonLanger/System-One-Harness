import {readFileSync} from 'node:fs';
import {outline, extractCallable, collectLocalContext, collectProjectContext, listCalledCallables, getCalledMethodLocations, getCallingMethodLocations, detectReferences, resolveReference} from './index';
try {
  const request: unknown = JSON.parse(readFileSync(0, 'utf8'));
  if (request && typeof request === 'object' && !Array.isArray(request) && 'action' in request &&
      (request.action === 'detect_references' || request.action === 'resolve_reference')) {
    const r = request as Record<string, unknown>;
    const result = request.action === 'detect_references'
      ? detectReferences(r.text as string, r.config as Parameters<typeof detectReferences>[1])
      : resolveReference(r.reference as string, r.cwd as string, r.repository_root as string);
    process.stdout.write(JSON.stringify(result) + '\n');
  } else {
  if (!request || typeof request !== 'object' || Array.isArray(request) ||
      !('action' in request) || (request.action !== 'outline' && request.action !== 'extract' && request.action !== 'collect_local_context' && request.action !== 'collect_project_context' && request.action !== 'list_called_callables' && request.action !== 'get_called_method_locations' && request.action !== 'get_calling_method_locations') ||
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
    if ((request.action === 'collect_project_context' || request.action === 'list_called_callables') && (!('repository_root' in request) || typeof request.repository_root !== 'string' || !request.repository_root)) throw new Error('Project collection requires repository_root');
    if ((request.action === 'get_called_method_locations' || request.action === 'get_calling_method_locations') && (!('project_root' in request) || typeof request.project_root !== 'string' || !request.project_root)) throw new Error('Navigation requires project_root');
    if (request.action === 'get_calling_method_locations' && (!('tsconfig_path' in request) || typeof request.tsconfig_path !== 'string' || !request.tsconfig_path)) throw new Error('Incoming navigation requires tsconfig_path');
    result = request.action === 'get_called_method_locations' ? getCalledMethodLocations(request.path, request.id, {projectRoot: (request as Record<string, unknown>).project_root as string}) : request.action === 'get_calling_method_locations' ? getCallingMethodLocations(request.path, request.id, {projectRoot: (request as Record<string, unknown>).project_root as string, tsconfigPath: (request as Record<string, unknown>).tsconfig_path as string}) : request.action === 'list_called_callables' ? listCalledCallables(request.path, request.id, {repositoryRoot: 'repository_root' in request ? request.repository_root as string : ''}) : request.action === 'collect_project_context' ? collectProjectContext(request.path, request.id, {
      repositoryRoot: 'repository_root' in request ? request.repository_root as string : '',
      maxDepth: 'max_depth' in request ? request.max_depth as number : undefined,
      maxDependencyChars: 'max_dependency_chars' in request ? request.max_dependency_chars as number : undefined
    }) : request.action === 'extract' ? extractCallable(request.path, request.id) : collectLocalContext(request.path, request.id, {
      maxDepth: 'max_depth' in request ? request.max_depth as number : undefined,
      maxDependencyChars: 'max_dependency_chars' in request ? request.max_dependency_chars as number : undefined
    });
  }
  process.stdout.write(JSON.stringify(result) + '\n');
  }
} catch (error) {
  process.stderr.write((error instanceof Error ? error.message : String(error)) + '\n');
  process.exitCode = 1;
}
