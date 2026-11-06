"""Intel-only plugins on Apple Silicon: run them in an x86_64 Python under Rosetta.

A process can only load plugins built for its own architecture, and many
older plugins ship x86_64 alone. uv fetches an x86_64 CPython and the Intel
pedalboard wheel for those, and macOS runs them translated.
"""

from __future__ import annotations

import platform
import plistlib
import struct
from pathlib import Path

# Keep in step with the `vst` launcher beside vst.py.
REQUIREMENTS = ["pedalboard>=0.9.26,<0.10", "numpy>=1.26"]
INTEL_PYTHON = "cpython-3.12-macos-x86_64-none"
CPU_TYPES = {0x01000007: "x86_64", 0x0100000C: "arm64", 7: "i386"}


def executable(bundle: Path) -> Path | None:
    try:
        with open(bundle / "Contents" / "Info.plist", "rb") as handle:
            name = plistlib.load(handle).get("CFBundleExecutable")
    except (OSError, plistlib.InvalidFileException):
        name = None
    macos = bundle / "Contents" / "MacOS"
    if name and (macos / name).is_file():
        return macos / name
    files = sorted(p for p in macos.iterdir() if p.is_file()) if macos.is_dir() else []
    return files[0] if files else None


def bundle_archs(bundle: str) -> list[str]:
    """Architectures in the bundle's Mach-O binary (fat or thin); empty if unreadable."""
    binary = executable(Path(bundle))
    if binary is None:
        return []
    with open(binary, "rb") as handle:
        head = handle.read(8 + 20 * 16)
    magic = struct.unpack(">I", head[:4])[0]
    if magic in (0xCAFEBABE, 0xCAFEBABF):  # fat: big-endian table of slices
        count = struct.unpack(">I", head[4:8])[0]
        size = 20 if magic == 0xCAFEBABE else 32
        types = [struct.unpack(">i", head[8 + i * size : 12 + i * size])[0] for i in range(min(count, 16))]
    elif struct.unpack("<I", head[:4])[0] in (0xFEEDFACE, 0xFEEDFACF):
        types = [struct.unpack("<i", head[4:8])[0]]
    else:
        return []
    return sorted(CPU_TYPES.get(t, hex(t)) for t in types)


def needs_rosetta(archs: list[str]) -> bool:
    return platform.machine() == "arm64" and "arm64" not in archs and "x86_64" in archs


def intel_python() -> list[str]:
    """The command prefix that runs a Python script as x86_64 with the skill's dependencies."""
    command = ["uv", "run", "--quiet", "--no-project", "--python", INTEL_PYTHON]
    for requirement in REQUIREMENTS:
        command += ["--with", requirement]
    return command + ["python"]
