# LAYA method selection experiment plan

Date: 2026-10-31  
Campaign: `method-selection-200`  
Status: experiment design updated with all ten rules from requested-action-500/versions/1/suite.json. Temperatures and two question wordings are fixed. The complete temperature-summary and aggregation-script handoff is included. Another agent must implement the dataset, runner adapter and reports before live execution; no new model campaign has been executed.

## 1. Experiment decision

Test the existing **method_selection_v2 building block** on 200 frozen inputs, using two question wordings, ten acceptance policies, and temperatures **0.5, 0.8, 1.0, 1.1**. Keep one installed LAYA model and English throughout. Capture one response per input, wording and temperature, then replay all ten policies against that response.

| Item | Count |
| --- | ---: |
| Inputs | 200 |
| Question wording variants | 2 |
| Rule policies | 10 |
| Temperatures | 4 |
| Comparison configurations | 80 |
| Model calls | 1,600 |
| Logical block outcomes after rule replay | 16,000 |

The block submits two questions together in one prediction: `method` and `multiple_relevant`. Two wording variants means two versions of that bundle, not two additional model calls for its internal questions. No repetitions, automatic temperature refinement, second-pass context, or fallback-model calls belong to this campaign.

This plan follows the existing Markdown campaign-document convention. It supersedes the generic 1,200-input authoring target for this campaign only.

## 2. What exists and what its evidence establishes

Source snapshot: `SharonLanger/laya-context-router`, main commit `01e15612ba41adbc075a13b7161b2ef00108afbe`.

- `method_selection_v2.block.run` is implemented. It accepts a full TypeScript outline and a request, constructs readable dynamic choices, calls the model, applies both named policies, and maps the selected label back to a source callable ID.
- `flows/first_method_context.py` calls V2 directly. The sandbox file-method flow calls the compatibility API, which routes versioned outlines to V2. The block has therefore already been integrated into method-selection flows.
- Automated tests cover selection, no match, rejection, multiple methods, label mapping, immutability, budgets, invalid outlines, and V2/legacy parity. Relevant tests are listed in section 12. They were inspected for this plan, not rerun.
- A committed real-mode result from **2026-10-30 at 14:57:47 Israel time** correctly selected `chooseDestination`: method answer confidence 0.7279, probability gap 0.5605, and an accepted `multiple_relevant=no`. That run used the older compatibility entry point and a synthetic abbreviated outline. It is evidence of a successful live example, not measured accuracy of current V2 across diverse inputs.

Conclusion: the block is implemented, used, and mechanically tested, with a recorded successful live example. This campaign measures how reliably it selects or refuses a method.

## 3. Freeze the task boundary

For this first campaign, the request asks to **explain** callable code. Select one supplied callable only when the request identifies exactly one appropriate target from the visible names and signatures. Otherwise return no selection.

This matches the current question text. The first flow also admits `generate_tests`, but the current method-selection wording says “explain.” Test-generation requests need a separate scope decision and subsequent campaign; success here does not establish their accuracy. Modification requests are also outside this campaign.

Only names, signatures, and request text are model evidence. No method bodies, docstrings, imports, call graphs, hidden author knowledge, expected answers, notes, tags, or split labels enter inference. A case requiring the implementation body to resolve the target belongs in the insufficient-information group.

Boundary policies:

| Request situation | Expected method answer | Expected multiple answer | Expected final selection |
| --- | --- | --- | --- |
| Exactly one identifiable target | Its generated readable label | `no` | That callable's ID |
| Requested callable absent | `none_or_unclear` | `no` | None |
| Singular target cannot be distinguished from the supplied signatures | `none_or_unclear` | `no` | None |
| Explicitly asks to explain two or more supplied callables | `none_or_unclear` | `yes` | None |

Mentioning a second method as background or explicitly excluding it does not make the request multi-method. “Explain A; ignore B” targets A. “Explain A and B” targets neither individually. Avoid unresolved mixed-intent cases that would require a new precedence policy.

For a genuine multi-method request, the final no-selection result is correct even if the raw method answer is a concrete method and the multiple-method guard blocks it. Report the raw method error separately; do not erase the guard's contribution.

## 4. Actual input and output structure

The public V2 input is:

```python
{
    "text": "Explain how calculateInvoiceTotal computes the total.",
    "source_outline": full_validated_typescript_outline
}
```

Generate outlines once from small checked-in TypeScript fixtures using the real outline utility. Preserve schema version, path, source hash, callable IDs, signatures, ranges, locations, diagnostics and limitations. Do not invent abbreviated outlines or fabricate identity fields. Validate fixtures before freezing the campaign; the block itself does not read source files.

The block prepares model criteria such as:

```json
{
  "calculateInvoiceTotal": "export function calculateInvoiceTotal(invoice: Invoice): number",
  "calculateInvoiceTotalWithAdjustment": "export function calculateInvoiceTotalWithAdjustment(invoice: Invoice, adjustment: number): number",
  "none_or_unclear": "No single matching callable, or unclear request."
}
```

Unique names become labels. Repeated names with distinct signatures use `name@line:column`; a real callable named `none_or_unclear` is disambiguated too. Private `candidate_map` and `label_map` retain source identity outside the model payload. Candidate order remains fixed for each input across every configuration.

A selection requires an accepted concrete `method` answer and an accepted `multiple_relevant=no`. The output contains `selected_id`, `reason`, both maps, and the two decisions. Capture `data.reason` as the domain outcome; a completed block can still refuse selection.

Empty candidates, repeated identical signatures, more than 64 candidates, or an input above the 16,000-character default are pre-inference skips. Test those mechanically outside the 200 inference inputs. Require all 200 cases to reach prediction under both wordings without truncation. Count limits in Unicode characters exactly as the block does, not in tokens.

## 5. Two question variants

**Q0 — current baseline, unchanged**

`method`:

> Select exactly one callable that the request asks to explain. Choose none_or_unclear when no single callable is appropriate.

**Q1 — explicit target and refusal wording**

`method`:

> Which single listed callable does the user want explained? Use the request and the callable names and signatures. Ignore callables mentioned only as background or explicitly excluded. Choose none_or_unclear if the target is absent, cannot be distinguished, or the request asks to explain multiple callables.

For both variants, preserve:

- The `choice` type, per-case label order, and exact signature descriptions.
- Sentinel description: `No single matching callable, or unclear request.`
- The `multiple_relevant` question, type `noul`: `Does the request require explaining more than one candidate callable?`
- The block's normal input preparation and reducer.

Override only the method instruction through the existing per-call question override. Runtime slots remain `method` and `multiple_relevant`; the catalog reference name `method_selection` is not a new prediction key. Validate the actual override shape against the current runtime before launch.

No third wording in round one. It would increase work without first knowing whether a second wording improves anything.

## 6. Ten rules copied from requested action version one

Use every entry in the `rules` array from [the exact version-one suite](https://github.com/SharonLanger/laya-context-router/blob/01e15612ba41adbc075a13b7161b2ef00108afbe/experiments/batch_v2/experiments/requested-action-500/versions/1/suite.json), preserving IDs, names, order, condition fields, operators and thresholds. Do not take rules from the current campaign suite or its V2 dataset. These ten replace the previous three provisional policies and resolve the pending extraction-rule item.

Source path: `experiments/batch_v2/experiments/requested-action-500/versions/1/suite.json`  
Source commit: `01e15612ba41adbc075a13b7161b2ef00108afbe`  
Source file Git blob SHA: `8e4c4aca8a86003c068408838d3e568c17c64aba`

| Rule ID | Acceptance conditions on the method answer |
| --- | --- |
| `r0-current` | `answer_confidence` ≥ 0.5 AND `probability_gap` ≥ 0.15 |
| `r1-ungated` | No method acceptance conditions |
| `r2-answer-060` | `answer_confidence` ≥ 0.6 |
| `r3-answer-080` | `answer_confidence` ≥ 0.8 |
| `r4-gap-010` | `probability_gap` ≥ 0.1 |
| `r5-gap-030` | `probability_gap` ≥ 0.3 |
| `r6-entropy-050` | `normalized_entropy` ≤ 0.5 |
| `r7-entropy-075` | `normalized_entropy` ≤ 0.75 |
| `r8-combined-loose` | `answer_confidence` ≥ 0.45 AND `probability_gap` ≥ 0.1 |
| `r9-combined-strict` | `answer_confidence` ≥ 0.7 AND `probability_gap` ≥ 0.25 |

All conditions within one rule are ANDed. Copy the rule objects exactly into the campaign suite; the complete JSON appears in section 9.1. These are the same extraction/acceptance rules used by the requested-action experiment, now evaluated against method-selection responses. Their earlier performance does not establish their performance on this task.

Apply each imported rule to the `method` choice answer only. They are choice rules: probability gap and normalized entropy must not be applied to the `multiple_relevant` noul answer. Keep that guard fixed at `answer_confidence >= 0.5` and retain the production interpretation and reducer. There is no ten-by-ten cross-product of guard rules.

`r1-ungated` removes only the method confidence/gap/entropy gate. It does not bypass the multiple-method guard, turn the sentinel into a selection, or accept malformed responses. Likewise, `action.act_probability` is not an additional condition in these ten rules. Use the existing enriched fields without substituting `confidence` for `answer_confidence`. Evaluate normalized entropy over each case's actual prepared choice set, including the sentinel, using the production enrichment function.

Baseline comparison: **q0-baseline / r0-current / t-100**. The source campaign's SDK-default baseline temperature is not copied; the four approved temperatures are explicit. Save both raw question answers and all ten replay outcomes.

## 7. Dataset of 200 inputs

Author **100 independent scenario families with two related requests each**. Keep both requests in one split. Each family includes its candidate set, so repeated names or cosmetic renaming alone do not create an independent scenario. A shared fixture may be used, but scenarios sharing the same semantic task remain one family.

| Primary category | Families | Cases |
| --- | ---: | ---: |
| Explicit unique method name | 25 | 50 |
| Behavioral description identifiable from signatures | 20 | 40 |
| Similar-name distractors, background mentions and negation | 15 | 30 |
| Same-name candidates distinguished by signatures or explicit location | 10 | 20 |
| Requested method absent | 10 | 20 |
| Insufficient information to identify a single method | 10 | 20 |
| Explicit multiple-method request | 10 | 20 |
| Total | 100 | 200 |

This gives **140 selectable cases and 60 expected refusals**. The last 60 have a settled refusal target under this task contract; they are not missing correctness labels. Exclude cases whose annotation genuinely remains unresolved and replace them before freeze.

Additional cross-cutting coverage:

- Candidate counts 2, 4, 8, and 16: 25 families / 50 inputs each, excluding the sentinel from the count.
- Noise totals: 160 regular, 30 noisy, 10 heavy. Use the existing meanings of these levels; corruption must preserve the intended task or be classified as insufficient information.
- Cover exported functions, class instance/static methods, async functions and callable expressions supported by the extractor.
- Distribute selectable targets across early, middle and late positions. Preserve source order within each case; no extra permutation dimension.
- Use realistic billing, authorization, caching, parsing, validation, persistence and reporting scenarios. Avoid near-duplicate filler.

Examples for annotation, not a complete dataset:

| Visible candidates | Request | Target |
| --- | --- | --- |
| `calculateTotal`, `formatInvoice`, `saveInvoice` | Explain calculateTotal; formatInvoice is unrelated. | `calculateTotal` |
| `readCache`, `invalidateCache`, `writeCache` | Explain the operation that removes a cached entry. | `invalidateCache`, if its signature supports that description |
| `parseCsv`, `parseJson`, `formatJson` | Explain parseXml. | None: absent |
| Two distinct signatures named `load` | Explain load. | None: singular target ambiguous |
| `validateOrder`, `saveOrder` | Explain validateOrder and saveOrder. | None: multiple |

Review labels before looking at LAYA predictions. A second annotation pass should determine targets from the request and visible signatures without seeing the first answer. Record whether it was independent review or self-review. Preserve disagreements and their resolutions in the annotation report.

## 8. Small, fixed comparison protocol

Use 60% of families for comparison and 40% for final checking: **120 development inputs and 80 held-out inputs**. Allocate within the seven primary categories, yielding development counts 30/24/18/12/12/12/12 and held-out counts 20/16/12/8/8/8/8. Shuffle family IDs within categories with seed `20261031` before assigning them. Balance candidate-count and noise groups across splits as closely as family integrity permits; report the exact counts.

“Development” here means the cases used to choose among the already-fixed configurations. It does not mean a different model, temperature setup, input set per configuration, or easier inputs. Every configuration sees the same 200 frozen inputs. Keep held-out prediction metrics out of the comparison report until finalists are recorded.

No separate calibration datasets and no threshold fitting in this small campaign. Choose finalists using development evidence only. Then reveal their held-out results once. If all 200 inputs are used to choose a winner instead, label that report exploratory and do not claim independent validation.

Freeze case bytes, outlines, labels, source-family assignments, question bundles, policies, model identity and settings before inference. Any correction creates a new dataset version; do not silently amend completed evidence.

## 9. Runner work required before execution

Current RV2 supports `generic-question`, `requested-action`, and `context-scope`. Its schema assumes fixed suite-wide labels and one scored question; its worker extracts that question's decision as the result. **A method-selection suite cannot currently be dropped into it unchanged.**

Implement a backward-compatible, experiment-owned `method-selection` adapter and schema branch under `experiments/batch_v2/`. Use the schema-version-2 adapter contract below; preserve version 1 behavior for all existing suites. Do not change production block behavior or relabel all methods as fixed A/B/C choices merely to fit the runner.

The new contract must represent:

- Per-case full block input and per-case valid labels derived by the real preparation path.
- Ground truth for `method_label`, `multiple_relevant`, and nullable final `selected_id`.
- Question bundles with two typed entries; policy bundles with two named rules.
- Predictions and decisions for both questions plus the final selected source ID and domain reason.

The exact proposed JSON representation is defined below. Implement and validate this schema branch before authoring the complete dataset; the current RV2 schema does not yet accept it.

Invoke the public V2 `run` with experiment catalog/rule overrides and the selected method wording. Reuse RV2 model loading, captured-response boundary, checkpoints, limits and collection where applicable. Replay the complete saved response through the same public block using `RecordedAgent`, not a second copy of the selection logic.

Use per-case label order for probability vectors and comparisons. Do not build a global confusion matrix treating unrelated callable names or IDs as universal classes. The native collector's `accepted` flag for one question is not final block selection; add explicit method-accepted, multiple-accepted and final-selected fields.

Resume identity must cover input and outline bytes, both question definitions, candidate order, policies, model/configuration, adapter code and source revision. Count actual prediction attempts, including failed calls. A pre-inference skip is not a prediction, wrong answer, or accepted refusal.

### 9.1 Exact suite definition for the new adapter

The following is the full target `rounds/001-small/suite.json`, not a runnable suite for the unmodified runner. Only `rules` is copied from the requested-action suite; its action-classification questions, labels, temperatures and dataset are not copied. The two question entries remain the method-selection wordings in section 5. Each entry is combined with the fixed internal `multiple_relevant` question in one model request.

The model identifier below comes from the source suite and the recorded method-selection run. Verify that it is the intended installed model before freezing; do not silently substitute a different model.

```json
{
  "schema_version": 2,
  "experiment_id": "method-selection-200",
  "dataset_id": "method-selection-200",
  "dataset_version": "1",
  "adapter": "method-selection",
  "question_type": "choice",
  "label_mode": "dynamic-per-case",
  "questions": [
    {
      "id": "q0-baseline",
      "variant_kind": "baseline",
      "definition": {
        "name": "method",
        "type": "choice",
        "instructions": "Select exactly one callable that the request asks to explain. Choose none_or_unclear when no single callable is appropriate.",
        "criteria": {
          "none_or_unclear": "No single matching callable, or unclear request."
        }
      }
    },
    {
      "id": "q1-explicit-target",
      "variant_kind": "wording",
      "definition": {
        "name": "method",
        "type": "choice",
        "instructions": "Which single listed callable does the user want explained? Use the request and the callable names and signatures. Ignore callables mentioned only as background or explicitly excluded. Choose none_or_unclear if the target is absent, cannot be distinguished, or the request asks to explain multiple callables.",
        "criteria": {
          "none_or_unclear": "No single matching callable, or unclear request."
        }
      }
    }
  ],
  "fixed_questions": {
    "multiple_relevant": {
      "name": "multiple_relevant",
      "type": "noul",
      "instructions": "Does the request require explaining more than one candidate callable?"
    }
  },
  "rules": [
    {
      "id": "r0-current",
      "definition": {
        "name": "r0-current",
        "conditions": [
          {
            "field": "answer_confidence",
            "op": "gte",
            "value": 0.5
          },
          {
            "field": "probability_gap",
            "op": "gte",
            "value": 0.15
          }
        ]
      }
    },
    {
      "id": "r1-ungated",
      "definition": {
        "name": "r1-ungated",
        "conditions": []
      }
    },
    {
      "id": "r2-answer-060",
      "definition": {
        "name": "r2-answer-060",
        "conditions": [
          {
            "field": "answer_confidence",
            "op": "gte",
            "value": 0.6
          }
        ]
      }
    },
    {
      "id": "r3-answer-080",
      "definition": {
        "name": "r3-answer-080",
        "conditions": [
          {
            "field": "answer_confidence",
            "op": "gte",
            "value": 0.8
          }
        ]
      }
    },
    {
      "id": "r4-gap-010",
      "definition": {
        "name": "r4-gap-010",
        "conditions": [
          {
            "field": "probability_gap",
            "op": "gte",
            "value": 0.1
          }
        ]
      }
    },
    {
      "id": "r5-gap-030",
      "definition": {
        "name": "r5-gap-030",
        "conditions": [
          {
            "field": "probability_gap",
            "op": "gte",
            "value": 0.3
          }
        ]
      }
    },
    {
      "id": "r6-entropy-050",
      "definition": {
        "name": "r6-entropy-050",
        "conditions": [
          {
            "field": "normalized_entropy",
            "op": "lte",
            "value": 0.5
          }
        ]
      }
    },
    {
      "id": "r7-entropy-075",
      "definition": {
        "name": "r7-entropy-075",
        "conditions": [
          {
            "field": "normalized_entropy",
            "op": "lte",
            "value": 0.75
          }
        ]
      }
    },
    {
      "id": "r8-combined-loose",
      "definition": {
        "name": "r8-combined-loose",
        "conditions": [
          {
            "field": "answer_confidence",
            "op": "gte",
            "value": 0.45
          },
          {
            "field": "probability_gap",
            "op": "gte",
            "value": 0.1
          }
        ]
      }
    },
    {
      "id": "r9-combined-strict",
      "definition": {
        "name": "r9-combined-strict",
        "conditions": [
          {
            "field": "answer_confidence",
            "op": "gte",
            "value": 0.7
          },
          {
            "field": "probability_gap",
            "op": "gte",
            "value": 0.25
          }
        ]
      }
    }
  ],
  "fixed_rules": {
    "multiple_relevant": {
      "name": "multiple_methods_default",
      "question_type": "noul",
      "conditions": [
        {
          "field": "answer_confidence",
          "op": "gte",
          "value": 0.5
        }
      ]
    }
  },
  "configurations": [
    {
      "id": "t-050",
      "model": "aac6fef/laya-typed-decisions-mlx",
      "temperature": 0.5,
      "lang": "en"
    },
    {
      "id": "t-080",
      "model": "aac6fef/laya-typed-decisions-mlx",
      "temperature": 0.8,
      "lang": "en"
    },
    {
      "id": "t-100",
      "model": "aac6fef/laya-typed-decisions-mlx",
      "temperature": 1.0,
      "lang": "en"
    },
    {
      "id": "t-110",
      "model": "aac6fef/laya-typed-decisions-mlx",
      "temperature": 1.1,
      "lang": "en"
    }
  ],
  "baseline": {
    "question_id": "q0-baseline",
    "rule_id": "r0-current",
    "config_id": "t-100"
  },
  "exclusions": []
}
```

### 9.2 Cases and protocol contracts

Use a schema-version-2 cases envelope with exactly `schema_version`, `dataset_id`, `dataset_version` and `cases`. Each case has the existing `id`, `input`, `expected`, `label_status`, `noise_level`, `tags`, `source_family_id`, `split`, and `notes` fields. For this adapter:

- `input` is exactly `{ "text": <request>, "source_outline": <full validated outline> }`.
- `expected` is an object with exactly `method_label`, `multiple_relevant`, and `selected_id`. A concrete target uses its generated label, `no`, and its true source ID. A refusal uses `none_or_unclear`, the appropriate `yes`/`no` from section 3, and null.
- All 200 cases have `label_status="settled"`; refuse dataset freeze on unresolved annotation, invalid source identity, unknown labels or contradictory expected fields.
- Store outlines inline in cases for this campaign so the existing frozen manifest captures the complete inference input. Fixture files remain provenance, not live dependencies of the block.
- Derive labels and their order with the real block preparation path. There is no global suite `labels` array. For each case, all variants must produce identical labels/order and signatures.
- Compute primary categories and candidate-count groups into a separately hashed report sidecar, or derive them from controlled tags and the outline. Never forward them to the model.

The new schema validates this expected-object form only for `adapter="method-selection"`; preserve the scalar expected format of existing adapters. Update dry-run distribution output and collection to handle the object explicitly instead of using it as a hash key. Compare exact selected source IDs within a case, never across unrelated cases.

`protocol.json` records the fixed design: 200 cases, Q0/Q1, all ten source rule IDs in source order, the four configuration IDs, one repetition, replay mode, baseline IDs, 120/80 family-preserving split, seed 20261031, main call cap 1600, separate smoke cap 8, and the source suite path/commit/blob SHA. Store content hashes for cases, suite, annotation records and report sidecars once generated. The manifest must freeze both fixed-question/fixed-rule definitions as well as the varied method definitions.

### 9.3 Runner and launcher definition

Implement the adapter inside RV2 and add the campaign launcher at `experiments/batch_v2/experiments/method-selection-200/run_experiment.py`. The launcher supplies this campaign's cases and suite to the shared runner and pins replay mode. It does not implement another model loop.

Required launcher behavior:

| Invocation | Behavior |
| --- | --- |
| No arguments / IDE Play | Validate and print a dry-run summary; zero model calls |
| `--validate-only` | Validate all contracts, source-rule equality, labels, budgets, hashes and matrix counts |
| `--dry-run` | Print 200 cases, 2 wordings, 10 rules, 4 temperatures, 80 vectors, 1600 calls and 16000 outcomes |
| `--smoke --mode live` | Run two fixed cases with Q0 at all four temperatures, replay all ten rules; 8 calls and 80 outcomes, separate run folder |
| `--mode live` | Run the full frozen suite in replay mode with a hard maximum of 1600 prediction attempts |
| `--resume <run-folder>` | Delegate resume using the manifest's frozen configuration; reject new suite/settings overrides |

Reject direct rule mode for this launcher; do not silently expand execution to 16,000 model calls. Forward supported time-limit flags to RV2. Resume reuses successful captured responses and must not treat replayed rules as new inference attempts. Require explicit live mode; never silently use synthetic fixture predictions for the real dataset.

Planned commands after adapter implementation and validation (not executable successfully against today's unmodified adapter):

```bash
python experiments/batch_v2/experiments/method-selection-200/run_experiment.py --validate-only
python experiments/batch_v2/experiments/method-selection-200/run_experiment.py --dry-run
python experiments/batch_v2/experiments/method-selection-200/run_experiment.py --smoke --mode live
python experiments/batch_v2/experiments/method-selection-200/run_experiment.py --mode live
```

The live command executes configurations in the frozen order `t-050`, `t-080`, `t-100`, `t-110`. Within each temperature, process Q0 then Q1 and the frozen case order. For each case, capture both raw answers once, then replay the ten rules in source order. Q0 and Q1 are separate inference units; rules share their respective unit's evidence. Add no iterations or unlisted models.

Reuse shared RV2 resume and collection commands with the printed run folder. Reports can be regenerated entirely from saved evidence. Unit tests inject deterministic responses and must not load MLX. Any shared compact-storage integration must maintain its current format and the eight question/temperature partitions described in section 11.

## 10. Reports that answer the experiment question

Provide a compact overview with one row per wording/rule/temperature, plus a short findings document. Report these outcomes separately:

1. Correct method selected.
2. Wrong method selected on a selectable input.
3. No method selected on a selectable input: missed useful context.
4. Correct refusal on an expected-refusal input.
5. A method incorrectly selected on an expected-refusal input: unsafe selection.
6. Technical failure, timeout, pre-inference skip or unattempted input.

Core metrics, with numerator and denominator:

- Raw method-label accuracy and raw multiple-answer accuracy, before rules.
- Correct selection yield: correct selections / successfully evaluated selectable cases.
- Selection precision: correct selections / all selections.
- Selection coverage: all selections / successfully evaluated cases.
- Refusal correctness: no-selection outcomes / successfully evaluated expected-refusal cases.
- End-to-end correctness: correct selection or correct refusal / successfully evaluated cases.
- Technical completion: successfully evaluated cases / planned cases.

Show the same metrics by primary category, candidate count, noise level and split. Include reason counts, per-case baseline differences, and examples of confidently wrong selections. Report which mistakes stricter rules filter and how many correct selections they lose. Do not count every refusal as success or allow an always-refuse policy to look useful through precision alone; precision is unavailable when there are no selections.

Compare configurations on paired case IDs. Retain the baseline and identify alternatives that improve errors without sacrificing useful coverage, or expose a tradeoff worth Sharon choosing. Do not invent a deployment error tolerance. Keep at most two non-baseline finalists on the development error-versus-yield frontier; use higher correct-selection yield and then simpler/current settings to break exact ties. Freeze finalists before revealing held-out metrics.

With 80 held-out inputs, small differences remain tentative. If uncertainty intervals are produced, resample whole scenario families, not individual related requests. This is a deliberately difficult benchmark, not an estimate of the production request mix.

### 10.1 Required summaries by temperature

Generate readable Markdown companions for every campaign summary CSV. Every Markdown companion starts with the run ID, dataset/suite hashes, split, completion status, and a short plain-language summary, followed by separate temperature sections in the order **0.5, 0.8, 1.0, 1.1**. Do not mix temperatures into an unlabelled overall ranking.

Output structure inside each run folder:

```text
analysis/development/
  vectors.csv
  summary.md
  by-question/
    q0-baseline.csv
    q0-baseline.md
    q1-explicit-target.csv
    q1-explicit-target.md
  by-temperature/
    t-050.csv
    t-050.md
    t-080.csv
    t-080.md
    t-100.csv
    t-100.md
    t-110.csv
    t-110.md
  temperature-totals.csv
  temperature-totals.md
  question-rule-totals.csv
  question-rule-totals.md
  totals.json
  report-manifest.json
```

The same layout is generated under `analysis/held_out/` and `analysis/all/` only after finalists are frozen as described below. These are derived views of one run, not extra model runs. The shared runner's existing summary files keep their established meanings; the campaign's explicit summary contract lives under `analysis/`.

- `vectors.csv`: exactly one row per question/rule/temperature for the selected split: **80 rows**, including explicit partial rows when predictions are missing.
- Each `by-question/*.csv`: **40 rows**; its Markdown companion has four temperature sections, with **ten rule rows per temperature**.
- Each `by-temperature/*.csv`: **20 rows**; its companion contains a short summary for that temperature and two clearly labelled tables, Q0 and Q1, with ten rule rows each. Together these cover all 20 combinations at that temperature.
- `summary.md`: four temperature sections, each stating what improved relative to that temperature's Q0/r0 baseline, what errors remain, and the coverage cost. Link the two question tables instead of copying a very wide table again.
- Totals files have the schemas in section 10.3. Each totals Markdown companion also has four temperature sections before presenting any cross-temperature totals.

Each ten-row rule table uses this compact primary layout:

| Rule | Correct selection | Wrong selection | Missed selection | Correct refusal | Unsafe selection | Evaluated / planned |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Each of the ten imported rule IDs | count | count | count | count | count | count / count |

A second table for the same ten rules shows selection precision, correct-selection yield, refusal correctness, end-to-end correctness, and technical completion. Display rates as **percentage (numerator/denominator)**, with percentages rounded only for display to one decimal place. Use `N/A (0/0)` for undefined rates; never display 100% for an empty selection set. Keep exact counts and unrounded rates in CSV/JSON. Add error/timeout/skip/unattempted counts below the tables, with a link to details.

The short summary for each temperature states:

1. How much of the planned comparison completed.
2. Which rule/question pairs made fewer incorrect selections and which retained more correct selections, with counts.
3. The baseline-relative tradeoff; list ties honestly and do not call a universally best rule when precision and yield disagree.

Use deterministic templates for these factual summaries; the aggregation script must not call a model to write them. A later interpretive report can add commentary from the saved evidence.

### 10.2 Canonical counts and summary row schema

Every vector row includes `schema_version`, `experiment_id`, `run_id`, `dataset_version`, `cases_hash`, `suite_hash`, `split`, `question_id`, `rule_id`, `config_id`, `temperature`, and `complete`.

Store these integer counters:

| Field | Meaning |
| --- | --- |
| `planned` | Number of cases in the selected split for this vector |
| `evaluated` | Completed block outcomes with valid, scorable decisions |
| `selectable_evaluated` | Evaluated cases whose expected selected ID is concrete |
| `refusal_evaluated` | Evaluated cases whose expected selected ID is null |
| `correct_selection` | Selected the expected concrete source ID |
| `wrong_selection` | Selected a different method on a selectable case |
| `missed_selection` | Selected nothing on a selectable case |
| `correct_refusal` | Selected nothing on an expected-refusal case |
| `unsafe_selection` | Selected a method on an expected-refusal case |
| `error`, `timeout`, `skipped`, `unattempted` | Mutually exclusive technical/noncompletion categories |

Count a configuration-load failure as `error` for its affected planned outcomes, with an error subtype retained. Any completed-but-invalid output is an error, not a scorable refusal. Each planned vector/case key belongs to exactly one outcome or technical bucket.

Required identities:

```text
evaluated = correct_selection + wrong_selection + missed_selection
          + correct_refusal + unsafe_selection
selectable_evaluated = correct_selection + wrong_selection + missed_selection
refusal_evaluated = correct_refusal + unsafe_selection
planned = evaluated + error + timeout + skipped + unattempted
selected = correct_selection + wrong_selection + unsafe_selection
incorrect_selections = wrong_selection + unsafe_selection
correct_outcomes = correct_selection + correct_refusal
```

Rates are recomputed from these counters:

```text
selection_precision = correct_selection / selected
correct_selection_yield = correct_selection / selectable_evaluated
refusal_correctness = correct_refusal / refusal_evaluated
selection_coverage = selected / evaluated
end_to_end_correctness = correct_outcomes / evaluated
technical_completion = evaluated / planned
```

Keep raw method accuracy and raw multiple-answer accuracy in a separate **eight-row question/temperature summary per split**, with their own evaluated denominators and a Markdown companion containing four temperature tables. This avoids counting the same raw prediction ten times. Add its proposed files as `raw-answers.csv` and `raw-answers.md` under each analysis split directory. Preserve the domain-reason histogram separately; reason totals must reconcile with evaluated outcomes where a reason exists.

### 10.3 Small aggregation script

Implement `experiments/batch_v2/experiments/method-selection-200/summarize_results.py`. Use Python's standard library and existing experiment record readers. No model imports, model loading, SDK calls, network requests, or new analysis framework are needed.

Two stages inside the same script:

1. Read the frozen run manifest and normalized block outcomes through the shared record reader, filter by requested split, and produce the canonical 80-row `vectors.csv` plus the eight-row raw-answer summary.
2. Compute the per-question/per-temperature tables and totals from those canonical rows. Read unique inference usage from the evidence index/attempt ledger, never from summed policy rows.

Define reusable pure functions for classifying a case outcome, summarizing vector counts, and aggregating counts. Keep Markdown/CSV formatting separate so the aggregation can be reused later without loading the runner. Keep implementation small; a second reporting engine is unnecessary.

**Exact totals to produce:**

- `temperature-totals.csv`: four rows, pooling the 20 question/rule vectors within each temperature. Sum outcome/technical counters and recompute every rate from summed numerators and denominators. Include `vector_count`, distinct input count, distinct evidence count and counted prediction attempts as separate fields.
- `question-rule-totals.csv`: 20 rows, one for each question/rule pair pooled across the four temperatures. Sum counters and recompute rates. Its Markdown companion first shows the constituent temperature tables, then this pooled comparison.
- `totals.json`: overall logical-outcome totals, all four temperature totals, all 20 question/rule totals, and separate inference accounting. Include the source hashes, split, completeness and report schema version.

These pooled totals describe the **experiment matrix**, not a combined production classifier or independent observations. Do not choose a winner based on the overall sum across competing rules. Do not average percentages, count overlapping tag rows, sum parent plus child groups, or treat Q0/Q1 and four temperatures as new independent user inputs.

For a fully completed main run, expected dimensions are:

| Scope | Distinct inputs | Unique inference units | Logical outcomes |
| --- | ---: | ---: | ---: |
| One temperature, all inputs | 200 | 400 | 4,000 |
| All four temperatures, all inputs | 200 | 1,600 | 16,000 |
| One temperature, development | 120 | 240 | 2,400 |
| All four temperatures, development | 120 | 960 | 9,600 |
| One temperature, held-out | 80 | 160 | 1,600 |
| All four temperatures, held-out | 80 | 640 | 6,400 |

One question/rule pair pooled across temperatures has 800 logical outcomes for `all`, 480 for development, or 320 for held-out. These are repeated evaluations of the same input set. Raw-answer summaries represent 1,600 inference units overall, even though each unit contains two internal answers. Failed attempts and records with missing responses remain separate from successful evidence counts. Smoke-run attempts are excluded from main-run totals and reported separately as up to eight additional calls.

Deduplicate valid outcomes by `(run_id, question_id, rule_id, config_id, case_id)` and evidence by its immutable inference ID. Read only the canonical storage index, not every temporary/checkpoint/compacted copy found by globbing. If duplicate logical keys or conflicting records remain in that canonical input, fail with the offending IDs rather than choosing one silently. Reject incompatible dataset/suite/model/settings hashes; never merge runs implicitly.

### 10.4 Commands, partial runs, and held-out protection

Planned commands, to be verified after implementation:

```bash
python experiments/batch_v2/experiments/method-selection-200/summarize_results.py --run <run-folder> --split development
python experiments/batch_v2/experiments/method-selection-200/summarize_results.py --run <run-folder> --split development --allow-partial
python experiments/batch_v2/experiments/method-selection-200/summarize_results.py --run <run-folder> --split held_out --finalists <frozen-finalists.json>
python experiments/batch_v2/experiments/method-selection-200/summarize_results.py --run <run-folder> --split all --finalists <frozen-finalists.json>
```

The default split is development. An incomplete run fails normal summarization with a completion report; `--allow-partial` emits explicitly labelled partial summaries with all planned vector rows and missing counts. It must not fabricate zero errors, exclude failed cases from planned totals, or rank a partial vector as a winner. Zero model calls in every reporting path.

`frozen-finalists.json` contains the run/dataset/suite hashes, baseline vector, at most two non-baseline finalist vectors, the development report hash, and a freeze timestamp. Validate that all IDs exist and the report hashes match. Without this artifact, reject held-out and all-input summaries before reading their prediction evidence into selection/report routines. Finalist evaluation is confirmatory; tables for the remaining combinations are descriptive and must not be used to select a new winner on the held-out set.

Write reports atomically under `analysis/<split>/`. `report-manifest.json` records canonical input hashes, script/schema version, selected split, output hashes and completeness. Rerunning unchanged input must yield identical data tables, ordering and metric values; keep generation timestamps in the report manifest only. Never alter saved inference or policy outcomes while reporting.

### 10.5 Reporting acceptance checks

Use small deterministic fixtures for these checks; none requires LAYA calls:

- Golden vector: 10 planned/evaluated cases, counts 4 correct selections, 1 wrong selection, 1 missed selection, 3 correct refusals and 1 unsafe selection. Expect 6 selections, precision 4/6, selectable yield 4/6, refusal correctness 3/4, end-to-end correctness 7/10, completion 10/10.
- All-refuse and no-selection cases yield undefined precision, not perfect precision; empty or unavailable groups retain their planned/missing counts.
- Unequal denominators: pooling precision 1/1 and 1/9 produces 2/10, not the unweighted mean of the two percentages.
- One captured response replayed over ten rules counts once in inference totals and ten times in logical-outcome totals. Raw-answer accuracy is computed once per evidence unit.
- Mixed errors/timeouts/skips/missing checkpoints reconcile to planned totals. Partial mode cannot mark the run complete or produce a definitive winner.
- Duplicate keys, mismatched hashes, accidental smoke inclusion and overlapping subgroup-row aggregation fail explicitly.
- Development reports contain no held-out prediction metrics. Held-out/all reports require a valid frozen-finalists artifact.
- All 80 vectors, eight raw-answer groups, four temperature totals and 20 question/rule totals exist in a complete report; each question summary has four ten-rule tables and each temperature summary has both question tables.
- CSV, Markdown and JSON counters agree; per-temperature totals sum to main-run logical totals while unique evidence counts remain 1,600 at full completion.
- Repeated summarization is deterministic and succeeds with a model-loader stub that raises immediately if invoked.

## 11. Evidence storage and execution limits

Save the entire raw response once per case/question-bundle/temperature: both answers, all returned probabilities, usage/truncation fields, and the exact submitted payload. Store rule outcomes as references to that evidence. Never duplicate the raw response for each policy.

Partition records by question variant and temperature, with no more than 500 predictions per evidence file. This campaign naturally has **eight partitions of 200 predictions**. Use resumable small checkpoints during execution and compact/index them using the available runner storage format; do not introduce a second competing evidence format if the shared storage work already supports this layout. Freeze a record index mapping inference IDs to their partition and offset.

The main campaign cap is **1,600 prediction attempts**. Stop on unexpected adapter/configuration failures; do not silently retry or switch to direct mode, which would raise the campaign to 16,000 calls. Preserve partial results and account for retries in any subsequently authorized continuation.

Before the main campaign, allow a separate, explicit **eight-call smoke test**: one selectable input and one refusal input at each temperature, Q0 only. Replay all ten policies from those eight responses. Total initial live budget including this smoke test is at most **1,608 calls**. Record the smoke separately; it is not an extra accuracy dataset or a hidden warm-up.

Use the configured installed LAYA model only; freeze its exact identifier, checkpoint fingerprint and package versions. Reuse the prior model only after confirming its installed identity. Do not download or upgrade assets as part of execution. Record requested temperature and loader arguments; if effective temperature is not observable, say unavailable. Do not infer “temperature ignored” merely because predicted labels are unchanged.

Run on Sharon's compatible Mac after implementation and dataset preparation. Generate the exact launch command only once the new adapter validates and its CLI is verified. The existing runner's supported limit flags include `--max-calls`, `--max-seconds`, and `--worker-timeout`; worker timeout covers a configuration worker, not an individual prediction. Estimate and record time limits from the smoke test before launching. Collector/report regeneration must make zero model calls.

## 12. Implementation sequence and acceptance checks

Keep implementation in small, testable commits and under the experiment area. No production promotion, plugin update, merge, or large live run is part of preparing this document.

1. **Adapter contract and fixtures:** implement per-case dynamic labels and the two-question bundle schema, with validation tests. Assert exact equality of the ten copied rule objects against the frozen source array. Reject missing/unknown expected IDs, invalid outlines, wrong question types, changed label mappings and annotation leakage. Preserve existing suite behavior.
2. **Execution and replay:** call the public block; capture both answers; prove direct execution and replay from identical mocked raw responses produce identical decisions, selected IDs and reasons. Prove ten policies use one real boundary prediction, with zero additional live calls for replay.
3. **Outcomes, storage and summaries:** implement sections 10.1–10.5, including summarize_results.py, the four temperature reports, canonical CSV counters, aggregation totals and golden tests. Add final-selection scoring, raw-answer diagnostics, family/split filtering, compact records and resume checks. Test an accepted method blocked by the multiple guard, sentinel acceptance, rejected correct selections, and errors without fabricated predictions.
4. **Dataset and campaign configuration:** author and review the 200 cases and fixtures, freeze Q0/Q1 and the exact ten imported rule definitions, then validate all counts, character budgets, identities, splits and hashes. Dry-run must show 80 vectors, 1,600 calls and 16,000 outcomes.
5. **Offline verification and handoff:** run relevant adapter checks and existing RV2 regressions, produce a fixture report, and confirm collected totals reconcile. A fake model that fails on access must still allow validation, dry-run and collection. Verify interruption/resume reuses saved evidence and rule replay consumes no live-call budget.
6. **Mac smoke and campaign:** execute the counted smoke, verify payloads/settings/truncation, and then run the frozen campaign within its limits. Stop if the actual matrix differs. Summarize development results, freeze finalists, then assess held-out results.

Existing regression references:

- `tests/test_method_selection.py`
- `tests/test_readable_method_selection.py`
- `tests/test_method_ambiguity_fallback.py`
- `tests/test_v2_blocks.py` method-selection cases
- `experiments/batch_v2/checks/`

Fixture tests establish mechanics; only the real campaign supplies method-selection accuracy evidence. New mechanical cases are outside the 200-input model budget.

## 13. Files to prepare

Proposed campaign locations:

```text
experiments/batch_v2/docs/campaigns/method-selection-200/
  README.md
  task-definition.md
  annotation-review.md
  dataset-summary.md
  preparation-checks.md
  run-journal.md
  rounds/001-small.md

experiments/batch_v2/experiments/method-selection-200/
  cases.json
  protocol.json
  fixtures/*.ts
  rounds/001-small/suite.json
  run_experiment.py
  summarize_results.py
```

Store frozen outlines inline in cases as fixed in section 9.2; do not introduce a competing companion-file representation. Add a reviewer record mapping each case to its target rationale, without including that record in inference. The campaign launcher has the explicit behavior defined in section 9.3 and must delegate inference, replay, resume and limits to the shared runner.

The final result package needs the frozen manifest, indexed response evidence, per-policy outcomes, every CSV/Markdown summary pair and totals artifact from section 10, baseline-difference examples, and a short conclusion: which wording helps, which rules filter bad selections, what useful selections they lose, and whether temperature materially changes the tradeoff.

## 14. Source references

All repository references below are pinned to the inspected commit.

- [Exact version-one source of the ten rules](https://github.com/SharonLanger/laya-context-router/blob/01e15612ba41adbc075a13b7161b2ef00108afbe/experiments/batch_v2/experiments/requested-action-500/versions/1/suite.json) — Git blob `8e4c4aca8a86003c068408838d3e568c17c64aba`.

- [V2 block and contract](https://github.com/SharonLanger/laya-context-router/tree/01e15612ba41adbc075a13b7161b2ef00108afbe/src/laya_context_router/building_blocks/questions/method_selection_v2)
- [Current question](https://github.com/SharonLanger/laya-context-router/blob/01e15612ba41adbc075a13b7161b2ef00108afbe/src/laya_context_router/defaults/questions/method_selection.json) and [current rule](https://github.com/SharonLanger/laya-context-router/blob/01e15612ba41adbc075a13b7161b2ef00108afbe/src/laya_context_router/defaults/rules/method_selection_default.json)
- [First flow integration](https://github.com/SharonLanger/laya-context-router/blob/01e15612ba41adbc075a13b7161b2ef00108afbe/src/laya_context_router/flows/first_method_context.py)
- [V2 tests](https://github.com/SharonLanger/laya-context-router/blob/01e15612ba41adbc075a13b7161b2ef00108afbe/tests/test_v2_blocks.py) and [method-selection tests](https://github.com/SharonLanger/laya-context-router/blob/01e15612ba41adbc075a13b7161b2ef00108afbe/tests/test_method_selection.py)
- [Recorded real-mode example](https://github.com/SharonLanger/laya-context-router/blob/01e15612ba41adbc075a13b7161b2ef00108afbe/experiments/results/block_method_selection/2026-10-30_14-57-47/details.json)
- [RV2 schema](https://github.com/SharonLanger/laya-context-router/blob/01e15612ba41adbc075a13b7161b2ef00108afbe/experiments/batch_v2/schema.py), [engine](https://github.com/SharonLanger/laya-context-router/blob/01e15612ba41adbc075a13b7161b2ef00108afbe/experiments/batch_v2/engine.py), and [runner guide](https://github.com/SharonLanger/laya-context-router/blob/01e15612ba41adbc075a13b7161b2ef00108afbe/experiments/batch_v2/README.md)
## 15. Handoff to the implementing agent

Sharon will assign a different agent to implement this plan. This handoff is a complete implementation specification, not evidence that the runnable campaign or reporting script already exists. Do not execute the 1,600-call campaign merely to verify that a document was updated.

Start by reading this plan in full and the target checkout's applicable AGENTS.md instructions. Inspect the current shared runner and storage format because other PRs may have landed since the pinned review snapshot. Preserve the two exact method wordings, the ten imported rules, the fixed multiple-method guard, the 200-input target and temperatures 0.5/0.8/1.0/1.1. Record the actual implementation commit and any adapter/schema differences from the design. Do not silently expand the model-call budget or modify production defaults.

Deliver in the testable sequence of section 12:

1. Backward-compatible method-selection adapter and schema.
2. Complete reviewed dataset, real outlines, frozen suite and protocol.
3. Campaign launcher, response reuse, storage and resume integration.
4. Small offline summary/aggregation script with every report and check in section 10.
5. A readiness note listing the exact commands verified, test outcomes, 80-vector dry-run, output locations and remaining Mac-only checks.

**Implementation ready for review** means offline checks pass, all 200 inputs validate, the exact rule-copy check passes, the matrix is 80 vectors / 1,600 calls / 16,000 outcomes, and deterministic fixture reporting demonstrates all four temperature tables and reconciled totals. It does not mean real-model accuracy is known.

**Live-run ready** additionally requires the intended installed Mac model/settings to be verified and the separately counted eight-call smoke test to pass. Launch the main campaign only under Sharon's subsequent execution instruction to the implementing agent; generating reports from existing results remains an offline operation. No live execution is requested by this document-edit turn.

If current runner interfaces differ, adapt the experiment integration while preserving the task contract and counts; document the change and its tests. If a proposed deviation changes questions, rules, labels, dataset scope, model or call budget, present the concrete deviation to Sharon before changing that experiment definition. End the implementation handoff with what is ready and what remains, without claiming that unperformed Mac checks passed.
