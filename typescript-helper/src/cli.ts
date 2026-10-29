import {readFileSync} from 'node:fs';
import {outline} from './index';
try {
  const request: unknown = JSON.parse(readFileSync(0, 'utf8'));
  if (!request || typeof request !== 'object' || Array.isArray(request) ||
      !('action' in request) || request.action !== 'outline' ||
      !('path' in request) || typeof request.path !== 'string' || !request.path) {
    throw new Error('Expected {action:"outline", path:<nonempty string>}');
  }
  process.stdout.write(JSON.stringify(outline(request.path)) + '\n');
} catch (error) {
  process.stderr.write((error instanceof Error ? error.message : String(error)) + '\n');
  process.exitCode = 1;
}
