# Phase 2 — common ingestion

Parent893ffc7d50f4f0089e5c80ea1fb0861da2732812. Explicit registry, common envelope, required event/session/absolute cwd validation, optional metadata validation, deep-copied raw payload and reserved identity enrichment seam. Unsupported events bypass feature requirements. No model/root/source work added.

Validation: accumulated gateway/common/baseline tests91passed. test_hook_common_dispatch50parameterized cases cover B01–B08/B12, C01/C07/C12, D01/D02/D05/D10 and common part of E08. Bad enrichment cannot replace raw/common fields or inject project root. Original caller payload stays unchanged even if an injected handler mutates its private deep copy.

No deviation from the Astra-approved provisional application field contract. D02 schema verification still prevents release/caller migration. D03 root API remains unavailable.
