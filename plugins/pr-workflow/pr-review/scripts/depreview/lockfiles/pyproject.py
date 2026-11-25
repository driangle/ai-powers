"""Direct dependencies declared in a pyproject.toml (Poetry sections and PEP 621 / PEP 735 tables)."""

import re
import tomllib

from ..graph import DEV, PROD

_REQUIREMENT_NAME = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")


def normalize(name: str) -> str:
    """PEP 503 name normalization, so `Typing_Extensions` and `typing-extensions` are one package."""
    return re.sub(r"[-_.]+", "-", name).lower()


def direct_dependencies(text: str) -> list:
    """Returns (normalized name, PROD | DEV) pairs."""
    data = tomllib.loads(text)
    found = []
    poetry = data.get("tool", {}).get("poetry", {})
    found += [(name, PROD) for name in poetry.get("dependencies", {}) if name.lower() != "python"]
    found += [(name, DEV) for name in poetry.get("dev-dependencies", {})]
    for group, body in poetry.get("group", {}).items():
        found += [(name, PROD if group == "main" else DEV) for name in body.get("dependencies", {})]
    project = data.get("project", {})
    found += [(_requirement_name(req), PROD) for req in project.get("dependencies", [])]
    for requirements in project.get("optional-dependencies", {}).values():
        found += [(_requirement_name(req), PROD) for req in requirements]
    for requirements in data.get("dependency-groups", {}).values():
        found += [(_requirement_name(req), DEV) for req in requirements if isinstance(req, str)]
    return [(normalize(name), scope) for name, scope in found if name]


def _requirement_name(requirement: str) -> str:
    match = _REQUIREMENT_NAME.match(requirement)
    return match.group(1) if match else ""
