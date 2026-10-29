"""Bounded subprocess bridge to the compiler-based, non-executing source helper."""
import json
from pathlib import Path
import re
import subprocess


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


def outline(path: str | Path, *, node: str = "node", helper: str | Path = DEFAULT_HELPER,
            timeout: float = 5.0) -> dict:
    """Read an outline using argv (never a shell); requires a fresh helper build.

    Default helper location supports the source checkout. Installed applications
    must supply an explicit built helper path with its pinned dependency present.
    Target source is parsed, never imported, transpiled, or executed.
    """
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not 0 < timeout <= 60:
        raise ValueError("timeout must be positive and at most 60 seconds")
    helper = Path(helper)
    if not helper.is_file():
        raise TypeScriptError(f"TypeScript helper build missing: {helper}; run npm run build")
    path = Path(path).resolve()
    try:
        result = subprocess.run([str(node), str(helper.resolve())],
            input=json.dumps({"action": "outline", "path": str(path)}),
            text=True, encoding="utf-8", capture_output=True, timeout=timeout, check=False)
    except FileNotFoundError as exc:
        raise TypeScriptError(f"Node executable unavailable: {node}") from exc
    except subprocess.TimeoutExpired as exc:
        raise TypeScriptError("TypeScript helper timed out") from exc
    except OSError as exc:
        raise TypeScriptError(f"TypeScript helper startup failed: {exc}") from exc
    if result.returncode:
        raise TypeScriptError(f"TypeScript helper failed ({result.returncode}): {result.stderr.strip()}")
    try:
        data = json.loads(result.stdout)
    except (ValueError, TypeError) as exc:
        raise TypeScriptError("TypeScript helper returned invalid JSON stdout") from exc
    return _validate_outline(data, path)
