# Scoring and probability reference

Use this file for metric definitions and edge cases. The [workflow](workflow.md) decides when each metric may influence selection. Additional metrics below are planned research helpers; see the [implementation plan](implementation-plan.md).

## Dataset metrics

### Label quality across the dataset

Use raw labels before rejection: accuracy, per-class recall/confusion, balanced accuracy, macro F1 and multiclass Matthews correlation coefficient (MCC).

MCC is a dataset-level association between expected and predicted classes, not a confidence for one answer. A constant majority predictor should not look strong merely because one label dominates. Include a development-selected constant-label baseline. In the binary 90-no/10-yes example, always-no gives accuracy 0.90, balanced accuracy 0.50 and MCC 0 under the declared zero-denominator convention.

MCC is not a universal utility function. Display degenerate denominators and class support; a single-class subgroup cannot establish ability to distinguish classes. For aggregate balanced accuracy over a subgroup with missing canonical classes, report the present-class value and class support explicitly; do not compare it as if all classes were represented. [S1, S2]

### Probability quality

NLL evaluates the probability assigned to the expected label; lower is better. Brier score is a companion; reliability plots are diagnostics. Compute these on every eligible prediction, including predictions later rejected. A high probability is a model estimate, not ground truth. [S3]

### Rule quality

Count four outcomes: correct accepted (AC), wrong accepted (AW), correct rejected (RC), wrong rejected (RW).

- Coverage = (AC + AW) / (AC + AW + RC + RW).
- Accepted error = AW / (AC + AW).
- Correct-accepted yield = AC / all scored cases.
- Per-class coverage and correct-accepted recall reveal classes that a rule avoids.

Plot error against coverage while sweeping a score threshold. For scalar score families also report area under that curve (AURC); lower is better. Compare rule rankings on identical underlying predictions. Across question/model variants, label quality also changes, so AURC is a joint-system comparison, not an isolated rule effect. [S4]

Optional gate MCC treats raw correctness as the binary target and acceptance as the prediction: TP=AC, FP=AW, FN=RC, TN=RW. It is a diagnostic, not the winner-selection objective. It has a degenerate denominator when all raw answers are correct or the rule always makes the same decision.

Never silently count abstention as another semantic class. Zero accepted answers means accepted error is N/A, not 0%.

## Probability scores and temperature

The returned LAYA probabilities are valid inputs to this work. "Raw score" means a logit before softmax, not a more authentic probability.

For an illustrative probability vector [0.70, 0.20, 0.10]:
- Probability gap is 0.50.
- DOCTOR concentration G = 0.70² + 0.20² + 0.10² = 0.54.
- G is a concentration score, not 54% probability of correctness.

Use the probability-only DOCTOR-alpha method: accept when G >= d. This is equivalent to the paper's rejection test 1-G > gamma*G with d=1/(1+gamma). It needs the full probability vector and no additional model call. It can still accept confidently wrong predictions. DOCTOR-beta adds no independent ranking beyond maximum probability. [S5]

Raw-logit margin is z1-z2, distinct from probability gap p1-p2. It is an optional comparator. The reviewed runner saves raw SDK responses but does not establish that logits or effective temperature are exposed. [S4, P1]

Temperature execution has three routes:
1. Captured logits: evaluate softmax(z/T) cheaply offline, then check selected values through the SDK.
2. Verified full-precision softmax probabilities at known T0: relative scores can be reconstructed up to an irrelevant additive constant. Equivalently, p_i(T) is proportional to p_i(T0)^(T0/T). This follows algebraically from softmax. Verify precision, transformations and live parity before using this shortcut.
3. Ordinary returned probabilities without those guarantees: run each temperature through LAYA and score the returned distributions. This is sufficient for the main experiment.

Rounded zeros or unknown transformations prevent calling reconstructed logits exact. They do not invalidate the probability-based experiment.

## Sources

[S1] Chicco and Jurman (2020), majority-class pitfalls and MCC: https://link.springer.com/article/10.1186/s12864-019-6413-7
[S2] Maintainer documentation: https://scikit-learn.org/stable/modules/generated/sklearn.metrics.matthews_corrcoef.html and https://scikit-learn.org/stable/modules/generated/sklearn.metrics.balanced_accuracy_score.html
[S3] Guo et al. (ICML 2017), validation NLL fitting: https://proceedings.mlr.press/v70/guo17a.html ; author explanation: https://geoffpleiss.com/blog/nn_calibration.html
[S4] Liang, Peng and Sun (TMLR 2024), raw margins and risk/coverage evaluation: https://arxiv.org/html/2405.05160v2
[S5] Granese et al. (NeurIPS 2021), DOCTOR: https://proceedings.neurips.cc/paper_files/paper/2021/hash/2cb6b10338a7fc4117a80da24b582060-Abstract.html
[P1] RV2 implementation reviewed at commit 7a1b031191d81edc3d9ac1993a972b989e91c2e9: https://github.com/SharonLanger/laya-context-router/pull/21

The workflow's grids, tolerances, dataset sizes and stopping rules are engineering decisions. They are not empirically proven LAYA settings.
