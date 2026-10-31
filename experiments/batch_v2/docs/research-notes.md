# Research rationale

This is a short explanation for agents, not a list of universally optimal settings. Operational definitions are in [scoring.md](scoring.md); next-round decisions are in [workflow.md](workflow.md).

## Temperature calibration

Guo, Pleiss, Sun and Weinberger fit one temperature on labeled validation data by minimizing negative log likelihood. Positive scalar temperature changes probabilities while preserving the highest-scoring class, apart from numerical/tie effects. It does not fix a wrong label.

Use this to select a probability-calibration candidate, then inspect nearby values. A 0.02 increment is a local sensitivity choice; it is not a research-prescribed universal step. The authors' example starts its optimizer at 1.5, which is an initialization, not a recommended answer.

Sources: [ICML 2017 paper](https://proceedings.mlr.press/v70/guo17a.html), [Geoff Pleiss explanation](https://geoffpleiss.com/blog/nn_calibration.html), [author code](https://github.com/gpleiss/temperature_scaling/blob/master/temperature_scaling.py).

## Selective classification

Geifman and El-Yaniv study accepting confident predictions and abstaining on others. Measure both how many requests are answered and the errors among those answers. Their formal risk-control procedure has assumptions; an empirical threshold sweep alone is not that guarantee.

We adopt risk/coverage comparisons and keep several trade-offs until a deployment preference is chosen.

Source: [NeurIPS 2017 paper](https://proceedings.neurips.cc/paper/2017/hash/4a8423d5e91fda00bb7e46540e2b0cf1-Abstract.html).

## Majority-class metrics

Chicco and Jurman explain why ordinary accuracy and some F1 uses can look strong for poor imbalanced classification. MCC is a useful additional dataset metric; balanced accuracy averages class recall. Neither replaces per-class inspection or the decision cost of accepting a wrong answer.

Use raw-label MCC for classifier comparisons. Accepted-only scores can look better merely because a rule avoids hard cases. A separate gate MCC is diagnostic and has degenerate cases.

Sources: [MCC study](https://link.springer.com/article/10.1186/s12864-019-6413-7), [MCC reference](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.matthews_corrcoef.html), [balanced accuracy](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.balanced_accuracy_score.html).

## DOCTOR

Granese and colleagues propose error detectors using the output probability distribution. Our selected probability-only alpha version uses its concentration, sum(p²), to rank predictions for acceptance. It requires no new inference or gradient perturbation.

It is a comparator to test, not a probability of correctness or a promised improvement. Confidently wrong outputs can pass. The beta variant is redundant with maximum probability for ranking.

Source: [NeurIPS 2021 paper](https://proceedings.neurips.cc/paper_files/paper/2021/hash/2cb6b10338a7fc4117a80da24b582060-Abstract.html).

## Raw margins and AURC

Liang, Peng and Sun compare selective-classification scores under distribution shifts. Their discussion motivates checking raw-logit margin as a comparator and using risk/coverage curves with AURC. Raw margin and probability gap are different quantities. Shared positive score scaling preserves raw-margin rankings; a fixed numeric threshold itself is not invariant.

Use probability-based methods immediately. Treat raw-logit capture as an optional capability, and do not call rounded-probability reconstruction exact.

Source: [TMLR 2024 paper](https://arxiv.org/html/2405.05160v2).

## Extensions to consider later

- Option-position bias was observed in generative multiple-choice models. It motivates a future separate order-robustness campaign, not a claim about LAYA. Current RV2 keeps order fixed. [ICLR 2024](https://proceedings.iclr.cc/paper_files/paper/2024/hash/54dd9e0cff6d9214e20d97eb2a3bae49-Abstract-Conference.html)
- Adaptive conformal prediction sets offer marginal coverage under their assumptions. Accepting only singleton sets does not inherit the same conditional accepted-error guarantee. Defer until simpler rules are measured. [NeurIPS 2020](https://proceedings.neurips.cc/paper/2020/hash/244edd7e85dc81602b7615cd705545f5-Abstract.html)

For binary tasks, several probability-concentration scores are monotonic equivalents and may give identical rankings. Do not count differently named but equivalent methods as independent evidence.
