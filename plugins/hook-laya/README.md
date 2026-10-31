# hook-laya

Current version: **1.1.0** (declared in `.claude-plugin/plugin.json`).

Connects Claude Code hooks to Laya Context Router through the existing CLI gateway and dispatcher.

## Hooks

- `UserPromptSubmit`: runs the existing prompt-context flow.
- `PostCompact`: runs `hook --hook PostCompact --log-state` after manual or automatic compaction, appending a `PostCompact` event and timestamp to the same session's JSONL log.

Build the TypeScript helper with `npm --prefix typescript-helper run build`, ensure Node is on PATH, and configure `LAYA_CONTEXT_ROUTER_CLI` to point to the installed LCR executable. Session logs live under the LCR installation's `logs/session-state/`. See `../../docs/post-compact/README.md` for logging behavior and the manual smoke check.

## Required versioning rule

**Every change to this plugin must include a new version in `.claude-plugin/plugin.json` in the same PR before merge.** This includes hook configuration, plugin metadata, documentation, and changes to the runtime behavior exposed by the plugin. Never publish changed plugin contents under an existing version.

Use semantic versioning: increment the patch for fixes or documentation, the minor for backward-compatible features, and the major for breaking changes. Keep this README's current version and changelog synchronized with the manifest. If additional plugin version declarations are introduced, update them together. A PR may group related edits into one release version; subsequent published changes require another version.

## Changelog

### 1.1.0

- Add `PostCompact --log-state` registration and session-state logging.
- Document mandatory version bumps for all plugin changes.

### 1.0.0

- Initial UserPromptSubmit plugin integration.
