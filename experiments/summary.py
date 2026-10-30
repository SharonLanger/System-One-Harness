"""Human-readable Markdown summaries for direct adapter experiments."""
from __future__ import annotations

import json
import re


def _json(value):
    try:
        return json.dumps(value, ensure_ascii=False, indent=2, default=repr)
    except Exception:
        try:
            return repr(value)
        except Exception:
            return "<unprintable value>"


def _fence(value, language=""):
    # Use a fence longer than any backtick run in user supplied text.
    text = str(value)
    longest = max((len(run) for run in re.findall(r"`+", text)), default=0)
    fence = "`" * max(3, longest + 1)
    return f"{fence}{language}\n{text}\n{fence}"


def _config_text(config):
    if not isinstance(config, dict):
        return "Unavailable"
    model = config.get("model", "unavailable")
    temperature = config.get("temperature")
    temperature = "SDK default" if temperature is None else str(temperature)
    return f"model `{model}`; temperature {temperature}; language `{config.get('lang', 'unavailable')}`"


def _question_lines(questions):
    if not isinstance(questions, dict) or not questions:
        return ["_Question definitions unavailable._"]
    lines = []
    for name, question in questions.items():
        lines += [f"### {name}"]
        if not isinstance(question, dict):
            lines += [f"Definition: {_fence(_json(question), 'json')}"]
            continue
        lines += [f"Type: `{question.get('type', 'unspecified')}`"]
        lines += ["Instructions:", _fence(question.get("instructions", "(not provided)"))]
        if "criteria" in question:
            lines += ["Criteria:", _fence(_json(question["criteria"]), "json")]
    return lines


def _answer_lines(name, question, answer):
    if not isinstance(answer, dict):
        return [f"**{name}:** unavailable in validated result"]
    kind = question.get("type") if isinstance(question, dict) else answer.get("type")
    lines = [f"**{name}**"]
    if kind == "choice":
        lines.append(f"Selected: `{answer.get('choice', 'unavailable')}`")
        if isinstance(answer.get("probabilities"), dict):
            lines.append("Probabilities:")
            lines.append(_fence(_json(answer["probabilities"]), "json"))
    elif kind == "noul":
        lines.append(f"Noul value: `{answer.get('noul', 'unavailable')}`")
    elif kind == "score":
        lines.append(f"Raw score: `{answer.get('score', 'unavailable')}`")
        if "legend" in answer:
            lines += ["Legend:", _fence(_json(answer["legend"]), "json")]
        if isinstance(answer.get("probabilities"), dict):
            lines += ["Probabilities:", _fence(_json(answer["probabilities"]), "json")]
    else:
        lines.append(f"Answer: {_fence(_json(answer), 'json')}")
    for field in ("confidence", "answer_confidence"):
        if field in answer:
            lines.append(f"{field.replace('_', ' ').capitalize()}: `{answer[field]}`")
    if isinstance(answer.get("action"), dict) and "act_probability" in answer["action"]:
        lines.append(f"Action probability: `{answer['action']['act_probability']}`")
    return lines


def _result_markdown(questions, answers):
    if not isinstance(answers, dict):
        return ["_No validated answer mapping is available._"]
    names = list(answers)
    if not names:
        return ["_The answer mapping is empty._"]
    if len(names) > 1:
        rows = ["| Question | Answer |", "|---|---|"]
        for name in names:
            answer = answers[name]
            kind = questions.get(name, {}).get("type") if isinstance(questions, dict) and isinstance(questions.get(name), dict) else None
            value = answer.get("choice", "") if isinstance(answer, dict) and kind == "choice" else answer.get("noul", "") if isinstance(answer, dict) and kind == "noul" else answer.get("score", "") if isinstance(answer, dict) and kind == "score" else "See details below"
            safe_name = str(name).replace("|", "\\|").replace("\n", " ")
            safe_value = str(value).replace("|", "\\|").replace("\n", " ")
            rows.append(f"| {safe_name} | {safe_value} |")
        lines = rows + [""]
        for name in names:
            lines.extend(_answer_lines(name, questions.get(name, {}) if isinstance(questions, dict) else {}, answers[name]))
            lines.append("")
        return lines
    return _answer_lines(names[0], questions.get(names[0], {}) if isinstance(questions, dict) else {}, answers[names[0]])


def _normalize_answers(value, questions):
    """Accept the legacy single-choice result shape used by details.json."""
    if (isinstance(value, dict) and set(value) == {"answer"}
            and isinstance(questions, dict) and len(questions) == 1):
        return {next(iter(questions)): value["answer"]}
    return value


def render_summary(details):
    """Render a readable report without assuming malformed data is valid."""
    details = details if isinstance(details, dict) else {}
    run = details.get("run") if isinstance(details.get("run"), dict) else {}
    config = details.get("model_config") if isinstance(details.get("model_config"), dict) else {}
    requested = config.get("requested")
    questions = details.get("questions")
    title = run.get("script", "Laya experiment").replace(".py", "").replace("_", " ").title()
    lines = [f"# {title}", "", f"Status: **{run.get('status', 'unknown')}**.",
             "This report records a direct adapter call. Enrichment and rule processing were not run.", "",
             "## Requested configuration", "", _config_text(requested), "",
             "## Input", "", _fence(details.get("input") if details.get("input") is not None else "(unavailable)"), "",
             "## Questions and exact instructions", ""]
    lines.extend(_question_lines(questions))
    lines += ["", "## Results", ""]
    result = details.get("result")
    raw = details.get("raw_response")
    if result is None:
        if isinstance(raw, dict) and isinstance(raw.get("answers"), dict):
            result = raw["answers"]
        elif isinstance(raw, dict) and isinstance(questions, dict) and any(name in raw for name in questions):
            result = raw
    result = _normalize_answers(result, questions)
    comparison = config.get("comparison_requested")
    if comparison is not None:
        lines += [f"Primary configuration: {_config_text(requested)}", ""]
        results = result if isinstance(result, list) else [result]
        results = [_normalize_answers(item, questions) for item in results]
        raw_results = raw if isinstance(raw, list) else [raw]
        if len(results) < 2 and len(raw_results) > 1:
            results = results + [item.get("answers", item) if isinstance(item, dict) else None for item in raw_results[1:]]
        lines += ["### Primary result", ""]
        lines.extend(_result_markdown(questions, results[0] if results else None))
        lines += ["", f"### Comparison configuration", "", _config_text(comparison), "", "### Comparison result", ""]
        lines.extend(_result_markdown(questions, results[1] if len(results) > 1 else None))
        if "same_agent_object_reused" in config:
            lines += ["", f"Same agent object reused: **{config['same_agent_object_reused']}**."]
        elif run.get("status") != "success":
            lines += ["", "Same agent object reused: unavailable (comparison did not reach the identity check)."]
    else:
        lines.extend(_result_markdown(questions, result))
    if run.get("status") != "success":
        error = details.get("error")
        lines += ["", "## Failure", ""]
        if isinstance(error, dict):
            lines += [f"Stage: `{error.get('stage', 'unknown')}`", f"Error: `{error.get('type', 'Error')}: {error.get('message', 'unknown error')}`"]
        else:
            lines.append("Failure details are unavailable.")
        raw = details.get("raw_response")
        if raw is not None:
            raw_text = _json(raw)
            limit = 8000
            if len(raw_text) > limit:
                raw_text = raw_text[:limit] + "\n… (truncated; full raw response is in details.json)"
            lines += ["", "Raw response captured before failure:", _fence(raw_text, "json")]
    lines += ["", "## Run details", ""]
    if run.get("started_local"):
        lines.append(f"Started: {run['started_local']} ({run.get('timezone_offset', 'timezone offset unavailable')}); UTC: {run.get('started_utc', 'unavailable')}.")
    if run.get("duration_seconds") is not None:
        lines.append(f"Duration: {run['duration_seconds']} seconds.")
    if run.get("result_directory"):
        lines.append(f"Result directory: `{run['result_directory']}` (see `details.json` for the structured source of truth).")
    return "\n".join(lines)
