"""Reporting helper: read one hook child's existing logs without rerunning Laya."""
import json
import re


def fenced(text, language="text"):
    """Keep source-code backticks from closing the report's display box."""
    fence = "`" * max(3, 1 + max((len(m.group()) for m in re.finditer(r"`+", text)), default=0))
    return f"{fence}{language}\n{text}\n{fence}\n"


def current_hook_records(details):
    records=[r for r in details.get('trace',[]) if r.get('component') in {'hook','hook_gateway'}]
    pid=details.get('hook_pid')
    if pid is not None:records=[r for r in records if r.get('pid')==pid]
    starts=[r for r in records if r.get('event')=='gateway_received']
    ends=[r for r in records if r.get('event')=='gateway_finished']
    anchor=(starts or ends or [None])[-1]
    invocation=anchor.get('details',{}).get('invocation_id') if anchor else None
    if invocation is not None:
        records=[r for r in records if r.get('component')=='hook_gateway'
                 and r.get('details',{}).get('invocation_id')==invocation]
    return records


def gateway_outcome(details):
    return next((r.get('details',{}) for r in reversed(current_hook_records(details))
                 if r.get('event')=='gateway_finished'),{})


def hook_output_sections(details):
    """Captured stdout proves returned bytes; preparation is metadata only."""
    records=current_hook_records(details)
    prepared=next((r.get('details',{}) for r in reversed(records)
                   if r.get('event')=='response_prepared'),{})
    rejected=next((r.get('details',{}) for r in reversed(records)
                   if r.get('event')=='response_rejected'),{})
    final=gateway_outcome(details)
    raw=details.get('stdout','')
    try:actual=json.loads(raw)
    except (ValueError,TypeError):actual=None
    specific=actual.get('hookSpecificOutput') if isinstance(actual,dict) else None
    returned=isinstance(specific,dict) and isinstance(specific.get('additionalContext'),str)
    partial=final.get('code')=='stdout_write_failed' or bool(prepared and (not final or final.get('stdout_bytes_written') is None))
    lines=['\n## Hook output — what was actually returned\n']
    if returned:
        lines.append('**Returned by the hook subprocess.** Live delivery to Claude is not verified by replay.\n')
        response=actual;label='Returned'
    else:
        if partial or raw.strip():
            lines.append('**Complete response not captured; partial delivery may have occurred.** See raw stdout in details.json.\n')
        else:
            lines.append("**No context was returned. stdout was empty.** The report's `null` is a missing parsed response; the hook did not send JSON `null`.\n")
        response=prepared.get('response')
        label='Prepared only — delivery not confirmed'
        if rejected:
            lines.append(f"Rejection: **{rejected.get('reason')}**.\n")
    if prepared and 'response' not in prepared:
        lines.append(f"Preparation metadata: event **{prepared.get('hook_event_name','unknown')}**, serialized bytes **{prepared.get('serialized_bytes','unknown')}**. Prepared payload content was not logged.\n")
    if final:
        lines.append(f"Gateway outcome: **{final.get('outcome')}**; reason/code **{final.get('reason') or final.get('code')}**; bytes written **{final.get('stdout_bytes_written')}**. This is not a Claude receipt.\n")
    specific = response.get("hookSpecificOutput") if isinstance(response, dict) else None
    context = specific.get("additionalContext") if isinstance(specific, dict) else None
    if not isinstance(context, str):
        lines.append("No prepared response was captured either; a payload cannot be shown from this run.\n")
        return "\n".join(lines)
    lines.append(f"\n### {label}: complete hook JSON\n\n"
                 "This is the hook protocol envelope; `additionalContext` is the string added alongside the prompt.\n\n"
                 + fenced(json.dumps(response, indent=2, ensure_ascii=False), "json"))
    lines.append(f"\n### {label}: additionalContext — exact text\n\n"
                 f"The box contains only the {len(context):,}-character string value, with no JSON-envelope escaping.\n\n"
                 + fenced(context))
    # The existing hook embeds a JSON context object after its first header line.
    # Decode only for display; never alter the string returned by the hook.
    try:
        header, body = context.split("\n", 1)
        content = json.loads(body)
    except (ValueError, TypeError):
        content = None
    if isinstance(content, dict):
        if isinstance(content.get("code"), str):
            lines.append("\n### Selected method code inside that context\n\n"
                         "This is one field of the payload above, not the entire additionalContext.\n\n"
                         + fenced(content["code"], "typescript"))
        lines.append("\n<details>\n<summary>All context fields, formatted for reading</summary>\n\n"
                     "Display formatting only; the exact original string is shown above.\n\n"
                     + fenced(json.dumps(content, indent=2, ensure_ascii=False), "json") + "\n</details>\n")
    return "\n".join(lines)


def read_trace(path, offset, pid):
    records, warnings = [], []
    if pid is None:
        return records, ["The hook subprocess was not started."]
    try:
        with path.open("rb") as handle:
            if path.stat().st_size < offset:
                offset = 0
                warnings.append("The debug log was truncated during this replay.")
            handle.seek(offset)
            for line in handle:
                try:
                    record = json.loads(line)
                except (ValueError, UnicodeDecodeError):
                    warnings.append("An unreadable log line was skipped; trace may be incomplete.")
                    continue
                if isinstance(record, dict) and record.get("pid") == pid:
                    records.append(record)
    except OSError as exc:
        warnings.append(f"Could not read debug log: {exc}")
    if not records:
        warnings.append("No log records were found for this hook PID; this does not prove that Laya ran.")
    return records, warnings


def collect_calls(records):
    calls = []
    for record in records:
        component, event = record.get("component"), record.get("event")
        data = record.get("details", {})
        if component == "laya" and event == "prediction_started":
            calls.append({"submitted_text": data.get("text"), "submitted_questions": data.get("questions"),
                          "config": {key: data.get(key) for key in ("model", "temperature", "lang")},
                          "agent_ready": False, "response_received": False, "response_validated": False,
                          "raw_response": None, "enriched_answers": {}, "applied_rules": {},
                          "decisions": {}, "errors": []})
        if not calls:
            continue
        call = calls[-1]
        if component == "laya":
            if event in {"load_completed", "agent_reused"}:
                call["agent_ready"] = True
            elif event == "response_received":
                call["response_received"] = True
                call["raw_response"] = data.get("response")
            elif event == "response_validated":
                call["response_validated"] = True
        elif component == "enrichment" and event == "completed":
            call["enriched_answers"][data["question"]] = data.get("enriched")
        elif component == "rules" and event == "evaluation_started":
            call["applied_rules"][data["question"]] = data
        elif component == "rules" and event == "decision":
            call["decisions"][data["question"]] = data.get("decision")
        if record.get("error"):
            call["errors"].append(record["error"])
    return calls


def render_summary(details):
    def section(title, value):
        return f"\n## {title}\n\n```json\n{json.dumps(value, indent=2, ensure_ascii=False)}\n```\n"

    finished = next((record.get("details", {}) for record in reversed(details["trace"])
                     if record.get("component") == "flow" and record.get("event") == "finished"), {})
    final = gateway_outcome(details)
    reason = (final.get("reason") or final.get("code")) if final else finished.get("reason")
    if reason is None:
        reason = next((line.strip() for line in reversed(details["stderr"].splitlines())
                       if "laya hook noop:" in line), None)
    lines = ["# UserPromptSubmit replay\n",
             f"Outcome: **{details['observed_status']}**. Exit code: {details['exit_code']}. "
             f"Hook PID: {details['hook_pid']}.\n",
             f"No-op/error reason: {reason or details['error'] or 'none recorded'}.\n",
             "This runs the real hook subprocess. It does not install a hook in Claude.\n",
             hook_output_sections(details),
             section("Input from Claude (replayed)", details["event"])]
    calls = details["laya_calls"]
    if not calls:
        lines.append("\n**No Laya request was observed.** The flow may have stopped before model selection, "
                     "or logging may be unavailable. Read the timeline and diagnostics below.\n")
    for index, call in enumerate(calls, 1):
        lines.append(f"\n## Laya request {index}\n\n"
                     f"Request prepared: yes. Agent ready: {call['agent_ready']}. "
                     f"Response received: {call['response_received']}. Validated: {call['response_validated']}.\n"
                     "Preparing a request alone does not prove inference ran.\n")
        for title, key in [("Requested model and temperature", "config"), ("Text submitted to Laya", "submitted_text"),
                           ("Exact questions and choices", "submitted_questions"), ("Raw Laya response", "raw_response"),
                           ("Enriched answers (including gap)", "enriched_answers"),
                           ("Rules evaluated", "applied_rules"), ("Answers accepted or rejected", "decisions"),
                           ("Errors observed", "errors")]:
            lines.append(section(title, call[key]))
    lines.append("\n## Execution timeline\n\n")
    lines.extend(f"- {r.get('time')} — {r.get('component')}.{r.get('event')}\n" for r in details["trace"])
    if not details["trace"]:
        lines.append("No entries captured.\n")
    lines.append(section("Diagnostics from stderr (can include SDK progress)", details["stderr"]))
    lines.append(section("Replay error", details["error"]))
    lines.append(section("Trace warnings", details["trace_warnings"]))
    lines.append(f"\nSource log: `{details['run']['log_path']}`. "
                 "`trace.jsonl` contains this hook PID's captured log entries only; "
                 "`details.json` contains the full report, including raw stdout.\n")
    return "\n".join(lines)
