# Four-choice revision

Sharon requested one catch-all `unclear` choice rather than a separate other class. Its intended meaning is non-actionable for this router. This changes the answer space and annotation contract, so the revision is dataset version 2 with its own experiment/results ID.

The previous 40 competing-action cases, 20 missing-intent cases and 20 unrelated-request cases now all expect unclear. They are settled annotations under the new definition and participate in accuracy, balanced accuracy, MCC, NLL, Brier and confusion matrices. Their former category remains in the per-case migration ledger, not as an additional model choice.

Root reviewed the 80 affected prompt texts against the new catch-all definition and the base prompts for all 105 unchanged action families. Mechanical checks compare every one of the 500 inputs and all family/split/tag/noise assignments with version 1. This is a contract migration review; it is not a new blinded review. The historical 498/500 agreement was against the three-choice contract and does not establish four-choice accuracy. No target-model results were used for this migration.

All ten question variants include unclear. Wording variants retain the same four choice descriptions; choice-description variants retain the baseline instruction. The prior three action descriptions, ten rules, model, seven temperatures and input texts are retained. Q0 is now the four-choice experimental baseline, not the unchanged production default.

Keep accepted-unclear and rule-rejected counts separate. Classification accuracy gives credit for correctly predicting unclear. Rule coverage includes accepted unclear labels; the additional flow-decision counts show how many accepted predictions would actually be actionable. An always-unclear model has zero actionable output and must not be presented as a useful routing winner. Inspect actionable coverage/error and per-action recall alongside overall metrics.

Version-1 cases, suite, role map and protocol are archived byte-for-byte in versions/1. Version-1 annotation ledgers remain historical. The current launcher uses version 2 and writes a new results namespace. It cannot resume or report a version-1 run with version-2 labels; preserve that run and its original runner revision. Do not reuse old three-choice distributions as four-choice evidence.

Production sources remain unchanged. Live validation on the Mac is still required; offline fixtures demonstrate mechanics, not LAYA accuracy. The previously reported interrupted version-1 run has not yet been diagnosed from its files.

Validation completed: launcher dry-run passes; all 44 offline experiment tests pass. New tests validate archived/current hashes, all 500 unchanged prompt/role/tag assignments, 80 relabelings, all ten four-choice variants, and synthetic four-class predictions through the actual worker and development report. They verify that accepted unclear is scored correctly, strict-rule rejection stays separate, and missing evidence or zero actionable output is not reported as zero error.
