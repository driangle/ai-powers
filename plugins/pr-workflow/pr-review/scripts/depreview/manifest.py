"""Field-level changes in a package's own manifest: the parts that break consumers without touching their code
(entry points, module format, engines, peer requirements) and install-time hooks."""

import json
from email.parser import HeaderParser
from pathlib import Path
from typing import Optional

_NPM_FIELDS = (
    "type", "main", "module", "browser", "types", "typings", "exports", "imports", "bin", "engines", "os", "cpu",
    "sideEffects", "dependencies", "peerDependencies", "peerDependenciesMeta", "optionalDependencies",
)
_NPM_INSTALL_HOOKS = ("preinstall", "install", "postinstall", "prepare")


def changes(ecosystem: str, old: Path, new: Path) -> dict:
    if ecosystem == "npm":
        return _npm(_read_json(old / "package.json"), _read_json(new / "package.json"))
    if ecosystem == "pypi":
        return _python(_python_metadata(old), _python_metadata(new))
    return {}


def npm_repository(root: Path):
    return (_read_json(root / "package.json") or {}).get("repository")


def _npm(old: Optional[dict], new: Optional[dict]) -> dict:
    if old is None or new is None:
        return {}
    found = {}
    for name in _NPM_FIELDS:
        before, after = old.get(name), new.get(name)
        if before == after:
            continue
        if isinstance(before, dict) and isinstance(after, dict) and name.endswith(("ependencies", "engines")):
            found[name] = _map_diff(before, after)
        else:
            found[name] = {"from": before, "to": after}
    hooks = {h: new["scripts"][h] for h in _NPM_INSTALL_HOOKS if h in (new.get("scripts") or {})}
    old_hooks = {h: old["scripts"][h] for h in _NPM_INSTALL_HOOKS if h in (old.get("scripts") or {})}
    if hooks or old_hooks:
        found["install_hooks"] = {"from": old_hooks, "to": hooks}
    return found


def _python(old: Optional[dict], new: Optional[dict]) -> dict:
    if old is None or new is None:
        return {}
    found = {}
    if old["requires_python"] != new["requires_python"]:
        found["Requires-Python"] = {"from": old["requires_python"], "to": new["requires_python"]}
    added, removed = sorted(new["requires"] - old["requires"]), sorted(old["requires"] - new["requires"])
    if added or removed:
        found["Requires-Dist"] = {"added": added, "removed": removed}
    return found


def _map_diff(before: dict, after: dict) -> dict:
    return {
        "added": {k: after[k] for k in after.keys() - before.keys()},
        "removed": {k: before[k] for k in before.keys() - after.keys()},
        "changed": {k: {"from": before[k], "to": after[k]} for k in before.keys() & after.keys() if before[k] != after[k]},
    }


def _python_metadata(root: Path) -> Optional[dict]:
    candidates = sorted(root.glob("*.dist-info/METADATA")) or sorted(root.glob("PKG-INFO"))
    if not candidates:
        return None
    headers = HeaderParser().parsestr(candidates[0].read_text(encoding="utf-8", errors="replace"))
    return {"requires_python": headers.get("Requires-Python"), "requires": set(headers.get_all("Requires-Dist") or [])}


def _read_json(path: Path) -> Optional[dict]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
