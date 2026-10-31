# Dataset summary: requested-action-500

Dataset `requested-action-500`, version `1`. These are synthetic, deliberately balanced inputs, not a random sample of production traffic. No target LAYA predictions were used to author or label them.

## Counts and source-family separation

500 prompts from 125 distinct authored scenarios, with four related variants per scenario. The variants are not independent observations. Each family stays in one role; analysis must resample or compare whole families.

| Label or unsettled status | Cases | Families | Development | Temperature | Policy | Held-out |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| explain | 140 | 35 | 56 | 28 | 28 | 28 |
| generate_tests | 140 | 35 | 56 | 28 | 28 | 28 |
| modify_code | 140 | 35 | 56 | 28 | 28 | 28 |
| taxonomy_pending | 40 | 10 | 16 | 8 | 8 | 8 |
| insufficient_context | 20 | 5 | 8 | 4 | 4 | 4 |
| out_of_scope | 20 | 5 | 8 | 4 | 4 | 4 |
| Total | 500 | 125 | 200 | 100 | 100 | 100 |

The 420 settled cases give 140 per label. The remaining 80 have `expected: null` and `desired_abstention: true`: they are operational abstention checks and are excluded from label-accuracy/calibration metrics.

The held-out set has 84 settled cases in 21 settled families. That is an exploratory check, not enough evidence to establish a rare-error guarantee. Counts do not establish the frequency of these intents in production.

## Conditions and overlapping tags

Noise counts: 250 regular (125 direct and 125 with authored misleading background), 125 noisy, 125 heavy. No `unspecified` entries remain. All prompts are English. Current length range: 27–219 characters.

| Tag | Cases |
| --- | ---: |
| boundary-case | 136 |
| irrelevant-text | 250 |
| misleading | 250 |
| missing-context | 20 |
| mixed-intent | 50 |
| negation | 192 |
| review-disagreement | 2 |
| reviewer-challenging | 16 |
| simple | 66 |
| typos | 250 |

Tags overlap. Noise describes textual condition; a regular prompt can contain a decoy. `review-disagreement` is added only for an actual recorded reviewer disagreement, never merely because a case looks difficult.

## Authoring and reproducibility

The input-authoring agent wrote 125 base scenarios and 125 scenario-specific misleading variants. The topics include current production behavior, existing-test comprehension and repair, new coverage, async control flow, parser/serialization edges, access checks, UI behavior, and unrelated or underspecified requests. No production requested-action fixtures or existing held-out cases were read or copied.

Moderate variants apply up to two recoverable word typos to the base and a rotating light chat-format wrapper. Heavy variants apply up to five such typos to the authored misleading form, plus a stronger copied-message/spacing wrapper. Transformations never delete a negation, insert a requested action, or change the underlying task. These controlled corruptions are intentionally reproducible but limited: they are not a realistic population model of all user noise. The repeated wrappers and directive writing style can make this first synthetic benchmark easier or more formulaic than real messages.

Splits use one `random.Random(20261031)` instance. Strata are processed in this order: explain, generate_tests, modify_code, taxonomy_pending, insufficient_context, out_of_scope. Within each stratum, family IDs are sorted then shuffled; allocate 40/20/20/20 percent to development/temperature/policy/held_out. Both calibration roles use `split: calibration` in the strict runner case schema. Every one of the 125 families appears in the role map.

Opaque case IDs were shuffled using seed 8162047; the blinded review packet was shuffled with seed 31970481. These seeds govern deterministic bookkeeping and transformations, not the LLM's text-generation sampling. The first runner case is in development. The supplied launcher uses the separate, pre-existing fruit example for its capability probe, so setup does not inspect campaign predictions.

## Validation and identity

Actual RV2 schema/runtime validation passes against the first-round suite. Family roles validate with `research.protocol.role_ids`. All four variants within each family preserve expected label/status. There are 500 unique exact inputs and 500 unique case/whitespace-normalized inputs. The lexical near-duplicate screen and review limitations are described in [annotation-review.md](annotation-review.md).

- Exact-byte cases SHA-256: `96798552363d98d3f10193e33e037e1e6c9875063f0f1f6e4dce0099e02514d2`
- Canonical cases hash (`schema.hash_value`): `09ecb8d7992c8115335b3605a9fb191ddca7cc588852ed76339cd841de4ba490`
- Exact-byte roles SHA-256: `2a66e1a822b79cccc656168d85b2058bb5c6f3434a4ce828ea4b9fae04e3a7b2`
- Canonical roles hash: `765ff4f2d9484d84b7660fe78169cafccd8353cf01f9869eee07eb3cc0e7cc76`

Review status: label-blind review completed and two pre-freeze wording clarifications applied; see [annotation-review.md](annotation-review.md) and the per-case ledger. These are the frozen version-1 hashes. Corrections after any target-model run require a new dataset version; never overwrite earlier evidence.
