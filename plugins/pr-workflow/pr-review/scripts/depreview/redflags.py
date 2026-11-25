"""Supply-chain signals in the code a release adds: process spawning, dynamic code, network calls, encoded blobs,
new native binaries. Each hit is a place to read, not a verdict: plenty of packages do these things legitimately."""

import re
from pathlib import PurePosixPath

from .treediff import DOCS, TEST

_PATTERNS = [
    ("spawns processes", re.compile(r"\bchild_process\b|\bsubprocess\b|\bos\.system\b|\bexecSync\b|\bspawnSync\b")),
    ("evaluates code", re.compile(r"\beval\s*\(|\bnew\s+Function\s*\(|\bexec\s*\(\s*compile\b")),
    ("network access", re.compile(
        r"require\(\s*['\"](?:node:)?(?:https?|net|dgram|dns|tls)['\"]\)|from\s+['\"](?:node:)?(?:https?|net|dgram|dns)['\"]"
        r"|\bfetch\s*\(\s*['\"`]https?://|\burllib\.request\b|\bsocket\.socket\b|\brequests\.(?:get|post)\s*\(\s*['\"]https?://"
    )),
    ("reads environment", re.compile(r"\bprocess\.env\b|\bos\.environ\b")),
    ("decodes base64", re.compile(r"Buffer\.from\([^)]*['\"]base64['\"]|\batob\s*\(|\bb64decode\s*\(")),
    ("long encoded literal", re.compile(r"['\"][A-Za-z0-9+/=]{200,}['\"]")),
]
_NATIVE_SUFFIXES = {".node", ".so", ".dylib", ".dll", ".exe", ".wasm", ".bin"}
_MAX_HITS = 60


def scan(changes: list) -> list:
    hits = []
    for change in changes:
        if change.category in (TEST, DOCS):
            continue
        if change.status == "added" and PurePosixPath(change.path).suffix in _NATIVE_SUFFIXES:
            hits.append({"path": change.path, "line": None, "signal": "new native binary", "text": ""})
        for number, text in change.added_lines:
            for label, pattern in _PATTERNS:
                if pattern.search(text):
                    hits.append({"path": change.path, "line": number, "signal": label, "text": text.strip()[:160]})
    return hits[:_MAX_HITS]
