# Phase 3 — UserPromptSubmit dispatcher

Parent566db9d02826cc579976f5eb3f368ec3ed0cd910. Added typed PromptRequest and event-specific dispatcher. Required prompt is validated without normalizing content; empty string accepted. Exactly one feature call, explicit outcomes, metadata logs and no I/O at this layer. Model/root configuration passed as dependency and not resolved by common dispatch.

Accumulated focused tests109passed in0.79s; event dispatcher18cases. Mapping B09–B11, D03–D06/D08/D09, S06/S07/S11/S12 via wrong_prompt_type, missing_prompt, prompt_preserved_and_one_handler, outcome_propagates, bad_handler_result, exception_reaches_outer_boundary and main_to_event_to_handler_and_extra_metadata. Unexpected failures propagate to gateway rather than being mislabeled no-match.

D02 schema and D03 root API remain blockers for registration/caller migration. The default feature import is intentionally connected in Phase4 only; this new gateway is not an active replacement yet. Existing executable unchanged.
