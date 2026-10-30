"""Readable summary for the method-selection block experiment."""
from __future__ import annotations


def _inline(value):
    return str(value).replace("`", "'").replace("\n", " ")


def render_summary(details):
    run = details.get("run") if isinstance(details.get("run"), dict) else {}
    lines = [
        "# Method selection block experiment",
        "",
        f"Status: **{run.get('status', 'unknown')}**.",
        "The request and outline are synthetic. The outline is static input; no Node build or source scan is involved.",
        "",
        "## Requested configuration",
        "",
    ]
    model_config = details.get("model_config")
    cfg = model_config.get("requested") if isinstance(model_config, dict) else None
    cfg = cfg if isinstance(cfg, dict) else {}
    temperature = cfg.get("temperature")
    lines.append(
        f"Model `{_inline(cfg.get('model', 'unavailable'))}`; temperature "
        f"`{_inline(temperature if temperature is not None else 'SDK default')}`; "
        f"language `{_inline(cfg.get('lang', 'unavailable'))}`."
    )
    lines += ["", "## Synthetic request", "", "```", str(details.get("input") or "(unavailable)"), "```", ""]

    submitted = details.get("submitted_questions")
    lines += ["## Submitted questions", ""]
    if isinstance(submitted, dict) and submitted:
        for name, question in submitted.items():
            question = question if isinstance(question, dict) else {}
            lines.append(f"### {name} (`{_inline(question.get('type', 'unknown'))}`)")
            lines.append(f"Instructions: {_inline(question.get('instructions', '(unavailable)'))}")
            criteria = question.get("criteria")
            if isinstance(criteria, dict):
                lines.append("Dynamic choice criteria:")
                for key, criterion in criteria.items():
                    lines.append(f"- `{_inline(key)}`: {_inline(criterion)}")
            lines.append("")
    else:
        lines.append("No model request was submitted (the block may have returned an early no-op).")

    raw = details.get("raw_response")
    answers = raw.get("answers") if isinstance(raw, dict) else None
    enriched = details.get("enriched_response")
    enriched_answers = enriched.get("answers") if isinstance(enriched, dict) else {}
    lines += ["## Answers", ""]
    if isinstance(answers, dict) and answers:
        for name, answer in answers.items():
            if not isinstance(answer, dict):
                lines.append(f"- **{name}:** malformed answer `{_inline(answer)}`")
                continue
            kind = answer.get("type")
            value = answer.get("choice", answer.get("noul", answer.get("score", "unavailable")))
            confidence = answer.get("answer_confidence", answer.get("confidence", "not supplied"))
            lines.append(f"- **{name}:** answer `{_inline(value)}`; answer confidence `{_inline(confidence)}`.")
            enriched_answer = enriched_answers.get(name) if isinstance(enriched_answers, dict) else None
            if isinstance(enriched_answer, dict):
                metrics = []
                for metric in ("probability_gap", "distance_from_boundary"):
                    if metric in enriched_answer:
                        metrics.append(f"{metric} `{_inline(enriched_answer[metric])}`")
                if metrics:
                    lines.append("  Enrichment: " + "; ".join(metrics) + ".")
    else:
        lines.append("No raw answer was captured.")

    lines += ["", "## Block outcome", ""]
    result = details.get("result")
    if isinstance(result, dict):
        selected = result.get("selected_id")
        reason = result.get("reason")
        lines.append(f"Outcome: **{'selected' if selected else 'no selection'}**; reason `{_inline(reason or 'accepted')}`.")
        decisions = result.get("decisions")
        if isinstance(decisions, dict):
            for name, decision in decisions.items():
                if not isinstance(decision, dict):
                    lines.append(f"- `{name}`: unavailable decision.")
                    continue
                outcome = "accepted" if decision.get("decided") else "rejected/undecided"
                lines.append(f"- `{name}`: {outcome}; interpreted answer `{_inline(decision.get('answer', 'unavailable'))}`; rule reason `{_inline(decision.get('reason', 'unavailable'))}`.")
        candidate_map = result.get("candidate_map")
        if selected and isinstance(candidate_map, dict) and isinstance(candidate_map.get(selected), dict):
            candidate = candidate_map[selected]
            lines.append(f"Selected candidate: **{_inline(candidate.get('name', selected))}** — `{_inline(candidate.get('signature', 'unavailable'))}`.")
            lines.append(f"Source: `{_inline(candidate.get('path', 'unavailable'))}`; hash `{_inline(candidate.get('source_hash', 'unavailable'))}`.")
    else:
        lines.append("No block result was returned.")
    enrichment_error = details.get("enrichment_error")
    if isinstance(enrichment_error, dict):
        lines += ["", f"Enrichment error: `{_inline(enrichment_error.get('type'))}: {_inline(enrichment_error.get('message'))}`."]
    error = details.get("error")
    if isinstance(error, dict):
        lines += ["", "## Error", "", f"Stage `{_inline(error.get('stage', 'unknown'))}`: `{_inline(error.get('type', 'Error'))}: {_inline(error.get('message', 'unknown error'))}`."]
    if run.get("started_local"):
        lines += ["", "## Run details", "", f"Started {run['started_local']} ({run.get('timezone_offset', 'timezone unavailable')}); UTC {run.get('started_utc', 'unavailable')}; duration {run.get('duration_seconds', 'unavailable')} seconds."]
    lines += ["", "Full submitted payload, raw SDK response, and enriched response are in `details.json`."]
    return "\n".join(lines)
