"""Bounded subprocess bridge to the compiler-based, non-executing source helper."""
import json
from pathlib import Path
import re
import subprocess
from ..log_utils import log


class TypeScriptError(RuntimeError):
    """Source helper startup, extraction, or protocol failure."""


DEFAULT_HELPER = Path(__file__).resolve().parents[3] / "typescript-helper/dist/cli.js"


def _integer(value, minimum=0):
    return type(value) is int and value >= minimum


def _validate_outline(data, path):
    if (not isinstance(data, dict) or type(data.get("schema_version")) is not int
            or data["schema_version"] != 1 or data.get("path") != str(path)
            or not isinstance(data.get("source_hash"), str)
            or not re.fullmatch(r"[0-9a-f]{64}", data["source_hash"])
            or not isinstance(data.get("callables"), list)
            or not isinstance(data.get("diagnostics"), list)
            or not isinstance(data.get("limitations"), list)
            or not all(isinstance(x, str) for x in data["limitations"])):
        raise TypeScriptError("invalid outline schema")
    ids = set()
    for item in data["callables"]:
        if (not isinstance(item, dict) or not all(isinstance(item.get(k), str) and item[k]
                for k in ("id", "name", "signature"))
                or not _integer(item.get("start")) or not _integer(item.get("end"))
                or item["end"] <= item["start"]
                or item["id"] != f'{data["source_hash"]}:{item["start"]}:{item["end"]}'
                or item["id"] in ids or not isinstance(item.get("location"), dict)
                or not all(_integer(item["location"].get(k), 1) for k in ("line", "column"))):
            raise TypeScriptError("invalid callable schema")
        ids.add(item["id"])
    for item in data["diagnostics"]:
        if (not isinstance(item, dict) or not all(isinstance(item.get(k), str) for k in ("code", "message"))
                or not _integer(item.get("start")) or not _integer(item.get("end"))
                or item["end"] < item["start"]):
            raise TypeScriptError("invalid diagnostic schema")
    return data


def _request(path: str | Path, request: dict, *, node: str, helper: str | Path,
             timeout: float) -> dict:
    """Read an outline using argv (never a shell); requires a fresh helper build.

    Default helper location supports the source checkout. Installed applications
    must supply an explicit built helper path with its pinned dependency present.
    Target source is parsed, never imported, transpiled, or executed.
    """
    log("INFO", "extractor", "request_started", path=path, request=request,
        node=node, helper=helper, timeout=timeout)
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not 0 < timeout <= 60:
        raise ValueError("timeout must be positive and at most 60 seconds")
    helper = Path(helper)
    if not helper.is_file():
        log("ERROR", "extractor", "helper_missing", helper=helper, path=path)
        raise TypeScriptError(f"TypeScript helper build missing: {helper}; run npm run build")
    path = Path(path).resolve()
    try:
        result = subprocess.run([str(node), str(helper.resolve())],
            input=json.dumps({**request, "path": str(path)}),
            text=True, encoding="utf-8", capture_output=True, timeout=timeout, check=False)
    except FileNotFoundError as exc:
        log("ERROR", "extractor", "node_unavailable", error=exc, path=path)
        raise TypeScriptError(f"Node executable unavailable: {node}") from exc
    except subprocess.TimeoutExpired as exc:
        log("ERROR", "extractor", "helper_timeout", error=exc, path=path)
        raise TypeScriptError("TypeScript helper timed out") from exc
    except OSError as exc:
        log("ERROR", "extractor", "helper_start_failed", error=exc, path=path)
        raise TypeScriptError(f"TypeScript helper startup failed: {exc}") from exc
    log("DEBUG", "extractor", "helper_returned", path=path, action=request.get("action"),
        exit_code=result.returncode, stdout=result.stdout, stderr=result.stderr)
    if result.returncode:
        raise TypeScriptError(f"TypeScript helper failed ({result.returncode}): {result.stderr.strip()}")
    try:
        data = json.loads(result.stdout)
    except (ValueError, TypeError) as exc:
        log("ERROR", "extractor", "invalid_json", error=exc, path=path)
        raise TypeScriptError("TypeScript helper returned invalid JSON stdout") from exc
    return data


def outline(path: str | Path, *, node: str = "node", helper: str | Path = DEFAULT_HELPER,
            timeout: float = 5.0) -> dict:
    """Return a validated compiler outline; source is parsed, never executed."""
    data = _request(path, {"action": "outline"}, node=node, helper=helper, timeout=timeout)
    result = _validate_outline(data, Path(path).resolve())
    log("DEBUG", "extractor", "outline_validated", path=path, outline=result)
    return result


def extract_callable(path: str | Path, callable_id: str, *, node: str = "node",
                     helper: str | Path = DEFAULT_HELPER, timeout: float = 5.0) -> dict:
    """Return exact source; UTF-16 indexing happens entirely inside the helper."""
    data = _request(path, {"action": "extract", "id": callable_id},
                    node=node, helper=helper, timeout=timeout)
    return _validate_extraction(data, Path(path).resolve(), callable_id)


def _validate_extraction(data, path, callable_id):
    if not isinstance(data, dict):
        raise TypeScriptError("invalid extraction schema")
    candidate = data.get("callable")
    _validate_outline({**data, "callables": [candidate]}, Path(path).resolve())
    code = data.get("code")
    if (candidate["id"] != callable_id or not isinstance(code, str) or not code
            or not isinstance(data.get("display_code"), str) or not data["display_code"]):
        raise TypeScriptError("invalid extraction schema")
    try:
        length = len(code.encode("utf-16-le")) // 2
    except UnicodeError as exc:
        raise TypeScriptError("invalid extraction schema: Unicode") from exc
    if length != candidate["end"] - candidate["start"]:
        raise TypeScriptError("invalid extraction schema: source range length")
    return data


def collect_local_context(path: str | Path, callable_id: str, *, max_depth: int = 2,
                          max_dependency_chars: int = 12000, node: str = "node",
                          helper: str | Path = DEFAULT_HELPER, timeout: float = 5.0) -> dict:
    """Collect partial same-file semantic context, with intact UTF-16 source units.

    The dependency-source budget excludes selected code and JSON metadata. It is
    independent of model-input and final rendered-hook budgets.
    """
    if (not _integer(max_depth) or max_depth > 20 or not _integer(max_dependency_chars, 1)
            or max_dependency_chars > 1000000):
        raise ValueError("invalid collection limits")
    data = _request(path, {"action": "collect_local_context", "id": callable_id,
        "max_depth": max_depth, "max_dependency_chars": max_dependency_chars},
        node=node, helper=helper, timeout=timeout)
    return _validate_context(data, Path(path).resolve(), callable_id, max_depth, max_dependency_chars)


def _validate_context(data, path, callable_id, max_depth, max_dependency_chars, repository_root=None):
    _validate_extraction(data, path, callable_id)
    if (data.get("coverage") != "partial" or not isinstance(data.get("dependencies"), list)
            or not isinstance(data.get("gaps"), list) or not isinstance(data.get("collection"), dict)):
        raise TypeScriptError("invalid local context schema")
    limits = data["collection"]
    if (limits.get("max_depth") != max_depth or type(limits.get("max_depth")) is not int
            or limits.get("max_dependency_chars") != max_dependency_chars
            or type(limits.get("max_dependency_chars")) is not int
            or not _integer(limits.get("dependency_chars"))):
        raise TypeScriptError("invalid local context schema: limits")
    total, previous, ids = 0, None, set()
    hash_prefix = data["source_hash"] + ":"
    for item in data["dependencies"]:
        if (not isinstance(item, dict) or not isinstance(item.get("path"), str)
                or not isinstance(item.get("source_hash"), str)
                or not re.fullmatch(r"[0-9a-f]{64}", item["source_hash"])
                or (repository_root is None and (item["path"] != data["path"]
                    or item["source_hash"] != data["source_hash"]))
                or (repository_root is not None and not _project_path(item["path"], repository_root))
                or not _integer(item.get("start")) or not _integer(item.get("end"))
                or item["end"] <= item["start"] or not isinstance(item.get("kind"), str)
                or not item["kind"] or not isinstance(item.get("code"), str)
                or not isinstance(item.get("location"), dict)
                or not all(_integer(item["location"].get(k), 1) for k in ("line", "column"))
                or item.get("id") != f'{item["source_hash"]}:{item["start"]}:{item["end"]}'
                or (item["path"], item["id"]) in ids or not isinstance(item.get("symbol_ids"), list)
                or not item["symbol_ids"]):
            raise TypeScriptError("invalid local context schema: dependency")
        hash_prefix = item["source_hash"] + ":"
        for symbol_id in item["symbol_ids"]:
            if not isinstance(symbol_id, str) or not re.fullmatch(re.escape(hash_prefix) + r"[0-9]+:[0-9]+", symbol_id):
                raise TypeScriptError("invalid local context schema: symbol")
            start, end = map(int, symbol_id[len(hash_prefix):].split(":"))
            if end <= start:
                raise TypeScriptError("invalid local context schema: symbol")
        if item["symbol_ids"] != sorted(set(item["symbol_ids"])):
            raise TypeScriptError("invalid local context schema: symbol order")
        try:
            length = len(item["code"].encode("utf-16-le")) // 2
        except UnicodeError as exc:
            raise TypeScriptError("invalid local context schema: Unicode") from exc
        position = (item["path"], item["start"], item["end"])
        if length != item["end"] - item["start"] or (previous is not None and position <= previous):
            raise TypeScriptError("invalid local context schema: source range/order")
        previous = position
        ids.add((item["path"], item["id"]))
        total += length
    _validate_outline({**data, "callables": [], "diagnostics": data["gaps"]}, Path(path).resolve())
    if total != limits["dependency_chars"] or total > max_dependency_chars:
        raise TypeScriptError("invalid local context schema: source budget")
    return data


def _project_path(value, repository_root):
    if not isinstance(value, str):
        return False
    path = Path(value)
    return path.is_absolute() and path.resolve() == path and path.is_relative_to(repository_root)


def collect_project_context(path: str | Path, callable_id: str, *, repository_root: str | Path,
                            max_depth: int = 2, max_dependency_chars: int = 12000,
                            node: str = "node", helper: str | Path = DEFAULT_HELPER,
                            timeout: float = 5.0) -> dict:
    """Collect confined tsconfig-aware partial context; never execute project code."""
    if (not _integer(max_depth) or max_depth > 20 or not _integer(max_dependency_chars, 1)
            or max_dependency_chars > 1000000):
        raise ValueError("invalid collection limits")
    root = Path(repository_root).resolve()
    data = _request(path, {"action": "collect_project_context", "id": callable_id,
        "repository_root": str(root), "max_depth": max_depth,
        "max_dependency_chars": max_dependency_chars}, node=node, helper=helper, timeout=timeout)
    _validate_context(data, Path(path).resolve(), callable_id, max_depth, max_dependency_chars, root)
    project = data.get("project")
    if (not _project_path(data["path"], root) or not isinstance(project, dict)
            or project.get("repository_root") != str(root)
            or not isinstance(project.get("config_sources"), list)):
        raise TypeScriptError("invalid project context schema")
    config_path, config_hash = project.get("config_path"), project.get("config_hash")
    if config_path is not None and (not _project_path(config_path, root)
            or not isinstance(config_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", config_hash)):
        raise TypeScriptError("invalid project context schema: configuration")
    if config_path is None and config_hash is not None:
        raise TypeScriptError("invalid project context schema: configuration")
    config_paths = []
    for item in project["config_sources"]:
        if (not isinstance(item, dict) or not _project_path(item.get("path"), root)
                or not isinstance(item.get("source_hash"), str)
                or not re.fullmatch(r"[0-9a-f]{64}", item["source_hash"])):
            raise TypeScriptError("invalid project context schema: configuration source")
        config_paths.append(item["path"])
    if config_paths != sorted(set(config_paths)):
        raise TypeScriptError("invalid project context schema: configuration order")
    if config_path is not None and not any(item["path"] == config_path and item["source_hash"] == config_hash
                                         for item in project["config_sources"]):
        raise TypeScriptError("invalid project context schema: configuration identity")
    source_hashes = {data["path"]: data["source_hash"]}
    for dependency in data["dependencies"]:
        existing = source_hashes.setdefault(dependency["path"], dependency["source_hash"])
        if existing != dependency["source_hash"]:
            raise TypeScriptError("invalid project context schema: inconsistent source snapshot")
    for gap in data["gaps"]:
        if (not _project_path(gap.get("path"), root) or not isinstance(gap.get("source_hash"), str)
                or not re.fullmatch(r"[0-9a-f]{64}", gap["source_hash"])):
            raise TypeScriptError("invalid project context schema: gap provenance")
        existing = source_hashes.setdefault(gap["path"], gap["source_hash"])
        if existing != gap["source_hash"]:
            raise TypeScriptError("invalid project context schema: inconsistent gap snapshot")
    log("DEBUG", "extractor", "context_validated", path=path, context=data)
    return data

