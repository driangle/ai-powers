"""Unpacks a downloaded package archive as untrusted data: regular files only, nothing outside the destination.

Symlinks, hard links and device entries are skipped rather than recreated, and any path that would land outside
the destination (absolute, or climbing with `..`) is skipped too.
"""

import io
import tarfile
import zipfile
from pathlib import Path, PurePosixPath

from .registries import FIRST_COMPONENT

_MAX_TOTAL_BYTES = 800 * 1024 * 1024


def extract(archive: Path, dest: Path, strip: str) -> list:
    """Unpacks into dest and returns the skipped entry names."""
    dest.mkdir(parents=True, exist_ok=True)
    if archive.name.endswith((".whl", ".zip", ".jar")):
        members = _zip_members(archive)
    elif archive.name.endswith(".gem"):
        members = _gem_members(archive)
    else:
        members = _tar_members(tarfile.open(archive, "r:*"))
    return _write(members, dest, strip)


def _tar_members(tar: tarfile.TarFile):
    with tar:
        for member in tar:
            if member.isfile():
                yield member.name, tar.extractfile(member).read()
            elif not member.isdir():
                yield member.name, None


def _zip_members(archive: Path):
    with zipfile.ZipFile(archive) as zipped:
        for info in zipped.infolist():
            if not info.is_dir():
                # Unix mode bits live in the high 16 bits; 0o120000 marks a symlink.
                is_link = (info.external_attr >> 16) & 0o170000 == 0o120000
                yield info.filename, None if is_link else zipped.read(info)


def _gem_members(archive: Path):
    """A .gem is a plain tar holding data.tar.gz (the files) and metadata.gz (the gemspec)."""
    with tarfile.open(archive, "r:") as outer:
        for member in outer:
            if member.name == "data.tar.gz" and member.isfile():
                inner = io.BytesIO(outer.extractfile(member).read())
                yield from _tar_members(tarfile.open(fileobj=inner, mode="r:gz"))


def _write(members, dest: Path, strip: str) -> list:
    root, skipped, total = dest.resolve(), [], 0
    for name, content in members:
        relative = _stripped(name, strip)
        if content is None or relative is None:
            skipped.append(name)
            continue
        target = (root / relative).resolve()
        if root not in target.parents:
            skipped.append(name)
            continue
        total += len(content)
        if total > _MAX_TOTAL_BYTES:
            raise RuntimeError(f"archive expands beyond {_MAX_TOTAL_BYTES // (1024 * 1024)} MB")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        target.chmod(0o644)
    return skipped


def _stripped(name: str, strip: str):
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts:
        return None
    if strip == FIRST_COMPONENT:
        return str(PurePosixPath(*path.parts[1:])) if len(path.parts) > 1 else None
    if strip:
        return name[len(strip):] if name.startswith(strip) and len(name) > len(strip) else None
    return name
