# Upgrading a local editable installation
Run these commands from the Laya Context Router repository root using the same Python interpreter you already use. Finish installation and the helper build before invoking the next real hook, since editable Python imports see pulled changes immediately.

```sh
git pull --ff-only
"/absolute/path/to/your/python" -m pip install -e .
npm --prefix typescript-helper ci
npm --prefix typescript-helper run build
laya-context-router doctor
printf '%s' '{"hook_event_name":"UserPromptSubmit","session_id":"manual-build-check","prompt":"hello"}' | laya-context-router hook --hook UserPromptSubmit --observe-only
laya-context-router logs --last 5
```

The observation command should print no response, and the log should contain `manual-build-check` and `observed`. The existing executable path, PATH setting, Claude setting `LAYA_CONTEXT_ROUTER_CLI`, and log location should remain the same when using the same Python environment. Test one real TypeScript request with your existing local model configuration once observation passes.

The new generated paths are `build/python/laya_context_router.egg-info` and `build/typescript`. After the upgrade passes, you may manually remove the old generated `src/laya_context_router.egg-info` and `typescript-helper/dist` directories if they exist. Check each before deleting it. Do not remove logs, Python environments, `node_modules`, or source files. If you remove `build/`, repeat the install and helper build.

For rollback, return to the previous commit on a clean checkout or branch, reinstall with the same Python, and rebuild its TypeScript helper. Keep your logs and local changes. This project builds the TypeScript helper in the checkout; it does not bundle it into the Python wheel.
