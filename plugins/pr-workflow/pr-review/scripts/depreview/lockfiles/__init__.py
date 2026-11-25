"""Reads any supported lockfile into a LockGraph. Each format lives in its own module with a `load(text, manifests)`."""

from pathlib import Path

from ..graph import LockGraph
from . import cargo, gomod, npm, pnpm, poetry, uvlock, yarn
from .errors import UnsupportedLockfile

LOADERS = {
    "npm": npm.load,
    "pnpm": pnpm.load,
    "yarn": yarn.load,
    "poetry": poetry.load,
    "uv": uvlock.load,
    "cargo": cargo.load,
    "gomod": gomod.load,
}

_FORMAT_BY_FILENAME = {
    "package-lock.json": "npm",
    "npm-shrinkwrap.json": "npm",
    "pnpm-lock.yaml": "pnpm",
    "yarn.lock": "yarn",
    "poetry.lock": "poetry",
    "uv.lock": "uv",
    "Cargo.lock": "cargo",
    "go.mod": "gomod",
}

__all__ = ["LOADERS", "UnsupportedLockfile", "detect_format", "load"]


def detect_format(path: Path) -> str:
    for filename, fmt in _FORMAT_BY_FILENAME.items():
        if path.name.endswith(filename):
            return fmt
    raise UnsupportedLockfile(
        f"cannot tell the lockfile format of {path.name}; pass --format ({', '.join(sorted(LOADERS))})"
    )


def load(path: Path, fmt: str, manifests: list) -> LockGraph:
    """`manifests` are package.json or pyproject.toml texts, used only by formats that do not record importers."""
    return LOADERS[fmt](path.read_text(encoding="utf-8"), manifests)
