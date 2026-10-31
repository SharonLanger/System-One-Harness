const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {spawnSync} = require('node:child_process');

const cli = path.resolve(__dirname, '../../build/typescript/session-state-cli.js');
const event = {source: {kind: 'hook', name: 'PostCompact'}, type: 'PostCompact', payload: {}};
function fixture(t) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'laya-state-cli-'));
  t.after(() => fs.rmSync(root, {recursive: true, force: true}));
  const logsRoot = path.join(root, 'logs');
  const request = {logsRoot, sessionId: 'session-01', event};
  const file = path.join(logsRoot, 'session-state', 'session-01.jsonl');
  return {root, logsRoot, request, file};
}
function run(input) {
  const result = spawnSync(process.execPath, [cli], {input, encoding: 'utf8', timeout: 10000});
  assert.ifError(result.error);
  assert.equal(result.signal, null);
  assert.equal(result.stdout, '');
  return result;
}
function fails(input, pattern) {
  const result = run(input);
  assert.equal(result.status, 1);
  assert.match(result.stderr, pattern);
}

test('standalone CLI awaits appends, preserves history and isolates sessions silently', t => {
  const f = fixture(t);
  const first = {...event, source: {kind: 'flow', name: 'enrichment'}, type: 'context_enriched',
    payload: {text: 'quotes " / \\ newline\n שלום 😀'}};
  for (const request of [{...f.request, event: first}, f.request, {...f.request, sessionId: 'other'}]) {
    const result = run(JSON.stringify(request));
    assert.equal(result.status, 0);
    assert.equal(result.stderr, '');
  }
  const records = fs.readFileSync(f.file, 'utf8').trimEnd().split('\n').map(JSON.parse);
  assert.equal(records.length, 2);
  for (const [i, expected] of [first, event].entries()) {
    const {timestamp, ...saved} = records[i];
    assert.deepEqual(saved, expected);
    assert.equal(timestamp, new Date(timestamp).toISOString());
  }
  assert.equal(fs.readFileSync(path.join(path.dirname(f.file), 'other.jsonl'), 'utf8').trimEnd().split('\n').length, 1);
});

test('invalid JSON, UTF-8, request fields, paths and events fail without creating logs', t => {
  const f = fixture(t);
  for (const input of ['', '{', 'null', '[]', '42', Buffer.from([0xff])]) {
    fails(input, /request/);
  }
  for (const request of [{}, {...f.request, logsRoot: 4}, {...f.request, logsRoot: 'relative'},
    {...f.request, sessionId: '../escape'}, {...f.request, sessionId: ''},
    {...f.request, sessionId: null}, {...f.request, event: undefined}, {...f.request, event: {}},
    {...f.request, event: {...event, payload: []}}]) {
    fails(JSON.stringify(request), /request|absolute|sessionId|session event|JSON/);
  }
  assert.equal(fs.existsSync(f.logsRoot), false);
});

test('input cap accepts exactly 1 MiB and rejects one byte more including UTF-8 bytes', t => {
  const f = fixture(t);
  const request = JSON.stringify(f.request);
  const exact = request + ' '.repeat(1024 * 1024 - Buffer.byteLength(request));
  assert.equal(run(exact).status, 0);
  const before = fs.readFileSync(f.file);
  fails(exact + ' ', /exceeds 1048576 bytes/);
  fails(JSON.stringify({...f.request, event: {...event, payload: {text: '😀'.repeat(262144)}}}), /exceeds/);
  assert.deepEqual(fs.readFileSync(f.file), before);
});

test('malformed history and filesystem errors propagate without false success or repairs', t => {
  const f = fixture(t);
  fs.mkdirSync(path.dirname(f.file), {recursive: true});
  fs.writeFileSync(f.file, '{"partial":');
  fails(JSON.stringify(f.request), /Invalid session log.*line 1/);
  assert.equal(fs.readFileSync(f.file, 'utf8'), '{"partial":');
  const blocked = path.join(f.root, 'blocked');
  fs.writeFileSync(blocked, 'file');
  fails(JSON.stringify({...f.request, logsRoot: blocked}), /ENOTDIR|EEXIST/);
  assert.equal(fs.readFileSync(blocked, 'utf8'), 'file');
});

test('compiled entry loads only the standalone store and Node builtins', () => {
  const source = fs.readFileSync(cli, 'utf8');
  const imports = [...source.matchAll(/require\("([^"]+)"\)/g)].map(match => match[1]);
  assert.deepEqual(imports.sort(), ['./session-state', 'node:util']);
});
