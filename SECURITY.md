# Security policy

System One Harness is an experimental project without published stable releases. The maintainer assesses reports against the current `main` branch; older revisions have no stated support window. This policy does not promise a response or fix within a particular time.

## Report a vulnerability

Use GitHub's private [Report a vulnerability form](https://github.com/SharonLanger/system-one-harness/security/advisories/new) for this repository. It lets you share details privately with the maintainer. Do not put a suspected vulnerability, exploit steps, credentials, private project source, prompts, or raw debug logs in a public issue.

Include the affected commit or version, operating system, steps to reproduce with a small sanitized example, expected and actual behavior, and the likely impact. Please say whether the issue requires real Laya/model execution or can be reproduced with the offline harness. The maintainer may ask for more detail and will coordinate any disclosure after assessing the report.

SOH does not distribute the Laya runtime or model weights. A vulnerability solely in a separately obtained runtime or model should also be reported to its provider. If its interaction with SOH creates a distinct problem, describe that interaction here.

For ordinary bugs and feature requests, use [GitHub issues](https://github.com/SharonLanger/system-one-harness/issues) and read [CONTRIBUTING.md](CONTRIBUTING.md).
