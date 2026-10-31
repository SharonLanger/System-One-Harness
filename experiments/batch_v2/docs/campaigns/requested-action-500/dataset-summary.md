# Dataset summary: version 2

The 500 prompt strings are identical to version 1. Version 2 adds the explicit unclear label.

| Expected label | Total | Development | Temperature | Policy | Held-out |
| --- | ---: | ---: | ---: | ---: | ---: |
| explain | 140 | 56 | 28 | 28 | 28 |
| generate_tests | 140 | 56 | 28 | 28 | 28 |
| modify_code | 140 | 56 | 28 | 28 | 28 |
| unclear | 80 | 32 | 16 | 16 | 16 |
| Total | 500 | 200 | 100 | 100 | 100 |

All 500 annotations are settled and scored. Unclear contains 40 competing-action, 20 missing-intent and 20 unrelated-request cases; these reasons are retained in the migration ledger. No desired_abstention flags remain.

Noise: 250 regular (125 direct, 125 grammatical misleading variants), 125 noisy, 125 heavy. Noise and difficulty differ; regular may contain a decoy. Tags overlap and are unchanged. There are 125 scenario families with four related variants each, wholly inside one role. The dataset is synthetic, short, English-only and intentionally challenging; it does not estimate real traffic prevalence or establish rare-error guarantees. Duplicate/wording limitations and the original review are described in the historical annotation review.

The role map is unchanged; the two calibration roles still share split=calibration in cases.json. All prompts, IDs, order, tags and splits are preserved. Label counts are intentionally unequal; use balanced accuracy and per-class recall alongside accuracy. An always-unclear prediction is not a successful router.

- Exact-byte cases SHA-256: `7deb6546d3f4583bed834ff4412e964ce5f26dcc90908efc06bc85198b886708`
- Canonical cases hash: `87ae28531763144365c56785e16e79b8b1364675f0fbb835a5be0a60182e7641`
- Canonical roles hash (unchanged): `765ff4f2d9484d84b7660fe78169cafccd8353cf01f9869eee07eb3cc0e7cc76`

See [unclear-v2.md](unclear-v2.md) for the current review and [unclear-v2-label-changes.json](unclear-v2-label-changes.json) for all 80 changes. Old blinded-review agreement is version-1 evidence, not a second four-choice review.
