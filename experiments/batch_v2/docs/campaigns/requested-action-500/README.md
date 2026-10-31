# Requested action: 500 cases, four choices

Open `experiments/batch_v2/experiments/requested-action-500/run_experiment.py` in PyCharm and press Run. No arguments are needed for a live run. Each launch creates a new dated folder under `results/requested-action-500-v2/`.

The model chooses **explain, generate_tests, modify_code, or unclear**. Choose unclear when no supported action fits, intent is missing, or competing actions prevent selecting one primary action. There is no separate other choice. Unclear is non-actionable. A confidence-rule rejection is also non-actionable, but is recorded separately as `undecided`.

Version 2 keeps the exact 500 prompts and family/role assignments. It has 140 explain, 140 generate_tests, 140 modify_code and 80 unclear labels. All 500 now have scored expected answers. The former 80 null labels are replaced by unclear; their old status/reason is preserved in the migration ledger.

The grid is unchanged in size: ten question/choice variants, ten rules, seven temperature settings; 35,000 model calls plus seven setup probes, and 350,000 rule outcomes. This remains a large run. Worker error logs are bounded; the result checkpoints are retained.

After completion, open `research-development/START-HERE.md` in the printed run folder. It distinguishes accepted actionable answers, accepted unclear answers and rule rejection. The companion `screening.json` includes per-class, noise and tag details. Rule acceptance is not the same as permission to enrich: accepted unclear is still non-actionable.

Keep old runs unchanged. Version 1 definitions are archived under `experiments/requested-action-500/versions/1/`. Version 2 requires fresh predictions; do not reuse or pool the three-choice predictions. Old runs must be resumed/reported using their original code and definitions.

- [Task definition](task-definition.md)
- [Dataset counts](dataset-summary.md)
- [Four-choice change and review](unclear-v2.md)
- [Per-case relabeling ledger](unclear-v2-label-changes.json)
- [Round plan](rounds/001-broad.md)
- [Run journal](run-journal.md)

Select wording using development cases (200), temperature using its calibration role (100), rules using policy calibration (100), and evaluate frozen finalists on held-out cases (100). The 125 families each have four related variants; these are not 500 independent production observations. Production code is unchanged.
