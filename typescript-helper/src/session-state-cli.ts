import {TextDecoder} from 'node:util';
import {SessionStateStore, type SessionEventInput} from './session-state';

// The bridge request contains metadata and one event, never the hook summary.
const MAX_INPUT_BYTES = 1024 * 1024;

async function main(): Promise<void> {
  const chunks: Buffer[] = [];
  let length = 0;
  for await (const chunk of process.stdin) {
    const bytes = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk);
    length += bytes.length;
    if (length > MAX_INPUT_BYTES) throw new Error('Session state request exceeds 1048576 bytes');
    chunks.push(bytes);
  }
  let request: unknown;
  try {
    request = JSON.parse(new TextDecoder('utf-8', {fatal: true}).decode(Buffer.concat(chunks, length)));
  } catch {
    throw new Error('Session state request must be valid UTF-8 JSON');
  }
  if (request === null || typeof request !== 'object' || Array.isArray(request)) {
    throw new TypeError('Session state request must be an object');
  }
  const {logsRoot, sessionId, event} = request as Record<string, unknown>;
  if (typeof logsRoot !== 'string' || typeof sessionId !== 'string') {
    throw new TypeError('Session state request requires string logsRoot and sessionId');
  }
  const store = new SessionStateStore(logsRoot, sessionId);
  await store.save(event as SessionEventInput);
}

void main().catch((error: unknown) => {
  process.stderr.write(`session-state-cli: ${error instanceof Error ? error.message : 'Unknown error'}\n`);
  process.exitCode = 1;
});
