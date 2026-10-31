# Hook invocation logs

In an editable installation the shared JSONL log is
`<laya-context-router>/src/logs/debug.jsonl`. Records contain timestamp, PID,
parent PID, invocation ID and hook name. Session ID is added when available.
These logs include prompt text and supplied hook fields.

## Gateway

- `gateway_started`: after valid argument parsing and deadline setup, before stdin
  is read; includes mode, process cwd, supplied project environment and source-root
  argument. Interpreter/module startup failures cannot be logged by the gateway.
- `gateway_input_received`: original stdin text before JSON validation, bounded
  to 65,536 characters, plus read count and truncation flag. Available even for
  malformed/oversized input; oversized input contains only the captured prefix.
- `gateway_received`: parsed payload and field names after JSON validation.
- `gateway_dispatch_started` / `gateway_dispatch_finished`: common dispatch call
  and returned result type. An exception or timeout can prevent a finish record.
- Existing `gateway_error`, `gateway_noop`, `response_prepared` and
  `gateway_finished` show errors, response size, result and stdout bytes written.

## Common dispatcher and event dispatcher

- `hook_dispatcher_started`: entry and command hook name.
- `common_input_validated`: validated common and derived field names.
- `hook_dispatcher_routed`: event destination and common/derived metadata.
- `hook_dispatcher_route_skipped`: unsupported event, with reason.
- `hook_dispatcher_rejected`: validation stage, field and error code.
- `event_dispatcher_started`: event dispatcher entry and received envelope metadata.
- `hook_input_ingested`: prompt length, cwd and project/source-root metadata.
- `feature_started` / `feature_finished`: feature result, duration and failure code.
- `event_input_rejected`: invalid event-specific input.
- `event_dispatcher_finished` / `hook_dispatcher_finished`: returned result type,
  no-op reason or failure code, including unexpected-exception markers.

Observe-only mode logs gateway entry/input plus the existing
`observation_input_received` and `hook_observed` records. It never logs actual
 dispatch entry because no dispatcher runs. Intended dispatch destinations remain
in `hook_observed` with `dispatcher_invoked: false`.

Logs use the existing local file sink, never protocol stdout. Raw capture does
not dump the full process environment or read a transcript. Deadline expiration
can prevent subsequent logging; a missing finish record is not proof of success.
