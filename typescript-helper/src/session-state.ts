import {appendFile, mkdir, readFile} from 'node:fs/promises';
import {isAbsolute, join} from 'node:path';
import {TextDecoder} from 'node:util';

export type JsonValue = null | boolean | number | string | JsonValue[] | {[key: string]: JsonValue};
export interface EventSource {kind: 'hook' | 'flow'; name: string}
export interface SessionEventInput {
  source: EventSource;
  type: string;
  payload: {[key: string]: JsonValue};
}
export interface SessionEvent extends SessionEventInput {timestamp: string}
export interface SessionStateAccess {
  save(event: SessionEventInput): Promise<SessionEvent>;
  load(): Promise<SessionEvent[]>;
}

function isObject(value: unknown): value is Record<string, unknown> {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) return false;
  const prototype = Object.getPrototypeOf(value);
  return prototype === Object.prototype || prototype === null;
}

/** Reject values JSON.stringify would silently omit or transform. */
function validateJson(value: unknown, ancestors = new Set<object>()): void {
  if (value === null || typeof value === 'string' || typeof value === 'boolean') return;
  if (typeof value === 'number' && Number.isFinite(value)) return;
  if (!Array.isArray(value) && !isObject(value)) throw new TypeError('Expected plain JSON data');
  const object = value as object;
  if (ancestors.has(object)) throw new TypeError('Cyclic JSON data');
  ancestors.add(object);
  const keys = Reflect.ownKeys(object);
  if (Array.isArray(value) && (Object.getPrototypeOf(value) !== Array.prototype || keys.length !== value.length + 1)) throw new TypeError('Sparse or decorated JSON array');
  for (const key of keys) {
    if (Array.isArray(value) && key === 'length') continue;
    if (typeof key !== 'string') throw new TypeError('Symbol JSON property');
    if (Array.isArray(value) && (!/^(0|[1-9][0-9]*)$/.test(key) || Number(key) >= value.length)) throw new TypeError('Decorated JSON array');
    const descriptor = Object.getOwnPropertyDescriptor(object, key)!;
    if (!descriptor.enumerable || !('value' in descriptor)) throw new TypeError('Expected enumerable JSON data property');
    validateJson(descriptor.value, ancestors);
  }
  ancestors.delete(object);
}

function validateEvent(value: unknown, stored: boolean): asserts value is SessionEventInput {
  validateJson(value);
  if (!isObject(value) || !isObject(value.source) ||
      !['hook', 'flow'].includes(value.source.kind as string) ||
      typeof value.source.name !== 'string' || value.source.name.trim() === '' ||
      typeof value.type !== 'string' || value.type.trim() === '' || !isObject(value.payload)) {
    throw new TypeError('Invalid session event: expected source, type and object payload');
  }
  if (stored && (typeof value.timestamp !== 'string' ||
      !/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z$/.test(value.timestamp) ||
      !Number.isFinite(Date.parse(value.timestamp)) || new Date(value.timestamp).toISOString() !== value.timestamp)) {
    throw new TypeError('Invalid session event timestamp');
  }
}

/** Append-only storage. Share one instance per session; no cross-process locking. */
export class SessionStateStore implements SessionStateAccess {
  private readonly directory: string;
  private readonly path: string;
  private queue: Promise<unknown> = Promise.resolve();

  constructor(logsRoot: string, sessionId: string) {
    if (typeof logsRoot !== 'string' || !isAbsolute(logsRoot)) throw new TypeError('logsRoot must be absolute');
    if (typeof sessionId !== 'string' || !/^[A-Za-z0-9_-]+$/.test(sessionId)) throw new TypeError('Invalid sessionId');
    this.directory = join(logsRoot, 'session-state');
    this.path = join(this.directory, sessionId + '.jsonl');
  }

  save(input: SessionEventInput): Promise<SessionEvent> {
    // Capture bytes before queueing, including a detached returned event.
    let serialized: string;
    try {
      validateEvent(input, false);
      serialized = JSON.stringify({source: input.source, type: input.type, payload: input.payload,
        timestamp: new Date().toISOString()});
    } catch (error) {
      return Promise.reject(error);
    }
    return this.enqueue(async () => {
      const history = await this.read();
      this.parse(history);
      await mkdir(this.directory, {recursive: true});
      const separator = history.length > 0 && !history.endsWith('\n') ? '\n' : '';
      await appendFile(this.path, separator + serialized + '\n', {encoding: 'utf8', flag: 'a'});
      return JSON.parse(serialized) as SessionEvent;
    });
  }

  load(): Promise<SessionEvent[]> {
    return this.enqueue(async () => this.parse(await this.read()));
  }

  private enqueue<T>(operation: () => Promise<T>): Promise<T> {
    const result = this.queue.then(operation);
    this.queue = result.catch(() => undefined);
    return result;
  }

  private async read(): Promise<string> {
    try {
      const bytes = await readFile(this.path);
      const decoder = new TextDecoder('utf-8', {fatal: true, ignoreBOM: true});
      const lines: string[] = [];
      let start = 0;
      while (start <= bytes.length) {
        const newline = bytes.indexOf(10, start);
        const end = newline === -1 ? bytes.length : newline;
        try {
          lines.push(decoder.decode(bytes.subarray(start, end)));
        } catch (cause) {
          throw new Error(`Invalid UTF-8 session log ${this.path} at line ${lines.length + 1}`, {cause});
        }
        if (newline === -1) break;
        start = newline + 1;
      }
      return lines.join('\n');
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code === 'ENOENT') return '';
      throw error;
    }
  }

  private parse(text: string): SessionEvent[] {
    if (text === '') return [];
    const lines = text.split('\n');
    if (lines[lines.length - 1] === '') lines.pop();
    return lines.map((line, index) => {
      try {
        const event: unknown = JSON.parse(line);
        validateEvent(event, true);
        return event as SessionEvent;
      } catch (cause) {
        throw new Error(`Invalid session log ${this.path} at line ${index + 1}`, {cause});
      }
    });
  }
}
