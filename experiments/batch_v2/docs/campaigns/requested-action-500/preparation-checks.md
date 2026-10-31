> Historical version-1 record. For the current four-choice definition and validation, see [unclear-v2.md](unclear-v2.md). The original review/verification below is preserved, not rerun evidence.

# Preparation checks

Prepared against main commit `f60e8b7b59ac2cc8e4ec647c39175e0292491de2`. All authored changes are under `experiments/batch_v2/`; no production file or existing runner implementation changed.

- Native schema/runtime validation accepts all 500 cases, ten question variants, ten rules and seven configurations.
- The launcher dry-run verifies the exact input-byte hash and canonical case/role hashes and reports 700 vectors, 35,000 shared model calls and 350,000 rule outcomes, plus seven setup probes.
- 125 families each have four variants; no family crosses roles. Role counts are 200/100/100/100. Each settled label has 140 cases.
- Input author self-review plus a label-blind root review covered all 500 prompts. Initial agreement was 498/500. Two prompts were clarified before freezing; all nine pre-freeze text revisions were checked. See the annotation ledger.
- No exact or normalized duplicate input strings remain. The dataset summary documents synthetic-generation limitations.
- The 30 existing offline RV2/research tests and five starter-report tests pass. The complete discovery run passed 34 tests before the fifth starter check was added; the final targeted starter run passed all five. No unrelated production tests were needed for this experiment-only addition.
- The new mechanical tests use existing fruit fixtures. They verify held-out inference/checkpoint files are never opened by the first report, missing rule outcomes and missing probabilities are visibly partial, frozen dataset changes fail, and stale rule provenance fails. These fixtures establish report behavior, not requested-action accuracy.

Commands exercised:

```bash
python -B experiments/batch_v2/experiments/requested-action-500/run_experiment.py --dry-run
# From experiments/batch_v2:
python -B -m unittest discover -s checks -v
python -B -m unittest discover -s checks -p test_requested_action_starter.py -v
```

Not yet exercised: live Mac SDK probe, actual requested-action model inference, the full 350,000-outcome workload, and real outcome analysis. The default launcher performs the SDK probe on the user's Mac before the broad run. No elapsed-time, accuracy, best-temperature or best-rule result is claimed.

The first report is deliberately bounded: all question/configuration point estimates and exact native-rule comparisons with class/noise/tag details, without automatically bootstrapping every pair. Family-paired uncertainty, temperature refinement, policy fitting and frozen final evaluation follow the round plan using the existing research helpers. Nothing is automatically selected or promoted to production.
