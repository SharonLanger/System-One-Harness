# Local files after cleanup

Before pulling the cleanup commit on your Mac, back up your root docs folder, .idea, results, exports and logs OUTSIDE the repository. Git can remove tracked files during pull even when the new revision ignores their paths. After pulling, restore historical docs under docs/local/ and restore .idea locally. Campaign docs and cases remain tracked. Raw results stay local for analysis; delete them yourself only when you finish analysis.

Repository documentation and historical research backup: https://drive.google.com/file/d/12DqOvOXTHFvDLjTrehp50_oS3yVCyM6g/view

To enable the optional local commit/push guard in this clone: `git config core.hooksPath .githooks`. Check existing hooks before changing this setting. The CI guard must be configured as a required main-branch check to prevent merging violations. Ignore rules and hooks can be bypassed; neither prevents every possible remote upload.

Legacy analysis may need the original evaluator checkout because source fingerprints include source paths and JSON evidence. Keep that checkout while analyzing old runs. Never edit recorded hashes to bypass this check.
