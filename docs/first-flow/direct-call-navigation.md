# Direct-call navigation in the first method flow

The flow supplies the complete selected implementation. When space permits, it also lists every resolved direct project method it calls, once per target. Each row contains the project-relative path, utility-provided signature and inclusive definition range as `Lines: X–Y`.

The list is optional as a whole. An empty, unavailable or oversized list produces method-only context without a heading or placeholder. Partial resolution lists the resolved targets; ordinary navigation failures are recorded in regular debug logs. The existing 8,000 UTF-16-unit cap and configured lower limit include all headings and separators.

Navigation is produced by the existing `get_called_method_locations` utility using the explicit project root. It provides locations, not callee implementations. Session state continues to record only the selected method implementation, so a later request for a listed callee remains eligible.

Formatting and flow tests cover source fidelity, line ranges, same-file and cross-file calls, deduplication, missing targets, failure fallback and exact budget boundaries. Hook tests check the serialized output.
