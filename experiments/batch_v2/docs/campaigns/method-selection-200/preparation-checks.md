# Implementation readiness

Verified on Linux x86_64:

- Campaign validation and dry-run: 200 cases, 80 vectors, 1,600 calls, 16,000 outcomes.
- All ten rule objects match the exact requested-action version-one suite.
- 61 method-selection/V2/readable-label pytest checks pass.
- 47 RV2 unittest checks pass, including three new campaign checks.
- New campaign fixture executes 16 simulated boundary calls and replays 160 rule outcomes. Resume leaves the attempt count at 16. Reports regenerate deterministically, and held-out reporting rejects a missing finalist freeze.
- Golden scoring and unequal-denominator aggregation checks pass. Real model calls: zero.

Remaining before live-run readiness: independent semantic annotation review; configured Mac/model verification; counted eight-call live smoke. This environment has no laya_mlx and cannot run MLX inference. Actual accuracy, live truncation behavior and model temperature settings remain unverified.

Integration details: RV2 schema version 2 adds the method-selection branch while existing version-one schemas retain their behavior. Evidence partitions use the current runner's atomic save primitive because the reviewed branch has no shared compact evidence store. The experiment-owned method_evidence module is the canonical indexed reader for this adapter. Reporting remains offline and experiment-owned.

No production/plugin defaults changed. No automatic publication or merge is part of the campaign launcher.
