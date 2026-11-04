# System One Harness migration

The Python distribution and primary command are `system-one-harness`; `python -m cli` is the module entry point. Source packages and the standalone modules live directly beneath `src/`. The new distribution also installs the transitional `laya-context-router` command, pointing to the same CLI. It does not include the former `laya_context_router` Python package.

For an existing editable installation, capture the current revision, interpreter and plugin version before updating the checkout. Use that same interpreter to uninstall the old `laya-context-router` distribution before installing `system-one-harness` from the updated checkout. Do not have both distributions installed concurrently: they both claim the legacy console command. Build the existing TypeScript helper in the checkout; installed wheels do not bundle its Node runtime. Preserve the existing logs and session-state directory. Roll back by restoring the prior checkout revision, reinstalling the old distribution with the recorded interpreter, and restoring the matching plugin files.

The plugin still reads `LAYA_CONTEXT_ROUTER_CLI`. Its value may name either executable installed by the new distribution, and the shipped hook commands retain their quoted expansion. Existing event names, JSON keys, state/log locations and protocol output remain unchanged.

Intentional older names remain in the compatibility executable and environment key, the upstream GitHub repository URL until Sharon renames it, historical research material and previous design documents, and LAYA SDK/model identifiers. Source imports and active module invocations use the flat packages.

See the implementation design (historical material; see docs/cleanup-local-files.md) and [plugin setup](../plugins/README.md).
